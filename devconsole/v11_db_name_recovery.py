"""Recover missing logical database names without embedding installation values.

Mapa Operativo needs distinct database names for Contratos and Destinaciones.
Some Kubernetes deployments provide host/user/password but omit an explicit
DATABASE_NAME because the application derives it from its service convention.

This adapter has two conservative recovery paths:

1. Parse a PostgreSQL URL/DSN when one is present in config YAML.
2. If the DB name is still absent, infer ``db_<service-user>`` only when the
   already-discovered PostgreSQL user unambiguously looks like the matching
   microservice account (for example an ``ms_*_contratos`` account).

No concrete host, user, database name or credential is embedded in source.
Nothing is persisted and DEVELOP is never copied into TEST/MAIN.
"""

from __future__ import annotations

import re
import sys
import urllib.parse
from pathlib import Path
from typing import Any

_INSTALLED = False
_ENVIRONMENTS = ("develop", "test", "main")
_LOGICAL = ("bitacora", "contratos", "destinaciones")
_LOGICAL_TOKENS = {
    "bitacora": {"bitacora", "bitacoras", "audit", "auditoria"},
    "contratos": {"contratos", "contrato", "ctto", "cttos"},
    "destinaciones": {"destinaciones", "destinacion", "destino", "destinos", "dest"},
}
_URL_KEYS = {
    "DATABASE_URL",
    "DB_URL",
    "POSTGRES_URL",
    "POSTGRESQL_URL",
    "DATABASE_DSN",
    "DB_DSN",
    "POSTGRES_DSN",
    "POSTGRESQL_DSN",
    "PG_DSN",
}


def _clean(value: str) -> str:
    value = str(value or "").strip().strip('"').strip("'")
    if not value or "${" in value or "{{" in value or value.startswith("__SECRET__"):
        return ""
    return value


def _logical_from_text(value: str) -> str | None:
    tokens = {token for token in re.split(r"[^a-z0-9]+", str(value or "").lower()) if token}
    matches = [logical for logical, aliases in _LOGICAL_TOKENS.items() if tokens & aliases]
    return matches[0] if len(matches) == 1 else None


def _database_from_url(value: str) -> str:
    raw = _clean(value)
    if not raw:
        return ""
    try:
        parsed = urllib.parse.urlparse(raw)
    except ValueError:
        return ""
    if parsed.scheme.lower() not in {"postgres", "postgresql", "pgsql"}:
        return ""
    name = urllib.parse.unquote((parsed.path or "").lstrip("/")).strip()
    if not name or "/" in name or len(name) > 63:
        return ""
    return name


def _extract_yaml_db_names(base_dir: Path | None = None) -> dict[str, dict[str, str]]:
    """Read only database names from explicit PostgreSQL URLs/DSNs in YAML."""
    from devconsole import v11_yaml_catalog as catalog

    result: dict[str, dict[str, str]] = {}
    key_pattern = re.compile(r"^[A-Z][A-Z0-9_]*$")

    for path in catalog._yaml_files(base_dir):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        env = catalog._detect_environment(path, text, base_dir)
        if env not in _ENVIRONMENTS:
            continue
        default_logical = catalog._logical_database(path, text)
        lines = text.splitlines()
        pending_key = ""
        pending_indent = -1

        for raw in lines:
            stripped = raw.strip()
            indent = len(raw) - len(raw.lstrip())
            name_match = re.match(r"^-?\s*name\s*:\s*['\"]?([A-Z][A-Z0-9_]*)['\"]?\s*$", stripped)
            if name_match:
                pending_key = name_match.group(1)
                pending_indent = indent
                continue
            if pending_key:
                value_match = re.match(r"^value\s*:\s*(.+)$", stripped)
                if value_match:
                    key = pending_key
                    pending_key = ""
                    if key in _URL_KEYS or key.endswith("_DATABASE_URL") or key.endswith("_DB_URL") or key.endswith("_DSN"):
                        db_name = _database_from_url(value_match.group(1))
                        logical = _logical_from_text(key) or default_logical
                        if db_name and logical in _LOGICAL:
                            result.setdefault(env, {}).setdefault(logical, db_name)
                    continue
                if stripped and indent <= pending_indent and not stripped.startswith("#"):
                    pending_key = ""

            direct = re.match(r"^\s*([A-Z][A-Z0-9_]*)\s*:\s*(.+?)\s*$", raw)
            if not direct:
                continue
            key = direct.group(1)
            if not key_pattern.match(key):
                continue
            if key not in _URL_KEYS and not key.endswith("_DATABASE_URL") and not key.endswith("_DB_URL") and not key.endswith("_DSN"):
                continue
            db_name = _database_from_url(direct.group(2))
            logical = _logical_from_text(key) or default_logical
            if db_name and logical in _LOGICAL:
                result.setdefault(env, {}).setdefault(logical, db_name)

    return result


