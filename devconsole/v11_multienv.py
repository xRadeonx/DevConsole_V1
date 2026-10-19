"""V1.1 multi-environment correctness layer.

V1 historically used DEVELOP as an implicit fallback whenever TEST/MAIN
configuration was missing.  That made the UI look as if the environment switch
worked while the backend was still querying DEVELOP.  This adapter removes that
ambiguous behaviour without rewriting the legacy telemetry service.

It also serves a bundled Chile map when the selected workspace does not contain
the historical SVG and exposes a secret-free environment capability endpoint
for the V1.1 UI.
"""

from __future__ import annotations

import functools
import urllib.parse
from pathlib import Path
from typing import Any, Callable

_INSTALLED_TELEMETRY = False
_INSTALLED_HANDLER = False


def _normalise_env(value: str | None) -> str:
    key = str(value or "develop").strip().lower()
    if key in {"prod", "production", "produccion", "main"}:
        return "main"
    if key in {"test", "qa", "testing"}:
        return "test"
    if key in {"dev", "develop", "desarrollo"}:
        return "develop"
    return key


def _refresh_local_catalog() -> None:
    """Refresh local compatibility data without performing network I/O."""
    try:
        from devconsole.v11_legacy_profile import hydrate_environment_catalog

        hydrate_environment_catalog()
    except Exception:
        # The legacy profile is an optional compatibility source. Explicit
        # panel/secrets configuration remains authoritative when it is absent.
        pass


def _environment_snapshot() -> dict[str, dict[str, Any]]:
    import devconsole.config as config

    _refresh_local_catalog()
    kc_map = getattr(config, "KEYCLOAK_ENV_CONFIGS", {}) or {}
    db_map = getattr(config, "DATABASE_ENV_CONFIGS", {}) or {}
    result: dict[str, dict[str, Any]] = {}
    for env in ("develop", "test", "main"):
        kc = kc_map.get(env) if isinstance(kc_map, dict) else None
        db = db_map.get(env) if isinstance(db_map, dict) else None
        kc_ok = isinstance(kc, dict) and bool(kc.get("url"))
        db_ok = isinstance(db, dict) and bool(db.get("host"))
        activity_ok = db_ok and bool(db.get("bitacora_db"))
        result[env] = {
            "configured": bool(kc_ok or db_ok),
            "keycloak": kc_ok,
            "database": db_ok,
            "activity": activity_ok,
            # Deliberately no URL, host, user, password, token or secret here.
        }
    return result


def environment_status() -> dict[str, Any]:
    envs = _environment_snapshot()
    return {
        "success": True,
        "environments": envs,
        "available": [name for name, state in envs.items() if state["configured"]],
        "telemetry_available": [
            name for name, state in envs.items()
            if state["keycloak"] and state["database"]
        ],
        "activity_available": [
            name for name, state in envs.items() if state["activity"]
        ],
    }


def _missing_payload(env: str, capability: str) -> dict[str, Any]:
    status = environment_status()
    return {
        "success": False,
        "error": f"Configuración {capability} no disponible para {env.upper()}",
        "configuration_missing": True,
        "requested_env": env,
        "env": env,
        "env_name": env.upper(),
        "available_environments": status.get("available", []),
        "items": [],
        "users": [],
        "zones": [],
        "count": 0,
        "unique_users": 0,
        "total_connections": 0,
        "keycloak": {"status": "not_configured", "latency_ms": 0},
        "db": {"configured": False},
    }


def _has_map_config(env: str) -> bool:
    state = _environment_snapshot().get(env, {})
    return bool(state.get("keycloak") and state.get("database"))


def _has_activity_config(env: str) -> bool:
    state = _environment_snapshot().get(env, {})
    return bool(state.get("activity"))


