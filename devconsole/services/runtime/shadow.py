"""Shadow mode: compare the legacy target with the safe target (phase 0B.6).

Mode is selected by the ``SISPER_PROCESS_MODE`` environment variable:

===========  ==========================================================
``legacy``   **Default.**  Nothing is computed, nothing is logged, the
             existing ``fuser -k`` / ``pkill`` behaviour is untouched.
``shadow``   The safe target is computed and compared against the legacy
             target.  :mod:`devconsole.services.runtime` still performs
             **no destructive action whatsoever**; the legacy mechanism
             remains the one that acts.
===========  ==========================================================

The comparison answers a single question: *would the safe system act on the
same process the legacy system acts on?*  A ``False`` answer is the whole point
of running shadow mode, and is logged as ``shadow_mismatch``.
"""

from __future__ import annotations

import enum
import os
from dataclasses import dataclass, field
from typing import Any, Sequence

from devconsole.services.runtime import audit
from devconsole.services.runtime.process_identity import Operation
from devconsole.services.runtime.process_resolver import (
    ProcessIdentityResolver,
    Resolution,
)

ENV_VAR = "SISPER_PROCESS_MODE"


class ProcessMode(str, enum.Enum):
    """How DevConsole resolves process targets."""

    LEGACY = "legacy"
    SHADOW = "shadow"

    @classmethod
    def from_env(cls, value: str | None = None) -> "ProcessMode":
        """Parse the mode, defaulting to ``LEGACY`` for anything unrecognised.

        Defaulting to LEGACY is the fail-safe direction: an unset or malformed
        value must never silently enable a new code path.
        """
        raw = (value if value is not None else os.environ.get(ENV_VAR, "")).strip().lower()
        if raw == ProcessMode.SHADOW.value:
            return cls.SHADOW
        return cls.LEGACY


def current_mode() -> ProcessMode:
    """Return the active :class:`ProcessMode`."""
    return ProcessMode.from_env()


def shadow_enabled() -> bool:
    return current_mode() is ProcessMode.SHADOW


@dataclass(frozen=True)
class ShadowComparison:
    """Structured legacy-vs-safe comparison for one operation."""

    service: str
    operation: str
    legacy: dict[str, Any]
    shadow: dict[str, Any]
    match: bool
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "service": self.service,
            "operation": self.operation,
            "legacy": self.legacy,
            "shadow": self.shadow,
            "match": self.match,
            "reason": self.reason,
        }


class ShadowComparator:
    """Computes the legacy target and the safe target for an operation.

    Deliberately holds **no destructive capability**: there is no ``kill``,
    ``signal`` or subprocess write path anywhere in this class.
    """

    def __init__(self, resolver: ProcessIdentityResolver | None = None) -> None:
        self.resolver = resolver or ProcessIdentityResolver()

    # ------------------------------------------------------------------ #
    # legacy side — what the current implementation would terminate
    # ------------------------------------------------------------------ #

    def legacy_target(self, *, service: str, port: int | None,
                      pids: Sequence[int] | None = None) -> dict[str, Any]:
        """Describe the process set the legacy mechanism would act on.

        Legacy semantics: ``fuser -k -n tcp <port>`` kills **every** PID bound
        to the port, with no ownership check at all.  The candidate set is
        therefore the full port→PID mapping, and it is intentionally *not*
        filtered by ownership — that is precisely the risk being measured.
        """
        resolved_pids = list(pids) if pids is not None else (
            list(self.resolver.inspector.port_to_pids(port)) if port is not None else []
        )
        return {
            "selector": "port",
            "port": port,
            "pids": sorted(resolved_pids),
        }

    # ------------------------------------------------------------------ #
    # comparison
    # ------------------------------------------------------------------ #

    def compare(self, *, service: str, operation: Operation | str = Operation.RESTART,
                port: int | None = None,
                resolution: Resolution | None = None) -> ShadowComparison:
        """Compare legacy and safe targets for one service operation."""
        op = operation.value if isinstance(operation, Operation) else str(operation)

        res = resolution if resolution is not None else self.resolver.resolve_service(service)
        effective_port = port if port is not None else res.descriptor.configured_port

        legacy = self.legacy_target(
            service=service,
            port=effective_port,
            pids=res.candidate_pids if res.candidate_pids else None,
        )

        identity = res.identity
        shadow = {
            "pid": identity.pid if identity else None,
            "confidence": res.confidence.value,
            "owned": res.owned,
            "allows_destructive_action": bool(identity and identity.allows_destructive_action),
            "ambiguous": res.ambiguous,
            "rejection_reason": identity.rejection_reason if identity else None,
            "evidence": list(identity.evidence) if identity else [],
        }

        match, reason = self._judge(legacy, shadow, res)
        return ShadowComparison(
            service=service,
            operation=op,
            legacy=legacy,
            shadow=shadow,
            match=match,
            reason=reason,
        )

    @staticmethod
    def _judge(legacy: dict[str, Any], shadow: dict[str, Any],
               res: Resolution) -> tuple[bool, str | None]:
        """Decide whether legacy and safe agree, with an explanatory reason.

        The question is *would the safe system act on the same process the
        legacy system acts on?*  A safe system that refuses to act is a
        **mismatch** whenever legacy would have acted — that divergence is
        exactly the risk shadow mode exists to surface.
        """
        legacy_pids = set(legacy.get("pids") or [])
        safe_would_act = bool(shadow.get("allows_destructive_action"))
        safe_pid = shadow.get("pid") if safe_would_act else None
        confidence = shadow.get("confidence", "NONE")

        if res.ambiguous:
            return False, "ambiguous_candidates_legacy_would_kill_all"

        if not legacy_pids:
            if shadow.get("pid") is None:
                return True, "no_target"
            # A candidate exists but legacy would not have acted on it while
            # the safe system refuses as well: both are inactive, so they agree.
            return True, "legacy_and_safe_both_inactive"

        if not safe_would_act:
            return False, (
                f"safe_refuses_{len(legacy_pids)}_legacy_candidate(s)"
                f"_graded_{confidence}"
            )

        if safe_pid not in legacy_pids:
            return False, "safe_target_not_in_legacy_set"

        if len(legacy_pids) > 1:
            return False, f"legacy_would_kill_{len(legacy_pids)}_pids_safe_would_kill_1"

        return True, "legacy_and_safe_agree"


