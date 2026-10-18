"""Authorization policy for the DevConsole HTTP surface (roadmap phase 0C).

This module is the **single place** where the question *"may this caller perform
this operation?"* is answered.  It exists because the pre-0C code answered it in
scattered, mutually inconsistent guards — one of which (BR-01) emitted a 403 and
then went on to execute the protected action anyway.

Model
-----
Two axes are kept deliberately separate:

``Role`` (who)
    ``ANONYMOUS`` < ``VIEWER`` < ``DEV`` < ``ADMIN``.  ``ADMIN`` requires a
    validated session token; it can never be obtained by declaring a header.

``ClientTrust`` (which client)
    Loopback origin, allowed ``Host`` and — when
    ``SISPER_LOCAL_TOKEN_REQUIRED=1`` — a valid ephemeral local token.

Both must pass.  Every decision is **fail-closed**: an unrecognised role, an
unexpected exception, a missing ``Host`` or a malformed cookie all resolve to
the least privilege available, never to the most.

Threat model addressed
----------------------
* **BR-01** — a denial that does not stop execution.
* **Origin/CSRF** — a page the developer visits driving the orchestrator.
* **DNS rebinding** — a hostile name resolving to ``127.0.0.1``.
* **Cross-origin data theft** — ``Access-Control-Allow-Origin: *`` previously
  let any web page read ``/api/env/get`` (service secrets) from this machine.
* **Role spoofing** — ``X-Auth-Role: admin`` with no session.
"""

from __future__ import annotations

import enum
import os
import socket
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from devconsole import auth
from devconsole import local_trust


class Role(str, enum.Enum):
    """Effective caller role, ordered from least to most privileged."""

    ANONYMOUS = "anonymous"
    VIEWER = "viewer"
    DEV = "dev"
    ADMIN = "admin"

    @property
    def rank(self) -> int:
        return {"anonymous": 0, "viewer": 1, "dev": 2, "admin": 3}[self.value]

    def at_least(self, other: "Role") -> bool:
        return self.rank >= other.rank


#: Roles a client may claim about itself *without* a credential.  Declaring one
#: of these can only reduce privilege relative to the default, so honouring it
#: is safe.  ``admin`` is deliberately absent: a role claim is never authority.
_SELF_DECLARABLE = {
    "viewer": Role.VIEWER,
    "dev": Role.DEV,
}

#: Default role for a caller that presents nothing (pre-0C behaviour, required
#: for UI compatibility: the bundled dashboard operates as an unauthenticated
#: ``dev``).
DEFAULT_ROLE = Role.DEV


# --------------------------------------------------------------------------- #
# the policy tables — single source of truth
# --------------------------------------------------------------------------- #

#: POST routes that require a validated ADMIN session.
#: Mirrors the pre-0C ``admin_paths`` tuple exactly; no endpoint was added or
#: removed, so no UI feature changes privilege level in this phase.
ADMIN_PATHS: frozenset[str] = frozenset({
    "/api/config_git/push",
    "/api/environment/switch",
    "/api/deployments/build",
    "/api/deployments/update_version",
    "/api/k8s/restart",
    "/api/k8s/rollout_all",
    "/api/k8s/restart_multiple",
    "/api/k8s/deploy",
    "/api/k8s/deploy_manifest",
})

#: ``/api/action`` sub-actions that require a validated ADMIN session.
ADMIN_ACTIONS: frozenset[str] = frozenset({
    "env-local", "env-intranet", "env-local-restart", "env-intranet-restart",
    "bitacora-local", "bitacora-intranet", "docker-keycloak", "podman-container",
})

#: Containers a non-admin may still start/stop (operational exemption present
#: in the pre-0C policy and relied upon by the infra panel).
INFRA_EXEMPT_CONTAINERS: frozenset[str] = frozenset({"keydb", "onlyoffice-local"})

#: Routes usable with no session and no role, but still subject to client-trust
#: checks.  Authentication and logout are the only such routes.
PUBLIC_PATHS: frozenset[str] = frozenset({
    "/api/auth/verify_pin",
    "/api/auth/logout",
})

