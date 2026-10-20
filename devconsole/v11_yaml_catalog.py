"""Recover SISPER environment metadata from the workspace config YAML tree.

The selected project already carries Kubernetes/manifests under ``config/`` in
many workstations. V1.1 reuses that information instead of asking the operator
to duplicate hosts, users and credentials by hand.

Important safety/correctness rules:

* scan only known config roots below the selected workspace;
* inspect only an allow-list of environment variable names;
* never execute YAML, templates or shell substitutions;
* explicit V1.1 / recovered V1 values win over discovered values;
* a local service ``.env`` belongs to DEVELOP only unless an environment-
  specific source proves otherwise;
* discovered secrets stay in memory until the operator explicitly saves them.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

_INSTALLED = False
_MAX_FILES = 500
_MAX_FILE_BYTES = 2_000_000
_ENV_ALIASES = {
    "develop": {"develop", "development", "dev", "desarrollo"},
    "test": {"test", "testing", "qa"},
    "main": {"main", "prod", "production", "produccion"},
}
_DB_LOGICAL = ("bitacora", "contratos", "destinaciones")
_KNOWN_VARS = {
    "KEYCLOAK_URL",
    "KEYCLOAK_BASE_URL",
    "KEYCLOAK_SERVER_URL",
    "KEYCLOAK_HOST",
    "KEYCLOAK_PORT",
    "KEYCLOAK_PROTOCOL",
    "KEYCLOAK_REALM",
    "KEYCLOAK_REALM_NAME",
    "KEYCLOAK_CLIENT_ID",
    "KEYCLOAK_CLIENT_SECRET",
    "KEYCLOAK_CLIENT_SECRET_KEY",
    "DATABASE_HOST",
    "DATABASE_PORT",
    "DATABASE_NAME",
    "DATABASE_USER",
    "DATABASE_PASSWORD",
    "DB_HOST",
    "DB_PORT",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "ONLYOFFICE_JWT_SECRET",
    "JWT_SECRET",
}


def _clean_scalar(value: str) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    value = re.split(r"\s+#", value, maxsplit=1)[0].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    lowered = value.strip().lower()
    if lowered in {"", "null", "none", "~"}:
        return ""
    if "${" in value or "{{" in value or value.startswith("__SECRET__"):
        return ""
    return value.strip()


def _extract_named_values(text: str) -> dict[str, str]:
    """Extract allow-listed scalar env values from common Kubernetes YAML forms."""
    values: dict[str, str] = {}
    lines = text.splitlines()

    # env:\n  - name: DATABASE_HOST\n    value: host
    pending_name = ""
    pending_indent = -1
    for raw in lines:
        stripped = raw.strip()
        indent = len(raw) - len(raw.lstrip())
        name_match = re.match(
            r"^-?\s*name\s*:\s*['\"]?([A-Z][A-Z0-9_]*)['\"]?\s*$",
            stripped,
        )
        if name_match:
            candidate = name_match.group(1)
            pending_name = candidate if candidate in _KNOWN_VARS else ""
            pending_indent = indent
            continue
        if pending_name:
            value_match = re.match(r"^value\s*:\s*(.+)$", stripped)
            if value_match:
                value = _clean_scalar(value_match.group(1))
                if value:
                    values.setdefault(pending_name, value)
                pending_name = ""
                continue
            if stripped and indent <= pending_indent and not stripped.startswith("#"):
                pending_name = ""

    # ConfigMap/stringData/plain mapping: DATABASE_HOST: host
    direct = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s*:\s*(.+?)\s*$")
    for raw in lines:
        match = direct.match(raw)
        if not match or match.group(1) not in _KNOWN_VARS:
            continue
        value = _clean_scalar(match.group(2))
        if value:
            values.setdefault(match.group(1), value)
    return values


def _tokens(value: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", value.lower()) if token}


def _normalise_env(value: str) -> str | None:
    """Normalise exact or embedded environment names such as ``sisper-test``."""
    raw = str(value or "").strip().lower()
    tokens = _tokens(raw)
    if raw:
        tokens.add(raw)
    matches = [env for env, aliases in _ENV_ALIASES.items() if tokens & aliases]
    return matches[0] if len(matches) == 1 else None


def _relative_config_path(path: Path, base_dir: Path | None = None) -> Path:
    """Return a path relative to the closest config root.

    Never classify an environment from the absolute workstation path. A common
    parent such as ``~/Develop`` must not make every YAML look like DEVELOP.
    """
    try:
        resolved = path.resolve()
    except Exception:
        resolved = path
    best: Path | None = None
    for root in _config_roots(base_dir):
        try:
            relative = resolved.relative_to(root.resolve())
        except (OSError, ValueError):
            continue
        if best is None or len(relative.parts) < len(best.parts):
            best = relative
    return best if best is not None else Path(path.name)


def _environment_from_path(path: Path, base_dir: Path | None = None) -> str | None:
    relative = _relative_config_path(path, base_dir)
    # Prefer the deepest path component: config/k8s/test/deployment.yaml should
    # resolve to TEST even if a higher directory contains another generic word.
    for part in reversed(relative.parts):
        env = _normalise_env(part)
        if env:
            return env
    return None


def _environment_from_text(text: str) -> str | None:
    """Read environment/namespace labels, including values like sisper-prod."""
    matches = re.findall(
        r"(?im)^\s*(?:environment|env|namespace)\s*:\s*['\"]?([a-zA-Z0-9_.-]+)",
        text,
    )
    detected = {env for raw in matches if (env := _normalise_env(raw))}
    return next(iter(detected)) if len(detected) == 1 else None


def _detect_environment(path: Path, text: str, base_dir: Path | None = None) -> str | None:
    # Explicit metadata is strongest; then the relative config-tree location.
    return _environment_from_text(text) or _environment_from_path(path, base_dir)


def _logical_database(path: Path, text: str = "") -> str | None:
    tokens = _tokens(str(path))
    head_tokens = _tokens(text[:5000])
    all_tokens = tokens | head_tokens
    for logical in _DB_LOGICAL:
        if logical in all_tokens:
            return logical
    return None


def _config_roots(base_dir: Path | None = None) -> list[Path]:
    from devconsole import config, settings

    base = Path(base_dir or config.BASE_DIR)
    candidates = [
        Path(getattr(config, "CONFIG_REPO_DIR", base / "config")),
        settings.config_repo_dir(base),
        base / "config",
        base / "backend" / "config",
    ]
    roots: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.expanduser().resolve()
        except Exception:
            continue
        if resolved in seen or not resolved.is_dir():
            continue
        seen.add(resolved)
        roots.append(resolved)
    return roots


def _yaml_files(base_dir: Path | None = None) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for root in _config_roots(base_dir):
        for pattern in ("*.yaml", "*.yml"):
            try:
                iterator = root.rglob(pattern)
            except Exception:
                continue
            for path in iterator:
                try:
                    resolved = path.resolve()
                    if (
                        resolved in seen
                        or not path.is_file()
                        or path.stat().st_size > _MAX_FILE_BYTES
                    ):
                        continue
                except OSError:
                    continue
                seen.add(resolved)
                files.append(path)
                if len(files) >= _MAX_FILES:
                    return files
    return files


def _first(values: dict[str, str], *names: str) -> str:
    for name in names:
        value = values.get(name)
        if value:
            return value
    return ""


def _keycloak_entry(values: dict[str, str]) -> dict[str, Any]:
    url = _first(values, "KEYCLOAK_URL", "KEYCLOAK_BASE_URL", "KEYCLOAK_SERVER_URL")
    if not url:
        host = _first(values, "KEYCLOAK_HOST")
        if host:
            if "://" in host:
                url = host.rstrip("/")
            else:
                protocol = _first(values, "KEYCLOAK_PROTOCOL") or "https"
                port = _first(values, "KEYCLOAK_PORT")
                suffix = f":{port}" if port and port not in {"80", "443"} else ""
                url = f"{protocol}://{host}{suffix}"
    entry: dict[str, Any] = {}
    if url:
        entry["url"] = url.rstrip("/")
    realm = _first(values, "KEYCLOAK_REALM", "KEYCLOAK_REALM_NAME")
    client_id = _first(values, "KEYCLOAK_CLIENT_ID")
    client_secret = _first(values, "KEYCLOAK_CLIENT_SECRET_KEY", "KEYCLOAK_CLIENT_SECRET")
    if realm:
        entry["realm"] = realm
    if client_id:
        entry["client_id"] = client_id
    if client_secret:
        entry["client_secret"] = client_secret
    return entry


def _database_fields(values: dict[str, str], logical: str) -> dict[str, Any]:
    host = _first(values, "DATABASE_HOST", "DB_HOST", "POSTGRES_HOST")
    port = _first(values, "DATABASE_PORT", "DB_PORT", "POSTGRES_PORT")
    db_name = _first(values, "DATABASE_NAME", "DB_NAME", "POSTGRES_DB")
    user = _first(values, "DATABASE_USER", "DB_USER", "POSTGRES_USER")
    password = _first(values, "DATABASE_PASSWORD", "DB_PASSWORD", "POSTGRES_PASSWORD")
    out: dict[str, Any] = {}
    if host:
        out["host"] = host
    if port:
        try:
            out["port"] = int(port)
        except (TypeError, ValueError):
            pass
    if db_name:
        out[f"{logical}_db"] = db_name
    if user:
        out[f"{logical}_user"] = user
    if password:
        out[f"{logical}_pass"] = password
    return out


def _mask(value: str) -> str:
    value = str(value or "")
    return value[:2] + "…" + value[-2:] if len(value) > 6 else "…"


def _display_origin(path: Path, base_dir: Path | None = None) -> str:
    return str(_relative_config_path(path, base_dir))


def scan_workspace_yaml(base_dir: Path | None = None) -> dict[str, Any]:
    keycloak: dict[str, dict[str, Any]] = {}
    databases: dict[str, dict[str, Any]] = {}
    secret_candidates: list[dict[str, str]] = []
    files_scanned = 0
    classified = {"develop": 0, "test": 0, "main": 0, "unknown": 0}

    for path in _yaml_files(base_dir):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        files_scanned += 1
        env = _detect_environment(path, text, base_dir)
        classified[env or "unknown"] += 1
        values = _extract_named_values(text)
        if not values:
            continue

        if env:
            kc = _keycloak_entry(values)
            if kc:
                target = keycloak.setdefault(env, {})
                for key, value in kc.items():
                    target.setdefault(key, value)
                secret = kc.get("client_secret")
                if secret:
                    secret_candidates.append(
                        {
                            "clave": f"keycloak.{env}.client_secret",
                            "valor": str(secret),
                            "pista": _mask(str(secret)),
                            "origen": _display_origin(path, base_dir),
                            "entorno": env,
                            "fuente": "config-yaml",
                        }
                    )

            logical = _logical_database(path, text)
            if logical:
                fields = _database_fields(values, logical)
                if fields:
                    target = databases.setdefault(env, {})
                    for key, value in fields.items():
                        target.setdefault(key, value)
                    password = fields.get(f"{logical}_pass")
                    if password:
                        secret_candidates.append(
                            {
                                "clave": f"databases.{env}.{logical}_pass",
                                "valor": str(password),
                                "pista": _mask(str(password)),
                                "origen": _display_origin(path, base_dir),
                                "entorno": env,
                                "fuente": "config-yaml",
                            }
                        )

        path_tokens = _tokens(str(_relative_config_path(path, base_dir))) | _tokens(text[:5000])
        jwt = _first(values, "ONLYOFFICE_JWT_SECRET")
        if not jwt and "onlyoffice" in path_tokens:
            jwt = _first(values, "JWT_SECRET")
        if jwt:
            secret_candidates.append(
                {
                    "clave": "infra.onlyoffice_jwt_secret",
                    "valor": jwt,
                    "pista": _mask(jwt),
                    "origen": _display_origin(path, base_dir),
                    "entorno": env or "global",
                    "fuente": "config-yaml",
                }
            )

    return {
        "keycloak": keycloak,
        "databases": databases,
        "secret_candidates": secret_candidates,
        "files_scanned": files_scanned,
        "classified_files": classified,
    }


def _merge_missing(target: dict[str, Any], source: dict[str, Any]) -> bool:
    changed = False
    for key, value in source.items():
        if value in (None, "", 0):
            continue
        if target.get(key) in (None, "", 0):
            target[key] = value
            changed = True
    return changed


def hydrate_environment_catalog(base_dir: Path | None = None) -> bool:
    """Fill missing DEVELOP/TEST/MAIN fields from config YAML, in memory only."""
    from devconsole import config

    scanned = scan_workspace_yaml(base_dir)
    changed = False
    telemetry = sys.modules.get("devconsole.services.telemetry_service")

    for attr, source_name in (
        ("KEYCLOAK_ENV_CONFIGS", "keycloak"),
        ("DATABASE_ENV_CONFIGS", "databases"),
    ):
        source_map = scanned.get(source_name) or {}
        current = getattr(config, attr, None)
        targets: list[dict[str, Any]] = []
        if isinstance(current, dict):
            targets.append(current)
        imported = getattr(telemetry, attr, None) if telemetry else None
        if isinstance(imported, dict) and imported is not current:
            targets.append(imported)

        for env, source in source_map.items():
            if env not in _ENV_ALIASES or not isinstance(source, dict):
                continue
            for target_map in targets:
                entry = target_map.setdefault(env, {})
                if not isinstance(entry, dict):
                    entry = {}
                    target_map[env] = entry
                changed = _merge_missing(entry, source) or changed
    return changed


def _merge_secret_candidates(
    original_items: list[dict],
    yaml_items: list[dict],
    required: set[str],
) -> list[dict]:
    result: list[dict] = []
    seen: set[str] = set()
    for item in [*original_items, *yaml_items]:
        if not isinstance(item, dict):
            continue
        key = str(item.get("clave") or "")
        if (
            not key
            or key not in required
            or key in seen
            or not str(item.get("valor") or "").strip()
        ):
            continue
        result.append(dict(item))
        seen.add(key)
    return result


def _install_secret_discovery() -> None:
    from devconsole import settings

    original = settings.buscar_secretos_en_servicios
    if getattr(original, "_v11_yaml_catalog", False) is True:
        return

    def buscar_con_yaml(env_key: str = "develop") -> list[dict]:
        env = _normalise_env(env_key) or "develop"
        # The service .env files describe the currently running local workspace,
        # which is DEVELOP in the existing V1 workflow. Re-labelling those same
        # values as TEST/MAIN was a correctness bug.
        original_items = original(env) if env == "develop" else []
        for item in original_items:
            if isinstance(item, dict):
                item.setdefault("entorno", env)
                item.setdefault("fuente", "service-env")
        required = set(settings.referenced_secret_keys())
        scanned = scan_workspace_yaml()
        yaml_items = [
            item
            for item in scanned.get("secret_candidates", [])
            if item.get("clave") == "infra.onlyoffice_jwt_secret"
            or f".{env}." in str(item.get("clave") or "")
        ]
        return _merge_secret_candidates(original_items, yaml_items, required)

    buscar_con_yaml._v11_yaml_catalog = True  # type: ignore[attr-defined]
    settings.buscar_secretos_en_servicios = buscar_con_yaml


def _install_catalog_refresh() -> None:
    """Layer YAML recovery into every existing legacy-profile refresh."""
    try:
        from devconsole import v11_legacy_profile as legacy
    except Exception:
        return
    original = legacy.hydrate_environment_catalog
    if getattr(original, "_v11_yaml_catalog", False) is True:
        return

    def hydrate_with_yaml(*args, **kwargs):
        changed = original(*args, **kwargs)
        root = kwargs.get("root")
        if root is None and args:
            root = args[0]
        return bool(hydrate_environment_catalog(root) or changed)

    hydrate_with_yaml._v11_yaml_catalog = True  # type: ignore[attr-defined]
    legacy.hydrate_environment_catalog = hydrate_with_yaml


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _install_catalog_refresh()
    _install_secret_discovery()
    hydrate_environment_catalog()
    _INSTALLED = True


def status() -> dict[str, Any]:
    scanned = scan_workspace_yaml()
    return {
        "installed": _INSTALLED,
        "files_scanned": int(scanned.get("files_scanned") or 0),
        "classified_files": dict(scanned.get("classified_files") or {}),
        "keycloak_environments": sorted(scanned.get("keycloak", {})),
        "database_environments": sorted(scanned.get("databases", {})),
        "secret_candidates": len(scanned.get("secret_candidates", [])),
    }
