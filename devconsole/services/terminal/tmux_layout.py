# devconsole/services/terminal/tmux_layout.py
"""Session naming, metadata schema and group membership for the tmux backend.

This module is **pure**: no subprocess, no filesystem writes, no tmux.  It answers
three questions and nothing else:

1. *What is the tmux session called for this service?* —
   :func:`service_to_tmux_session_name`.
2. *What metadata does a managed session carry, and how is it validated?* —
   the ``META_*`` keys and :func:`validate_metadata`.
3. *Which services does an action refer to?* — the port groups and
   :func:`extract_layout_services`.

Separating "layout definition" from "process host"
--------------------------------------------------
DevConsole's session JSON files historically described *Tilix* windows.  They are
still useful as **workspace definitions** — an ordered set of service
directories — and Phase 3 keeps consuming them as such.  What changed is that
they no longer decide who owns the process: tmux does.  A Tilix layout is now a
*viewer* artifact (see :mod:`devconsole.services.terminal.tmux_attach`).

One session per service
-----------------------
Each managed service gets its own tmux session (``sisper_<service>``), and each
auxiliary console gets its own (``sisper_aux_<service>_<type>``).  Reasons:

* **isolation** — one misbehaving service cannot take another down;
* **exact restart** — ``respawn-pane`` on one session touches exactly one service;
* **unambiguous ownership** — metadata on a single-pane session maps 1:1 to a
  service, with no per-pane inference;
* **simple attach** — a viewer attaches by name and needs no pane addressing;
* **multiple clients** — several viewers can attach to the same session
  concurrently, which a single shared session makes contentious;
* **recovery** — re-discovery after a DevConsole restart is a session list;
* **future node-pty** — a bounded, named unit to attach to;
* **no window stealing** — N Tilix clients cannot fight over one session's
  active window, because each has its own.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Iterable, Sequence

# --------------------------------------------------------------------------- #
# Naming
# --------------------------------------------------------------------------- #

#: Prefix of every session owned by DevConsole for a service.
SESSION_PREFIX = "sisper_"

#: Additional infix marking an auxiliary console session.
AUX_INFIX = "aux_"

#: tmux reserves ``:`` and ``.`` for target syntax; keep the charset narrow.
_UNSAFE = re.compile(r"[^A-Za-z0-9_-]")

#: Bound the name so it stays comfortably inside every tmux/OS limit.
MAX_SESSION_NAME = 64

#: Length of the disambiguating suffix appended when a name is not verbatim.
_HASH_LEN = 8

AUX_TYPES = ("consumer", "worker", "beat", "shell")


def _disambiguate(text: str) -> str:
    """Deterministic short digest used to keep sanitised names collision-free."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:_HASH_LEN]


def sanitize_component(value: str) -> str:
    """Return a tmux-safe component for ``value``.

    A value that is already safe is returned **verbatim**, so the common case
    (real service names such as ``ms_sisper_contratos``) stays reversible.  A
    value that had to be altered gets no special treatment here — the caller
    (:func:`service_to_tmux_session_name`) appends a digest so that two distinct
    inputs can never collapse onto the same name.
    """
    if not isinstance(value, str):
        raise TypeError("value must be a string")
    return _UNSAFE.sub("_", value.strip())


def service_to_tmux_session_name(service: str, aux_type: str | None = None) -> str:
    """Return the tmux session name for ``service`` (optionally an auxiliary).

    Deterministic, collision-free, charset-safe, length-bounded and reversible
    for every name DevConsole actually uses.

    Raises
    ------
    ValueError
        If ``service`` is empty or is not a string.
    """
    if not isinstance(service, str) or not service.strip():
        raise ValueError("service name must be a non-empty string")

    original = service.strip()
    base = sanitize_component(original)

    if aux_type is not None:
        if aux_type not in AUX_TYPES:
            raise ValueError(
                f"unknown auxiliary type {aux_type!r}; expected one of {AUX_TYPES}")
        component = f"{base}_{aux_type}"
    else:
        component = base

    prefix = SESSION_PREFIX + (AUX_INFIX if aux_type is not None else "")
    name = f"{prefix}{component}"

    # A name whose service part survived verbatim needs no digest: it is already
    # unique against every other verbatim name and it is reversible.  Anything
    # else (sanitised, or longer than the bound) gets one, so that two distinct
    # inputs can never share a session name.
    if base == original and len(name) <= MAX_SESSION_NAME:
        return name

    digest = _disambiguate(f"{original}|{aux_type or ''}")
    room = MAX_SESSION_NAME - len(prefix) - len(digest) - 1
    return f"{prefix}{component[:max(room, 1)]}-{digest}"