#: POST routes that mutate state or trigger privileged work.  Everything not
#: listed here is either public or read-only.
MUTATING_PATHS: frozenset[str] = frozenset({
    "/api/action",
    "/api/secrets/buscar",
    "/api/secrets/guardar",
    "/api/k8s/deploy_manifest",
    "/api/auth/verify_pin",
    "/api/auth/logout",
    "/api/config_git/pull",
    "/api/config_git/push",
    "/api/deployments/build",
    "/api/deployments/update_version",
    "/api/env/save",
    "/api/environment/switch",
    "/api/git/fetch_all",
    "/api/k8s/deploy",
    "/api/k8s/restart",
    "/api/k8s/restart_multiple",
    "/api/k8s/rollout_all",
    "/api/k8s/theme",
    "/api/onlyoffice/sync_env",
    "/api/root_dir/set",
    "/api/telemetry/heartbeat",
    "/api/telemetry/mirror_control",
    "/api/telemetry/mirror_stream",
    "/api/tilix/import",
    "/api/tilix/launch",
    "/api/tilix/launch_auxiliary",
    "/api/tilix/launch_selected",
    "/api/tilix/launch_selected_services",
    "/api/tilix/launch_selected_auxiliary",
    "/api/tilix/attach_viewer",
})



#: GET routes with observable side effects (they contact the network or the
#: cluster).  They stay readable without a session for UI compatibility, but
#: their `Origin` is validated so a hostile page cannot trigger them.
SIDE_EFFECTING_GETS: frozenset[str] = frozenset({
    "/api/git/fetch_all",
})

#: Loopback host names accepted in the ``Host`` header.
LOOPBACK_HOSTS: frozenset[str] = frozenset({
    "127.0.0.1", "localhost", "::1", "[::1]", "127.0.0.2",
})


# --------------------------------------------------------------------------- #
# origin / host
# --------------------------------------------------------------------------- #

def _extra_allowed_origins() -> set[str]:
    """Explicit operator-supplied extra origins (comma separated)."""
    raw = os.environ.get("SISPER_ALLOWED_ORIGINS", "")
    return {o.strip().rstrip("/") for o in raw.split(",") if o.strip()}


#: Nombres e IP propias del equipo, calculados una vez por proceso.
_LOCAL_HOSTNAMES: set[str] | None = None


def _local_hostnames() -> set[str]:
    """Nombres e IP por los que se puede alcanzar este equipo.

    El frontend puede servirse por una IP de LAN (p. ej. ``172.23.22.38:3000``),
    así que su ``Origin`` no es ``localhost``: si no se contemplan las propias
    direcciones del equipo, el navegador bloquea la telemetría por CORS.
    """
    global _LOCAL_HOSTNAMES
    if _LOCAL_HOSTNAMES is not None:
        return _LOCAL_HOSTNAMES
    nombres: set[str] = {"localhost", "127.0.0.1", "[::1]"}
    try:
        host = socket.gethostname()
        if host:
            nombres.add(host)
            nombres.add(host.split(".")[0])
        for info in socket.getaddrinfo(host, None):
            ip = str(info[4][0])
            if ip:
                nombres.add(ip)
    except Exception:
        pass
    _LOCAL_HOSTNAMES = nombres
    return nombres


def _frontend_origins() -> set[str]:
    """Orígenes de los **frontends del laboratorio** (los que el panel lanza).

    El tracker de telemetría / Espejo Visual corre dentro del frontend, en su
    propio puerto, así que su ``Origin`` no es el del panel (9099).  Sin estos
    orígenes el navegador bloquea la petición por CORS —era lo que impedía que el
    espejo mostrara nada—.  Se toman los puertos **configurados** de los
    frontends, no «cualquier localhost»: un puerto desconocido sigue rechazado.
    """
    origenes: set[str] = set()
    try:
        import devconsole.config as dcfg
        for svc in getattr(dcfg, "SERVICES_FRONTEND", []) or []:
            puerto = svc.get("port")
            if not puerto:
                continue
            for host in _local_hostnames():
                origenes.add(f"http://{host}:{int(puerto)}")
    except Exception:
        pass
    return origenes


