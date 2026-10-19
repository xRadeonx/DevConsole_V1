"""Compatibility adapters for the existing Kubernetes API surface.

V1.1 keeps the public V1 function signatures but uses the structured
``ruamel.yaml`` implementation whenever available.  If the optional dependency
is absent, the previously shipped implementation remains the fallback so the
application never loses an existing capability in an offline installation.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import devconsole.config as dcfg
from devconsole.services.manifest_service import ManifestDependencyMissing, apply_image_tag_update


LegacyUpdate = Callable[[str, str, str], tuple[bool, str]]


def make_structured_update_yaml_version(legacy_update: LegacyUpdate) -> LegacyUpdate:
    def update(service_name: str, new_version: str, env_key: str = "develop") -> tuple[bool, str]:
        service = (service_name or "").strip()
        version = (new_version or "").strip()
        if not service:
            return False, "Servicio no indicado."
        if not version:
            return False, "Versión no indicada."

        from devconsole.services.k8s_service import k8s_dir_for

        all_services = list(dcfg.SERVICES_BACKEND) + list(dcfg.SERVICES_FRONTEND)
        meta = next((item for item in all_services if item.get("name") == service), None)
        if not meta or not meta.get("k8s_file"):
            # Preserve V1 discovery/fallback behavior for unusual installations.
            return legacy_update(service_name, new_version, env_key)

        root = (Path(dcfg.BASE_DIR) / k8s_dir_for(env_key)).resolve()
        manifest = (root / str(meta["k8s_file"])).resolve()
        try:
            manifest.relative_to(root)
        except ValueError:
            return False, "Ruta de manifiesto fuera de la carpeta Kubernetes permitida."
        if not manifest.is_file():
            return legacy_update(service_name, new_version, env_key)

        try:
            change = apply_image_tag_update(manifest, version)
        except ManifestDependencyMissing:
            return legacy_update(service_name, new_version, env_key)
        except Exception as exc:
            return False, f"No se pudo actualizar {manifest.name}: {exc}"

        if not change.changed:
            return False, f"No se encontró una imagen versionada actualizable en {manifest.name}."
        before = ", ".join(change.images_before) or "sin imagen"
        after = ", ".join(change.images_after) or "sin imagen"
        return True, f"{manifest.name} actualizado de [{before}] a [{after}] con parser YAML round-trip."

    return update


def install_k8s_compatibility_adapters() -> None:
    """Install structured mutation under the existing V1 call sites."""
    from devconsole.services import k8s_service
    from devconsole.services import build_service
    from devconsole.api import handlers

    current = k8s_service.update_yaml_version
    if getattr(current, "_devconsole_v11_structured", False):
        return
    wrapped = make_structured_update_yaml_version(current)
    setattr(wrapped, "_devconsole_v11_structured", True)
    k8s_service.update_yaml_version = wrapped
    handlers.update_yaml_version = wrapped
    build_service.update_yaml_version = wrapped
