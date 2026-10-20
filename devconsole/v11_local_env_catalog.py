"""Recover non-secret DEVELOP connection metadata from local service .env files.

A workstation checkout often contains the values needed by Mapa Operativo and
Actividad in each service's local ``.env``.  Those files describe DEVELOP only;
this adapter never copies them into TEST or MAIN.

Only allow-listed connection metadata is recovered.  Passwords/client secrets
remain handled by the existing secrets workflow.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_INSTALLED = False

_KEYCLOAK_KEYS = {
    "KEYCLOAK_URL",
    "KEYCLOAK_BASE_URL",
    "KEYCLOAK_SERVER_URL",
    "KEYCLOAK_HOST",
    "KEYCLOAK_PORT",
    "KEYCLOAK_PROTOCOL",
    "KEYCLOAK_REALM",
    "KEYCLOAK_REALM_NAME",
    "KEYCLOAK_CLIENT_ID",
}
_DB_KEYS = {
    "DATABASE_HOST",
    "DATABASE_PORT",
    "DATABASE_NAME",
    "DATABASE_USER",
    "DB_HOST",
    "DB_PORT",
    "DB_NAME",
    "DB_USER",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "POSTGRES_USER",
}
_DB_SERVICE_HINTS = {
    "bitacora": "bitacora",
    "contratos": "contratos",
    "destinaciones": "destinaciones",
}


def _read_env(path: Path) -> dict[str, str]:
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
        if key not in _KEYCLOAK_KEYS and key not in _DB_KEYS:
            continue
        value = value.strip().strip('"').strip("'")
        if not value or "${" in value or "{{" in value:
            continue
        values.setdefault(key, value)
    return values


def _service_dirs(base_dir: Path) -> list[Path]:
    result: list[Path] = []
    seen: set[Path] = set()
    roots = [base_dir / "backend", base_dir / "frontend", base_dir]
    for root in roots:
        if not root.is_dir():
            continue
        try:
            children = list(root.iterdir())
        except OSError:
            continue
        for child in children:
            if not child.is_dir() or not (child / ".env").is_file():
                continue
            try:
                resolved = child.resolve()
            except OSError:
                resolved = child
            if resolved in seen:
                continue
            seen.add(resolved)
            result.append(child)
    return result


def scan_local_develop(base_dir: Path | None = None) -> dict[str, Any]:
    from devconsole import config
    from devconsole import v11_yaml_catalog as catalog

    base = Path(base_dir or config.BASE_DIR)
    keycloak: dict[str, Any] = {}
    database: dict[str, Any] = {}
    sources: dict[str, str] = {}

    for service in _service_dirs(base):
        values = _read_env(service / ".env")
        if not values:
            continue

        kc_values = {key: value for key, value in values.items() if key in _KEYCLOAK_KEYS}
        if kc_values:
            entry = catalog._keycloak_entry(kc_values)
            for key, value in entry.items():
                if key == "client_secret":
                    continue
                if value and not keycloak.get(key):
                    keycloak[key] = value
                    sources[f"keycloak.{key}"] = f"{service.name}/.env"

        logical = None
        lowered = service.name.lower().replace("-", "_")
        for name, token in _DB_SERVICE_HINTS.items():
            if token in lowered:
                logical = name
                break
        if logical:
            db_values = {key: value for key, value in values.items() if key in _DB_KEYS}
            fields = catalog._database_fields(db_values, logical)
            for key, value in fields.items():
                if key.endswith("_pass"):
                    continue
                if value not in (None, "", 0) and database.get(key) in (None, "", 0):
                    database[key] = value
                    sources[f"database.{key}"] = f"{service.name}/.env"

    return {"keycloak": keycloak, "database": database, "sources": sources}


def _merge_missing(target: dict[str, Any], source: dict[str, Any]) -> bool:
    changed = False
    for key, value in source.items():
        if value in (None, "", 0):
            continue
        if target.get(key) in (None, "", 0):
            target[key] = value
            changed = True
    return changed


def hydrate_local_develop(base_dir: Path | None = None) -> bool:
    from devconsole import config

    scanned = scan_local_develop(base_dir)
    changed = False

    kc_map = getattr(config, "KEYCLOAK_ENV_CONFIGS", None)
    if isinstance(kc_map, dict) and scanned["keycloak"]:
        changed = _merge_missing(kc_map.setdefault("develop", {}), scanned["keycloak"]) or changed

    db_map = getattr(config, "DATABASE_ENV_CONFIGS", None)
    if isinstance(db_map, dict) and scanned["database"]:
        changed = _merge_missing(db_map.setdefault("develop", {}), scanned["database"]) or changed

    try:
        from devconsole.services import telemetry_service as telemetry
    except Exception:
        telemetry = None
    if telemetry is not None:
        imported_kc = getattr(telemetry, "KEYCLOAK_ENV_CONFIGS", None)
        if isinstance(imported_kc, dict) and scanned["keycloak"]:
            changed = _merge_missing(imported_kc.setdefault("develop", {}), scanned["keycloak"]) or changed
        imported_db = getattr(telemetry, "DATABASE_ENV_CONFIGS", None)
        if isinstance(imported_db, dict) and scanned["database"]:
            changed = _merge_missing(imported_db.setdefault("develop", {}), scanned["database"]) or changed

    return changed


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from devconsole import v11_yaml_catalog as catalog

    original = catalog.hydrate_environment_catalog
    if not getattr(original, "_v11_local_env_catalog", False):
        def hydrate_with_local_env(base_dir: Path | None = None) -> bool:
            changed = original(base_dir)
            return bool(hydrate_local_develop(base_dir) or changed)

        hydrate_with_local_env._v11_local_env_catalog = True  # type: ignore[attr-defined]
        catalog.hydrate_environment_catalog = hydrate_with_local_env

    hydrate_local_develop()
    _INSTALLED = True


def status() -> dict[str, Any]:
    scanned = scan_local_develop()
    return {
        "installed": _INSTALLED,
        "keycloak_fields": sorted(scanned["keycloak"]),
        "database_fields": sorted(scanned["database"]),
        "sources": sorted(set(scanned["sources"].values())),
    }
