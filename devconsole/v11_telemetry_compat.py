"""Compatibility metadata for legacy telemetry responses.

The original V1 telemetry formatter expects every Keycloak environment entry to
contain a decorative ``name`` field.  Catalogs recovered from Kubernetes YAML
only need the actual connection metadata and therefore may omit that label.
TEST/MAIN can be fully configured and still crash at response formatting with
``KeyError: 'name'``.

This adapter adds only a non-secret display label (DEVELOP/TEST/MAIN).  It does
not alter endpoints, credentials, database targets or environment selection.
"""

from __future__ import annotations

import sys
from typing import Any

_INSTALLED = False
_ENV_LABELS = {
    "develop": "DEVELOP",
    "test": "TEST",
    "main": "MAIN",
}


def _apply_to_map(mapping: Any) -> bool:
    if not isinstance(mapping, dict):
        return False
    changed = False
    for env, label in _ENV_LABELS.items():
        entry = mapping.get(env)
        if not isinstance(entry, dict):
            continue
        # Only enrich a real Keycloak target.  Never create an environment from
        # a label alone and never overwrite an explicit legacy display name.
        if entry.get("url") and not entry.get("name"):
            entry["name"] = label
            changed = True
    return changed


def apply_environment_labels() -> bool:
    """Add missing non-secret display names to current/imported Keycloak maps."""
    from devconsole import config

    changed = _apply_to_map(getattr(config, "KEYCLOAK_ENV_CONFIGS", None))

    telemetry = sys.modules.get("devconsole.services.telemetry_service")
    if telemetry is not None:
        imported = getattr(telemetry, "KEYCLOAK_ENV_CONFIGS", None)
        current = getattr(config, "KEYCLOAK_ENV_CONFIGS", None)
        if imported is not current:
            changed = _apply_to_map(imported) or changed
    return changed


def _install_catalog_refresh() -> None:
    """Re-apply labels after every local catalog refresh used by telemetry."""
    try:
        from devconsole import v11_legacy_profile as legacy
    except Exception:
        return

    original = legacy.hydrate_environment_catalog
    if getattr(original, "_v11_telemetry_compat", False) is True:
        return

    def hydrate_with_labels(*args, **kwargs):
        changed = original(*args, **kwargs)
        return bool(apply_environment_labels() or changed)

    hydrate_with_labels._v11_telemetry_compat = True  # type: ignore[attr-defined]
    legacy.hydrate_environment_catalog = hydrate_with_labels


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _install_catalog_refresh()
    apply_environment_labels()
    _INSTALLED = True


def status() -> dict[str, Any]:
    return {
        "installed": _INSTALLED,
        "labels": dict(_ENV_LABELS),
    }
