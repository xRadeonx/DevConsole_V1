"""Compose the infrastructure matrix without treating a partial catalog as complete.

V1.1 can receive infrastructure metadata from four local sources:

1. explicit ``config/panel.json`` rows from the current checkout;
2. a sibling/older DevConsole ``config/panel.json`` already used on the workstation;
3. a safely parsed historical V1 JavaScript catalog;
4. non-secret Keycloak/database endpoints already present in the in-memory
   environment catalog.

The important invariant is that a fresh ZIP must not silently reduce a working
SISPER matrix to only the two components that V1.1 can synthesize.  Existing
installation-specific ``infra_targets`` are configuration, not credentials, so
this adapter recovers them read-only from a neighbouring DevConsole checkout.
Explicit rows in the current checkout remain authoritative.
"""

from __future__ import annotations

import json
import urllib.parse
from pathlib import Path
from typing import Any

_INSTALLED = False
_ENVIRONMENTS = ("develop", "test", "main")
_CANONICAL_ENV_ORDER = ("local", "develop", "test", "main")
_MAX_PANEL_BYTES = 2_000_000
_ALLOWED_ROW_FIELDS = {
    "id",
    "name",
    "type",
    "target",
    "localKey",
    "k8sPod",
    "testUrl",
    "note",
    "cmd",
}


def _normalise_env(value: str) -> str:
    key = str(value or "").strip().lower()
    if key in {"prod", "production", "produccion", "main"}:
        return "main"
    if key in {"dev", "development", "develop", "desarrollo"}:
        return "develop"
    if key in {"qa", "testing", "test"}:
        return "test"
    if key in {"local", "localhost"}:
        return "local"
    return key


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


def _safe_panel_row(row: Any) -> dict[str, Any] | None:
    """Return one non-secret infrastructure row from a local panel file.

    ``infra_targets`` should contain only endpoints and probe metadata.  A
    malformed/local panel can still contain a secret marker, so do not promote
    such a value into the live matrix.
    """
    if not isinstance(row, dict):
        return None
    clean = {key: value for key, value in row.items() if key in _ALLOWED_ROW_FIELDS}
    key = _row_key(clean)
    target = clean.get("target")
    if not key or target in (None, ""):
        return None
    if "__SECRET__" in str(target):
        return None
    for optional in ("testUrl", "cmd"):
        if "__SECRET__" in str(clean.get(optional) or ""):
            clean[optional] = None if optional == "testUrl" else ""
    return clean


def _read_panel_targets_at(root: Path) -> dict[str, list[dict[str, Any]]]:
    """Read only ``infra_targets`` from one neighbouring panel.json."""
    path = Path(root) / "config" / "panel.json"
    try:
        if not path.is_file() or path.stat().st_size > _MAX_PANEL_BYTES:
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    raw_targets = payload.get("infra_targets")
    if not isinstance(raw_targets, dict):
        return {}

    result: dict[str, list[dict[str, Any]]] = {}
    for raw_env, raw_rows in raw_targets.items():
        env = _normalise_env(str(raw_env))
        if env not in _CANONICAL_ENV_ORDER or not isinstance(raw_rows, list):
            continue
        rows = [clean for row in raw_rows if (clean := _safe_panel_row(row)) is not None]
        if rows:
            result[env] = _merge_rows(result.get(env, []), rows)
    return result


def _read_sibling_panel_targets(root: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    """Choose the richest existing local DevConsole panel catalog.

    Automatic legacy discovery can see both the fresh V1.1 ZIP and an older
    checkout.  Returning the first panel would therefore be unstable.  Prefer
    the candidate with the broadest environment coverage and then the largest
    number of infrastructure rows.  This recovers the already-working matrix
    without combining unrelated installations.
    """
    try:
        from devconsole.v11_legacy_profile import _candidate_roots

        candidates = _candidate_roots(root)
    except Exception:
        candidates = [Path(root)] if root is not None else []

    best: dict[str, list[dict[str, Any]]] = {}
    best_score = (-1, -1)
    for candidate in candidates:
        targets = _read_panel_targets_at(Path(candidate))
        if not targets:
            continue
        score = (len(targets), sum(len(rows) for rows in targets.values()))
        if score > best_score:
            best = targets
            best_score = score
    return best


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


def _normalise_target_map(mapping: Any) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    if not isinstance(mapping, dict):
        return result
    for raw_env, rows in mapping.items():
        env = _normalise_env(str(raw_env))
        if env not in _CANONICAL_ENV_ORDER or not isinstance(rows, list):
            continue
        valid = [dict(row) for row in rows if isinstance(row, dict) and _row_key(row)]
        if valid:
            result[env] = _merge_rows(result.get(env, []), valid)
    return result


def compose_targets(explicit_or_current: dict[str, Any] | None = None) -> dict[str, list[dict[str, Any]]]:
    """Merge current, sibling-panel, historical and synthesized targets per env."""
    from devconsole.v11_legacy_profile import _read_legacy_infra_targets, hydrate_environment_catalog

    # Refreshing the local catalog is read-only and makes synthesis useful even
    # if the historical dashboard had no INFRA_ENDPOINTS literal.
    hydrate_environment_catalog()

    current = _normalise_target_map(explicit_or_current)
    sibling_panel = _normalise_target_map(_read_sibling_panel_targets())
    try:
        legacy = _normalise_target_map(_read_legacy_infra_targets())
    except Exception:
        legacy = {}
    synthesized = _normalise_target_map(_synthesized_targets())

    result: dict[str, list[dict[str, Any]]] = {}
    discovered_envs = set(current) | set(sibling_panel) | set(legacy) | set(synthesized)
    ordered_envs = [env for env in _CANONICAL_ENV_ORDER if env in discovered_envs]
    ordered_envs.extend(sorted(discovered_envs - set(ordered_envs)))

    for env in ordered_envs:
        rows: list[dict[str, Any]] = []
        # Current panel wins.  A sibling panel is the next-best representation
        # because it is the configuration that produced the already-working V1
        # matrix.  Historical JS and synthesis only fill actual gaps.
        for source in (current, sibling_panel, legacy, synthesized):
            source_rows = source.get(env, [])
            rows = _merge_rows(rows, source_rows)
        if rows:
            result[env] = rows
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
        "environments": [key for key in _CANONICAL_ENV_ORDER if targets.get(key)],
        "counts": {key: len(rows) for key, rows in targets.items() if rows},
        "sibling_panel_detected": bool(_read_sibling_panel_targets()),
    }