def parse_tmux_session_name(name: str) -> dict[str, Any] | None:
    """Best-effort inverse of :func:`service_to_tmux_session_name`.

    Returns ``{"service": ..., "aux_type": ...}``, or ``None`` when ``name`` is
    not a DevConsole session name.

    The name is a **convenience, not an authority**: a digested name cannot be
    inverted, and nothing in this codebase is allowed to act on a session based
    on its name alone.  Metadata (below) is what decides ownership — see
    :func:`validate_metadata`.
    """
    if not isinstance(name, str) or not name.startswith(SESSION_PREFIX):
        return None

    rest = name[len(SESSION_PREFIX):]
    aux_type = None
    if rest.startswith(AUX_INFIX):
        rest = rest[len(AUX_INFIX):]
        for candidate in AUX_TYPES:
            suffix = f"_{candidate}"
            if rest.endswith(suffix):
                aux_type = candidate
                rest = rest[: -len(suffix)]
                break
        else:
            return None

    if not rest or rest.endswith("-") or re.search(r"-[0-9a-f]{8}$", rest):
        # Either empty or carrying a digest: the service cannot be recovered.
        if rest and re.search(r"-[0-9a-f]{8}$", rest):
            return {"service": None, "aux_type": aux_type, "recoverable": False}
        return None

    return {"service": rest, "aux_type": aux_type, "recoverable": True}


# --------------------------------------------------------------------------- #
# Metadata schema
# --------------------------------------------------------------------------- #

#: tmux user options carrying DevConsole ownership metadata.
#:
#: User options (``@``-prefixed) are the supported extension point and survive
#: ``respawn-pane``, so ownership outlives the process inside the pane.
META_MANAGED = "@sisper_managed"
META_SERVICE = "@sisper_service"
META_SERVICE_TYPE = "@sisper_service_type"
META_PORT = "@sisper_port"
META_ENVIRONMENT = "@sisper_environment"
META_CWD = "@sisper_cwd"
META_SCHEMA = "@sisper_schema_version"
META_AUX_TYPE = "@sisper_aux_type"

#: Bumped whenever the metadata contract changes shape.
SCHEMA_VERSION = "1"

#: Keys every managed session must carry.
REQUIRED_META = (
    META_MANAGED,
    META_SERVICE,
    META_SERVICE_TYPE,
    META_CWD,
    META_SCHEMA,
)

SERVICE_TYPES = ("backend", "frontend", "auxiliary")


def build_metadata(*, service: str, service_type: str, cwd: str, environment: str,
                   port: int | None = None, aux_type: str | None = None) -> dict[str, str]:
    """Build the metadata mapping for a managed session."""
    if service_type not in SERVICE_TYPES:
        raise ValueError(f"unknown service_type {service_type!r}; expected {SERVICE_TYPES}")
    meta = {
        META_MANAGED: "1",
        META_SERVICE: service,
        META_SERVICE_TYPE: service_type,
        META_ENVIRONMENT: environment,
        META_CWD: str(cwd),
        META_SCHEMA: SCHEMA_VERSION,
    }
    if port is not None:
        meta[META_PORT] = str(port)
    if aux_type is not None:
        meta[META_AUX_TYPE] = aux_type
    return meta