def allowed_origins(port: int | None = None) -> set[str]:
    """Origins permitted to drive this DevConsole instance.

    Only loopback origins, plus anything the operator adds through
    ``SISPER_ALLOWED_ORIGINS`` (needed for LAN mode).  ``*`` is never allowed.
    """
    if port is None:
        try:
            import devconsole.config as dcfg
            port = dcfg.PORT
        except Exception:
            port = 9099
    origins = {
        f"http://127.0.0.1:{port}",
        f"http://localhost:{port}",
        f"http://[::1]:{port}",
    }
    origins |= _frontend_origins()
    origins |= _extra_allowed_origins()
    return origins


def is_origin_allowed(origin: str | None, port: int | None = None) -> bool:
    """Is ``origin`` in the allowlist?

    An **absent** origin is treated as allowed (see :func:`resolve_caller`): only
    browsers send ``Origin``, and blocking its absence would break ``curl``,
    CLI tooling and the future Electron main process.  An origin that *is*
    present must be allowed — that is what defeats a hostile web page.
    """
    if origin is None or origin == "":
        return True
    if origin == "null":
        # Sandboxed iframes / file:// report "null".  Not allowed by default;
        # an operator can opt in explicitly via SISPER_ALLOWED_ORIGINS.
        return "null" in _extra_allowed_origins()
    return origin.rstrip("/") in allowed_origins(port)


def is_loopback_host(host_header: str | None, port: int | None = None) -> bool:
    """Validate the ``Host`` header.

    When DevConsole is bound to loopback, only loopback host names are
    accepted.  This is what makes DNS rebinding ineffective: a hostile name that
    resolves to ``127.0.0.1`` still arrives with ``Host: evil.example`` and is
    refused.

    When the operator has explicitly bound to a non-loopback address, the check
    is relaxed (any Host), because the set of legitimate names is then unknown.
    """
    if not host_header:
        return False
    if _bound_to_loopback():
        hostname = host_header.rsplit(":", 1)[0] if ":" in host_header else host_header
        if host_header.startswith("["):
            hostname = host_header.split("]")[0] + "]"
        return hostname in LOOPBACK_HOSTS
    return True


def _bound_to_loopback() -> bool:
    try:
        import devconsole.config as dcfg
        return bool(getattr(dcfg, "HOST_IS_LOOPBACK", True))
    except Exception:
        return True


# --------------------------------------------------------------------------- #
# caller context
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class CallerContext:
    """Everything the policy needs to know about one request."""

    role: Role
    role_header: str | None
    admin_session_valid: bool
    local_token_valid: bool
    local_token_required: bool
    origin: str | None
    origin_allowed: bool
    host_header: str | None
    host_allowed: bool
    client_ip: str | None
    notes: tuple[str, ...] = ()

    @property
    def authenticated(self) -> bool:
        return self.admin_session_valid

    @property
    def is_admin(self) -> bool:
        return self.role is Role.ADMIN

    @property
    def role_spoof_attempted(self) -> bool:
        """Claimed ``admin`` without a session, or claimed an unknown role."""
        if not self.role_header:
            return False
        claimed = self.role_header.strip().lower()
        if claimed == "admin" and not self.admin_session_valid:
            return True
        return claimed not in _SELF_DECLARABLE and claimed != "admin"

    def to_dict(self) -> dict:
        """Redacted view for logs: never includes tokens or cookies."""
        return {
            "role": self.role.value,
            "role_header": self.role_header,
            "admin_session_valid": self.admin_session_valid,
            "local_token_valid": self.local_token_valid,
            "local_token_required": self.local_token_required,
            "origin": self.origin,
            "origin_allowed": self.origin_allowed,
            "host_allowed": self.host_allowed,
            "client_ip": self.client_ip,
            "role_spoof_attempted": self.role_spoof_attempted,
            "notes": list(self.notes),
        }


