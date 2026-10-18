"""Runtime process-identity layer for DevConsole (roadmap phase 0B).

Replaces the unsafe notion ``service == port`` with ``service == an identified
process that provably belongs to this workspace``.

**This package has no destructive capability by design.**  It never imports
:mod:`signal`, never calls ``os.kill``/``os.killpg``, and never spawns
``pkill``/``kill``/``killall``/``fuser -k``.  The invariant is enforced by
``tests/devconsole/test_runtime_safety.py::test_runtime_has_no_destructive_primitives``.

Deliberately **not** part of this phase (see the roadmap): ``RuntimeManager``,
``TmuxManager``, ``TerminalBackend``, anything Electron or node-pty related.
"""

from devconsole.services.runtime.process_identity import (
    Confidence,
    Operation,
    ProcessFacts,
    ProcessIdentity,
    ServiceDescriptor,
    ServiceType,
)
from devconsole.services.runtime.process_inspector import ProcessInspector
from devconsole.services.runtime.process_ownership import (
    OwnershipVerdict,
    OwnershipVerifier,
    RejectionReason,
    command_matches_type,
    executable_matches_type,
    select_candidate,
)
from devconsole.services.runtime.process_resolver import (
    ProcessIdentityResolver,
    Resolution,
    build_descriptor,
)
from devconsole.services.runtime.shadow import (
    ENV_VAR,
    ProcessMode,
    ShadowComparator,
    ShadowComparison,
    ShadowReport,
    build_report,
    current_mode,
    observe_operation,
    shadow_enabled,
)

__all__ = [
    # identity model
    "Confidence",
    "Operation",
    "ProcessFacts",
    "ProcessIdentity",
    "ServiceDescriptor",
    "ServiceType",
    # inspection
    "ProcessInspector",
    # ownership / confidence
    "OwnershipVerdict",
    "OwnershipVerifier",
    "RejectionReason",
    "command_matches_type",
    "executable_matches_type",
    "select_candidate",
    # resolution
    "ProcessIdentityResolver",
    "Resolution",
    "build_descriptor",
    # shadow mode
    "ENV_VAR",
    "ProcessMode",
    "ShadowComparator",
    "ShadowComparison",
    "ShadowReport",
    "build_report",
    "current_mode",
    "observe_operation",
    "shadow_enabled",
]
