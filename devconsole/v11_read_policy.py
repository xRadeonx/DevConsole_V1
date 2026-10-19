"""Read-side authorization policy for sensitive V1 endpoints.

V1 centralised authorization for POST routes but kept every GET endpoint behind
client-trust only.  That was sufficient against cross-origin theft, not against
least-privilege mistakes inside the product: Viewer/QA could still request raw
.env values and user-level operational telemetry.

This adapter protects only the sensitive reads.  All status/QA endpoints retain
their V1 behaviour.  It is installed on the handler class after import so the
large legacy dispatcher does not need a risky big-bang rewrite.
"""

from __future__ import annotations

import urllib.parse
from typing import Any

from devconsole import security

# Minimum product role for sensitive read endpoints.  Everything absent from
# this table keeps the existing Viewer-compatible GET behaviour.
READ_MIN_ROLE: dict[str, security.Role] = {
    "/api/env/get": security.Role.DEV,
    "/api/analytics/connections": security.Role.ADMIN,
    "/api/activity/feed": security.Role.ADMIN,
    "/api/activity/detail": security.Role.ADMIN,
    "/api/telemetry/live": security.Role.ADMIN,
    "/api/telemetry/mirror_view": security.Role.ADMIN,
}

_INSTALLED = False
_ORIGINAL_DO_GET = None


def required_role(path: str) -> security.Role | None:
    """Return the minimum role for a path, or ``None`` for normal Viewer GETs."""
    return READ_MIN_ROLE.get(path)


def decision(path: str, headers: Any, client_address=None) -> tuple[bool, int, dict[str, Any]]:
    """Evaluate a sensitive read without executing its handler."""
    minimum = required_role(path)
    if minimum is None:
        return True, 200, {}

    ctx = security.resolve_caller(headers, client_address)
    trust = security.require_client_trust(ctx)
    if not trust.allowed:
        return False, trust.status, trust.as_response()

    if not ctx.role.at_least(minimum):
        return False, 403, {
            "success": False,
            "message": f"Esta lectura requiere rol {minimum.value}.",
            "required_role": minimum.value,
            "current_role": ctx.role.value,
        }
    return True, 200, {
        "required_role": minimum.value,
        "current_role": ctx.role.value,
    }


def install(handler_cls) -> None:
    """Wrap ``_do_GET`` while preserving the complete V1 dispatcher."""
    global _INSTALLED, _ORIGINAL_DO_GET
    if _INSTALLED:
        return

    _ORIGINAL_DO_GET = handler_cls._do_GET

    def _do_GET_v11(self):
        path = urllib.parse.urlparse(self.path).path
        minimum = required_role(path)
        if minimum is not None:
            allowed, status, payload = decision(path, self.headers, self.client_address)
            if not allowed:
                self.send_json(payload, status=status)
                return
        return _ORIGINAL_DO_GET(self)

    handler_cls._do_GET = _do_GET_v11
    _INSTALLED = True


def status() -> dict[str, Any]:
    return {
        "installed": _INSTALLED,
        "sensitive_reads": {path: role.value for path, role in READ_MIN_ROLE.items()},
    }