def resolve_caller(headers, client_address=None, *, port: int | None = None) -> CallerContext:
    """Derive the effective role and client trust for one request.

    Failure of any individual check degrades privilege; it never raises and
    never grants.
    """
    notes: list[str] = []

    try:
        role_header = headers.get("X-Auth-Role")
    except Exception:
        role_header = None
        notes.append("role_header_unreadable")

    # -- role: only a validated session can produce ADMIN ------------------ #
    try:
        session_token = auth.admin_token_from(headers)
        admin_valid = bool(session_token) and auth.is_valid_admin_token(session_token)
    except Exception:
        admin_valid = False
        notes.append("session_check_failed")

    claimed = (role_header or "").strip().lower()
    if admin_valid:
        role = Role.ADMIN
    elif claimed in _SELF_DECLARABLE:
        role = _SELF_DECLARABLE[claimed]
    elif claimed == "":
        role = DEFAULT_ROLE
    elif claimed == "admin":
        # Claimed admin without a session: explicitly refused, and recorded.
        role = DEFAULT_ROLE
        notes.append("role_claimed_admin_without_session")
    else:
        # Unrecognised role claim → least privilege, never the default.
        role = Role.ANONYMOUS
        notes.append(f"unrecognised_role_claim:{claimed}")

    # -- client trust ------------------------------------------------------ #
    try:
        origin = headers.get("Origin")
    except Exception:
        origin = None
    origin_ok = is_origin_allowed(origin, port)
    if not origin_ok:
        notes.append("origin_not_allowed")

    try:
        host_header = headers.get("Host")
    except Exception:
        host_header = None
    host_ok = is_loopback_host(host_header, port)
    if not host_ok:
        notes.append("host_not_allowed")

    required = local_trust.token_required()
    try:
        token_ok, token_reason = local_trust.enforce_request_token(headers.get)
    except Exception:
        token_ok, token_reason = False, "local_token_check_failed"
    if required and not token_ok:
        notes.append(f"local_token:{token_reason}")
        # A caller that cannot prove local trust is not even a developer.
        if role.rank > Role.ANONYMOUS.rank:
            role = Role.ANONYMOUS
            notes.append("downgraded_to_anonymous")

    client_ip = None
    if isinstance(client_address, (tuple, list)) and client_address:
        client_ip = client_address[0]

    return CallerContext(
        role=role,
        role_header=role_header,
        admin_session_valid=admin_valid,
        local_token_valid=token_ok,
        local_token_required=required,
        origin=origin,
        origin_allowed=origin_ok,
        host_header=host_header,
        host_allowed=host_ok,
        client_ip=client_ip,
        notes=tuple(notes),
    )


# --------------------------------------------------------------------------- #
# decisions
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class AuthzDecision:
    """Outcome of a policy check.  ``allowed=False`` always carries a status."""

    allowed: bool
    status: int = 200
    message: str = ""
    reason: str = "allowed"
    requires_admin: bool = False
    payload: dict = field(default_factory=dict)

    def as_response(self) -> dict:
        body = {"success": False, "message": self.message}
        if self.requires_admin:
            body["requires_admin"] = True
        body.update(self.payload)
        return body


def _deny(status: int, message: str, reason: str, *, requires_admin: bool = False) -> AuthzDecision:
    return AuthzDecision(allowed=False, status=status, message=message,
                         reason=reason, requires_admin=requires_admin)


def require_admin(ctx: CallerContext) -> AuthzDecision:
    """Admin session required.  Anonymous, viewer and dev are all refused."""
    if ctx.role is Role.ADMIN:
        return AuthzDecision(allowed=True)
    if ctx.role is Role.ANONYMOUS:
        return _deny(401, "Autenticación requerida: esta acción necesita una "
                          "sesión de Administrador / DevOps válida.",
                     "anonymous_refused", requires_admin=True)
    return _deny(403,
                 "Acción protegida: Requiere rol Administrador / DevOps con PIN válido.",
                 f"{ctx.role.value}_refused", requires_admin=True)