# --------------------------------------------------------------------------- #
# guarded observation hook
# --------------------------------------------------------------------------- #

def observe_operation(
    *,
    service: str,
    operation: Operation | str,
    port: int | None,
    comparator: ShadowComparator | None = None,
) -> ShadowComparison | None:
    """Observe one operation, returning ``None`` unless shadow mode is on.

    **This function must never raise and never act.**  It is called from the
    existing restart path purely to gather evidence; any failure inside it is
    swallowed so the legacy behaviour cannot be affected.

    Returns the comparison when shadow mode is active and the computation
    succeeded, otherwise ``None``.
    """
    if not shadow_enabled():
        return None
    try:
        cmp = (comparator or ShadowComparator()).compare(
            service=service, operation=operation, port=port)
        audit.log_identity_decision(
            service=service,
            operation=cmp.operation,
            candidate_pid=cmp.shadow.get("pid"),
            confidence=cmp.shadow.get("confidence", "NONE"),
            owned=bool(cmp.shadow.get("owned")),
            match=cmp.match,
            reason=cmp.reason,
            mode=ProcessMode.SHADOW.value,
        )
        if not cmp.match:
            audit.log_shadow_mismatch(service=service, operation=cmp.operation,
                                      legacy=cmp.legacy, shadow=cmp.shadow)
        return cmp
    except Exception:  # pragma: no cover - defensive: observation never breaks legacy
        return None


@dataclass
class ShadowReport:
    """Aggregate shadow report across services."""

    mode: str
    comparisons: list[ShadowComparison] = field(default_factory=list)

    @property
    def matches(self) -> int:
        return sum(1 for c in self.comparisons if c.match)

    @property
    def mismatches(self) -> int:
        return sum(1 for c in self.comparisons if not c.match)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "totals": {
                "services": len(self.comparisons),
                "matches": self.matches,
                "mismatches": self.mismatches,
            },
            "comparisons": [c.to_dict() for c in self.comparisons],
        }


def build_report(*, services: Sequence[str] | None = None,
                 operation: Operation | str = Operation.RESTART,
                 comparator: ShadowComparator | None = None,
                 only_running: bool = True) -> ShadowReport:
    """Build a shadow report for the requested services (read-only)."""
    comp = comparator or ShadowComparator()
    names = list(services) if services else comp.resolver.list_configured_services()
    report = ShadowReport(mode=current_mode().value)
    for name in names:
        resolution = comp.resolver.resolve_service(name)
        if only_running and not resolution.candidate_pids:
            continue
        report.comparisons.append(
            comp.compare(service=name, operation=operation, resolution=resolution))
    return report
