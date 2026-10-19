"""Resolve non-secret Kubernetes ConfigMap metadata into the V1.1 catalog.

Mapa Operativo and Actividad need more than credentials: Keycloak URL/realm/
client_id and PostgreSQL host/port (plus DB names/users) must also be known.
Those values are commonly supplied through ``ConfigMap.data``,
``configMapKeyRef`` or ``envFrom.configMapRef``.

This adapter is read-only and recovers only allow-listed connection metadata.
It never persists values and never treats ConfigMaps as a secret store.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_INSTALLED = False


@dataclass(frozen=True)
class ConfigMapRecord:
    environment: str | None
    name: str
    logical_database: str | None
    path: Path
    raw_values: dict[str, str]
    canonical_values: dict[str, str]


def _clean(value: str) -> str:
    value = str(value or "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    value = value.strip()
    if not value or "${" in value or "{{" in value or value.startswith("__SECRET__"):
        return ""
    return value


def _documents(text: str) -> list[str]:
    return [doc for doc in re.split(r"(?m)^\s*---\s*$", text) if doc.strip()]


def _is_configmap_document(text: str) -> bool:
    return bool(re.search(r"(?im)^\s*kind\s*:\s*ConfigMap\s*(?:#.*)?$", text))


def _metadata_name(text: str) -> str:
    lines = text.splitlines()
    metadata_indent: int | None = None
    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        if re.match(r"^metadata\s*:\s*$", stripped):
            metadata_indent = indent
            continue
        if metadata_indent is not None:
            if indent <= metadata_indent:
                metadata_indent = None
                continue
            match = re.match(r"^name\s*:\s*(.+?)\s*$", stripped)
            if match:
                return _clean(match.group(1))
    return ""


def _mapping_section(text: str, section: str) -> dict[str, str]:
    result: dict[str, str] = {}
    lines = text.splitlines()
    section_indent: int | None = None
    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        if re.match(rf"^{re.escape(section)}\s*:\s*$", stripped):
            section_indent = indent
            continue
        if section_indent is None:
            continue
        if indent <= section_indent:
            section_indent = None
            continue
        match = re.match(r"^([^:#][^:]*)\s*:\s*(.*?)\s*$", stripped)
        if not match:
            continue
        key = _clean(match.group(1))
        value = _clean(match.group(2))
        # Block scalar payloads are intentionally ignored; the catalog consumes
        # simple scalar connection metadata only.
        if key and value and value not in {"|", ">", "|-", ">-"}:
            result.setdefault(key, value)
    return result


def _normal_key(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", str(value or "").upper()).strip("_")


def _role_tokens(path: Path, name: str, text: str) -> set[str]:
    from devconsole import v11_yaml_catalog as catalog

    relative = catalog._relative_config_path(path)
    return catalog._tokens(f"{relative} {name} {text[:2500]}")


def _canonical_key(
    raw_key: str,
    *,
    logical: str | None,
    role_tokens: set[str],
) -> str | None:
    from devconsole import v11_yaml_catalog as catalog

    key = _normal_key(raw_key)
    if key in catalog._KNOWN_VARS:
        # Never promote password/secret values from ConfigMap into the non-secret
        # catalog even if a poorly maintained manifest contains them.
        if "PASSWORD" in key or "SECRET" in key:
            return None
        return key

    keycloak_context = bool(role_tokens & {"keycloak", "oidc", "oauth", "auth"})
    if keycloak_context:
        aliases = {
            "URL": "KEYCLOAK_URL",
            "BASE_URL": "KEYCLOAK_BASE_URL",
            "SERVER_URL": "KEYCLOAK_SERVER_URL",
            "AUTH_SERVER_URL": "KEYCLOAK_SERVER_URL",
            "OIDC_ISSUER_URL": "KEYCLOAK_URL",
            "HOST": "KEYCLOAK_HOST",
            "HOSTNAME": "KEYCLOAK_HOST",
            "PORT": "KEYCLOAK_PORT",
            "PROTOCOL": "KEYCLOAK_PROTOCOL",
            "REALM": "KEYCLOAK_REALM",
            "REALM_NAME": "KEYCLOAK_REALM_NAME",
            "CLIENT_ID": "KEYCLOAK_CLIENT_ID",
            "CLIENTID": "KEYCLOAK_CLIENT_ID",
        }
        if key in aliases:
            return aliases[key]

    if logical:
        aliases = {
            "HOST": "DATABASE_HOST",
            "DBHOST": "DB_HOST",
            "HOSTNAME": "DATABASE_HOST",
            "PORT": "DATABASE_PORT",
            "DATABASE": "DATABASE_NAME",
            "DATABASE_NAME": "DATABASE_NAME",
            "DB": "DB_NAME",
            "NAME": "DATABASE_NAME",
            "USERNAME": "DATABASE_USER",
            "USER": "DATABASE_USER",
            "DB_USERNAME": "DB_USER",
            "POSTGRESQL_HOST": "POSTGRES_HOST",
            "POSTGRESQL_PORT": "POSTGRES_PORT",
            "POSTGRESQL_DATABASE": "POSTGRES_DB",
            "POSTGRESQL_USER": "POSTGRES_USER",
        }
        return aliases.get(key)
    return None


def _build_records(base_dir: Path | None = None) -> list[ConfigMapRecord]:
    from devconsole import v11_yaml_catalog as catalog

    records: list[ConfigMapRecord] = []
    for path in catalog._yaml_files(base_dir):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for doc in _documents(text):
            if not _is_configmap_document(doc):
                continue
            env = catalog._detect_environment(path, doc, base_dir)
            name = _metadata_name(doc)
            logical = catalog._logical_database(path, f"{name}\n{doc}")
            tokens = _role_tokens(path, name, doc)
            raw_values = _mapping_section(doc, "data")
            canonical: dict[str, str] = {}
            for raw_key, value in raw_values.items():
                key = _canonical_key(raw_key, logical=logical, role_tokens=tokens)
                if key and value:
                    canonical.setdefault(key, value)
            if raw_values:
                records.append(
                    ConfigMapRecord(
                        environment=env,
                        name=name,
                        logical_database=logical,
                        path=path,
                        raw_values=raw_values,
                        canonical_values=canonical,
                    )
                )
    return records


def _extract_configmap_key_refs(text: str) -> list[tuple[str, str, str]]:
    refs: list[tuple[str, str, str]] = []
    pattern = re.compile(
        r"(?ms)^\s*-\s*name\s*:\s*['\"]?([A-Z][A-Z0-9_]*)['\"]?\s*$"
        r"(?P<body>.*?)(?=^\s*-\s*name\s*:|\Z)"
    )
    for match in pattern.finditer(text):
        target_var = match.group(1)
        body = match.group("body")
        if "configMapKeyRef" not in body:
            continue
        ref_match = re.search(
            r"(?ms)configMapKeyRef\s*:\s*\n(?P<body>(?:\s+.*\n?)*)",
            body,
        )
        ref_body = ref_match.group("body") if ref_match else body
        name_match = re.search(r"(?m)^\s*name\s*:\s*['\"]?([^\s#'\"]+)", ref_body)
        key_match = re.search(r"(?m)^\s*key\s*:\s*['\"]?([^\s#'\"]+)", ref_body)
        if name_match and key_match:
            refs.append((target_var, name_match.group(1), key_match.group(1)))
    return refs


def _extract_envfrom_refs(text: str) -> list[str]:
    refs: list[str] = []
    for match in re.finditer(
        r"(?ms)^\s*configMapRef\s*:\s*$\n(?P<body>(?:\s+.*\n?)*)",
        text,
    ):
        name_match = re.search(r"(?m)^\s*name\s*:\s*['\"]?([^\s#'\"]+)", match.group("body"))
        if name_match:
            refs.append(name_match.group(1))
    return refs


def _record_for(records: list[ConfigMapRecord], env: str | None, name: str) -> ConfigMapRecord | None:
    exact = [record for record in records if record.name == name and record.environment == env]
    if exact:
        return exact[0]
    no_env = [record for record in records if record.name == name and record.environment is None]
    if len(no_env) == 1:
        return no_env[0]
    return None


def _apply_values(
    result: dict[str, Any],
    *,
    env: str,
    logical: str | None,
    values: dict[str, str],
) -> None:
    from devconsole import v11_yaml_catalog as catalog

    keycloak = catalog._keycloak_entry(values)
    if keycloak:
        target = result.setdefault("keycloak", {}).setdefault(env, {})
        for key, value in keycloak.items():
            if key != "client_secret" and value:
                target.setdefault(key, value)

    if logical:
        fields = catalog._database_fields(values, logical)
        if fields:
            target = result.setdefault("databases", {}).setdefault(env, {})
            for key, value in fields.items():
                if not key.endswith("_pass") and value not in (None, "", 0):
                    target.setdefault(key, value)


def _augment_scan(result: dict[str, Any], base_dir: Path | None = None) -> dict[str, Any]:
    from devconsole import v11_yaml_catalog as catalog

    records = _build_records(base_dir)

    # Directly classifiable ConfigMaps with canonical keys.
    for record in records:
        if record.environment and record.canonical_values:
            _apply_values(
                result,
                env=record.environment,
                logical=record.logical_database,
                values=record.canonical_values,
            )

    # Resolve workload references. The target env-var name is authoritative and
    # lets generic ConfigMap keys such as HOST/PORT/REALM map safely.
    for path in catalog._yaml_files(base_dir):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(_is_configmap_document(doc) for doc in _documents(text)):
            continue
        env = catalog._detect_environment(path, text, base_dir)
        if not env:
            continue
        logical = catalog._logical_database(path, text)
        workload_tokens = catalog._tokens(f"{catalog._relative_config_path(path, base_dir)} {text[:2500]}")
        resolved: dict[str, str] = {}

        for target_var, configmap_name, configmap_key in _extract_configmap_key_refs(text):
            record = _record_for(records, env, configmap_name)
            if not record:
                continue
            value = record.raw_values.get(configmap_key)
            if value is None:
                matches = [v for k, v in record.raw_values.items() if k.lower() == configmap_key.lower()]
                value = matches[0] if len(matches) == 1 else None
            if value:
                canonical_target = _canonical_key(
                    target_var,
                    logical=logical,
                    role_tokens=workload_tokens,
                )
                if canonical_target:
                    resolved[canonical_target] = value

        for configmap_name in _extract_envfrom_refs(text):
            record = _record_for(records, env, configmap_name)
            if not record:
                continue
            for raw_key, value in record.raw_values.items():
                canonical_target = _canonical_key(
                    raw_key,
                    logical=logical or record.logical_database,
                    role_tokens=workload_tokens | _role_tokens(record.path, record.name, ""),
                )
                if canonical_target and value:
                    resolved.setdefault(canonical_target, value)

        if resolved:
            _apply_values(result, env=env, logical=logical, values=resolved)

    result["k8s_configmap_records"] = len(records)
    return result


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from devconsole import v11_yaml_catalog as catalog

    original_scan = catalog.scan_workspace_yaml
    if not getattr(original_scan, "_v11_k8s_configmap_aware", False):
        def scan_with_configmaps(base_dir: Path | None = None) -> dict[str, Any]:
            return _augment_scan(original_scan(base_dir), base_dir)

        scan_with_configmaps._v11_k8s_configmap_aware = True  # type: ignore[attr-defined]
        catalog.scan_workspace_yaml = scan_with_configmaps

    catalog.hydrate_environment_catalog()
    _INSTALLED = True


def status() -> dict[str, Any]:
    records = _build_records()
    return {
        "installed": _INSTALLED,
        "records": len(records),
        "environments": sorted({record.environment for record in records if record.environment}),
    }
