# devconsole/services/terminal/__init__.py
"""Terminal backend abstraction (desktop migration, Phase 2).

Import surface for consumers::

    from devconsole.services.terminal import get_terminal_backend

    backend = get_terminal_backend()
    sessions = backend.scan_sessions()

The active backend is ``tilix`` and will remain so until a tmux backend exists.
See :mod:`devconsole.services.terminal.base` for the contract and
:mod:`devconsole.services.terminal.registry` for selection rules.
"""

from devconsole.services.terminal.base import (
    KNOWN_ACTIONS,
    TerminalBackend,
    TerminalBackendError,
    UnsupportedTerminalBackend,
)
from devconsole.services.terminal.tilix_backend import (
    LAUNCHER_SCRIPT,
    TilixBackend,
)
from devconsole.services.terminal.tmux_backend import TmuxBackend
from devconsole.services.terminal.tmux_layout import (
    SCHEMA_VERSION,
    service_to_tmux_session_name,
)
from devconsole.services.terminal.tmux_runtime import TmuxRuntime
from devconsole.services.terminal.registry import (
    DEFAULT_BACKEND,
    ENV_VAR,
    configured_value,
    get_terminal_backend,
    reset_terminal_backend,
    resolve_backend_name,
)

__all__ = [
    "DEFAULT_BACKEND",
    "ENV_VAR",
    "KNOWN_ACTIONS",
    "LAUNCHER_SCRIPT",
    "TerminalBackend",
    "TerminalBackendError",
    "SCHEMA_VERSION",
    "TilixBackend",
    "TmuxBackend",
    "TmuxRuntime",
    "UnsupportedTerminalBackend",
    "configured_value",
    "get_terminal_backend",
    "reset_terminal_backend",
    "resolve_backend_name",
    "service_to_tmux_session_name",
    "MosaicService",
    "MosaicItem",
    "LiveConsoleBroker",
    "LiveConsoleItem",
    "get_live_broker",
]

from devconsole.services.terminal.mosaic_service import MosaicItem, MosaicService
from devconsole.services.terminal.live_broker import LiveConsoleBroker, LiveConsoleItem, get_live_broker

