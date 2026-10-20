"""Promote structured YAML updates with transparent V1 fallback.

When ruamel.yaml is available, image tag updates are performed on parsed YAML
and written atomically.  If the optional dependency is absent, the exact V1
``update_yaml_version`` function remains available.  The adapter is installed
before build/API modules import the function by value.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from devconsole.services import yaml_service

_INSTALLED = False
_ORIGINAL_UPDATE = None
_TAG_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$")


def _manifest_path(k8s_service, service_name: str, env_key: str) -> tuple[Path | None, str]:
    if env_key not in k8s_service.ENVIRONMENTS:
        return None, f"Entorno desconocido: {env_key}"

    services = list(k8s_service.SERVICES_BACKEND) + list(k8s_service.SERVICES_FRONTEND)
    metadata = next((item for item in services if item.get("name") == service_name), None)
    if not metadata or not metadata.get("k8s_file"):
        return None, "Servicio sin archivo de manifiesto K8s mapeado"

    root = (Path(k8s_service.BASE_DIR) / k8s_service.k8s_dir_for(env_key)).resolve()
    target = (root / str(metadata["k8s_file"])).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None, "Ruta de manifiesto fuera de la carpeta K8s del entorno"
    if not target.is_file():
        return None, f"Archivo no encontrado: {target}"
    return target, ""


def update_structured(k8s_service, legacy_update, service_name: str,
                      new_version: str, env_key: str = "develop") -> tuple[bool, str]:
    """Update one mapped manifest using structured YAML when possible."""
    version = str(new_version or "").strip()
    if not _TAG_RE.fullmatch(version):
        return False, "Versión de imagen inválida; usa una etiqueta OCI/Docker simple"

    if not yaml_service.available():
        return legacy_update(service_name, version, env_key)

    target, error = _manifest_path(k8s_service, service_name, env_key)
    if target is None:
        return False, error

    try:
        original = target.read_text(encoding="utf-8")
        updated, changes = yaml_service.update_image_tags(original, version)
    except Exception as exc:
        return False, f"YAML inválido o no procesable: {type(exc).__name__}: {exc}"

    if not changes:
        return False, "No se encontraron etiquetas de imagen para actualizar"

    valid, errors = yaml_service.validate_manifest(updated)
    if not valid:
        return False, "El manifiesto actualizado no pasó validación: " + "; ".join(errors)

    try:
        temporary = target.with_suffix(target.suffix + ".devconsole.tmp")
        temporary.write_text(updated, encoding="utf-8")
        temporary.replace(target)
    except OSError as exc:
        return False, f"No se pudo escribir {target.name}: {exc}"

    return True, f"Versión cambiada a {version} en {target.name} (YAML estructurado)"


def install() -> None:
    global _INSTALLED, _ORIGINAL_UPDATE
    if _INSTALLED:
        return

    from devconsole.services import k8s_service

    _ORIGINAL_UPDATE = k8s_service.update_yaml_version

    def update_yaml_version_v11(service_name: str, new_version: str,
                                env_key: str = "develop"):
        return update_structured(
            k8s_service,
            _ORIGINAL_UPDATE,
            service_name,
            new_version,
            env_key,
        )

    k8s_service.update_yaml_version = update_yaml_version_v11
    _INSTALLED = True


def status() -> dict[str, Any]:
    return {
        "installed": _INSTALLED,
        "structured_yaml_available": yaml_service.available(),
        "fallback": "legacy-update_yaml_version",
    }
