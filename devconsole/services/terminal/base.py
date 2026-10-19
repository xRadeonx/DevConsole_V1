# devconsole/services/terminal/base.py
"""Backend-neutral contract for DevConsole terminal integration.

The required launch/lifecycle API stays stable. Optional viewer/session methods
have conservative defaults so existing providers and test doubles do not break
when the UI asks for richer terminal capabilities.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Sequence

from devconsole.config import env_keys


class TerminalBackendError(RuntimeError):
    """Base error for terminal backend selection problems."""


class UnsupportedTerminalBackend(TerminalBackendError):
    """Raised when a requested backend is not available."""


KNOWN_ACTIONS = frozenset({
    *env_keys(),
    "single", "all", "tabs", "b1", "b2", "front",
    "stop", "stop-close", "stop-single",
    "restart", "restart-backends", "restart-frontends", "restart-single",
    "start",
})


class TerminalBackend(ABC):
    """Stable public contract for terminal providers."""

    name: str = "unknown"

    @abstractmethod
    def scan_sessions(self) -> list[dict[str, Any]]:
        """Return launchable session descriptors in deterministic order."""

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
        """Launch one console per named service."""

    @abstractmethod
    def launch_auxiliary(
        self,
        service: str,
        aux_type: str = "consumer",
        environment: str = "develop",
        base_dir: Path | None = None,
    ) -> tuple[bool, str]:
        """Launch one auxiliary console."""

    @abstractmethod
    def launch_selected_auxiliaries(
        self,
        services: Sequence[str],
        aux_type: str = "consumer",
        environment: str = "develop",
        base_dir: Path | None = None,
    ) -> tuple[bool, str, int]:
        """Launch auxiliary consoles for selected services."""

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
        """Apply a lifecycle action to consoles owned by this provider."""

    def attach_viewer(
        self,
        service: str,
        title: str | None = None,
    ) -> tuple[bool, str]:
        """Open one external viewer when supported."""
        return False, "attach_viewer no está soportado por este backend"

    def attach_viewers(
        self,
        services: Sequence[str],
        title: str | None = None,
    ) -> tuple[bool, str]:
        """Open viewers for several services without making it mandatory.

        Backends with a grouped viewer override this method. The default calls
        ``attach_viewer`` and reports unsupported functionality normally instead
        of raising ``AttributeError`` from existing API routes.
        """
        requested = [str(service) for service in services if str(service).strip()]
        if not requested:
            return False, "No se indicaron servicios para el visor."
        opened = 0
        messages: list[str] = []
        for service in requested:
            ok, message = self.attach_viewer(service, title=title)
            opened += int(ok)
            if message:
                messages.append(message)
        if opened:
            return True, f"Visores abiertos: {opened}/{len(requested)}. " + " ".join(messages)
        return False, messages[0] if messages else "Visor externo no soportado por este backend."

    def managed_sessions(self) -> list[Any]:
        """Return provider-owned sessions when that capability exists."""
        return []