def validate_metadata(meta: dict[str, str], *, service: str | None = None,
                      cwd: str | None = None,
                      service_type: str | None = None,
                      port: int | None = None) -> tuple[bool, str | None]:
    """Decide whether a session's metadata proves DevConsole ownership.

    Returns ``(ok, reason)``.  A session whose *name* looks right but whose
    metadata does not match must be treated as FOREIGN/CONFLICT and left alone —
    this function is the single place that decides that.
    """
    for key in REQUIRED_META:
        if not meta.get(key):
            return False, f"missing_metadata:{key}"

    if meta.get(META_MANAGED) != "1":
        return False, "not_managed"

    if meta.get(META_SCHEMA) != SCHEMA_VERSION:
        return False, f"schema_mismatch:{meta.get(META_SCHEMA)}"

    if meta.get(META_SERVICE_TYPE) not in SERVICE_TYPES:
        return False, f"unknown_service_type:{meta.get(META_SERVICE_TYPE)}"

    if service is not None and meta.get(META_SERVICE) != service:
        return False, "service_mismatch"

    if service_type is not None and meta.get(META_SERVICE_TYPE) != service_type:
        return False, "service_type_mismatch"

    if cwd is not None:
        recorded = meta.get(META_CWD)
        if recorded != str(cwd):
            return False, "cwd_mismatch"

    if port is not None:
        recorded = meta.get(META_PORT)
        if recorded is not None and recorded != str(port):
            return False, "port_mismatch"

    return True, None


# --------------------------------------------------------------------------- #
# Group membership (derived from the real legacy artifacts)
# --------------------------------------------------------------------------- #

#: Backend ports, transcribed from ``PORTS_BACKEND`` in ``start_tilix.sh``.
#:
#: Kept as an explicit tuple rather than computed from config because the legacy
#: ``restart-backends`` acts on exactly these ports, and Phase 3 must select the
#: *same* set.  ``test_tmux_backend`` re-derives it from the script and fails if
#: the two ever disagree.
BACKEND_PORTS: tuple[int, ...] = (
    8000, 8001, 8002, 8003, 8004, 8006, 8007, 8008, 8009,
    8010, 8012, 8016, 8018, 8019, 8020, 8021, 8100,
)

#: Frontend ports, transcribed from ``PORTS_FRONTEND`` in ``start_tilix.sh``.
FRONTEND_PORTS: tuple[int, ...] = (
    3000, 3001, 3002, 3003, 3004, 3006, 3007, 3008, 3009, 3010,
)

#: Session files the legacy launcher uses for each named layout action.
LAYOUT_FILES: dict[str, str] = {
    "b1": "backend/backend-terminal-auto.json",
    "b2": "backend/backend-terminal-2-auto.json",
    "front": "frontend_terminal_auto.json",
    "single": "sisper_all_single_session_auto.json",
}

#: Service default runner script, reused verbatim as the tmux pane command.
RUNNER_SCRIPT = "tilix_runner.sh"

#: Command each auxiliary console runs, copied verbatim from the legacy tilix
#: backend (``launch_auxiliary_console``), which is where they only existed.
#: Without this, an auxiliary session fell back to ``RUNNER_SCRIPT`` and ran the
#: *backend* again: "Lanzar Consumer" opened a second copy of the service.
#: ``pipenv run`` is used first with a bare fallback because the pane is not a
#: login shell.
AUX_COMMANDS: dict[str, str] = {
    "consumer": "pipenv run python manage.py start_consumer || python manage.py start_consumer",
    "worker": "pipenv run celery -A config worker -l info || celery -A config worker -l info",
    "beat": "pipenv run celery -A config beat -l info || celery -A config beat -l info",
    "shell": "pipenv shell || exec bash",
}

#: The fixed Tilix profile id the legacy layout generator uses.
TILIX_PROFILE_ID = "c8e01000-0000-0000-0000-000000000001"

#: Matches the generated default command:
#: ``bash -c 'cd "<dir>" && exec "<runner>"'``
_DEFAULT_COMMAND_RE = re.compile(
    r"""^bash\s+-c\s+['"]cd\s+"(?P<dir>[^"]+)"\s*&&\s*exec\s+"(?P<exec>[^"]+)"['"]$""")


