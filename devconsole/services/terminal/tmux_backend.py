# devconsole/services/terminal/tmux_backend.py
"""tmux-backed implementation of the terminal backend contract.

The architectural change of Phase 3 is *who owns the process*:

Before::

    Tilix → shell/panel → tilix_runner.sh → service

After::

    tmux  → tilix_runner.sh → service
    Tilix → tmux attach     → the same service (viewer only)

``tilix_runner.sh`` is reused **verbatim** as the supervisor: no logic was copied
into Python, no loop, sentinel, stagger or service command was changed.  What
changed is the PTY host underneath it.

States, and why they exist
--------------------------
Deciding "do I start this service?" needs more than "is the port open".  The six
states below are the minimum needed to guarantee that Phase 3 never creates a
duplicate and never touches a process it does not own:

``STOPPED``
    Nothing listening, no session, no identified process → safe to create.
``TMUX_RUNNING``
    A session exists whose metadata proves DevConsole ownership → already ours.
``LEGACY_RUNNING``
    No session, but a verified DevConsole-owned process is listening on the
    configured port (the pre-Phase-3 world) → **do not create a duplicate**.
``EXTERNAL_CONFLICT``
    Something we cannot prove we own holds the port, or a session name is taken
    by a session whose metadata is not ours → **never touch it**.
``TMUX_STALE``
    Our session exists but the service is not actually serving → restartable.
``AMBIGUOUS``
    Process identity could not choose a single candidate → **fail closed**.

Only ``STOPPED`` and ``TMUX_STALE`` ever lead to a tmux write.
"""

from __future__ import annotations

import enum
import os
import subprocess
from dataclasses import dataclass, field

from pathlib import Path
from typing import Any, Sequence

from devconsole.config import env_keys
from devconsole.services.runtime import ProcessIdentityResolver
from devconsole.services.terminal.base import TerminalBackend
from devconsole.services.terminal.tilix_backend import scan_tilix_sessions
from devconsole.services.terminal.tmux_layout import (
    AUX_COMMANDS,
    BACKEND_PORTS,
    FRONTEND_PORTS,
    LAYOUT_FILES,
    META_AUX_TYPE,
    META_SERVICE,
    RUNNER_SCRIPT,
    SESSION_PREFIX,
    build_metadata,
    classify_directory,
    extract_layout_services,
    service_to_tmux_session_name,
    validate_metadata,
)
from devconsole.services.terminal.tmux_runtime import (
    TmuxError,
    TmuxRuntime,
    TmuxSession,
    default_runtime,
)

#: Environment variable carrying the target environment into the pane.
ENV_VAR_ENVIRONMENT = "SISPER_ENV"


class RuntimeState(str, enum.Enum):
    """Classification of one service with respect to process ownership."""

    STOPPED = "STOPPED"
    TMUX_RUNNING = "TMUX_RUNNING"
    LEGACY_RUNNING = "LEGACY_RUNNING"
    EXTERNAL_CONFLICT = "EXTERNAL_CONFLICT"
    TMUX_STALE = "TMUX_STALE"
    AMBIGUOUS = "AMBIGUOUS"

    @property
    def is_owned_by_tmux(self) -> bool:
        return self in (RuntimeState.TMUX_RUNNING, RuntimeState.TMUX_STALE)

    @property
    def blocks_launch(self) -> bool:
        """True when starting a service here would duplicate or trespass."""
        return self in (RuntimeState.LEGACY_RUNNING, RuntimeState.EXTERNAL_CONFLICT,
                        RuntimeState.AMBIGUOUS)


@dataclass
class Classification:
    """Everything decided about one service, plus the evidence for it."""

    service: str
    service_type: str
    port: int | None
    cwd: str | None
    session_name: str
    state: RuntimeState
    reason: str
    session: TmuxSession | None = None
    identity_pid: int | None = None
    confidence: str | None = None
    listening: bool = False
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "service": self.service,
            "service_type": self.service_type,
            "port": self.port,
            "cwd": self.cwd,
            "session": self.session_name,
            "state": self.state.value,
            "reason": self.reason,
            "session_present": self.session is not None,
            "attached": self.session.attached if self.session else 0,
            "pane_pid": self.session.pane_pid if self.session else None,
            "identity_pid": self.identity_pid,
            "confidence": self.confidence,
            "listening": self.listening,
            **({"details": self.details} if self.details else {}),
        }


@dataclass
class ActionResult:
    """Outcome of one action for one service.

    ``ok`` is explicit rather than derived from ``state``: a service can be
    legitimately *owned by tmux* (``TMUX_RUNNING``/``TMUX_STALE``) and still have
    failed the requested action, e.g. a restart refused because the recorded cwd
    no longer exists.  Deriving success from ownership alone would report that
    failure as a success.
    """

    service: str
    state: RuntimeState
    changed: bool
    message: str
    ok: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {"service": self.service, "state": self.state.value,
                "changed": self.changed, "ok": self.ok, "message": self.message}