def _infer_from_service_user(logical: str, user: Any) -> str:
    """Infer only from an unmistakable microservice account name.

    This intentionally rejects generic users such as ``postgres``, ``reader``
    or ``app``.  A wrong database name is worse than a visible pending state.
    """
    raw = str(user or "").strip().lower()
    if not raw or len(raw) > 60 or not re.fullmatch(r"[a-z0-9_.-]+", raw):
        return ""
    normalized = raw.replace("-", "_")
    if not normalized.startswith("ms_"):
        return ""
    tokens = {token for token in normalized.split("_") if token}
    if not (tokens & _LOGICAL_TOKENS.get(logical, set())):
        return ""
    candidate = f"db_{normalized}"
    return candidate if len(candidate) <= 63 else ""


def _merge_names(target: dict[str, Any], explicit: dict[str, str]) -> bool:
    changed = False
    for logical in _LOGICAL:
        field = f"{logical}_db"
        if target.get(field) not in (None, "", 0):
            continue
        db_name = explicit.get(logical) or _infer_from_service_user(logical, target.get(f"{logical}_user"))
        if db_name:
            target[field] = db_name
            changed = True
    return changed


def recover_database_names(base_dir: Path | None = None) -> bool:
    from devconsole import config

    explicit = _extract_yaml_db_names(base_dir)
    changed = False
    telemetry = sys.modules.get("devconsole.services.telemetry_service")

    maps: list[dict[str, Any]] = []
    current = getattr(config, "DATABASE_ENV_CONFIGS", None)
    if isinstance(current, dict):
        maps.append(current)
    imported = getattr(telemetry, "DATABASE_ENV_CONFIGS", None) if telemetry else None
    if isinstance(imported, dict) and imported is not current:
        maps.append(imported)

    for db_map in maps:
        for env in _ENVIRONMENTS:
            entry = db_map.get(env)
            if not isinstance(entry, dict):
                continue
            changed = _merge_names(entry, explicit.get(env, {})) or changed
    return changed


def _install_catalog_refresh() -> None:
    """Reapply recovery after every local catalog refresh."""
    try:
        from devconsole import v11_legacy_profile as legacy
    except Exception:
        return

    original = legacy.hydrate_environment_catalog
    if getattr(original, "_v11_db_name_recovery", False):
        return

    def hydrate_with_db_names(*args, **kwargs):
        changed = original(*args, **kwargs)
        root = kwargs.get("root")
        if root is None and args:
            root = args[0]
        return bool(recover_database_names(root) or changed)

    hydrate_with_db_names._v11_db_name_recovery = True  # type: ignore[attr-defined]
    legacy.hydrate_environment_catalog = hydrate_with_db_names


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _install_catalog_refresh()
    recover_database_names()
    _INSTALLED = True


def status() -> dict[str, Any]:
    return {"installed": _INSTALLED, "environments": list(_ENVIRONMENTS)}
