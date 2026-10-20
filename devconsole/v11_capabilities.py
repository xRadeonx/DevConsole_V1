"""Capability enrichment adapter for the V1.1 incremental migration.

V1 services keep their existing dictionary contract.  This module only appends
new metadata under stable keys so legacy consumers continue to work unchanged.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from devconsole.services.project_detector import ProjectProfile, detect_project

_INSTALLED = False
_ORIGINAL_DISCOVER = None


def _resolve_service_path(config_module, service: dict[str, Any], kind: str) -> Path | None:
    name = str(service.get("name") or "").strip()
    if not name:
        return None

    # Prefer the canonical resolver already used by DevConsole.
    try:
        path = config_module.get_service_repo_dir(name)
        if path:
            resolved = Path(path).expanduser().resolve()
            if resolved.is_dir():
                return resolved
    except Exception:
        pass

    base = Path(getattr(config_module, "BASE_DIR", "."))
    folder = "backend" if kind == "backend" else "frontend"
    candidate = (base / folder / name).resolve()
    return candidate if candidate.is_dir() else None


def _profile_payload(profile: ProjectProfile) -> dict[str, Any]:
    return {
        "kind": profile.kind,
        "languages": list(profile.languages),
        "frameworks": list(profile.frameworks),
        "package_manager": profile.package_manager,
        "manifests": list(profile.manifests),
        "capabilities": dict(profile.capabilities),
        "commands": dict(profile.commands),
        "signals": list(profile.signals),
        "confidence": profile.confidence,
    }


def enrich_service(config_module, service: dict[str, Any], kind: str) -> dict[str, Any]:
    """Append detector metadata to one existing V1 service dictionary."""
    if not isinstance(service, dict):
        return service
    path = _resolve_service_path(config_module, service, kind)
    if path is None:
        service.setdefault("detected", {
            "kind": kind,
            "languages": [],
            "frameworks": [],
            "package_manager": None,
            "manifests": [],
            "capabilities": {},
            "commands": {},
            "signals": ["service-path-unavailable"],
            "confidence": 0,
        })
        return service

    try:
        profile = detect_project(path)
    except Exception as exc:
        service.setdefault("detected", {
            "kind": kind,
            "languages": [],
            "frameworks": [],
            "package_manager": None,
            "manifests": [],
            "capabilities": {},
            "commands": {},
            "signals": [f"detector-error:{type(exc).__name__}"],
            "confidence": 0,
        })
        return service

    service["detected"] = _profile_payload(profile)
    return service


def enrich_lists(config_module, backend: list[dict], frontend: list[dict]):
    """Enrich lists in-place and return them for compatibility."""
    for service in backend or []:
        enrich_service(config_module, service, "backend")
    for service in frontend or []:
        enrich_service(config_module, service, "frontend")
    return backend, frontend


def install() -> None:
    """Enrich current services and future ``discover_services`` results.

    No service is added, removed or renamed.  Existing dictionaries are mutated
    only by adding the ``detected`` key.
    """
    global _INSTALLED, _ORIGINAL_DISCOVER
    if _INSTALLED:
        return

    import devconsole.config as config

    enrich_lists(config, config.SERVICES_BACKEND, config.SERVICES_FRONTEND)

    _ORIGINAL_DISCOVER = config.discover_services

    def discover_services_v11():
        backend, frontend = _ORIGINAL_DISCOVER()
        return enrich_lists(config, backend, frontend)

    config.discover_services = discover_services_v11
    _INSTALLED = True


def summary() -> dict[str, Any]:
    import devconsole.config as config

    services = list(config.SERVICES_BACKEND or []) + list(config.SERVICES_FRONTEND or [])
    detected = [svc for svc in services if isinstance(svc.get("detected"), dict)]
    return {
        "services": len(services),
        "detected": len(detected),
        "with_capabilities": sum(bool((svc.get("detected") or {}).get("capabilities")) for svc in detected),
    }
