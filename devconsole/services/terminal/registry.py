# devconsole/services/terminal/registry.py
"""Backend selection for :mod:`devconsole.services.terminal`.

Selection is configured with ``SISPER_TERMINAL_BACKEND`` and defaults to
``tilix``.  No dependency-injection framework is involved: consumers call
:func:`get_terminal_backend` and receive a cached instance.

Value policy
------------
Two tiers, deliberately distinguished so that neither a typo nor a future
backend name can ever change behaviour silently:

``unset`` / empty / whitespace
    → ``tilix``.  This is the default and must never surprise anyone.

``tilix``
    → ``tilix``.  Still the compile-time default.

``tmux``
    → ``tmux``.  Implemented in Phase 3; the process host becomes tmux while
    Tilix degrades to a viewer.

any *reserved but unimplemented* name
    → raises :class:`~devconsole.services.terminal.base.UnsupportedTerminalBackend`.
    Reserved names must not appear to work: quietly serving Tilix to an operator
    who asked for something else would be misleading, so it fails loudly.  The
    set is empty today (Phase 3 implemented ``tmux``).

anything else (e.g. a typo such as ``tliix``)
    → logs a clear one-time warning and falls back to ``tilix``.  A typo in an
    environment variable should not take the whole DevConsole down, and the
    invariant that matters — *never silently run something different* — is
    upheld by the warning.  The warning is emitted once per distinct value so
    that per-request calls cannot flood the log.

Matching is case-insensitive and whitespace-trimmed.
"""

from __future__ import annotations

import os
import sys

from devconsole.services.terminal.base import (
    TerminalBackend,
    UnsupportedTerminalBackend,
)
from devconsole.services.terminal.tilix_backend import TilixBackend
from devconsole.services.terminal.tmux_backend import TmuxBackend

#: Environment variable selecting the active backend.
ENV_VAR = "SISPER_TERMINAL_BACKEND"

#: Backend used when nothing is configured. Must remain ``tilix`` for Phase 2.
DEFAULT_BACKEND = "tilix"

#: Backends that exist and can be instantiated.
IMPLEMENTED: dict[str, type[TerminalBackend]] = {
    "tilix": TilixBackend,
    "tmux": TmuxBackend,
}

#: Names reserved by the roadmap but intentionally not implemented yet.
#:
#: Empty as of Phase 3: ``tmux`` graduated from reserved to implemented.  The
#: set is kept because the two-tier policy below still needs the concept — a
#: future backend can be reserved before it exists.
RESERVED_UNIMPLEMENTED: frozenset[str] = frozenset()

_LOG_PREFIX = "[TERMINAL]"

_cache: TerminalBackend | None = None
_cache_key: str | None = None
_warned_values: set[str] = set()


def configured_value() -> str:
    """Return the raw (un-normalised) configured value, or ``""`` if unset."""
    return os.environ.get(ENV_VAR, "")


def resolve_backend_name(raw: str | None = None) -> str:
    """Normalise and validate a backend name.

    ``raw=None`` reads ``SISPER_TERMINAL_BACKEND`` from the environment.  Raises
    :class:`UnsupportedTerminalBackend` for a reserved-unimplemented name.
    """
    value = configured_value() if raw is None else raw
    normalized = (value or "").strip().lower()

    if not normalized:
        return DEFAULT_BACKEND

    if normalized in IMPLEMENTED:
        return normalized

    if normalized in RESERVED_UNIMPLEMENTED:
        raise UnsupportedTerminalBackend(
            f"{ENV_VAR}={normalized!r} is reserved and not implemented yet; "
            f"only {sorted(IMPLEMENTED)} are available. "
            f"A tmux backend is planned for a later phase — nothing was started."
        )

    if normalized not in _warned_values:
        _warned_values.add(normalized)
        print(
            f"{_LOG_PREFIX} unknown backend {normalized!r} in {ENV_VAR}; "
            f"falling back to {DEFAULT_BACKEND!r}. "
            f"Known backends: {sorted(IMPLEMENTED)}.",
            file=sys.stderr,
        )
    return DEFAULT_BACKEND


def get_terminal_backend(name: str | None = None) -> TerminalBackend:
    """Return the active backend instance.

    The instance is cached and rebuilt only when the resolved name changes, so
    per-request use is cheap and switching configuration mid-process (as tests
    do) is still honoured.
    """
    global _cache, _cache_key

    resolved = resolve_backend_name(name)
    if _cache is None or _cache_key != resolved:
        _cache = IMPLEMENTED[resolved]()
        _cache_key = resolved
    return _cache


def reset_terminal_backend() -> None:
    """Drop the cached instance and the warning memory.

    Intended for tests that change ``SISPER_TERMINAL_BACKEND`` mid-process.
    """
    global _cache, _cache_key
    _cache = None
    _cache_key = None
    _warned_values.clear()


__all__ = [
    "ENV_VAR",
    "DEFAULT_BACKEND",
    "IMPLEMENTED",
    "RESERVED_UNIMPLEMENTED",
    "UnsupportedTerminalBackend",
    "configured_value",
    "get_terminal_backend",
    "reset_terminal_backend",
    "resolve_backend_name",
]