def parse_override_command(command: str | None) -> dict[str, Any]:
    """Classify a layout's ``overrideCommand``.

    Returns ``{"kind": ..., "path": ...}`` where ``kind`` is one of:

    ``profile_default``
        ``overrideCommand`` is absent.  This is the case for **every** checked-in
        layout (``backend-terminal-auto.json``, ``frontend_terminal_auto.json``,
        …): they carry no per-pane command and rely on the Tilix profile
        ``c8e01000-…`` ("SISPER-Auto"), whose ``custom-command`` is
        ``tilix_runner.sh`` with ``use-custom-command=true``.  So "no override"
        means "run the workspace runner", which is what the tmux backend
        substitutes.  Verified against dconf, not assumed.
    ``runner``
        The generated default form
        ``bash -c 'cd "<dir>" && exec "<runner>"'``; ``path`` is the exec'd script.
    ``script``
        A plain absolute path to a generated script (auxiliary consoles).
    ``unknown``
        Anything else.  Callers must refuse to guess rather than execute it.
    """
    if command is None or command == "":
        return {"kind": "profile_default", "path": None}

    match = _DEFAULT_COMMAND_RE.match(command.strip())
    if match:
        return {"kind": "runner", "path": match.group("exec")}

    stripped = command.strip()
    if stripped.startswith("/") and stripped.endswith(".sh"):
        return {"kind": "script", "path": stripped}

    return {"kind": "unknown", "path": None}


def _walk_terminals(node: Any) -> Iterable[dict[str, Any]]:
    """Yield terminal nodes in deterministic in-order tree order.

    Order matters: viewers are expected to show services in the layout's own
    order, so a dictionary iteration or a set would be a behaviour change.
    """
    if not isinstance(node, dict):
        return
    node_type = node.get("type")
    if node_type == "Terminal":
        yield node
        return
    for key in ("child", "child1", "child2"):
        if key in node:
            yield from _walk_terminals(node[key])


def classify_directory(directory: str | Path, base_dir: str | Path) -> dict[str, Any] | None:
    """Map a service directory to ``{service, service_type, cwd}``.

    Handles both shapes DevConsole uses: the nested ``backend/<svc>`` /
    ``frontend/<svc>`` layout and a flat ``<svc>`` directly under the workspace
    root (which is what ``launch_custom_services_tilix`` also accepts).  Returns
    ``None`` when the directory is outside the workspace or has no name.
    """
    try:
        path = Path(directory).resolve()
        root = Path(base_dir).resolve()
    except (OSError, ValueError):
        return None

    try:
        relative = path.relative_to(root)
    except ValueError:
        return None

    parts = relative.parts
    if not parts:
        return None

    if len(parts) >= 2 and parts[0] in ("backend", "frontend"):
        return {"service": parts[1], "service_type": parts[0], "cwd": str(path)}

    if len(parts) == 1:
        return {"service": parts[0], "service_type": "unknown", "cwd": str(path)}

    return None


def extract_layout_services(session_data: dict[str, Any],
                            base_dir: str | Path) -> list[dict[str, Any]]:
    """Turn a Tilix layout definition into an ordered list of services.

    Each entry is ``{"service", "service_type", "cwd", "command", "command_kind"}``.

    This is the "layout definition → workspace membership" step described in the
    module docstring: the layout supplies *which* directories and *what* command,
    while tmux supplies the process host.  Entries are de-duplicated by
    ``(service_type, service)`` keeping first-seen order, because a layout may
    legitimately contain the same directory twice but a service must own exactly
    one session.
    """
    seen: set[tuple[str, str]] = set()
    ordered: list[dict[str, Any]] = []

    for node in _walk_terminals(session_data):
        directory = node.get("directory")
        if not isinstance(directory, str):
            continue
        classified = classify_directory(directory, base_dir)
        if classified is None:
            continue
        key = (classified["service_type"], classified["service"])
        if key in seen:
            continue
        seen.add(key)

        parsed = parse_override_command(node.get("overrideCommand"))
        ordered.append({
            **classified,
            "command": parsed["path"],
            "command_kind": parsed["kind"],
        })

    return ordered


def services_for_ports(services: Sequence[dict[str, Any]],
                       ports: Sequence[int]) -> list[dict[str, Any]]:
    """Filter configured services down to those whose port is in ``ports``.

    Used by the ``restart-backends`` / ``restart-frontends`` groups so that a
    tmux restart selects exactly the same set the legacy script would have.
    """
    wanted = set(int(p) for p in ports)
    return [s for s in services if s.get("port") in wanted]
