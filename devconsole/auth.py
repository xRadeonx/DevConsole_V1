# devconsole/auth.py
"""User authentication: PIN → admin session token (roadmap phase 0C).

Two hardening changes over the pre-0C version:

1. **The session store moved out of ``/tmp``.**  ``/tmp/.sisper_admin_sessions.json``
   was created with the default umask (0644), i.e. **readable by every local
   user**, who could then replay an admin token found in it.  Sessions now live
   in the per-user runtime directory with ``0600``.
2. **Sessions can be carried by a cookie.**  The bundled UI performs several
   mutating calls with a bare ``fetch`` and no auth headers; an
   ``HttpOnly; SameSite=Strict`` cookie lets those same-origin requests carry
   the admin session automatically.  This is what allows
   :data:`devconsole.security.ADMIN_PATHS` to be enforced without editing the
   334 KB ``dashboard.js``.

This module answers *who is calling*.  Whether a given operation is permitted
is decided in :mod:`devconsole.security`; client trust is in
:mod:`devconsole.local_trust`.
"""

import json
import os
import secrets
import time
import uuid
from pathlib import Path

from devconsole.local_trust import runtime_dir

ADMIN_PIN = os.environ.get("SISPER_ADMIN_PIN", "sisper2026")

#: Name of the admin-session cookie.
ADMIN_COOKIE_NAME = "sisper_admin_session"

#: Session lifetime (unchanged from the pre-0C contract).
SESSION_TTL_HOURS = 24

#: File mode for the session store.
_FILE_MODE = 0o600


def _sessions_file() -> Path:
    """Location of the admin session store.

    ``SISPER_ADMIN_SESSIONS_FILE`` overrides it (tests, and operators who want
    to relocate the store).  Defaults to the per-user runtime directory, never
    ``/tmp``.
    """
    override = os.environ.get("SISPER_ADMIN_SESSIONS_FILE")
    if override:
        return Path(override).expanduser()
    return runtime_dir() / "admin_sessions.json"


#: Kept as a module-level name for backwards compatibility with existing
#: imports; it is now a per-user ``0600`` path rather than ``/tmp``.
ADMIN_SESSIONS_FILE = _sessions_file()


def _load_admin_sessions() -> dict[str, float]:
    path = _sessions_file()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        now = time.time()
        return {k: float(v) for k, v in data.items()
                if (now - float(v)) < (SESSION_TTL_HOURS * 3600)}
    except Exception:
        return {}


def _save_admin_sessions(sessions: dict[str, float]):
    path = _sessions_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(path.parent, 0o700)
        except OSError:
            pass
        # Create restrictively *before* writing, so the tokens are never
        # briefly world-readable.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, _FILE_MODE)
        try:
            os.write(fd, json.dumps(sessions).encode("utf-8"))
        finally:
            os.close(fd)
        os.chmod(path, _FILE_MODE)
    except Exception:
        pass


def verify_pin(pin: str, role: str = "admin") -> tuple[bool, str]:
    """Valida el PIN del rol indicado y, **sólo para admin**, emite token.

    El PIN vive hasheado (scrypt) en ``devconsole.pins``; aquí no hay ninguna
    clave en claro.  Desarrollador entra sin token elevado: puede operar pero no
    ejecutar acciones de administrador.
    """
    from devconsole import pins

    if not pins.verify(role, pin):
        return False, ""
    if role != "admin":
        return True, ""
    token = str(uuid.uuid4())
    sessions = _load_admin_sessions()
    sessions[token] = time.time()
    _save_admin_sessions(sessions)
    return True, token


def verify_admin_pin(pin: str) -> tuple[bool, str]:
    """Compatibilidad: equivale a ``verify_pin(pin, "admin")``."""
    return verify_pin(pin, "admin")


def is_valid_admin_token(token: str) -> bool:
    if not token:
        return False
    sessions = _load_admin_sessions()
    return token in sessions


def invalidate_admin_token(token: str) -> bool:
    """Drop one session.  Returns ``True`` if it existed."""
    if not token:
        return False
    sessions = _load_admin_sessions()
    if token in sessions:
        sessions.pop(token, None)
        _save_admin_sessions(sessions)
        return True
    return False


# --------------------------------------------------------------------------- #
# cookie helpers
# --------------------------------------------------------------------------- #

def cookie_value(cookie_header: str | None, name: str) -> str | None:
    """Extract ``name`` from a raw ``Cookie`` header."""
    if not cookie_header or not name:
        return None
    for part in cookie_header.split(";"):
        key, _, value = part.strip().partition("=")
        if key == name:
            return value or None
    return None


def build_admin_cookie(token: str) -> str:
    """``Set-Cookie`` value granting the admin session to same-origin requests.

    ``HttpOnly`` keeps the token away from page scripts; ``SameSite=Strict``
    guarantees a cross-origin page can never cause the browser to attach it.
    """
    return (
        f"{ADMIN_COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Strict; "
        f"Max-Age={SESSION_TTL_HOURS * 3600}"
    )


def build_admin_cookie_clear() -> str:
    """``Set-Cookie`` value removing the admin session."""
    return f"{ADMIN_COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0"


def admin_token_from(headers) -> str:
    """Return the admin session token presented by the caller, or ``""``.

    Accepts either the ``X-Auth-Token`` header (programmatic clients) or the
    admin cookie (bare same-origin browser requests).
    """
    try:
        header_token = (headers.get("X-Auth-Token") or "").strip()
    except Exception:
        header_token = ""
    if header_token:
        return header_token
    try:
        return (cookie_value(headers.get("Cookie"), ADMIN_COOKIE_NAME) or "").strip()
    except Exception:
        return ""


# --------------------------------------------------------------------------- #
# back-compat predicates
# --------------------------------------------------------------------------- #

def is_admin_request(headers) -> bool:
    """Is the caller a validated administrator?

    The **session token is the credential**.  ``X-Auth-Role: admin`` on its own
    confers nothing: a role claim without a live session is never accepted.
    """
    return is_valid_admin_token(admin_token_from(headers))


def is_viewer_request(headers) -> bool:
    """Did the caller self-declare the read-only role?

    Self-declaration is honoured because it can only ever *reduce* privilege
    below the default.  It is never a source of authority.
    """
    try:
        return (headers.get("X-Auth-Role", "dev") or "dev").lower() == "viewer"
    except Exception:
        return False
