"""Minimal audit logging for process identity decisions (roadmap phase 0B.7).

Design rules
------------
* **Never log secrets.**  This module logs only the fields listed in
  :func:`log_identity_decision`.  No environment variables, no command
  environment, no tokens, no paths outside the workspace.
* **Never flood.**  Identical consecutive decisions are de-duplicated per
  ``(service, operation, pid, confidence, match)`` key, so a polling caller
  cannot drown the journal.
* Standard :mod:`logging` only; the handler is the root logger already
  configured by the systemd unit (journald).
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

LOGGER_NAME = "devconsole.runtime.audit"

_logger = logging.getLogger(LOGGER_NAME)

#: Seconds during which an identical decision is not logged again.
DEDUP_WINDOW_SECONDS = 30.0

_lock = threading.Lock()
_recent: dict[tuple[Any, ...], float] = {}


def _should_emit(key: tuple[Any, ...]) -> bool:
    now = time.monotonic()
    with _lock:
        last = _recent.get(key)
        if last is not None and (now - last) < DEDUP_WINDOW_SECONDS:
            return False
        _recent[key] = now
        # Bound the de-duplication table so it can never grow without limit.
        if len(_recent) > 512:
            cutoff = now - DEDUP_WINDOW_SECONDS
            for k in [k for k, t in _recent.items() if t < cutoff]:
                _recent.pop(k, None)
    return True


def reset_dedup_state() -> None:
    """Clear the de-duplication table (used by tests)."""
    with _lock:
        _recent.clear()


def log_identity_decision(
    *,
    service: str,
    operation: str,
    candidate_pid: int | None,
    confidence: str,
    owned: bool,
    match: bool | None,
    reason: str | None = None,
    mode: str = "legacy",
) -> None:
    """Record one identity decision.

    Only the fields below are emitted; nothing else is derived from the
    process environment.
    """
    key = (service, operation, candidate_pid, confidence, owned, match, reason, mode)
    if not _should_emit(key):
        return
    _logger.info(
        "identity service=%s operation=%s mode=%s candidate_pid=%s "
        "confidence=%s owned=%s match=%s reason=%s",
        service,
        operation,
        mode,
        candidate_pid if candidate_pid is not None else "-",
        confidence,
        owned,
        match if match is not None else "-",
        reason or "-",
    )


def log_rejection(*, service: str, operation: str, pid: int | None, reason: str,
                  mode: str = "legacy") -> None:
    """Record that a candidate was refused.  Always ``owned=False``."""
    log_identity_decision(
        service=service,
        operation=operation,
        candidate_pid=pid,
        confidence="NONE",
        owned=False,
        match=None,
        reason=reason,
        mode=mode,
    )


def log_shadow_mismatch(*, service: str, operation: str, legacy: dict[str, Any],
                        shadow: dict[str, Any]) -> None:
    """Record a legacy/new divergence, which is the signal shadow mode exists for."""
    key = ("mismatch", service, operation,
           tuple(legacy.get("pids", ()) or ()), shadow.get("pid"))
    if not _should_emit(key):
        return
    _logger.warning(
        "shadow_mismatch service=%s operation=%s legacy_pids=%s shadow_pid=%s "
        "shadow_confidence=%s shadow_owned=%s",
        service,
        operation,
        ",".join(str(p) for p in (legacy.get("pids") or [])) or "-",
        shadow.get("pid") if shadow.get("pid") is not None else "-",
        shadow.get("confidence", "NONE"),
        shadow.get("owned", False),
    )
