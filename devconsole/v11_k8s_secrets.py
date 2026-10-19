"""Decode Kubernetes Secret manifests for the V1.1 local catalog.

Kubernetes ``Secret.data`` values are base64-encoded while ``stringData`` is
plain text. The generic YAML catalog intentionally does not parse Kubernetes
objects deeply, so this adapter adds Secret-aware recovery without ever
printing or committing decoded values.

It also resolves the most common workload forms::

    env:
      - name: DATABASE_PASSWORD
        valueFrom:
          secretKeyRef:
            name: ms-contratos-secret
            key: password

and ``envFrom.secretRef``.  Recovered values stay in memory until the operator
explicitly stores a selected value through the existing 0600 secrets workflow.
"""

from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_INSTALLED = False


@dataclass(frozen=True)
class SecretRecord:
    environment: str | None
    name: str
    logical_database: str | None
    path: Path
    raw_values: dict[str, str]
    canonical_values: dict[str, str]
    sources: dict[str, str]


def _clean(value: str) -> str:
    value = str(value or "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return value.strip()


def _is_secret_document(text: str) -> bool:
    return bool(re.search(r"(?im)^\s*kind\s*:\s*Secret\s*(?:#.*)?$", text))


def _documents(text: str) -> list[str]:
    return [doc for doc in re.split(r"(?m)^\s*---\s*$", text) if doc.strip()]


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
    """Read a simple top-level YAML mapping without executing YAML."""
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
        if key and value and value not in {"|", ">"}:
            result.setdefault(key, value)
    return result


def _decode_base64(value: str) -> str:
    raw = _clean(value)
    if not raw:
        return ""
    try:
        decoded = base64.b64decode(raw, validate=True)
        text = decoded.decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return ""
    # Do not treat binary/null-containing payloads as application credentials.
    if "\x00" in text:
        return ""
    return text


def _normal_key(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", str(value or "").upper()).strip("_")


def _role_tokens(path: Path, name: str, text: str) -> set[str]:
    from devconsole import v11_yaml_catalog as catalog

    relative = catalog._relative_config_path(path)
    return catalog._tokens(f"{relative} {name} {text[:2500]}")


def _canonical_key(raw_key: str, *, logical: str | None, role_tokens: set[str]) -> str | None:
    from devconsole import v11_yaml_catalog as catalog

    key = _normal_key(raw_key)
    if key in catalog._KNOWN_VARS:
        return key

    keycloak = "keycloak" in role_tokens
    onlyoffice = "onlyoffice" in role_tokens

    if key in {"CLIENT_SECRET", "CLIENTSECRET", "KEYCLOAK_SECRET", "SECRET"} and keycloak:
        return "KEYCLOAK_CLIENT_SECRET"
    if key in {"JWT", "JWT_SECRET", "SECRET"} and onlyoffice:
        return "ONLYOFFICE_JWT_SECRET"

    if logical:
        aliases = {
            "PASSWORD": "DATABASE_PASSWORD",
            "PASS": "DATABASE_PASSWORD",
            "DB_PASS": "DATABASE_PASSWORD",
            "DB_PASSWORD": "DB_PASSWORD",
            "DATABASE_PASS": "DATABASE_PASSWORD",
            "POSTGRESQL_PASSWORD": "POSTGRES_PASSWORD",
            "USERNAME": "DATABASE_USER",
            "USER": "DATABASE_USER",
            "DB_USERNAME": "DB_USER",
            "POSTGRESQL_USER": "POSTGRES_USER",
            "DATABASE": "DATABASE_NAME",
            "DB": "DB_NAME",
            "POSTGRESQL_DATABASE": "POSTGRES_DB",
            "HOST": "DATABASE_HOST",
            "DBHOST": "DB_HOST",
            "POSTGRESQL_HOST": "POSTGRES_HOST",
            "PORT": "DATABASE_PORT",
            "POSTGRESQL_PORT": "POSTGRES_PORT",
        }
        return aliases.get(key)
    return None


def _build_secret_records(base_dir: Path | None = None) -> list[SecretRecord]:
    from devconsole import v11_yaml_catalog as catalog

    records: list[SecretRecord] = []
    for path in catalog._yaml_files(base_dir):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for doc in _documents(text):
            if not _is_secret_document(doc):
                continue
            environment = catalog._detect_environment(path, doc, base_dir)
            name = _metadata_name(doc)
            logical = catalog._logical_database(path, f"{name}\n{doc}")
            tokens = _role_tokens(path, name, doc)

            raw_values: dict[str, str] = {}
            canonical: dict[str, str] = {}
            sources: dict[str, str] = {}

            for raw_key, encoded in _mapping_section(doc, "data").items():
                decoded = _decode_base64(encoded)
                if not decoded:
                    continue
                raw_values[raw_key] = decoded
                canonical_key = _canonical_key(raw_key, logical=logical, role_tokens=tokens)
                if canonical_key:
                    canonical[canonical_key] = decoded
                    sources[canonical_key] = "k8s-secret-data-b64"

            for raw_key, plain in _mapping_section(doc, "stringData").items():
                if not plain:
                    continue
                raw_values[raw_key] = plain
                canonical_key = _canonical_key(raw_key, logical=logical, role_tokens=tokens)
                if canonical_key:
                    canonical[canonical_key] = plain
                    sources[canonical_key] = "k8s-secret-stringData"

            if raw_values:
                records.append(
                    SecretRecord(
                        environment=environment,
                        name=name,
                        logical_database=logical,
                        path=path,
                        raw_values=raw_values,
                        canonical_values=canonical,
                        sources=sources,
                    )
                )
    return records


def _extract_secret_key_refs(text: str) -> list[tuple[str, str, str]]:
    """Return (target env var, secret name, secret key) references."""
    refs: list[tuple[str, str, str]] = []
    pattern = re.compile(
        r"(?ms)^\s*-\s*name\s*:\s*['\"]?([A-Z][A-Z0-9_]*)['\"]?\s*$"
        r"(?P<body>.*?)(?=^\s*-\s*name\s*:|\Z)"
    )
    for match in pattern.finditer(text):
        target_var = match.group(1)
        body = match.group("body")
        if "secretKeyRef" not in body:
            continue
        secret_match = re.search(
            r"(?ms)secretKeyRef\s*:\s*\n(?P<body>(?:\s+.*\n?)*)",
            body,
        )
        secret_body = secret_match.group("body") if secret_match else body
        name_match = re.search(r"(?m)^\s*name\s*:\s*['\"]?([^\s#'\"]+)", secret_body)
        key_match = re.search(r"(?m)^\s*key\s*:\s*['\"]?([^\s#'\"]+)", secret_body)
        if name_match and key_match:
            refs.append((target_var, name_match.group(1), key_match.group(1)))
    return refs


def _extract_envfrom_refs(text: str) -> list[str]:
    refs: list[str] = []
    for match in re.finditer(
        r"(?ms)^\s*secretRef\s*:\s*$\n(?P<body>(?:\s+.*\n?)*)",
        text,
    ):
        name_match = re.search(r"(?m)^\s*name\s*:\s*['\"]?([^\s#'\"]+)", match.group("body"))
        if name_match:
            refs.append(name_match.group(1))
    return refs


def _record_for(records: list[SecretRecord], env: str | None, name: str) -> SecretRecord | None:
    exact = [r for r in records if r.name == name and r.environment == env]
    if exact:
        return exact[0]
    # A Secret may have no environment metadata while the referencing workload
    # does. Only accept that fallback when its name is unique.
    unnamed_env = [r for r in records if r.name == name and r.environment is None]
    if len(unnamed_env) == 1:
        return unnamed_env[0]
    return None


def _candidate_key(env: str, canonical_var: str, logical: str | None) -> str | None:
    if canonical_var in {"KEYCLOAK_CLIENT_SECRET", "KEYCLOAK_CLIENT_SECRET_KEY"}:
        return f"keycloak.{env}.client_secret"
    if canonical_var in {"DATABASE_PASSWORD", "DB_PASSWORD", "POSTGRES_PASSWORD"} and logical:
        return f"databases.{env}.{logical}_pass"
    if canonical_var in {"ONLYOFFICE_JWT_SECRET", "JWT_SECRET"}:
        return "infra.onlyoffice_jwt_secret"
    return None


def _upsert_candidate(
    result: dict[str, Any],
    *,
    key: str,
    value: str,
    env: str,
    origin: str,
    source: str,
) -> None:
    from devconsole import v11_yaml_catalog as catalog

    items = result.setdefault("secret_candidates", [])
    items[:] = [item for item in items if str(item.get("clave") or "") != key]
    items.append(
        {
            "clave": key,
            "valor": value,
            "pista": catalog._mask(value),
            "origen": origin,
            "entorno": env,
            "fuente": source,
        }
    )


def _apply_values(
    result: dict[str, Any],
    *,
    env: str,
    logical: str | None,
    values: dict[str, str],
    origin: str,
    source: str,
) -> None:
    from devconsole import v11_yaml_catalog as catalog

    keycloak = catalog._keycloak_entry(values)
    if keycloak:
        target = result.setdefault("keycloak", {}).setdefault(env, {})
        for key, value in keycloak.items():
            if key == "client_secret":
                target[key] = value
            else:
                target.setdefault(key, value)
        secret = keycloak.get("client_secret")
        if secret:
            _upsert_candidate(
                result,
                key=f"keycloak.{env}.client_secret",
                value=str(secret),
                env=env,
                origin=origin,
                source=source,
            )

    if logical:
        fields = catalog._database_fields(values, logical)
        if fields:
            target = result.setdefault("databases", {}).setdefault(env, {})
            for key, value in fields.items():
                if key == f"{logical}_pass":
                    target[key] = value
                else:
                    target.setdefault(key, value)
            password = fields.get(f"{logical}_pass")
            if password:
                _upsert_candidate(
                    result,
                    key=f"databases.{env}.{logical}_pass",
                    value=str(password),
                    env=env,
                    origin=origin,
                    source=source,
                )

    jwt = values.get("ONLYOFFICE_JWT_SECRET") or values.get("JWT_SECRET")
    if jwt:
        _upsert_candidate(
            result,
            key="infra.onlyoffice_jwt_secret",
            value=str(jwt),
            env=env,
            origin=origin,
            source=source,
        )


def _augment_scan(result: dict[str, Any], base_dir: Path | None = None) -> dict[str, Any]:
    from devconsole import v11_yaml_catalog as catalog

    records = _build_secret_records(base_dir)

    # First, consume directly classifiable Secret manifests.
    for record in records:
        if not record.environment or not record.canonical_values:
            continue
        origin = catalog._display_origin(record.path, base_dir)
        source = "k8s-secret-data-b64"
        if record.sources and all(value == "k8s-secret-stringData" for value in record.sources.values()):
            source = "k8s-secret-stringData"
        _apply_values(
            result,
            env=record.environment,
            logical=record.logical_database,
            values=record.canonical_values,
            origin=origin,
            source=source,
        )

    # Then resolve workload references. This is the important path when Secret
    # keys are generic (e.g. ``password``) and the Deployment tells us which
    # application environment variable they feed.
    for path in catalog._yaml_files(base_dir):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(_is_secret_document(doc) for doc in _documents(text)):
            continue
        env = catalog._detect_environment(path, text, base_dir)
        if not env:
            continue
        logical = catalog._logical_database(path, text)
        resolved: dict[str, str] = {}
        origins: list[str] = []

        for target_var, secret_name, secret_key in _extract_secret_key_refs(text):
            record = _record_for(records, env, secret_name)
            if not record:
                continue
            value = record.raw_values.get(secret_key)
            if value is None:
                # Kubernetes keys are case-sensitive, but a few hand-maintained
                # manifests drift only by case; accept a unique case-insensitive
                # match without guessing between duplicates.
                matches = [v for k, v in record.raw_values.items() if k.lower() == secret_key.lower()]
                value = matches[0] if len(matches) == 1 else None
            if value:
                resolved[target_var] = value
                origins.append(catalog._display_origin(record.path, base_dir))

        for secret_name in _extract_envfrom_refs(text):
            record = _record_for(records, env, secret_name)
            if not record:
                continue
            resolved.update(record.canonical_values)
            origins.append(catalog._display_origin(record.path, base_dir))

        if resolved:
            workload = catalog._display_origin(path, base_dir)
            secret_origins = ", ".join(dict.fromkeys(origins))
            origin = f"{secret_origins} ← {workload}" if secret_origins else workload
            _apply_values(
                result,
                env=env,
                logical=logical,
                values=resolved,
                origin=origin,
                source="k8s-secretKeyRef",
            )

    result["k8s_secret_records"] = len(records)
    return result


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from devconsole import v11_yaml_catalog as catalog

    original_extract = catalog._extract_named_values
    if not getattr(original_extract, "_v11_k8s_secret_aware", False):
        def extract_without_raw_secret_data(text: str) -> dict[str, str]:
            # Critical: never let the generic parser mistake Secret.data base64
            # text for the actual credential.
            if _is_secret_document(text):
                return {}
            return original_extract(text)

        extract_without_raw_secret_data._v11_k8s_secret_aware = True  # type: ignore[attr-defined]
        catalog._extract_named_values = extract_without_raw_secret_data

    original_scan = catalog.scan_workspace_yaml
    if not getattr(original_scan, "_v11_k8s_secret_aware", False):
        def scan_with_k8s_secrets(base_dir: Path | None = None) -> dict[str, Any]:
            return _augment_scan(original_scan(base_dir), base_dir)

        scan_with_k8s_secrets._v11_k8s_secret_aware = True  # type: ignore[attr-defined]
        catalog.scan_workspace_yaml = scan_with_k8s_secrets

    # Rehydrate the in-memory catalog now that the scanner understands Secret.
    catalog.hydrate_environment_catalog()
    _INSTALLED = True


def status() -> dict[str, Any]:
    records = _build_secret_records()
    return {
        "installed": _INSTALLED,
        "records": len(records),
        "environments": sorted({record.environment for record in records if record.environment}),
    }