class TmuxBackend(TerminalBackend):
    """Terminal backend whose process host is tmux."""

    name = "tmux"

    def __init__(
        self,
        *,
        runtime: TmuxRuntime | None = None,
        resolver: ProcessIdentityResolver | None = None,
        base_dir: str | Path | None = None,
        runner: str | Path | None = None,
    ) -> None:
        self.runtime = runtime or default_runtime()
        self.resolver = resolver or ProcessIdentityResolver()
        self.base_dir = Path(base_dir) if base_dir else None
        self._runner_override = Path(runner) if runner else None

    # ------------------------------------------------------------------ #
    # paths and small helpers
    # ------------------------------------------------------------------ #

    @property
    def workspace(self) -> Path:
        if self.base_dir is not None:
            return self.base_dir
        from devconsole import config as dev_config
        return Path(dev_config.BASE_DIR)

    def runner_path(self) -> Path:
        if self._runner_override is not None:
            return self._runner_override
        return (self.workspace / RUNNER_SCRIPT).resolve()

    def session_name(self, service: str, aux_type: str | None = None) -> str:
        return service_to_tmux_session_name(service, aux_type)

    def _configured_services(self) -> list[dict[str, Any]]:
        from devconsole import config as dev_config
        out = []
        for svc in dev_config.SERVICES_BACKEND:
            out.append({**svc, "service_type": "backend"})
        for svc in dev_config.SERVICES_FRONTEND:
            out.append({**svc, "service_type": "frontend"})
        return out

    def _service_config(self, service: str) -> dict[str, Any] | None:
        for svc in self._configured_services():
            if svc["name"] == service:
                return svc
        return None

    def _service_dir(self, service: str, base_dir: Path | None = None) -> Path | None:
        """Resolve a service directory the same way the legacy code does."""
        root = base_dir or self.workspace
        for candidate in (root / "backend" / service, root / "frontend" / service,
                          root / service):
            if candidate.is_dir():
                return candidate.resolve()
        return None

    @staticmethod
    def _port_listening(port: int | None) -> bool:
        if port is None:
            return False
        import socket
        s = socket.socket()
        s.settimeout(0.2)
        try:
            return s.connect_ex(("127.0.0.1", int(port))) == 0
        except OSError:
            return False
        finally:
            s.close()

    def _pane_command(self, service_dir: Path, command: str | None,
                      aux_type: str | None = None) -> list[str]:
        """Build the pane argv: an explicit multi-element command, never a shell.

        The runner is invoked as ``["bash", "<runner>"]`` rather than
        ``["<runner>"]`` on purpose: tmux hands a *single* element to the shell
        but ``exec``s a multi-element argv directly.  Two elements keep the call
        out of a shell parser entirely.

        An auxiliary console runs its own command (``AUX_COMMANDS``): before,
        with no explicit command, it fell back to the service runner and started
        the backend again, so "Lanzar Consumer" and "Lanzar Worker" opened a
        second copy of the service instead of the consumer or the worker.
        """
        if command is None and aux_type:
            aux = AUX_COMMANDS.get(aux_type)
            if aux:
                # `-lc` envuelve el comando tal cual (incluye el `||` de respaldo).
                return ["bash", "-lc", aux]
        script = command or str(self.runner_path())
        Path(script)
        return ["bash", script]

    def _pane_environment(self, environment: str) -> dict[str, str]:
        """Environment handed to the pane explicitly.

        Passed with ``-e`` so the pane never depends on whatever environment the
        tmux server happened to start with.
        """
        return {ENV_VAR_ENVIRONMENT: environment}

    # ------------------------------------------------------------------ #
    # classification
    # ------------------------------------------------------------------ #

    def classify(self, service: str, *, port: int | None = None,
                 service_type: str | None = None,
                 base_dir: Path | None = None,
                 sessions: list[TmuxSession] | None = None,
                 aux_type: str | None = None) -> Classification:
        """Decide the state of one service without changing anything.

        ``aux_type`` selects the auxiliary session namespace.  An auxiliary's
        session is a *different* session from the service's own, so omitting it
        looks for the wrong name and reports STOPPED forever — the tmux suite
        caught exactly that.
        """
        config = self._service_config(service)
        if port is None and aux_type is None:
            port = config.get("port") if config else None
        if service_type is None:
            service_type = (config or {}).get("service_type", "unknown")

        service_dir = self._service_dir(service, base_dir)
        session_name = self.session_name(service, aux_type)
        listening = self._port_listening(port)

        all_sessions = self.runtime.list_sessions() if sessions is None else sessions
        session = next((s for s in all_sessions if s.name == session_name), None)

        base = {
            "service": service,
            "service_type": service_type,
            "port": port,
            "cwd": str(service_dir) if service_dir else None,
            "session_name": session_name,
            "listening": listening,
            "session": session,
        }

        # ---- the tmux axis decides first: it is authoritative for ownership --
        if session is not None:
            ok, reason = validate_metadata(
                session.metadata, service=service,
                cwd=str(service_dir) if service_dir else None,
                service_type=None if service_type == "unknown" else service_type,
                port=port)
            if ok and aux_type is not None and \
                    session.metadata.get("@sisper_aux_type") != aux_type:
                ok, reason = False, "aux_type_mismatch"
            if not ok:
                return Classification(
                    state=RuntimeState.EXTERNAL_CONFLICT,
                    reason=f"session_metadata_invalid:{reason}",
                    details={"metadata": session.metadata}, **base)
            if not session.has_live_pane:
                return Classification(state=RuntimeState.TMUX_STALE,
                                      reason="pane_not_alive", **base)
            # An auxiliary console (worker/beat/consumer/shell) has no port, so a
            # live pane is the only liveness signal available — and the only one
            # needed.  Requiring a listening port here would make every
            # auxiliary permanently TMUX_STALE and therefore unlaunchable; the
            # tmux test suite caught exactly that.
            if port is None or listening:
                return Classification(
                    state=RuntimeState.TMUX_RUNNING,
                    reason="managed_session_and_pane_alive" if port is None
                    else "managed_session_and_port_listening", **base)
            return Classification(state=RuntimeState.TMUX_STALE,
                                  reason="managed_session_but_port_closed", **base)

        # ---- consola auxiliar: sólo importa su propia sesión ----------------
        # Un consumer / worker / beat / shell es una consola **adicional** del
        # servicio: que el servicio ya esté corriendo (y sea su proceso el que
        # ocupa el puerto) no puede impedir crearla.  Sin esta salvaguarda,
        # classify() devolvía LEGACY_RUNNING por el proceso del propio servicio,
        # `blocks_launch` era cierto y ensure_session se negaba a crear nada:
        # "Lanzar Consumer (RabbitMQ)" no hacía nada.
        if aux_type is not None:
            return Classification(state=RuntimeState.STOPPED,
                                  reason="aux_session_absent", **base)

        # ---- no session: who else might own the port? -----------------------
        resolution = self.resolver.resolve_service(service)
        if resolution.ambiguous:
            return Classification(state=RuntimeState.AMBIGUOUS,
                                  reason="identity_ambiguous",
                                  details={"candidates": list(resolution.candidate_pids)},
                                  **base)

        identity = resolution.identity
        if identity is not None and resolution.candidate_pids:
            owned = resolution.owned
            high = resolution.confidence.value.upper() == "HIGH"
            if not owned or not high:
                return Classification(
                    state=RuntimeState.EXTERNAL_CONFLICT,
                    reason=f"process_not_verified:{resolution.confidence.value}",
                    identity_pid=identity.pid,
                    confidence=resolution.confidence.value,
                    details={"owned": owned}, **base)
            return Classification(state=RuntimeState.LEGACY_RUNNING,
                                  reason="verified_legacy_process_owns_port",
                                  identity_pid=identity.pid,
                                  confidence=resolution.confidence.value, **base)

        if listening:
            return Classification(state=RuntimeState.EXTERNAL_CONFLICT,
                                  reason="port_busy_unidentified", **base)

        return Classification(state=RuntimeState.STOPPED, reason="nothing_running", **base)

    def classify_all(self, services: Sequence[str] | None = None) -> list[Classification]:
        """Classify many services with a single tmux inventory call."""
        sessions = self.runtime.list_sessions()
        names = list(services) if services else [s["name"] for s in self._configured_services()]
        return [self.classify(name, sessions=sessions) for name in names]

    # ------------------------------------------------------------------ #
    # creation / lifecycle primitives
    # ------------------------------------------------------------------ #

    def ensure_session(self, *, service: str, service_type: str, port: int | None,
                       cwd: Path, environment: str,
                       command: str | None = None,
                       aux_type: str | None = None) -> Classification:
        """Create the session for a service, refusing on any unsafe state."""
        current = self.classify(service, port=port, service_type=service_type,
                                aux_type=aux_type)
        if current.state is RuntimeState.TMUX_RUNNING:
            return current
        if current.state.blocks_launch:
            return current
        if current.state is RuntimeState.TMUX_STALE:
            # stale means our own session is there but not serving: restart it
            self.restart_session(service, port=port, service_type=service_type,
                                 environment=environment, cwd=cwd, command=command,
                                 aux_type=aux_type)
            return self.classify(service, port=port, service_type=service_type,
                                 aux_type=aux_type)

        session_name = self.session_name(service, aux_type)
        metadata = build_metadata(service=service, service_type=service_type,
                                  cwd=str(cwd), environment=environment,
                                  port=port, aux_type=aux_type)
        self.runtime.new_session(
            name=session_name, cwd=cwd,
            command=self._pane_command(cwd, command, aux_type),
            environment=self._pane_environment(environment),
            window_name=service)
        # Metadata immediately after creation, in one tmux call, so the window in
        # which the session exists unowned is as small as possible.  Until it is
        # set, classification reports EXTERNAL_CONFLICT — i.e. it fails closed
        # rather than adopting a session it cannot prove it owns.
        self.runtime.set_options(session_name, metadata)
        return self.classify(service, port=port, service_type=service_type,
                             aux_type=aux_type)

    def restart_session(self, service: str, *, port: int | None,
                        service_type: str, environment: str, cwd: Path,
                        command: str | None = None,
                        aux_type: str | None = None) -> bool:
        """Restart the pane in place, preserving the session and its viewers.

        ``respawn-pane -k`` was chosen over ``kill-session`` + ``new-session`` on
        evidence from the Phase 3K fixture: it changes the pane's PID, keeps the
        session, keeps **both** attached clients, keeps the cwd and applies the
        new environment — whereas killing the session destroys it and detaches
        every viewer.  See ``tests/devconsole/test_tmux_runtime.py``.
        """
        session_name = self.session_name(service, aux_type)
        session = self.runtime.find_session(session_name)
        if session is None:
            return False
        ok, reason = validate_metadata(session.metadata, service=service,
                                       cwd=str(cwd), port=port)
        if not ok:
            raise TmuxError(
                f"refusing to respawn {session_name!r}: {reason}")
        self.runtime.respawn_pane(session_name, cwd=cwd,
                                  command=self._pane_command(cwd, command, aux_type),
                                  environment=self._pane_environment(environment))
        return True

    def stop_service(self, service: str, *, aux_type: str | None = None) -> bool:
        """Terminate the managed session for exactly one service.

        Identity comes from session + metadata + validated cwd.  There is no
        ``pkill``, no ``fuser -k`` and no port-based kill anywhere on this path.
        """
        session_name = self.session_name(service, aux_type)
        session = self.runtime.find_session(session_name)
        if session is None:
            return False
        ok, reason = validate_metadata(session.metadata, service=service)
        if not ok:
            raise TmuxError(f"refusing to stop foreign session {session_name!r}: {reason}")
        return self.runtime.kill_session(session_name)

    def managed_sessions(self) -> list[TmuxSession]:
        """Every session on the server that carries valid DevConsole metadata."""
        out = []
        for session in self.runtime.list_sessions():
            if not session.name.startswith(SESSION_PREFIX):
                continue
            ok, _ = validate_metadata(session.metadata)
            if ok:
                out.append(session)
        return out

    # ------------------------------------------------------------------ #
    # ABC — discovery
    # ------------------------------------------------------------------ #

    def scan_sessions(self) -> list:
        """Return the workspace layout definitions.

        Public compatibility: ``GET /api/tilix/sessions`` keeps working and keeps
        its payload.  These files are consumed as **workspace definitions** (an
        ordered set of service directories) — see ``tmux_layout``.  They are no
        longer a statement about who owns the process; tmux does.
        """
        return scan_tilix_sessions()

    # ------------------------------------------------------------------ #
    # ABC — launching
    # ------------------------------------------------------------------ #

    def _launch_one(self, *, service: str, service_type: str, port: int | None,
                    environment: str, cwd: Path,
                    command: str | None = None,
                    aux_type: str | None = None) -> ActionResult:
        state = self.classify(service, port=port, service_type=service_type,
                              aux_type=aux_type)
        if state.state is RuntimeState.TMUX_RUNNING:
            return ActionResult(service, state.state, False,
                                "ya gestionado por tmux; no se duplica")
        if state.state.blocks_launch:
            return ActionResult(service, state.state, False,
                                f"no se lanza: {state.state.value} ({state.reason})",
                                ok=False)
        try:
            result = self.ensure_session(service=service, service_type=service_type,
                                        port=port, cwd=cwd, environment=environment,
                                        command=command, aux_type=aux_type)
        except (TmuxError, ValueError) as exc:
            return ActionResult(service, RuntimeState.STOPPED, False,
                                f"error: {exc}", ok=False)
        created = result.state.is_owned_by_tmux
        return ActionResult(service, result.state, created,
                            "sesion tmux creada" if created
                            else f"no creada: {result.state.value}")

    def launch_services(self, services: Sequence[str] | None = None,
                        environment: str = "develop",
                        base_dir: Path | None = None) -> tuple[bool, str, int]:
        """Create one tmux session per service, never duplicating anything."""
        root = base_dir or self.workspace
        names = list(services) if services else [s["name"] for s in self._configured_services()]

        results: list[ActionResult] = []
        for name in names:
            config = self._service_config(name) or {}
            service_dir = self._service_dir(name, root)
            if service_dir is None:
                results.append(ActionResult(name, RuntimeState.STOPPED, False,
                                            "directorio no encontrado", ok=False))
                continue
            results.append(self._launch_one(
                service=name, service_type=config.get("service_type", "unknown"),
                port=config.get("port"), environment=environment, cwd=service_dir))

        managed = sum(1 for r in results if r.state.is_owned_by_tmux)
        blocked = [r for r in results if r.state.blocks_launch]
        failed = [r for r in results if not r.changed and r.state is RuntimeState.STOPPED]

        if not results:
            return False, "No se encontraron directorios válidos para los servicios seleccionados.", 0
        if blocked and not managed:
            detail = "; ".join(f"{r.service}: {r.state.value}" for r in blocked)
            return False, f"No se lanzo nada: {detail}", 0
        if failed and not managed:
            detail = "; ".join(f"{r.service}: {r.message}" for r in failed)
            return False, f"Error lanzando en tmux: {detail}", 0

        note = f" en {environment.upper()}"
        if blocked:
            note += f" ({len(blocked)} sin migrar: {', '.join(r.service for r in blocked)})"
        return True, f"{managed} servicio(s) en sesiones tmux{note}.", managed

    def launch_auxiliary(self, service: str, aux_type: str = "consumer",
                         environment: str = "develop",
                         base_dir: Path | None = None) -> tuple[bool, str]:
        """Create a dedicated tmux session for one auxiliary console."""
        root = base_dir or self.workspace
        service_dir = self._service_dir(service, root)
        if service_dir is None:
            return False, f"Directorio no encontrado para el servicio: {service}"
        if aux_type not in ("consumer", "worker", "beat", "shell"):
            return False, f"Tipo de auxiliar no reconocido: {aux_type}"
        try:
            result = self.ensure_session(service=service, service_type="auxiliary",
                                         port=None, cwd=service_dir,
                                         environment=environment, aux_type=aux_type)
        except (TmuxError, ValueError) as exc:
            return False, f"Error lanzando auxiliar: {exc}"
        if result.state.is_owned_by_tmux:
            return True, f"Consola {aux_type} de {service} en sesion tmux {result.session_name}."
        return False, f"No se pudo crear el auxiliar {aux_type}: {result.state.value}"

    def launch_selected_auxiliaries(self, services: Sequence[str],
                                    aux_type: str = "consumer",
                                    environment: str = "develop",
                                    base_dir: Path | None = None) -> tuple[bool, str, int]:
        """One auxiliary session per selected service."""
        if not services:
            return False, "No se seleccionaron servicios.", 0
        count = 0
        failures = []
        for name in services:
            ok, msg = self.launch_auxiliary(name, aux_type, environment, base_dir)
            if ok:
                count += 1
            else:
                failures.append(f"{name}: {msg}")
        if not count:
            return False, "; ".join(failures) or "No se pudo lanzar ningun auxiliar.", 0
        msg = f"{count} consola(s) de tipo '{aux_type}' en sesiones tmux."
        if failures:
            msg += f" Fallos: {'; '.join(failures)}"
        return True, msg, count

    def launch_session(self, session_path: Path, environment: str = "develop") -> bool:
        """Launch every service of a layout definition as its own tmux session."""
        import json
        try:
            data = json.loads(Path(session_path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        services = extract_layout_services(data, self.workspace)
        if not services:
            return False
        ok = True
        for entry in services:
            config = self._service_config(entry["service"]) or {}
            result = self._launch_one(
                service=entry["service"],
                service_type=entry["service_type"] if entry["service_type"] != "unknown"
                else config.get("service_type", "unknown"),
                port=config.get("port"), environment=environment,
                cwd=Path(entry["cwd"]), command=entry.get("command"))
            ok = ok and (result.state.is_owned_by_tmux or result.state is RuntimeState.LEGACY_RUNNING)
        return ok

    # ------------------------------------------------------------------ #
    # ABC — lifecycle
    # ------------------------------------------------------------------ #

    #: Actions this backend implements.  Derived from the vocabulary the code
    #: actually passes to ``run_action`` (see ``tmux_layout`` and the tests that
    #: re-derive it from ``start_tilix.sh``); nothing is invented here.
    ACTIONS = frozenset({
        *env_keys(),
        "single", "all", "tabs", "b1", "b2", "front",
        "start", "stop", "stop-close", "restart", "restart-backends",
        "restart-frontends", "restart-single", "stop-single",
    })

    def run_action(self, action: str, args: Sequence[str] = (), *,
                   wait: bool, check: bool = False, timeout: float | None = None,
                   base_dir: Path | None = None) -> dict[str, Any]:
        """Dispatch a lifecycle action onto tmux sessions.

        ``start_tilix.sh`` is deliberately **not** executed here: it is a
        ``TilixBackend``/legacy detail.  Assigning the script to the tmux backend
        would reintroduce the ``pkill``/``fuser -k`` surface this backend exists
        to remove.

        The return value is a structured report rather than the legacy script's
        exit code, because tmux has per-service outcomes that a single status
        cannot express.  ``wait``/``check``/``timeout`` are accepted for ABC
        compatibility; tmux operations are synchronous and bounded by the
        runtime's own timeout.
        """
        if action not in self.ACTIONS:
            return {"ok": False, "action": action,
                    "message": f"accion no soportada por el backend tmux: {action}",
                    "results": []}

        handler = {
            "start": self._act_start,
            "stop": self._act_stop,
            "stop-close": self._act_stop_close,
            "restart": self._act_restart_all,
            "restart-backends": lambda root, a: self._act_restart_group("backend", root),
            "restart-frontends": lambda root, a: self._act_restart_group("frontend", root),
            "restart-single": self._act_restart_single,
            "stop-single": self._act_stop_single,
            "develop": lambda root, a: self._act_group("single", root, "develop"),
            "test": lambda root, a: self._act_group("single", root, "test"),
            "main": lambda root, a: self._act_group("single", root, "main"),
            "single": lambda root, a: self._act_group("single", root, "develop"),
            "all": lambda root, a: self._act_group("single", root, "develop"),
            "tabs": lambda root, a: self._act_group(("b1", "b2", "front"), root, "develop"),
            "b1": lambda root, a: self._act_group("b1", root, "develop"),
            "b2": lambda root, a: self._act_group("b2", root, "develop"),
            "front": lambda root, a: self._act_group("front", root, "develop"),
        }[action]
        root = base_dir or self.workspace
        return handler(root, list(args))

    # -- individual action implementations --------------------------------- #

    def _report(self, action: str, results: list[ActionResult],
                message: str) -> dict[str, Any]:
        """An action succeeds only when every service it touched succeeded."""
        ok = bool(results) and all(r.ok for r in results)
        return {"ok": ok, "action": action, "message": message,
                "results": [r.to_dict() for r in results]}

    def _act_start(self, root: Path, args: list[str]) -> dict[str, Any]:
        if not args:
            return {"ok": False, "action": "start", "message": "falta el servicio",
                    "results": []}
        service = args[0]
        config = self._service_config(service) or {}
        service_dir = self._service_dir(service, root)
        if service_dir is None:
            return {"ok": False, "action": "start",
                    "message": f"servicio no encontrado: {service}", "results": []}
        result = self._launch_one(service=service,
                                  service_type=config.get("service_type", "unknown"),
                                  port=config.get("port"), environment="develop",
                                  cwd=service_dir)
        return self._report("start", [result], result.message)

    def _act_stop(self, root: Path, args: list[str]) -> dict[str, Any]:
        results: list[ActionResult] = []
        for session in self.managed_sessions():
            service = session.metadata.get("@sisper_service", session.name)
            aux_type = session.metadata.get("@sisper_aux_type") or None
            try:
                ok = True
                changed = self.stop_service(service, aux_type=aux_type)
                message = "sesion tmux terminada" if changed else "ya no existia"
            except TmuxError as exc:
                changed, message, ok = False, f"rechazado: {exc}", False
            else:
                ok = True
            results.append(ActionResult(service, RuntimeState.STOPPED, changed,
                                        message, ok=ok))
        return self._report("stop", results, f"{len(results)} sesion(es) gestionada(s)")

    def _act_restart_all(self, root: Path, args: list[str]) -> dict[str, Any]:
        results = []
        for session in self.managed_sessions():
            results.append(self._restart_from_metadata(session))
        return self._report("restart", results,
                            f"{sum(1 for r in results if r.changed)} sesion(es) reiniciada(s)")

    def _act_restart_group(self, service_type: str, root: Path) -> dict[str, Any]:
        ports = BACKEND_PORTS if service_type == "backend" else FRONTEND_PORTS
        wanted = {s["name"] for s in self._configured_services()
                  if s.get("port") in ports and s.get("service_type") == service_type}
        results = []
        for session in self.managed_sessions():
            service = session.metadata.get("@sisper_service", "")
            if service in wanted:
                results.append(self._restart_from_metadata(session))
        action = f"restart-{service_type}s"
        return self._report(action, results,
                            f"{sum(1 for r in results if r.changed)} de {len(wanted)} "
                            f"{service_type}(s) reiniciado(s)")

    def _find_session_any(self, service: str) -> TmuxSession | None:
        """Localiza la sesión de un servicio, incluida su consola auxiliar.

        El muro nombra la tarjeta de una auxiliar con el nombre que publica el
        broker (``ms_sisper_x_consumer``), mientras que la sesión de tmux se llama
        ``sisper_aux_ms_sisper_x_consumer`` y sus metadatos apuntan al servicio
        BASE.  Buscar sólo ``session_name(service)`` no encontraba nada, así que
        "Parar servicio" respondía "no tiene sesion tmux" y no se podía cancelar
        un worker ni un consumer desde el muro.
        """
        session = self.runtime.find_session(self.session_name(service))
        if session is not None:
            return session
        for candidate in self.runtime.list_sessions():
            if candidate.name == service:
                return candidate
            base = candidate.metadata.get(META_SERVICE) or ""
            aux = candidate.metadata.get(META_AUX_TYPE) or ""
            if aux and base and f"{base}_{aux}" == service:
                return candidate
        return None

    def _act_stop_close(self, root: Path, args: list[str]) -> dict[str, Any]:
        """«Cerrar todo»: detiene las sesiones gestionadas **y** cierra las
        ventanas de Tilix que abrió el panel.  Antes era idéntico a «Detener
        servidores», por eso no se entendía la diferencia."""
        report = self._act_stop(root, args)
        cerradas = self.close_viewers()
        report["message"] = f"{report.get('message', '')} · {cerradas} ventana(s) de Tilix cerrada(s)"
        return report

    def _act_stop_single(self, root: Path, args: list[str]) -> dict[str, Any]:
        """Detiene UN servicio terminando su sesión tmux (no toca el resto).

        ``stop`` detiene todas las sesiones gestionadas; esta acción existe para
        que la consola de un servicio pueda detenerse desde su propio panel.
        """
        if not args:
            return {"ok": False, "action": "stop-single",
                    "message": "falta el servicio", "results": []}
        service = args[0]
        session = self._find_session_any(service)
        if session is None:
            return self._report("stop-single", [], f"{service} no tiene sesion tmux")
        # En una auxiliar, los metadatos apuntan al servicio BASE: hay que
        # pararla como (base, aux_type) o validate_metadata la rechaza.
        base = session.metadata.get(META_SERVICE) or service
        aux_type = session.metadata.get(META_AUX_TYPE) or None
        try:
            changed = self.stop_service(base, aux_type=aux_type)
            result = ActionResult(service, RuntimeState.STOPPED, changed,
                                  "sesion tmux terminada" if changed else "ya no existia",
                                  ok=True)
        except TmuxError as exc:
            result = ActionResult(service, RuntimeState.STOPPED, False,
                                  f"rechazado: {exc}", ok=False)
        return self._report("stop-single", [result], result.message)

    def _act_restart_single(self, root: Path, args: list[str]) -> dict[str, Any]:
        if not args:
            return {"ok": False, "action": "restart-single",
                    "message": "falta el servicio", "results": []}
        service = args[0]
        session = self._find_session_any(service)
        if session is None:
            return self._report("restart-single", [], f"{service} no tiene sesion tmux")
        result = self._restart_from_metadata(session)
        return self._report("restart-single", [result], result.message)

    def _act_group(self, layout: str | tuple[str, ...], root: Path,
                   environment: str) -> dict[str, Any]:
        """Create the sessions for every service a layout definition names."""
        import json
        layouts = (layout,) if isinstance(layout, str) else layout
        services: list[dict[str, Any]] = []
        seen: set[str] = set()
        for key in layouts:
            rel = LAYOUT_FILES.get(key)
            if rel is None:
                continue
            path = root / rel
            if not path.is_file():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            for entry in extract_layout_services(data, root):
                if entry["service"] in seen:
                    continue
                seen.add(entry["service"])
                services.append(entry)

        results = []
        for entry in services:
            config = self._service_config(entry["service"]) or {}
            results.append(self._launch_one(
                service=entry["service"],
                service_type=entry["service_type"] if entry["service_type"] != "unknown"
                else config.get("service_type", "unknown"),
                port=config.get("port"), environment=environment,
                cwd=Path(entry["cwd"]), command=entry.get("command")))
        action = layout if isinstance(layout, str) else "+".join(layout)
        return self._report(action, results,
                            f"{sum(1 for r in results if r.changed)} de {len(services)} "
                            f"servicio(s) en tmux")

    def _restart_from_metadata(self, session: TmuxSession) -> ActionResult:
        """Restart a session using its own metadata as the source of truth."""
        service = session.metadata.get("@sisper_service", "")
        service_type = session.metadata.get("@sisper_service_type", "unknown")
        cwd = session.metadata.get("@sisper_cwd") or ""
        environment = session.metadata.get("@sisper_environment", "develop")
        aux_type = session.metadata.get("@sisper_aux_type") or None

        ok, reason = validate_metadata(session.metadata, service=service, cwd=cwd
                                       if cwd else None)
        if not ok:
            return ActionResult(service or session.name,
                                RuntimeState.EXTERNAL_CONFLICT, False,
                                f"metadata invalida: {reason}", ok=False)
        if not cwd or not Path(cwd).is_dir():
            return ActionResult(service or session.name, RuntimeState.TMUX_STALE, False,
                                "cwd del metadata no existe", ok=False)
        try:
            port = session.metadata.get("@sisper_port")
            self.restart_session(service, port=int(port) if port else None,
                                 service_type=service_type, environment=environment,
                                 cwd=Path(cwd), aux_type=aux_type)
        except TmuxError as exc:
            return ActionResult(service or session.name, RuntimeState.EXTERNAL_CONFLICT,
                                False, f"rechazado: {exc}", ok=False)
        return ActionResult(service or session.name, RuntimeState.TMUX_RUNNING, True,
                            "pane reiniciado en su lugar (sesion conservada)")

    def _spawn_viewer(self, argv: list[str]) -> None:
        """Launch the external viewer process without blocking."""
        proc = subprocess.Popen(argv, start_new_session=True)
        self._viewers = [p for p in getattr(self, "_viewers", []) if p.poll() is None]
        self._viewers.append(proc)

    def close_viewers(self) -> int:
        """Cierra las ventanas de Tilix que abrió **este** proceso.

        Se termina el proceso que lanzamos (``Popen.terminate``), sin recurrir a
        `pkill`/`os.kill`: el paquete de terminal tiene prohibido ese instrumental
        (lo comprueba `test_no_destructive_primitive_in_the_terminal_package`) y,
        además, así no se toca ninguna ventana que haya abierto el usuario.  No
        toca las sesiones tmux: los servicios siguen corriendo.
        """
        cerradas = 0
        for proc in list(getattr(self, "_viewers", [])):
            if proc.poll() is not None:
                continue
            try:
                proc.terminate()
                cerradas += 1
            except Exception:
                pass
        self._viewers = []
        return cerradas

    def attach_viewers(self, services: Sequence[str],
                       title: str | None = None) -> tuple[bool, str]:
        """Abre UNA ventana de Tilix con un panel por cada sesión activa.

        Es lo que hacía el lanzador legacy (una ventana, varios paneles) y lo que
        faltaba: los botones de «Lanzar Tilix» creaban las sesiones tmux pero no
        abrían ninguna ventana, así que parecía que no hacían nada.
        """
        from devconsole.services.terminal.tmux_attach import (
            viewer_argv,
            write_attach_layout,
        )

        entradas: list[tuple[str, str | None]] = []
        sin_sesion: list[str] = []
        for svc in services:
            sess = self.session_name(svc)
            if self.runtime.find_session(sess) is not None:
                entradas.append((sess, svc))
            else:
                sin_sesion.append(svc)
        if not entradas:
            return False, "No hay sesiones tmux activas para esas consolas."
        try:
            path = write_attach_layout(entradas, tag=title or "consolas")
            self._spawn_viewer(viewer_argv(path))
        except Exception as exc:
            return False, f"Error abriendo el visor Tilix: {exc}"
        msg = f"Ventana Tilix con {len(entradas)} consola(s)."
        if sin_sesion:
            msg += f" Sin sesion: {', '.join(sin_sesion[:3])}" + ("..." if len(sin_sesion) > 3 else "")
        return True, msg

    def attach_viewer(self, service: str, title: str | None = None) -> tuple[bool, str]:
        """Open an isolated external Tilix viewer attached to the service's tmux session."""
        from devconsole.services.terminal.tmux_attach import viewer_argv_single

        sess_name = self.session_name(service)
        session = self.runtime.find_session(sess_name)
        if session is None:
            return False, f"La sesión tmux para {service} ({sess_name}) no existe o no está activa."
        try:
            argv = viewer_argv_single(sess_name, title=title or service)
            self._spawn_viewer(argv)
            return True, f"Visor Tilix abierto de forma aislada para {service}."
        except Exception as exc:
            return False, f"Error ejecutando visor Tilix: {exc}"


