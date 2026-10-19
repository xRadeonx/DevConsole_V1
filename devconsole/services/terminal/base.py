# devconsole/services/terminal/base.py
"""Backend-neutral contract for DevConsole terminal integration.

This module defines the seam introduced in Phase 2 of the desktop migration.
Its only job is to describe *what* the rest of DevConsole needs from a terminal
provider, without saying anything about *how* any particular provider does it.

Scope discipline
----------------
A terminal backend in DevConsole does exactly two families of things today:

1. **Discovery and launching** — find session files and open windows/consoles
   for a set of services (the ``launch_*`` / ``scan_sessions`` methods).
2. **Lifecycle actions** — ask the provider to start, restart or stop the
   consoles it already owns (``run_action``).

It deliberately does **not** cover:

* process identity, ownership or safety verdicts — that is
  :mod:`devconsole.services.runtime` (Phase 0B) and must stay there;
* anything about terminals inside a window (PTY, xterm.js, tmux panes) — that
  is Phase 3 and later.

Why this interface returns the legacy tuples
--------------------------------------------
The sketch in the migration roadmap suggested optional ``TerminalLaunchRequest``
/ ``TerminalLaunchResult`` dataclasses.  They were evaluated and **deliberately
not introduced**, for two reasons:

* The existing signatures are *already* backend-neutral.  They take service
  **names** and an environment label, and return ``(ok, message, count)``.
  No caller ever passes or receives a Tilix JSON document, a ``Paned`` node, a
  terminal ``uuid`` or an ``overrideCommand``.  Those concepts already live
  entirely inside :mod:`devconsole.services.terminal.tilix_backend`.
* Phase 2's contract is *parity*.  Wrapping the frozen tuple returns in
  dataclasses would force either a translation layer at the compatibility shim
  or a change to the 55 characterization tests that pin those exact tuples —
  cost with no behavioural benefit, since a future ``TmuxBackend`` is equally
  free to ignore Tilix internals while still returning ``(ok, msg, count)``.

If a future backend genuinely needs richer results (a session id, structured
details), the dataclasses can be added then, as an additive change, once a real
consumer needs them.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Sequence

from devconsole.config import env_keys


class TerminalBackendError(RuntimeError):
    """Base error for terminal backend selection problems."""


class UnsupportedTerminalBackend(TerminalBackendError):
    """Raised for a backend name that is reserved but not implemented yet.

    ``tmux`` is the intended member of this class until Phase 3 ships a real
    implementation.  Falling back to Tilix for it would silently give the
    operator something other than what was asked for, which is exactly the
    misleading behaviour the roadmap forbids.
    """


#: Lifecycle actions understood by :meth:`TerminalBackend.run_action`.
#:
#: This is **documentation, not validation** — an unknown action is still passed
#: through to the provider unchanged, because the previous implementation did no
#: validation either and adding it here would be a behaviour change.  The names
#: are the DevConsole's own public vocabulary (they are the values accepted by
#: the ``action`` field of ``POST /api/action``), not a Tilix-specific concept.
KNOWN_ACTIONS = frozenset({
    # Las acciones de entorno salen de los entornos configurados, no de una
    # lista fija: otra instalación con otros nombres debe funcionar igual.
    *env_keys(),
    # Session/window actions.
    "single", "all", "tabs", "b1", "b2", "front",
    "stop", "stop-close", "stop-single",
    # Refresh actions.
    "restart", "restart-backends", "restart-frontends", "restart-single",
    # Single-service start.
    "start",
})


class TerminalBackend(ABC):
    """What DevConsole needs from whatever is hosting its consoles.

    Implementations are obtained through
    :func:`devconsole.services.terminal.registry.get_terminal_backend`; they are
    never constructed directly by consumers.
    """

    #: Stable identifier matching the ``SISPER_TERMINAL_BACKEND`` value.
    name: str = "unknown"

    # -- discovery ---------------------------------------------------------- #

    @abstractmethod
    def scan_sessions(self) -> list[dict[str, Any]]:
        """Return the session files this backend can launch.

        Each entry is a mapping with at least ``name``, ``rel_path``,
        ``abs_path`` and ``terminals`` keys.  Ordering is the backend's own
        contract but must be deterministic.
        """

    # -- launching ---------------------------------------------------------- #

    @abstractmethod
    def launch_session(self, session_path: Path, environment: str = "develop") -> bool:
        """Launch a previously discovered session file."""

    @abstractmethod
    def launch_services(
        self,
        services: Sequence[str] | None = None,
        environment: str = "develop",
        base_dir: Path | None = None,
    ) -> tuple[bool, str, int]:
        """Launch one console per named service.

        ``services=None`` means "every service discovered in the workspace".
        Returns ``(ok, message, service_count)``.
        """

    @abstractmethod
    def launch_auxiliary(
        self,
        service: str,
        aux_type: str = "consumer",
        environment: str = "develop",
        base_dir: Path | None = None,
    ) -> tuple[bool, str]:
        """Launch a single auxiliary console (consumer / worker / beat / shell)."""

    @abstractmethod
    def launch_selected_auxiliaries(
        self,
        services: Sequence[str],
        aux_type: str = "consumer",
        environment: str = "develop",
        base_dir: Path | None = None,
    ) -> tuple[bool, str, int]:
        """Launch one auxiliary console per named service."""

    # -- lifecycle ---------------------------------------------------------- #

    @abstractmethod
    def run_action(
        self,
        action: str,
        args: Sequence[str] = (),
        *,
        wait: bool,
        check: bool = False,
        timeout: float | None = None,
        base_dir: Path | None = None,
    ) -> Any:
        """Apply a lifecycle ``action`` to consoles the backend already owns.

        ``wait`` selects between the two invocation styles the DevConsole has
        always used, and must be passed explicitly because the correct choice
        differs per call site:

        * ``wait=False`` — fire and forget.  Returns the provider's process
          handle, which callers ignore.
        * ``wait=True`` — block until done.  ``check`` and ``timeout`` are
          forwarded; with ``check=True`` a non-zero exit raises, exactly as the
          previous direct ``subprocess.run(..., check=True)`` did.

        ``base_dir`` overrides the workspace root used to locate the provider's
        launcher, and exists so callers that already own a patched
        ``BASE_DIR`` keep full control of resolution.
        """

    def attach_viewer(
        self,
        service: str,
        title: str | None = None,
    ) -> tuple[bool, str]:
        """Open an external viewer attached to an active session.

        Default implementation returns not supported; overriden by backends
        supporting detached viewers (e.g. TmuxBackend).
        """
        return False, "attach_viewer no está soportado por este backend"
