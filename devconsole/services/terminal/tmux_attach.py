# devconsole/services/terminal/tmux_attach.py
"""Tilix as a *viewer* of tmux sessions.

This is the Phase 3 milestone in code form: for a service hosted by tmux, Tilix
must **not** run ``tilix_runner.sh``.  It runs only::

    tmux attach-session -t <session>

so that closing every Tilix window leaves the service running, and reopening one
re-attaches to the very same session.

Two safety properties are built in deliberately:

1. **The attach layout uses the default Tilix profile**, not ``SISPER-Auto``.
   That profile's ``custom-command`` is ``tilix_runner.sh``; the attach layout
   must never be one ignored-``overrideCommand`` away from starting a *second*
   copy of a service.  The default profile runs a login shell, so the worst case
   is a useless shell — never a duplicate service.

2. **Attaching never creates a session.**  ``attach-session`` fails if the
   session is absent; it cannot spawn a service.  Creation is the backend's job
   and requires passing the ownership checks in ``tmux_backend``.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Sequence

#: Profile id of Tilix's built-in default profile ("Predeterminado").
#:
#: Chosen over ``SISPER-Auto`` (``c8e01000-…``) on purpose: that profile carries
#: ``custom-command=/…/tilix_runner.sh`` with ``use-custom-command=true``, so a
#: layout that failed to apply ``overrideCommand`` would start the service
#: again.  The default profile has no custom command.
DEFAULT_PROFILE_ID = "2b7c4080-0ddd-46c5-8f23-563fd3ba789d"

#: Terminal geometry, matching the values the legacy generator uses.
TERMINAL_WIDTH = 640
TERMINAL_HEIGHT = 420
SESSION_WIDTH = 1920
SESSION_HEIGHT = 1080

#: Where dynamic attach layouts are written, mirroring the legacy convention.
ATTACH_LAYOUT_PREFIX = "/tmp/tilix_attach"


UNSAFE_CHARS = frozenset({":", ".", " ", "\t", "\n", ";", "&", "|", "$", "\\", "`", "<", ">", '"', "'"})


def attach_command(session_name: str) -> str:
    """The exact command a viewer pane runs for ``session_name``.

    **Sin** ``exec``: Tilix no interpreta una shell, hace ``execve`` directo
    partiendo la cadena por espacios, así que un prefijo ``exec`` se convertía en
    ``execve("exec")`` y la ventana fallaba con "Failed to execve: No existe el
    fichero o el directorio".  Con ``tmux`` como primer argumento el panel arranca
    el cliente y, al salir tmux, Tilix cierra el panel: no queda shell colgando.

    ``-t`` es el objetivo exacto: sin coincidencia por prefijo, un nombre
    incompleto no puede engancharse al servicio equivocado.
    """
    if not session_name or not isinstance(session_name, str):
        raise ValueError("session_name must be a non-empty string")
    if any(ch in UNSAFE_CHARS for ch in session_name):
        raise ValueError(f"refusing unsafe tmux target: {session_name!r}")
    # `set-option status off` va en el mismo comando (tmux separa por `;`): la
    # barra de estado ("[sesion:ventana] titulo 14:26 15-oct-26") solo estorba en
    # las consolas del visor, que son de lectura de logs.
    return (f"tmux set-option -t {session_name} status off ; "
            f"attach-session -t {session_name}")


def _terminal_node(session_name: str, title: str | None = None,
                   directory: str | None = None) -> dict[str, Any]:
    #: Tilix exige `directory` en cada nodo Terminal: sin él rechaza el fichero
    #: con "Key not found: directory" y la ventana no se abre (era el motivo de
    #: que «Abrir en Tilix» no hiciera nada).
    import os

    node = {
        "directory": directory or os.path.expanduser("~"),
        "height": TERMINAL_HEIGHT,
        "profile": DEFAULT_PROFILE_ID,
        # Sólo lectura: estos paneles son para **leer** logs.  Si no, la rueda del
        # ratón se traduce en flechas y el servicio las recibe como entrada
        # (aparecían [[A[[A[[A por la consola).
        "readOnly": True,
        "synchronizedInput": False,
        "type": "Terminal",
        "uuid": str(uuid.uuid4()),
        "width": TERMINAL_WIDTH,
        "overrideCommand": attach_command(session_name),
    }
    if title:
        node["title"] = title
    return node


def _build_node(items: Sequence[tuple[str, str | None]], depth: int = 0) -> dict[str, Any]:
    if len(items) == 1:
        session_name, title = items[0]
        return _terminal_node(session_name, title)
    mid = len(items) // 2
    return {
        "child1": _build_node(items[:mid], depth + 1),
        "child2": _build_node(items[mid:], depth + 1),
        "orientation": 0 if depth % 2 == 0 else 1,
        "position": 50,
        "ratio": 0.5,
        "type": "Paned",
    }


def build_attach_layout(entries: Sequence[tuple[str, str | None]],
                        session_name: str = "SISPER tmux") -> dict[str, Any]:
    """Build a Tilix session that only attaches to the given tmux sessions.

    ``entries`` is an ordered sequence of ``(tmux_session_name, pane_title)``.
    Layout shape matches the legacy generator (balanced panes, alternating
    orientation) so the visual experience stays familiar; what changed is the
    command and the profile.
    """
    if not entries:
        return {}
    return {
        "child": _build_node(list(entries)),
        "height": SESSION_HEIGHT,
        "width": SESSION_WIDTH,
        "name": f"SISPER - {session_name}",
        "synchronizedInput": False,
        "type": "Session",
        "uuid": str(uuid.uuid4()),
        "version": "1.0",
    }


def write_attach_layout(entries: Sequence[tuple[str, str | None]],
                        *, user: str | None = None,
                        tag: str = "selected") -> Path:
    """Write an attach layout to ``/tmp`` and return its path.

    Writes only a layout document — no service is started, no tmux session is
    created, and nothing is signalled.
    """
    import os

    owner = user or os.environ.get("USER", "user")
    layout = build_attach_layout(entries, tag)
    path = Path(f"{ATTACH_LAYOUT_PREFIX}_{owner}_{tag}.json")
    path.write_text(json.dumps(layout, indent=2), encoding="utf-8")
    return path


def viewer_argv(path: Path) -> list[str]:
    """argv that opens the attach layout in Tilix (never shell-interpreted).

    Uses ``--new-process`` to isolate the viewer from any existing Tilix GApplication
    session, preventing D-Bus collisions or peer disconnections.
    """
    return ["tilix", "--new-process", f"--session={path}"]


def viewer_argv_single(session_name: str, title: str | None = None) -> list[str]:
    """argv that opens a single tmux session viewer directly in Tilix.

    Bypasses session files entirely by passing ``-e "tmux attach-session -t ..."``
    with ``--new-process`` and the safe default profile.
    """
    if not session_name or not isinstance(session_name, str):
        raise ValueError("session_name must be a non-empty string")
    if any(ch in UNSAFE_CHARS for ch in session_name):
        raise ValueError(f"refusing unsafe tmux target: {session_name!r}")
    cmd = f"tmux attach-session -t {session_name}"
    args = ["tilix", "--new-process", "-p", DEFAULT_PROFILE_ID]
    if title:
        args.extend(["-t", title])
    args.extend(["-e", cmd])
    return args
