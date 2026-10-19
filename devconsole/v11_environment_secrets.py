"""Apply explicitly configured local secrets to the recovered environment catalog.

No credential is embedded in source control and this module never searches Git
history or unrelated files. Values are read only from ``config/secrets.json``
(the existing 0600 local store) and merged into the in-memory environment maps.
"""

from __future__ import annotations

import sys
from typing import Any

_INSTALLED = False
_ENVIRONMENTS = ("develop", "test", "main")
_DB_LOGICAL = ("bitacora", "contratos", "destinaciones")


def _secret_keys() -> list[str]:
    keys: list[str] = []
    for env in _ENVIRONMENTS:
        keys.append(f"keycloak.{env}.client_secret")
        for logical in _DB_LOGICAL:
            keys.append(f"databases.{env}.{logical}_pass")
    return keys


def apply_secret_overlay() -> bool:
    """Merge only values the operator explicitly saved in secrets.json."""
    from devconsole import config, settings

    changed = False
    telemetry = sys.modules.get("devconsole.services.telemetry_service")

    maps: list[tuple[dict[str, Any], dict[str, Any]]] = []
    kc_current = getattr(config, "KEYCLOAK_ENV_CONFIGS", None)
    db_current = getattr(config, "DATABASE_ENV_CONFIGS", None)
    if isinstance(kc_current, dict) and isinstance(db_current, dict):
        maps.append((kc_current, db_current))

    kc_imported = getattr(telemetry, "KEYCLOAK_ENV_CONFIGS", None) if telemetry else None
    db_imported = getattr(telemetry, "DATABASE_ENV_CONFIGS", None) if telemetry else None
    if (
        isinstance(kc_imported, dict)
        and isinstance(db_imported, dict)
        and (kc_imported is not kc_current or db_imported is not db_current)
    ):
        maps.append((kc_imported, db_imported))

    for kc_map, db_map in maps:
        for env in _ENVIRONMENTS:
            kc_entry = kc_map.get(env)
            if isinstance(kc_entry, dict) and not kc_entry.get("client_secret"):
                value = settings.secret(f"keycloak.{env}.client_secret")
                if value:
                    kc_entry["client_secret"] = value
                    changed = True

            db_entry = db_map.get(env)
            if not isinstance(db_entry, dict):
                continue
            for logical in _DB_LOGICAL:
                field = f"{logical}_pass"
                if db_entry.get(field):
                    continue
                value = settings.secret(f"databases.{env}.{logical}_pass")
                if value:
                    db_entry[field] = value
                    changed = True
    return changed


def _install_required_keys() -> None:
    from devconsole import settings

    original = settings.referenced_secret_keys
    if getattr(original, "_v11_environment_secrets", False) is True:
        return

    def referenced_secret_keys_v11() -> list[str]:
        return sorted(set(original()) | set(_secret_keys()))

    referenced_secret_keys_v11._v11_environment_secrets = True  # type: ignore[attr-defined]
    settings.referenced_secret_keys = referenced_secret_keys_v11


def _install_save_refresh() -> None:
    from devconsole import settings

    original = settings.set_secrets
    if getattr(original, "_v11_environment_secrets", False) is True:
        return

    def set_secrets_v11(values: dict):
        result = original(values)
        try:
            ok = bool(result[0])
        except Exception:
            ok = False
        if ok:
            settings.reload()
            apply_secret_overlay()
        return result

    set_secrets_v11._v11_environment_secrets = True  # type: ignore[attr-defined]
    settings.set_secrets = set_secrets_v11


def _install_catalog_refresh() -> None:
    """Apply local secrets whenever the legacy catalog is refreshed."""
    try:
        from devconsole import v11_legacy_profile as legacy
    except Exception:
        return

    original = legacy.hydrate_environment_catalog
    if getattr(original, "_v11_environment_secrets", False) is True:
        return

    def hydrate_with_secrets(*args, **kwargs):
        changed = original(*args, **kwargs)
        return bool(apply_secret_overlay() or changed)

    hydrate_with_secrets._v11_environment_secrets = True  # type: ignore[attr-defined]
    legacy.hydrate_environment_catalog = hydrate_with_secrets


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _install_required_keys()
    _install_save_refresh()
    _install_catalog_refresh()
    apply_secret_overlay()
    _INSTALLED = True


def status() -> dict[str, Any]:
    from devconsole import settings

    present = settings.secret_values_present()
    return {
        "installed": _INSTALLED,
        "configured": sorted(key for key in _secret_keys() if key in present),
        "missing": sorted(key for key in _secret_keys() if key not in present),
    }
