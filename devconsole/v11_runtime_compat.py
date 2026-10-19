"""Runtime compatibility guards for the incremental V1.1 branch.

A fresh ZIP checkout intentionally does not contain ``config/panel.json`` or
``config/services.json``.  The legacy dashboard, however, still has a few V1
code paths that assume SISPER infrastructure/environment entries exist.  Those
assumptions must not make the entire status endpoint fail: filesystem discovery
must remain useful before the operator configures institutional integrations.

This module is installed before the HTTP handler imports service functions by
value.  It is deliberately small and additive; configured installations keep
using the original implementations.
"""

from __future__ import annotations

import subprocess
from typing import Any

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
                # A partially configured installation must still render status.
                pass
        return _fallback_infra_snapshot(infra_service)

    infra_service.get_infra_info = safe_get_infra_info


def _install_telemetry_defaults() -> None:
    """Avoid eager ``['develop']`` fallbacks exploding on fresh installs."""
    import devconsole.config as config
    from devconsole.services import telemetry_service

    for mapping_name in ("KEYCLOAK_ENV_CONFIGS", "DATABASE_ENV_CONFIGS"):
        mapping = getattr(config, mapping_name, None)
        if isinstance(mapping, dict):
            mapping.setdefault("develop", {})
        imported_mapping = getattr(telemetry_service, mapping_name, None)
        if isinstance(imported_mapping, dict):
            imported_mapping.setdefault("develop", {})


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


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _install_terminal_optional_capabilities()
    _install_telemetry_defaults()
    _install_infra_guard()
    _INSTALLED = True


def status() -> dict[str, Any]:
    return {"installed": _INSTALLED}