def _wrap_env_function(
    original: Callable[..., Any],
    *,
    capability: str,
    validator: Callable[[str], bool],
) -> Callable[..., Any]:
    # Some test doubles (notably unittest.mock.Mock) synthesize arbitrary
    # attributes on access; only the literal boolean marker means "wrapped".
    if getattr(original, "_v11_strict_environment", False) is True:
        return original

    @functools.wraps(original)
    def wrapper(*args, **kwargs):
        if "env_key" in kwargs:
            env = _normalise_env(kwargs.get("env_key"))
            kwargs["env_key"] = env
        elif args:
            env = _normalise_env(args[0])
            args = (env, *args[1:])
        else:
            env = "develop"
            kwargs["env_key"] = env

        _refresh_local_catalog()
        if env not in {"develop", "test", "main"} or not validator(env):
            return _missing_payload(env, capability)
        result = original(*args, **kwargs)
        if isinstance(result, dict):
            # Make the effective environment explicit so UI/tests can detect a
            # future regression instead of trusting a label.
            result = dict(result)
            result.setdefault("requested_env", env)
            result["effective_env"] = env
            result.setdefault("env", env)
        return result

    wrapper._v11_strict_environment = True  # type: ignore[attr-defined]
    return wrapper


def install_telemetry() -> None:
    """Promote strict multi-env semantics before handlers import functions."""
    global _INSTALLED_TELEMETRY
    if _INSTALLED_TELEMETRY:
        return

    from devconsole.services import telemetry_service

    telemetry_service.get_operational_map_data = _wrap_env_function(
        telemetry_service.get_operational_map_data,
        capability="de Mapa Operativo",
        validator=_has_map_config,
    )
    telemetry_service.get_live_activity_data = _wrap_env_function(
        telemetry_service.get_live_activity_data,
        capability="de Actividad",
        validator=_has_activity_config,
    )
    telemetry_service.get_activity_detail = _wrap_env_function(
        telemetry_service.get_activity_detail,
        capability="de Actividad",
        validator=_has_activity_config,
    )
    telemetry_service.get_user_live_session_info = _wrap_env_function(
        telemetry_service.get_user_live_session_info,
        capability="de Keycloak",
        validator=lambda env: bool(_environment_snapshot().get(env, {}).get("keycloak")),
    )
    _INSTALLED_TELEMETRY = True


def _map_candidates(handlers_module) -> list[Path]:
    import devconsole.config as config

    return [
        Path(config.BASE_DIR) / "config" / "chile_naval_map.svg",
        Path(handlers_module.DASHBOARD_DIR) / "static" / "assets" / "chile_naval_map_v11.svg",
    ]


def _send_trusted_json(handler, handlers_module, payload: dict[str, Any]) -> bool:
    ctx = handlers_module.resolve_caller(handler.headers, handler.client_address)
    trust = handlers_module.require_client_trust(ctx)
    if not trust.allowed:
        handler.send_json(trust.as_response(), status=trust.status)
        return False
    handler.send_json(payload)
    return True


def install_handler(handler_cls, handlers_module) -> None:
    """Add map fallback + environment diagnostics without replacing V1 routes."""
    global _INSTALLED_HANDLER
    if _INSTALLED_HANDLER:
        return

    original = handler_cls._do_GET
    if getattr(original, "_v11_multienv", False) is True:
        _INSTALLED_HANDLER = True
        return

    def _do_GET_multienv(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/v1.1/environments":
            _send_trusted_json(self, handlers_module, environment_status())
            return

        if path == "/api/map/chile_svg":
            ctx = handlers_module.resolve_caller(self.headers, self.client_address)
            trust = handlers_module.require_client_trust(ctx)
            if not trust.allowed:
                self.send_json(trust.as_response(), status=trust.status)
                return
            map_file = next((candidate for candidate in _map_candidates(handlers_module) if candidate.is_file()), None)
            if map_file is None:
                self.send_response(404)
                self._send_security_headers()
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self._send_security_headers()
            self.end_headers()
            self.wfile.write(map_file.read_bytes())
            return

        return original(self)

    _do_GET_multienv._v11_multienv = True  # type: ignore[attr-defined]
    handler_cls._do_GET = _do_GET_multienv
    _INSTALLED_HANDLER = True


def status() -> dict[str, Any]:
    return {
        "telemetry_installed": _INSTALLED_TELEMETRY,
        "handler_installed": _INSTALLED_HANDLER,
        **environment_status(),
    }
