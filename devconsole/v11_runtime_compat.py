"""Runtime compatibility guards for the incremental V1.1 branch.

A fresh ZIP checkout intentionally does not contain ``config/panel.json`` or
``config/services.json``. The legacy dashboard still has a few V1 code paths
that assume SISPER infrastructure/environment entries exist. Those assumptions
must not make the dashboard unusable before local installation data is present.

This adapter is installed before the HTTP handler imports service functions by
value. Explicit ``panel.json`` configuration always wins. When it is absent we
recover non-persistent runtime configuration from the selected workspace's
``.env`` files; secrets remain in memory and are never written to the repo.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_INSTALLED = False


def _container_state(runtime: str, name: str) -> str:
    try:
        return (
            subprocess.check_output(
                [runtime, "inspect", "--format", "{{.State.Status}}", name],
                stderr=subprocess.DEVNULL,
                timeout=2,
                text=True,
            ).strip()
            or "not_found"
        )
    except Exception:
        return "not_found"


def _image_exists(runtime: str, image: str) -> bool:
    if not image:
        return False
    try:
        return subprocess.run(
            [runtime, "image", "exists", image],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
            check=False,
        ).returncode == 0
    except Exception:
        return False


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return values
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        values[key] = value.strip().strip('"').strip("'")
    return values


def _pick(values: dict[str, str], *keys: str, default: str = "") -> str:
    for key in keys:
        value = str(values.get(key) or "").strip()
        if value:
            return value
    return default


def _workspace_backend_envs() -> dict[str, dict[str, str]]:
    import devconsole.config as config

    root = Path(config.BASE_DIR) / "backend"
    out: dict[str, dict[str, str]] = {}
    if not root.is_dir():
        return out
    try:
        children = list(root.iterdir())
    except OSError:
        return out
    for child in children:
        if child.is_dir() and (child / ".env").is_file():
            out[child.name] = _read_env_file(child / ".env")
    return out


def _env_with_any(envs: dict[str, dict[str, str]], preferred: tuple[str, ...], keys: tuple[str, ...]) -> dict[str, str]:
    for name in preferred:
        values = envs.get(name) or {}
        if any(_pick(values, key) for key in keys):
            return values
    for values in envs.values():
        if any(_pick(values, key) for key in keys):
            return values
    return {}


def _db_from_env(values: dict[str, str]) -> dict[str, Any]:
    user = _pick(values, "DATABASE_USER", "DB_USER", "POSTGRES_USER")
    db_name = _pick(values, "DATABASE_NAME", "DATABASE_DB", "DB_NAME", "POSTGRES_DB", default=user)
    port_raw = _pick(values, "DATABASE_PORT", "DB_PORT", "POSTGRES_PORT", default="5432")
    try:
        port = int(port_raw)
    except (TypeError, ValueError):
        port = 5432
    return {
        "host": _pick(values, "DATABASE_HOST", "DB_HOST", "POSTGRES_HOST"),
        "port": port,
        "db": db_name,
        "user": user,
        "pass": _pick(values, "DATABASE_PASSWORD", "DB_PASSWORD", "POSTGRES_PASSWORD"),
    }


def _discover_workspace_integrations() -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, str]]]:
    """Build the telemetry shape from the currently selected SISPER workspace."""
    envs = _workspace_backend_envs()

    kc_keys = (
        "KEYCLOAK_SERVER_URL", "KEYCLOAK_URL", "KEYCLOAK_REALM",
        "KEYCLOAK_CLIENT_ID", "KEYCLOAK_CLIENT_SECRET_KEY", "KEYCLOAK_CLIENT_SECRET",
    )
    kc_env = _env_with_any(
        envs,
        ("ms_sisper_sesion", "ms_sisper_adm_usuario", "ms_sisper_identificacion", "ms_sisper_contratos"),
        kc_keys,
    )
    kc_url = _pick(kc_env, "KEYCLOAK_SERVER_URL", "KEYCLOAK_URL").rstrip("/")
    keycloak = {
        "name": "DESARROLLO",
        "url": kc_url,
        "realm": _pick(kc_env, "KEYCLOAK_REALM", "KEYCLOAK_REALM_NAME", "KEYCLOAK_REALM_KEY", "REALM"),
        "client_id": _pick(kc_env, "KEYCLOAK_CLIENT_ID", "KEYCLOAK_CLIENT_ID_KEY", "CLIENT_ID"),
        "client_secret": _pick(
            kc_env,
            "KEYCLOAK_CLIENT_SECRET_KEY",
            "KEYCLOAK_CLIENT_SECRET",
            "CLIENT_SECRET",
        ),
        "ingress_ip": "",
    }

    bitacora = _db_from_env(envs.get("ms_sisper_bitacora") or {})
    contratos = _db_from_env(envs.get("ms_sisper_contratos") or {})
    destinaciones = _db_from_env(envs.get("ms_sisper_destinaciones") or {})
    first_db = next((item for item in (bitacora, contratos, destinaciones) if item.get("host")), {})
    database = {
        "host": first_db.get("host", ""),
        "port": first_db.get("port", 5432),
        "bitacora_db": bitacora.get("db", ""),
        "bitacora_user": bitacora.get("user", ""),
        "bitacora_pass": bitacora.get("pass", ""),
        "contratos_db": contratos.get("db", ""),
        "contratos_user": contratos.get("user", ""),
        "contratos_pass": contratos.get("pass", ""),
        "destinaciones_db": destinaciones.get("db", ""),
        "destinaciones_user": destinaciones.get("user", ""),
        "destinaciones_pass": destinaciones.get("pass", ""),
    }
    return keycloak, database, envs


def _merge_missing(target: dict[str, Any], discovered: dict[str, Any]) -> None:
    for key, value in discovered.items():
        if target.get(key) in (None, "", 0) and value not in (None, ""):
            target[key] = value


def _refresh_telemetry_from_workspace() -> None:
    import devconsole.config as config
    from devconsole.services import telemetry_service

    discovered_kc, discovered_db, _ = _discover_workspace_integrations()
    kc_defaults = {
        "name": "DESARROLLO",
        "url": "",
        "realm": "",
        "client_id": "",
        "client_secret": "",
        "ingress_ip": "",
    }
    db_defaults = {
        "host": "",
        "port": 5432,
        "bitacora_db": "",
        "bitacora_user": "",
        "bitacora_pass": "",
        "contratos_db": "",
        "contratos_user": "",
        "contratos_pass": "",
        "destinaciones_db": "",
        "destinaciones_user": "",
        "destinaciones_pass": "",
    }

    for module in (config, telemetry_service):
        kc_map = getattr(module, "KEYCLOAK_ENV_CONFIGS", None)
        if isinstance(kc_map, dict):
            entry = kc_map.setdefault("develop", {})
            if not isinstance(entry, dict):
                entry = {}
                kc_map["develop"] = entry
            for key, value in kc_defaults.items():
                entry.setdefault(key, value)
            _merge_missing(entry, discovered_kc)

        db_map = getattr(module, "DATABASE_ENV_CONFIGS", None)
        if isinstance(db_map, dict):
            entry = db_map.setdefault("develop", {})
            if not isinstance(entry, dict):
                entry = {}
                db_map["develop"] = entry
            for key, value in db_defaults.items():
                entry.setdefault(key, value)
            _merge_missing(entry, discovered_db)


def _discover_infra_targets() -> dict[str, list[dict[str, Any]]]:
    """Rebuild the read-only infrastructure matrix without persisting secrets."""
    keycloak, database, envs = _discover_workspace_integrations()

    local = [
        {"id": "postgres", "name": "🐘 PostgreSQL", "type": "Base de Datos Relacional", "target": "127.0.0.1:5432", "localKey": "postgres_local", "testUrl": None, "note": "PostgreSQL local", "cmd": "nc -zv 127.0.0.1 5432"},
        {"id": "keycloak", "name": "🔐 Keycloak", "type": "Identidad / SSO", "target": "http://127.0.0.1:8080", "localKey": "keycloak", "testUrl": "http://127.0.0.1:8080", "note": "Keycloak local", "cmd": "curl -I http://127.0.0.1:8080"},
        {"id": "rabbitmq", "name": "🐰 RabbitMQ", "type": "Mensajería", "target": "127.0.0.1:5672", "localKey": "rabbitmq_local", "testUrl": None, "note": "RabbitMQ local", "cmd": "nc -zv 127.0.0.1 5672"},
        {"id": "keydb", "name": "⚡ KeyDB", "type": "Cache", "target": "127.0.0.1:6379", "localKey": "keydb", "testUrl": None, "note": "KeyDB local", "cmd": "nc -zv 127.0.0.1 6379"},
        {"id": "onlyoffice", "name": "📄 OnlyOffice", "type": "DocumentServer", "target": "http://127.0.0.1:8082", "localKey": "onlyoffice", "testUrl": "http://127.0.0.1:8082", "note": "OnlyOffice local", "cmd": "curl -I http://127.0.0.1:8082"},
    ]

    develop: list[dict[str, Any]] = []
    db_host = str(database.get("host") or "")
    db_port = int(database.get("port") or 5432)
    if db_host:
        develop.append({"id": "postgres", "name": "🐘 PostgreSQL", "type": "Base de Datos Relacional", "target": f"{db_host}:{db_port}", "localKey": None, "testUrl": None, "note": "Descubierto desde los .env del workspace", "cmd": f"nc -zv {db_host} {db_port}"})

    kc_url = str(keycloak.get("url") or "")
    if kc_url:
        parsed = urlparse(kc_url)
        host = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        develop.append({"id": "keycloak", "name": "🔐 Keycloak", "type": "Identidad / SSO", "target": kc_url, "localKey": None, "testUrl": kc_url, "note": "Descubierto desde los .env del workspace", "cmd": f"nc -zv {host} {port}" if host else ""})

    broker_env = _env_with_any(
        envs,
        ("ms_sisper_sesion", "ms_sisper_bitacora"),
        ("RABBITMQ_HOST", "BROKER_HOST", "CELERY_BROKER_URL"),
    )
    broker_host = _pick(broker_env, "RABBITMQ_HOST", "BROKER_HOST")
    if not broker_host:
        broker_url = _pick(broker_env, "CELERY_BROKER_URL")
        if broker_url:
            parsed_broker = urlparse(broker_url)
            broker_host = parsed_broker.hostname or ""
            broker_port = parsed_broker.port or 5672
        else:
            broker_port = 5672
    else:
        broker_port_raw = _pick(broker_env, "RABBITMQ_PORT", "BROKER_PORT", default="5672")
        try:
            broker_port = int(broker_port_raw)
        except (TypeError, ValueError):
            broker_port = 5672
    if broker_host:
        develop.append({"id": "rabbitmq", "name": "🐰 RabbitMQ", "type": "Mensajería", "target": f"{broker_host}:{broker_port}", "localKey": None, "testUrl": None, "note": "Descubierto desde los .env del workspace", "cmd": f"nc -zv {broker_host} {broker_port}"})

    office_env = _env_with_any(envs, ("ms_sisper_contratos",), ("ONLYOFFICE_DOCUMENTSERVER_URL", "ONLYOFFICE_API_URL"))
    office_url = _pick(office_env, "ONLYOFFICE_DOCUMENTSERVER_URL", "ONLYOFFICE_API_URL")
    if office_url:
        develop.append({"id": "onlyoffice", "name": "📄 OnlyOffice", "type": "DocumentServer", "target": office_url, "localKey": None, "testUrl": office_url, "note": "Descubierto desde los .env del workspace", "cmd": ""})

    return {"local": local, "develop": develop}


def _fallback_infra_snapshot(infra_module) -> dict[str, Any]:
    """Return the legacy response shape without assuming a local catalog."""
    cfg = getattr(infra_module, "INFRA_CONTAINERS", {}) or {}
    keydb_cfg = cfg.get("keydb") or {}
    office_cfg = cfg.get("onlyoffice-local") or {}

    keydb_image = str(keydb_cfg.get("image") or "")
    office_image = str(office_cfg.get("image") or "")

    probe_host = ""
    try:
        probe_host = infra_module._probe_host() or ""
    except Exception:
        pass

    missing = []
    if not keydb_cfg:
        missing.append("keydb")
    if not office_cfg:
        missing.append("onlyoffice-local")

    try:
        contracts_env = infra_module.sync_contracts_onlyoffice_env(auto_fix=False)
    except Exception as exc:
        contracts_env = {
            "success": False,
            "synced": False,
            "updated": False,
            "message": f"OnlyOffice no configurado: {type(exc).__name__}",
        }

    return {
        "configured": not missing,
        "configuration_missing": missing,
        "keydb": {
            "port_open": infra_module.is_port_open(6379),
            "container": _container_state("podman", "keydb"),
            "image_exists": _image_exists("podman", keydb_image),
            "image": keydb_image,
            "configured": bool(keydb_cfg),
        },
        "onlyoffice": {
            "port_open": infra_module.is_port_open(8082),
            "container": _container_state("podman", "onlyoffice-local"),
            "image_exists": _image_exists("podman", office_image),
            "image": office_image,
            "contracts_env": contracts_env,
            "configured": bool(office_cfg),
        },
        "keycloak": {
            "port_open": infra_module.is_port_open(8080),
            "container": _container_state("docker", "keycloak-sisper-local"),
        },
        "postgres_local": {"port_open": infra_module.is_port_open(5432, "127.0.0.1")},
        "postgres_intranet": {
            "port_open": infra_module.is_port_open(5432, probe_host) if probe_host else False
        },
        "mongo_local": {"port_open": infra_module.is_port_open(27017, "127.0.0.1")},
        "rabbitmq_local": {"port_open": infra_module.is_port_open(5672, "127.0.0.1")},
        "k8s_infra": {"develop": {}, "test": {}, "prod": {}},
    }


def _install_infra_guard() -> None:
    from devconsole.services import infra_service
    from devconsole.services.ttl_cache import ttl_cache

    original = infra_service.get_infra_info

    @ttl_cache(seconds=45)
    def safe_get_infra_info() -> dict[str, Any]:
        cfg = getattr(infra_service, "INFRA_CONTAINERS", {}) or {}
        if cfg.get("keydb") and cfg.get("onlyoffice-local"):
            try:
                return original()
            except KeyError:
                pass
        return _fallback_infra_snapshot(infra_service)

    infra_service.get_infra_info = safe_get_infra_info


def _install_infra_targets_fallback() -> None:
    from devconsole import settings

    original = settings.infra_targets
    if getattr(original, "_v11_workspace_fallback", False):
        return

    def infra_targets_v11() -> dict:
        configured = original()
        if configured:
            return configured
        return _discover_infra_targets()

    infra_targets_v11._v11_workspace_fallback = True  # type: ignore[attr-defined]
    settings.infra_targets = infra_targets_v11


def _install_telemetry_defaults() -> None:
    """Recover telemetry settings from the selected workspace when necessary."""
    from devconsole.services import telemetry_service

    _refresh_telemetry_from_workspace()

    names = (
        "get_operational_map_data",
        "get_live_activity_data",
        "get_activity_detail",
        "get_user_live_session_info",
    )
    for name in names:
        original = getattr(telemetry_service, name)
        if getattr(original, "_v11_workspace_refresh", False):
            continue

        def wrapper(*args, __original=original, **kwargs):
            _refresh_telemetry_from_workspace()
            return __original(*args, **kwargs)

        wrapper.__name__ = getattr(original, "__name__", name)
        wrapper.__doc__ = getattr(original, "__doc__", None)
        wrapper._v11_workspace_refresh = True  # type: ignore[attr-defined]
        setattr(telemetry_service, name, wrapper)


def _install_public_auth_policy() -> None:
    """Authentication endpoints must be reachable while the caller is Viewer."""
    from devconsole import security

    original = security.authorize_post
    if getattr(original, "_v11_public_auth", False):
        return

    def authorize_post_v11(path, ctx, payload=None):
        if path in security.PUBLIC_PATHS:
            return security.require_client_trust(ctx)
        return original(path, ctx, payload)

    authorize_post_v11._v11_public_auth = True  # type: ignore[attr-defined]
    security.authorize_post = authorize_post_v11


def _install_terminal_optional_capabilities() -> None:
    """Give non-tmux backends safe defaults for optional viewer APIs."""
    from devconsole.services.terminal.base import TerminalBackend

    if not hasattr(TerminalBackend, "managed_sessions"):
        def managed_sessions(self):
            return []

        TerminalBackend.managed_sessions = managed_sessions  # type: ignore[attr-defined]

    if not hasattr(TerminalBackend, "attach_viewers"):
        def attach_viewers(self, services, title=None):
            names = [str(name) for name in (services or []) if str(name).strip()]
            if not names:
                return False, "No hay sesiones gestionadas para adjuntar."

            opened = 0
            messages: list[str] = []
            for name in names:
                try:
                    ok, message = self.attach_viewer(name, title=title)
                except TypeError:
                    ok, message = self.attach_viewer(name)
                except Exception as exc:
                    ok, message = False, f"{type(exc).__name__}: {exc}"
                if ok:
                    opened += 1
                if message:
                    messages.append(str(message))

            if opened:
                return True, f"Visor abierto para {opened} servicio(s)."
            return False, messages[-1] if messages else "El backend no soporta visor adjunto."

        TerminalBackend.attach_viewers = attach_viewers  # type: ignore[attr-defined]


def _preferred_terminal_backend(raw: str | None = None) -> str | None:
    """Use tmux as process owner unless the operator explicitly selected another backend."""
    value = os.environ.get("SISPER_TERMINAL_BACKEND", "") if raw is None else raw
    return value.strip().lower() or "tmux"


def _install_terminal_preference() -> None:
    import devconsole.services.terminal as terminal_api

    original = terminal_api.get_terminal_backend
    if getattr(original, "_v11_tmux_default", False):
        return

    def get_terminal_backend_v11(name=None):
        if name is not None:
            return original(name)
        return original(_preferred_terminal_backend())

    get_terminal_backend_v11._v11_tmux_default = True  # type: ignore[attr-defined]
    terminal_api.get_terminal_backend = get_terminal_backend_v11


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _install_public_auth_policy()
    _install_terminal_optional_capabilities()
    _install_terminal_preference()
    _install_telemetry_defaults()
    _install_infra_guard()
    _install_infra_targets_fallback()
    _INSTALLED = True


def status() -> dict[str, Any]:
    return {
        "installed": _INSTALLED,
        "terminal_default": _preferred_terminal_backend(),
        "workspace_integrations": True,
    }