def require_role(ctx: CallerContext, minimum: Role) -> AuthzDecision:
    """Generic minimum-role gate."""
    if ctx.role.at_least(minimum):
        return AuthzDecision(allowed=True)
    if ctx.role is Role.ANONYMOUS:
        return _deny(401, "Autenticación requerida para esta operación.",
                     "anonymous_refused")
    return _deny(403, "Acción denegada: El rol Soporte / QA tiene permisos de solo lectura.",
                 f"{ctx.role.value}_below_{minimum.value}")


def require_mutating(ctx: CallerContext) -> AuthzDecision:
    """Gate applied to every state-changing request.

    Requires DEV-or-better, an allowed ``Origin`` (when the browser sends one),
    a valid ``Host``, and — when enforcement is on — a valid local token.
    """
    if not ctx.host_allowed:
        return _deny(403, "Solicitud rechazada: cabecera Host no permitida.",
                     "host_not_allowed")
    if not ctx.origin_allowed:
        return _deny(403, "Solicitud rechazada: origen no autorizado.",
                     "origin_not_allowed")
    if ctx.local_token_required and not ctx.local_token_valid:
        return _deny(401, "Solicitud rechazada: falta el token de confianza local.",
                     "local_token_missing")
    if not ctx.role.at_least(Role.DEV):
        return _deny(403, "Acción denegada: El rol Soporte / QA tiene permisos de solo lectura.",
                     f"{ctx.role.value}_cannot_mutate")
    return AuthzDecision(allowed=True)


def require_client_trust(ctx: CallerContext) -> AuthzDecision:
    """Gate applied to read-only requests that still have observable effects."""
    if not ctx.host_allowed:
        return _deny(403, "Solicitud rechazada: cabecera Host no permitida.",
                     "host_not_allowed")
    if not ctx.origin_allowed:
        return _deny(403, "Solicitud rechazada: origen no autorizado.",
                     "origin_not_allowed")
    return AuthzDecision(allowed=True)


def policy_for_post(path: str, payload: dict | None = None) -> tuple[Role, bool]:
    """Return ``(minimum_role, needs_mutating_gate)`` for a POST route.

    Keeping this mapping here — rather than inline in the request handler — is
    what makes the policy auditable and testable in isolation.
    """
    if path in PUBLIC_PATHS:
        return Role.ANONYMOUS, True
    if path in ADMIN_PATHS:
        return Role.ADMIN, True
    if path == "/api/action":
        action = (payload or {}).get("action")
        container = (payload or {}).get("container")
        if action in ADMIN_ACTIONS:
            # Operational exemption preserved from the pre-0C policy.
            if action == "podman-container" and container in INFRA_EXEMPT_CONTAINERS:
                return Role.DEV, True
            return Role.ADMIN, True
        return Role.DEV, True
    return Role.DEV, True


def authorize_post(path: str, ctx: CallerContext, payload: dict | None = None) -> AuthzDecision:
    """Full policy decision for a POST route: client trust, then role."""
    trust = require_mutating(ctx)
    if not trust.allowed:
        return trust
    minimum, _ = policy_for_post(path, payload)
    if minimum is Role.ADMIN:
        return require_admin(ctx)
    if minimum is Role.ANONYMOUS:
        return AuthzDecision(allowed=True)
    return require_role(ctx, minimum)


def describe_policy() -> dict:
    """Machine-readable dump of the policy tables (used by tests and docs)."""
    return {
        "admin_paths": sorted(ADMIN_PATHS),
        "admin_actions": sorted(ADMIN_ACTIONS),
        "infra_exempt_containers": sorted(INFRA_EXEMPT_CONTAINERS),
        "public_paths": sorted(PUBLIC_PATHS),
        "mutating_paths": sorted(MUTATING_PATHS),
        "side_effecting_gets": sorted(SIDE_EFFECTING_GETS),
        "loopback_hosts": sorted(LOOPBACK_HOSTS),
    }
