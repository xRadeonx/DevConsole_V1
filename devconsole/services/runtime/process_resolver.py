"""Resolve a configured service to a verified process identity (phase 0B.2/0B.4).

Pipeline::

    Service (config)
      → ServiceDescriptor
      → ProcessIdentityResolver        (port → candidate PIDs)
      → ProcessIdentity                (facts + verdict)
      → OwnershipVerifier              (HIGH / MEDIUM / LOW / NONE)

The port is used **only to nominate candidates**.  Nothing is trusted until the
ownership verifier has cross-checked location, command, runtime and lineage.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import devconsole.config as dcfg

from devconsole.services.runtime.process_identity import (
    Confidence,
    ProcessFacts,
    ProcessIdentity,
    ServiceDescriptor,
    ServiceType,
    identity_from,
)
from devconsole.services.runtime.process_inspector import ProcessInspector
from devconsole.services.runtime.psutil_inspector import create_process_inspector
from devconsole.services.runtime.process_ownership import (
    OwnershipVerifier,
    RejectionReason,
    select_candidate,
)


def build_descriptor(
    service_name: str,
    *,
    base_dir: Path | None = None,
    services: Sequence[dict] | None = None,
) -> ServiceDescriptor:
    root = Path(base_dir) if base_dir is not None else Path(dcfg.BASE_DIR)
    entries: list[dict] = list(services) if services is not None else (
        list(dcfg.SERVICES_BACKEND) + list(dcfg.SERVICES_FRONTEND))

    entry = next((s for s in entries if s.get("name") == service_name), None)
    service_type = ServiceType.from_name(service_name)

    configured_port: int | None = None
    if entry and isinstance(entry.get("port"), int):
        configured_port = entry["port"]

    if service_type is ServiceType.BACKEND:
        expected = root / "backend" / service_name
    elif service_type is ServiceType.FRONTEND:
        expected = root / "frontend" / service_name
    else:
        expected = None

    if expected is not None and not expected.exists():
        other = root / ("frontend" if service_type is ServiceType.BACKEND else "backend") / service_name
        if other.exists():
            expected = other

    return ServiceDescriptor(
        name=service_name,
        service_type=service_type,
        configured_port=configured_port,
        expected_service_dir=expected,
        base_dir=root,
    )


@dataclass(frozen=True)
class Resolution:
    descriptor: ServiceDescriptor
    identity: ProcessIdentity | None
    candidate_pids: tuple[int, ...]
    rejected: tuple[dict[str, Any], ...]
    ambiguous: bool = False

    @property
    def confidence(self) -> Confidence:
        return self.identity.confidence if self.identity else Confidence.NONE

    @property
    def owned(self) -> bool:
        return bool(self.identity and self.identity.owned_by_devconsole)

    def to_dict(self) -> dict[str, Any]:
        return {
            "service": self.descriptor.name,
            "service_type": self.descriptor.service_type.value,
            "configured_port": self.descriptor.configured_port,
            "expected_service_dir": str(self.descriptor.expected_service_dir)
            if self.descriptor.expected_service_dir else None,
            "candidate_pids": list(self.candidate_pids),
            "ambiguous": self.ambiguous,
            "identity": self.identity.to_dict() if self.identity else None,
            "confidence": self.confidence.value,
            "owned": self.owned,
            "rejected": list(self.rejected),
        }


class ProcessIdentityResolver:
    """Turns a service name into a verified :class:`ProcessIdentity`."""

    def __init__(
        self,
        *,
        base_dir: Path | None = None,
        inspector: ProcessInspector | None = None,
        verifier: OwnershipVerifier | None = None,
        require_ancestry_for_high: bool = True,
        protected_pids: Iterable[int] = (),
    ) -> None:
        self.base_dir = Path(base_dir) if base_dir is not None else Path(dcfg.BASE_DIR)
        # V1.1 selects psutil only when available on the real host.  Injected
        # inspectors and synthetic /proc fixtures keep the exact V1 behavior.
        self.inspector = inspector or create_process_inspector()
        self.verifier = verifier or OwnershipVerifier(
            self.base_dir,
            require_ancestry_for_high=require_ancestry_for_high,
            protected_pids=protected_pids,
        )

    def list_configured_services(self) -> list[str]:
        return [s["name"] for s in (list(dcfg.SERVICES_BACKEND) + list(dcfg.SERVICES_FRONTEND))
                if s.get("name")]

    def ancestry_context(self, pid: int) -> list[tuple[tuple[str, ...], str | None]]:
        context: list[tuple[tuple[str, ...], str | None]] = []
        chain = self.inspector.read_ancestry(pid)
        for ancestor_pid in chain[1:]:
            argv, _ = self.inspector.read_cmdline(ancestor_pid)
            cwd, _ = self.inspector.read_cwd(ancestor_pid)
            context.append((argv, cwd))
        return context

    def resolve_pid(self, descriptor: ServiceDescriptor, pid: int,
                    *, expected_start_ticks: int | None = None) -> ProcessIdentity:
        if not self.inspector.is_alive(pid):
            return ProcessIdentity.unresolved(
                descriptor,
                reason=RejectionReason.PROCESS_DISAPPEARED.value,
                pid=pid,
            )

        facts: ProcessFacts = self.inspector.read_facts(pid)

        if expected_start_ticks is not None and facts.start_time_ticks is not None:
            if facts.start_time_ticks != expected_start_ticks:
                return ProcessIdentity.unresolved(
                    descriptor,
                    reason=RejectionReason.PID_REUSED.value,
                    evidence=[f"expected_start={expected_start_ticks} observed={facts.start_time_ticks}"],
                    pid=pid,
                )

        ancestors = self.ancestry_context(pid)
        verdict = self.verifier.verify(descriptor, facts, ancestors=ancestors)

        return identity_from(
            descriptor,
            facts,
            executable_matches=verdict.executable_matches,
            cwd_matches=verdict.cwd_matches,
            port_matches=verdict.port_matches,
            command_matches=verdict.command_matches,
            ancestry_matches=verdict.ancestry_matches,
            confidence=verdict.confidence,
            owned_by_devconsole=verdict.owned,
            evidence=verdict.evidence,
            rejection_reason=verdict.rejection_reason,
        )

    def resolve_service(self, service_name: str,
                        *, descriptor: ServiceDescriptor | None = None,
                        pids: Sequence[int] | None = None) -> Resolution:
        desc = descriptor or build_descriptor(service_name, base_dir=self.base_dir)

        if pids is None:
            candidates = (
                tuple(self.inspector.port_to_pids(desc.configured_port))
                if desc.configured_port is not None else ()
            )
        else:
            candidates = tuple(pids)

        if not candidates:
            return Resolution(
                descriptor=desc,
                identity=None,
                candidate_pids=(),
                rejected=(),
            )

        identities = [self.resolve_pid(desc, pid) for pid in candidates]

        if len(identities) > 1:
            return Resolution(
                descriptor=desc,
                identity=None,
                candidate_pids=candidates,
                rejected=tuple(i.to_dict() for i in identities),
                ambiguous=True,
            )

        chosen, rejection = select_candidate(identities)
        return Resolution(
            descriptor=desc,
            identity=chosen,  # type: ignore[arg-type]
            candidate_pids=candidates,
            rejected=(),
            ambiguous=False,
        )

    def resolve_all(self) -> list[Resolution]:
        return [self.resolve_service(name) for name in self.list_configured_services()]
