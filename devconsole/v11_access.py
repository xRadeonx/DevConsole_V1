"""Compatibility access policy for the DevConsole V1.1 migration.

This module deliberately sits in front of the legacy V1 auth/security modules.
It lets V1.1 enforce the product rule (Viewer by default, Developer unlocked by
credential, Admin by session token) without rewriting the large HTTP/UI surface
in one step.

The adapter is temporary by design: once the API handlers and frontend auth
code are modularized, the same policy will live natively in those modules.
"""

from __future__ import annotations

import dataclasses
import os
import threading
import time
from typing import Any, Callable

_DEFAULT_DEV_TTL_HOURS = 24.0
_LOCK = threading.RLock()
_DEV_UNLOCK_UNTIL = 0.0
_INSTALLED = False
_ORIGINAL_VERIFY_PIN: Callable[..., tuple[bool, str]] | None = None
_ORIGINAL_RESOLVE_CALLER: Callable[..., Any] | None = None


def _ttl_seconds() -> float:
    raw = os.environ.get("SISPER_DEV_SESSION_TTL_HOURS", str(_DEFAULT_DEV_TTL_HOURS))
    try:
        hours = float(raw)
    except (TypeError, ValueError):
        hours = _DEFAULT_DEV_TTL_HOURS
    return max(60.0, min(hours * 3600.0, 7 * 24 * 3600.0))


def unlock_developer(*, ttl_seconds: float | None = None) -> float:
    """Unlock Developer capabilities for the current DevConsole process.

    The V1 frontend does not persist a developer session token.  During the
    migration we therefore keep a process-local, expiring unlock after the
    developer credential is successfully verified.  It is intentionally not
    written to disk and disappears when DevConsole restarts.
    """
    ttl = _ttl_seconds() if ttl_seconds is None else max(0.0, float(ttl_seconds))
    with _LOCK:
        global _DEV_UNLOCK_UNTIL
        _DEV_UNLOCK_UNTIL = time.time() + ttl
        return _DEV_UNLOCK_UNTIL


def lock_developer() -> None:
    """Immediately return Developer access to the locked state."""
    with _LOCK:
        global _DEV_UNLOCK_UNTIL
        _DEV_UNLOCK_UNTIL = 0.0


def developer_unlocked(*, now: float | None = None) -> bool:
    """Return whether the process-local Developer unlock is still valid."""
    current = time.time() if now is None else float(now)
    with _LOCK:
        return _DEV_UNLOCK_UNTIL > current


def developer_unlock_remaining(*, now: float | None = None) -> int:
    current = time.time() if now is None else float(now)
    with _LOCK:
        return max(0, int(_DEV_UNLOCK_UNTIL - current))


def _role_header(headers: Any) -> str:
    try:
        return str(headers.get("X-Auth-Role") or "").strip().lower()
    except Exception:
        return ""


def enforce_context(ctx: Any, headers: Any) -> Any:
    """Apply the V1.1 product-level role rule to a legacy CallerContext.

    * no role header -> Viewer (handled by patched DEFAULT_ROLE)
    * viewer -> Viewer
    * dev -> Developer only after successful developer PIN validation
    * admin -> unchanged; legacy security already requires a valid admin token
    """
    declared = _role_header(headers)
    role = getattr(ctx, "role", None)
    value = getattr(role, "value", "")

    if declared == "dev" and value == "dev" and not developer_unlocked():
        try:
            from devconsole.security import Role

            notes = tuple(getattr(ctx, "notes", ())) + ("developer_locked",)
            return dataclasses.replace(ctx, role=Role.VIEWER, notes=notes)
        except Exception:
            return ctx
    return ctx


def install() -> None:
    """Install the V1.1 policy before ``devconsole.api.handlers`` is imported.

    The operation is idempotent.  Only two legacy call points are wrapped:
    credential verification and caller resolution.  All authorization tables,
    endpoint behaviour and Admin session handling remain untouched.
    """
    global _INSTALLED, _ORIGINAL_VERIFY_PIN, _ORIGINAL_RESOLVE_CALLER
    with _LOCK:
        if _INSTALLED:
            return

        from devconsole import auth, security

        _ORIGINAL_VERIFY_PIN = auth.verify_pin
        _ORIGINAL_RESOLVE_CALLER = security.resolve_caller

        def verify_pin_v11(pin: str, role: str = "admin") -> tuple[bool, str]:
            assert _ORIGINAL_VERIFY_PIN is not None
            ok, token = _ORIGINAL_VERIFY_PIN(pin, role)
            if ok and role == "dev":
                unlock_developer()
            return ok, token

        def resolve_caller_v11(headers, client_address=None, *, port: int | None = None):
            assert _ORIGINAL_RESOLVE_CALLER is not None
            ctx = _ORIGINAL_RESOLVE_CALLER(headers, client_address, port=port)
            return enforce_context(ctx, headers)

        # Viewer/QA is the product baseline.  Keeping the existing self-declared
        # `dev` path temporarily is intentional: the wrapper above turns it into
        # Viewer until a valid developer credential has unlocked the process.
        security.DEFAULT_ROLE = security.Role.VIEWER
        auth.verify_pin = verify_pin_v11
        security.resolve_caller = resolve_caller_v11
        _INSTALLED = True


def status() -> dict[str, Any]:
    """Machine-readable status for diagnostics and future UI exposure."""
    return {
        "policy": "v1.1",
        "default_role": "viewer",
        "developer_unlocked": developer_unlocked(),
        "developer_unlock_remaining_seconds": developer_unlock_remaining(),
        "admin_model": "session-token",
        "developer_model": "process-local-expiring-unlock",
    }
