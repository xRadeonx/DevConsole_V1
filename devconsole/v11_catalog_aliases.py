"""Normalize common SISPER/Kubernetes connection variable aliases.

The V1 telemetry contract needs separate Contratos, Destinaciones and Bitácora
DB name/user/password fields. Real manifests do not always use the generic
``DATABASE_NAME`` / ``DATABASE_USER`` vocabulary; service-specific ConfigMaps
and Secrets often use names such as ``CONTRATOS_DB``, ``CTTO_USER``,
``DESTINACIONES_DATABASE`` or standard libpq names such as ``PGDATABASE``.

This compatibility layer expands only the parser vocabulary. It does not invent
values, copy DEVELOP into TEST/MAIN, perform network I/O, or persist anything.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_INSTALLED = False

_LOGICAL_ALIASES = {
    "bitacora": {"bitacora", "bitacoras", "audit", "auditoria"},
    "contratos": {"contratos", "contrato", "ctto", "cttos"},
    "destinaciones": {"destinaciones", "destinacion", "destino", "destinos", "dest"},
}

_LOGICAL_PREFIXES = {
    "bitacora": ("BITACORA", "BITACORAS", "AUDIT", "AUDITORIA"),
    "contratos": ("CONTRATOS", "CONTRATO", "CTTO", "CTTOS"),
    "destinaciones": ("DESTINACIONES", "DESTINACION", "DESTINO", "DESTINOS", "DEST"),
}

_KEYCLOAK_ALIASES = {
    "KC_URL",
    "KC_HOST",
    "KC_PORT",
    "KC_PROTOCOL",
    "KC_REALM",
    "KC_CLIENT_ID",
    "KC_CLIENT_SECRET",
    "OIDC_ISSUER_URL",
    "OIDC_REALM",
    "OIDC_CLIENT_ID",
    "AUTH_SERVER_URL",
    "AUTH_REALM",
    "AUTH_CLIENT_ID",
}

_DB_ALIASES = {
    "PGHOST",
    "PGPORT",
    "PGDATABASE",
    "PGUSER",
    "PGPASSWORD",
    "DATABASE_USERNAME",
    "DATABASE_PASS",
    "DB_DATABASE",
    "DB_USERNAME",
    "DB_PASS",
    "POSTGRESQL_HOST",
    "POSTGRESQL_PORT",
    "POSTGRESQL_DB",
    "POSTGRESQL_DATABASE",
    "POSTGRESQL_USER",
    "POSTGRESQL_USERNAME",
    "POSTGRESQL_PASSWORD",
    "HOST_DB",
    "PORT_DB",
    "NAME_DB",
    "USER_DB",
    "PASSWORD_DB",
    "BD_HOST",
    "BD_PORT",
    "BD_NAME",
    "BD_USER",
    "BD_PASSWORD",
}


def _first(values: dict[str, str], *names: str) -> str:
    for name in names:
        value = values.get(name)
        if value not in (None, "", 0):
            return str(value)
    return ""


def _logical_names(logical: str, suffixes: tuple[str, ...]) -> tuple[str, ...]:
    prefixes = _LOGICAL_PREFIXES.get(logical, (logical.upper(),))
    names: list[str] = []
    for prefix in prefixes:
        for suffix in suffixes:
            names.extend((f"{prefix}_{suffix}", f"{suffix}_{prefix}"))
    return tuple(dict.fromkeys(names))


def _specific_names(logical: str) -> dict[str, tuple[str, ...]]:
    return {
        "db": _logical_names(logical, ("DB", "DATABASE", "DATABASE_NAME", "DB_NAME", "NAME")),
        "user": _logical_names(logical, ("USER", "USERNAME", "DATABASE_USER", "DB_USER")),
        "pass": _logical_names(logical, ("PASS", "PASSWORD", "DATABASE_PASSWORD", "DB_PASSWORD")),
        "host": _logical_names(logical, ("HOST", "DATABASE_HOST", "DB_HOST")),
        "port": _logical_names(logical, ("PORT", "DATABASE_PORT", "DB_PORT")),
    }


def _extend_known_vars(catalog) -> None:
    catalog._KNOWN_VARS.update(_KEYCLOAK_ALIASES | _DB_ALIASES)
    for logical in _LOGICAL_PREFIXES:
        for names in _specific_names(logical).values():
            catalog._KNOWN_VARS.update(names)


def _install_logical_database(catalog) -> None:
    original = catalog._logical_database
    if getattr(original, "_v11_catalog_aliases", False):
        return

    def logical_database(path: Path, text: str = "") -> str | None:
        current = original(path, text)
        if current:
            return current
        tokens = catalog._tokens(f"{path} {text[:5000]}")
        matches = [
            logical
            for logical, aliases in _LOGICAL_ALIASES.items()
            if tokens & aliases
        ]
        return matches[0] if len(matches) == 1 else None

    logical_database._v11_catalog_aliases = True  # type: ignore[attr-defined]
    catalog._logical_database = logical_database


def _install_keycloak_entry(catalog) -> None:
    original = catalog._keycloak_entry
    if getattr(original, "_v11_catalog_aliases", False):
        return

    def keycloak_entry(values: dict[str, str]) -> dict[str, Any]:
        normalized = dict(values)
        aliases = {
            "KEYCLOAK_URL": ("KC_URL", "OIDC_ISSUER_URL", "AUTH_SERVER_URL"),
            "KEYCLOAK_HOST": ("KC_HOST",),
            "KEYCLOAK_PORT": ("KC_PORT",),
            "KEYCLOAK_PROTOCOL": ("KC_PROTOCOL",),
            "KEYCLOAK_REALM": ("KC_REALM", "OIDC_REALM", "AUTH_REALM"),
            "KEYCLOAK_CLIENT_ID": ("KC_CLIENT_ID", "OIDC_CLIENT_ID", "AUTH_CLIENT_ID"),
            "KEYCLOAK_CLIENT_SECRET": ("KC_CLIENT_SECRET",),
        }
        for canonical, candidates in aliases.items():
            if not normalized.get(canonical):
                value = _first(values, *candidates)
                if value:
                    normalized[canonical] = value
        return original(normalized)

    keycloak_entry._v11_catalog_aliases = True  # type: ignore[attr-defined]
    catalog._keycloak_entry = keycloak_entry


def _install_database_fields(catalog) -> None:
    original = catalog._database_fields
    if getattr(original, "_v11_catalog_aliases", False):
        return

    def database_fields(values: dict[str, str], logical: str) -> dict[str, Any]:
        normalized = dict(values)
        specific = _specific_names(logical)
        aliases = {
            "DATABASE_HOST": (
                "PGHOST", "POSTGRESQL_HOST", "HOST_DB", "BD_HOST", *specific["host"]
            ),
            "DATABASE_PORT": (
                "PGPORT", "POSTGRESQL_PORT", "PORT_DB", "BD_PORT", *specific["port"]
            ),
            "DATABASE_NAME": (
                "PGDATABASE", "DB_DATABASE", "POSTGRESQL_DB", "POSTGRESQL_DATABASE",
                "NAME_DB", "BD_NAME", *specific["db"]
            ),
            "DATABASE_USER": (
                "PGUSER", "DATABASE_USERNAME", "DB_USERNAME", "POSTGRESQL_USER",
                "POSTGRESQL_USERNAME", "USER_DB", "BD_USER", *specific["user"]
            ),
            "DATABASE_PASSWORD": (
                "PGPASSWORD", "DATABASE_PASS", "DB_PASS", "POSTGRESQL_PASSWORD",
                "PASSWORD_DB", "BD_PASSWORD", *specific["pass"]
            ),
        }
        for canonical, candidates in aliases.items():
            if not normalized.get(canonical):
                value = _first(values, *candidates)
                if value:
                    normalized[canonical] = value
        return original(normalized, logical)

    database_fields._v11_catalog_aliases = True  # type: ignore[attr-defined]
    catalog._database_fields = database_fields


def _has_specific_db_values(values: dict[str, str], logical: str) -> bool:
    names = _specific_names(logical)
    keys = set(values)
    return any(keys & set(group) for group in names.values())


def _install_shared_mapping_support(catalog) -> None:
    """Allow one shared ConfigMap/Secret to define multiple logical databases."""
    try:
        from devconsole import v11_k8s_configmaps as configmaps
        from devconsole import v11_k8s_secrets as secrets
    except Exception:
        return

    configmap_apply = configmaps._apply_values
    if not getattr(configmap_apply, "_v11_catalog_aliases", False):
        def apply_configmap(result, *, env, logical, values):
            configmap_apply(result, env=env, logical=logical, values=values)
            if logical is None:
                for candidate in catalog._DB_LOGICAL:
                    if _has_specific_db_values(values, candidate):
                        configmap_apply(result, env=env, logical=candidate, values=values)

        apply_configmap._v11_catalog_aliases = True  # type: ignore[attr-defined]
        configmaps._apply_values = apply_configmap

    secret_apply = secrets._apply_values
    if not getattr(secret_apply, "_v11_catalog_aliases", False):
        def apply_secret(result, *, env, logical, values, origin, source):
            secret_apply(
                result,
                env=env,
                logical=logical,
                values=values,
                origin=origin,
                source=source,
            )
            if logical is None:
                for candidate in catalog._DB_LOGICAL:
                    if _has_specific_db_values(values, candidate):
                        secret_apply(
                            result,
                            env=env,
                            logical=candidate,
                            values=values,
                            origin=origin,
                            source=source,
                        )

        apply_secret._v11_catalog_aliases = True  # type: ignore[attr-defined]
        secrets._apply_values = apply_secret


def _extend_local_env_keys() -> None:
    try:
        from devconsole import v11_local_env_catalog as local_catalog
    except Exception:
        return
    local_catalog._KEYCLOAK_KEYS.update(_KEYCLOAK_ALIASES)
    local_catalog._DB_KEYS.update(_DB_ALIASES)
    for logical in _LOGICAL_PREFIXES:
        for names in _specific_names(logical).values():
            local_catalog._DB_KEYS.update(names)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from devconsole import v11_yaml_catalog as catalog

    _extend_known_vars(catalog)
    _install_logical_database(catalog)
    _install_keycloak_entry(catalog)
    _install_database_fields(catalog)
    _install_shared_mapping_support(catalog)
    _extend_local_env_keys()
    catalog.hydrate_environment_catalog()
    _INSTALLED = True


def status() -> dict[str, Any]:
    return {
        "installed": _INSTALLED,
        "logical_aliases": sorted(_LOGICAL_ALIASES),
        "database_aliases": len(_DB_ALIASES),
        "keycloak_aliases": len(_KEYCLOAK_ALIASES),
    }
