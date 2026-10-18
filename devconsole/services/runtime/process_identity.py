"""Process identity model for DevConsole (roadmap phase 0B).

This module replaces the unsafe concept ``service == port`` with
``service == an identified process that provably belongs to this workspace``.

Design constraints (phase 0B):

* **No destructive capability.**  Nothing in ``devconsole.services.runtime``
  may import :mod:`signal`, call ``os.kill``/``os.killpg``, or spawn
  ``pkill``/``kill``/``killall``/``fuser -k``.  This is enforced by test
  ``test_runtime_has_no_destructive_primitives``.
* **Fail closed.**  Only :attr:`Confidence.HIGH` may ever enable a future
  destructive action, and :func:`Confidence.allows_destructive_action` is the
  single place that decision is encoded.
* **Multiple independent evidence sources.**  Port, cwd, cmdline and ancestry
  are each individually insufficient.  See
  :mod:`devconsole.services.runtime.process_ownership`.
* **Standard library only.**  No ``psutil``: ``/proc`` provides everything
  needed on Linux.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


class ServiceType(str, enum.Enum):
    """Kind of DevConsole-managed service."""

    BACKEND = "backend"
    FRONTEND = "frontend"
    AUXILIARY = "auxiliary"
    UNKNOWN = "unknown"

    @classmethod
    def from_name(cls, name: str) -> "ServiceType":
        """Infer the type from the repository naming convention.

        ``ms_*`` → BACKEND, ``mf_*`` → FRONTEND.  Anything else is UNKNOWN so
        that the ownership verifier cannot accidentally bless a foreign
        process.
        """
        if not name:
            return cls.UNKNOWN
        if name.startswith("ms_"):
            return cls.BACKEND
        if name.startswith("mf_"):
            return cls.FRONTEND
        return cls.UNKNOWN


class Confidence(str, enum.Enum):
    """How strongly the collected evidence identifies a DevConsole process.

    Ordered from strongest to weakest.  ``NONE`` is the default for anything
    that cannot be proven.
    """

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"

    def allows_destructive_action(self) -> bool:
        """Return ``True`` only for :attr:`HIGH`.

        This is intentionally the *only* gate.  No heuristic may raise LOW or
        MEDIUM to HIGH; the verifier must produce HIGH directly from primary
        evidence.
        """
        return self is Confidence.HIGH

    @property
    def rank(self) -> int:
        return {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0}[self.value]


class Operation(str, enum.Enum):
    """An operation whose target process may need to be identified."""

    INSPECT = "inspect"
    RESTART = "restart"
    STOP = "stop"
    STOP_ALL = "stop_all"
    RESTART_BACKENDS = "restart_backends"
    RESTART_FRONTENDS = "restart_frontends"
    START = "start"


@dataclass(frozen=True)
class ServiceDescriptor:
    """What DevConsole *expects* a service to look like.

    Built from :mod:`devconsole.config` (discovered services) so the
    expectation always tracks the real configuration.
    """

    name: str
    service_type: ServiceType
    configured_port: int | None
    expected_service_dir: Path | None
    base_dir: Path

    @property
    def expected_dir_resolved(self) -> Path | None:
        if self.expected_service_dir is None:
            return None
        try:
            return self.expected_service_dir.resolve()
        except OSError:
            return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "service_type": self.service_type.value,
            "configured_port": self.configured_port,
            "expected_service_dir": str(self.expected_service_dir) if self.expected_service_dir else None,
            "base_dir": str(self.base_dir),
        }


@dataclass(frozen=True)
class ProcessFacts:
    """Raw, unverified facts read from ``/proc``.

    Named "facts" deliberately: nothing here is trusted until
    :class:`~devconsole.services.runtime.process_ownership.OwnershipVerifier`
    has cross-checked it against the service descriptor.
    """

    pid: int
    ppid: int | None = None
    pgid: int | None = None
    sid: int | None = None
    start_time_ticks: int | None = None
    executable: str | None = None
    command_line: tuple[str, ...] = ()
    cwd: str | None = None
    listening_ports: tuple[int, ...] = ()
    read_errors: tuple[str, ...] = ()

    @property
    def command_line_str(self) -> str:
        return " ".join(self.command_line)

    @property
    def exe_basename(self) -> str | None:
        if not self.executable:
            return None
        # An executable may be reported as "name (deleted)".
        return Path(self.executable).name.split(" (", 1)[0] or None

    @property
    def cwd_basename(self) -> str | None:
        return Path(self.cwd).name if self.cwd else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "pid": self.pid,
            "ppid": self.ppid,
            "pgid": self.pgid,
            "sid": self.sid,
            "start_time_ticks": self.start_time_ticks,
            "executable": self.executable,
            "command_line": list(self.command_line),
            "cwd": self.cwd,
            "listening_ports": list(self.listening_ports),
            "read_errors": list(self.read_errors),
        }


@dataclass(frozen=True)
class ProcessIdentity:
    """The outcome of resolving and verifying one candidate process.

    This is the object a *future* bounded-kill operation would consult.  In
    phase 0B it is produced, logged and compared — never acted upon.
    """

    service_name: str
    service_type: ServiceType
    configured_port: int | None

    pid: int
    ppid: int | None
    pgid: int | None
    executable: str | None
    command_line: tuple[str, ...]
    cwd: str | None
    listening_ports: tuple[int, ...]

    expected_service_dir: str | None
    base_dir: str

    executable_matches: bool = False
    cwd_matches: bool = False
    port_matches: bool = False
    command_matches: bool = False
    ancestry_matches: bool = False

    confidence: Confidence = Confidence.NONE
    owned_by_devconsole: bool = False
    evidence: tuple[str, ...] = ()
    rejection_reason: str | None = None

    # -- convenience ------------------------------------------------------- #

    @property
    def command_line_str(self) -> str:
        return " ".join(self.command_line)

    @property
    def allows_destructive_action(self) -> bool:
        """Fail-closed gate: only HIGH + owned may ever authorise a kill."""
        return self.confidence.allows_destructive_action() and self.owned_by_devconsole

    @property
    def matched_evidence_count(self) -> int:
        return sum((self.executable_matches, self.cwd_matches,
                    self.port_matches, self.command_matches))

    def to_dict(self) -> dict[str, Any]:
        """Serialise for logs and API responses.

        Contains no environment variables and no secrets by construction.
        """
        return {
            "service_name": self.service_name,
            "service_type": self.service_type.value,
            "configured_port": self.configured_port,
            "pid": self.pid,
            "ppid": self.ppid,
            "pgid": self.pgid,
            "executable": self.executable,
            "command_line": list(self.command_line),
            "cwd": self.cwd,
            "listening_ports": list(self.listening_ports),
            "expected_service_dir": self.expected_service_dir,
            "base_dir": self.base_dir,
            "executable_matches": self.executable_matches,
            "cwd_matches": self.cwd_matches,
            "port_matches": self.port_matches,
            "command_matches": self.command_matches,
            "ancestry_matches": self.ancestry_matches,
            "confidence": self.confidence.value,
            "owned_by_devconsole": self.owned_by_devconsole,
            "evidence": list(self.evidence),
            "rejection_reason": self.rejection_reason,
            "allows_destructive_action": self.allows_destructive_action,
        }

    @classmethod
    def unresolved(
        cls,
        descriptor: ServiceDescriptor,
        *,
        reason: str,
        evidence: Iterable[str] = (),
        pid: int = 0,
    ) -> "ProcessIdentity":
        """Build a NONE identity explicitly, used for every failure path."""
        return cls(
            service_name=descriptor.name,
            service_type=descriptor.service_type,
            configured_port=descriptor.configured_port,
            pid=pid,
            ppid=None,
            pgid=None,
            executable=None,
            command_line=(),
            cwd=None,
            listening_ports=(),
            expected_service_dir=str(descriptor.expected_service_dir) if descriptor.expected_service_dir else None,
            base_dir=str(descriptor.base_dir),
            confidence=Confidence.NONE,
            owned_by_devconsole=False,
            evidence=tuple(evidence),
            rejection_reason=reason,
        )


def identity_from(descriptor: ServiceDescriptor, facts: ProcessFacts, **overrides: Any) -> ProcessIdentity:
    """Assemble a :class:`ProcessIdentity` from a descriptor and raw facts."""
    base = dict(
        service_name=descriptor.name,
        service_type=descriptor.service_type,
        configured_port=descriptor.configured_port,
        pid=facts.pid,
        ppid=facts.ppid,
        pgid=facts.pgid,
        executable=facts.executable,
        command_line=facts.command_line,
        cwd=facts.cwd,
        listening_ports=facts.listening_ports,
        expected_service_dir=str(descriptor.expected_service_dir) if descriptor.expected_service_dir else None,
        base_dir=str(descriptor.base_dir),
    )
    base.update(overrides)
    return ProcessIdentity(**base)
