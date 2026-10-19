"""Compose the infrastructure matrix without treating a partial catalog as complete.

V1.1 can receive infrastructure metadata from three local sources:

1. explicit ``config/panel.json`` rows;
2. a safely parsed historical V1 checkout;
3. non-secret Keycloak/database endpoints already present in the in-memory
   environment catalog.

Earlier compatibility code returned as soon as source (1) was non-empty. A
workstation with only DEVELOP configured therefore hid TEST/MAIN even when the
legacy catalog knew about them. This adapter merges sources per environment and
per component while preserving explicit rows as authoritative.
"""

from __future__ import annotations

import urllib.parse
from typing import Any

_INSTALLED = False
_ENVIRONMENTS = ("develop", "test", "main")


def _row_key(row: dict[str, Any]) -> str:
    return str(row.get("id") or row.get("name") or row.get("target") or "").strip().lower()


def _merge_rows(primary: list[dict[str, Any]], fallback: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = [dict(row) for row in primary if isinstance(row, dict)]
    seen = {_row_key(row) for row in result if _row_key(row)}
    for row in fallback:
        if not isinstance(row, dict):
            continue
        key = _row_key(row)
        if not key or key in seen:
            continue
        result.append(dict(row))
        seen.add(key)
    return result


def _synthesized_targets() -> dict[str, list[dict[str, Any]]]:
    """Build non-secret rows from the effective in-memory environment maps."""
    from devconsole import config

    kc_map = getattr(config, "KEYCLOAK_ENV_CONFIGS", {}) or {}
    db_map = getattr(config, "DATABASE_ENV_CONFIGS", {}) or {}
    result: dict[str, list[dict[str, Any]]] = {}

    for env in _ENVIRONMENTS:
        rows: list[dict[str, Any]] = []

        db = db_map.get(env, {}) if isinstance(db_map, dict) else {}
        if isinstance(db, dict):
            host = str(db.get("host") or "").strip()
            try:
                port = int(db.get("port") or 5432)
            except (TypeError, ValueError):
                port = 5432
            if host:
                rows.append(
                    {
                        "id": "postgres",
                        "name": f"PostgreSQL {env.upper()}",
                        "type": "Base de Datos Relacional",
                        "target": f"{host}:{port}",
                        "testUrl": None,
                        "note": "Destino derivado del catálogo local de entorno",
                        "cmd": f"nc -zv {host} {port}",
                    }
                )

        kc = kc_map.get(env, {}) if isinstance(kc_map, dict) else {}
        if isinstance(kc, dict):
            url = str(kc.get("url") or "").strip().rstrip("/")
            if url:
                try:
                    parsed = urllib.parse.urlparse(url)
                    target = parsed.hostname or url
                except Exception:
                    target = url
                rows.append(
                    {
                        "id": "keycloak",
                        "name": f"Keycloak {env.upper()}",
                        "type": "Identidad / SSO",
                        "target": target,
                        "testUrl": url,
                        "note": "Destino derivado del catálogo local de entorno",
                        "cmd": f"curl -k -I --max-time 4 {url}",
                    }
                )

        if rows:
            result[env] = rows
    return result


def compose_targets(explicit_or_current: dict[str, Any] | None = None) -> dict[str, list[dict[str, Any]]]:
    """Merge explicit/current, historical and synthesized targets per env."""
    from devconsole.v11_legacy_profile import _read_legacy_infra_targets, hydrate_environment_catalog

    # Refreshing the local catalog is read-only and makes synthesis useful even
    # if the historical dashboard had no INFRA_ENDPOINTS literal.
    hydrate_environment_catalog()

    current = explicit_or_current if isinstance(explicit_or_current, dict) else {}
    try:
        legacy = _read_legacy_infra_targets()
    except Exception:
        legacy = {}
    synthesized = _synthesized_targets()

    result: dict[str, list[dict[str, Any]]] = {}
    all_envs = list(dict.fromkeys([*current.keys(), *legacy.keys(), *synthesized.keys()]))
    for env in all_envs:
        configured_rows = current.get(env, [])
        legacy_rows = legacy.get(env, [])
        synthesized_rows = synthesized.get(env, [])
        if not isinstance(configured_rows, list):
            configured_rows = []
        if not isinstance(legacy_rows, list):
            legacy_rows = []
        if not isinstance(synthesized_rows, list):
            synthesized_rows = []
        rows = _merge_rows(configured_rows, legacy_rows)
        rows = _merge_rows(rows, synthesized_rows)
        if rows:
            result[str(env)] = rows
    return result


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from devconsole import settings

    original = settings.infra_targets
    if getattr(original, "_v11_composed_infra", False) is True:
        _INSTALLED = True
        return

    def infra_targets_composed() -> dict:
        try:
            current = original()
        except Exception:
            current = {}
        return compose_targets(current)

    infra_targets_composed._v11_composed_infra = True  # type: ignore[attr-defined]
    settings.infra_targets = infra_targets_composed
    _INSTALLED = True


def status() -> dict[str, Any]:
    from devconsole import settings

    targets = settings.infra_targets() if _INSTALLED else compose_targets({})
    return {
        "installed": _INSTALLED,
        "environments": sorted(key for key, rows in targets.items() if rows),
        "counts": {key: len(rows) for key, rows in targets.items() if rows},
    }
