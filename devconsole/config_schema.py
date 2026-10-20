"""Optional typed configuration validation for DevConsole V1.1.

Schemas are intentionally permissive (``extra='allow'``): configuration used by
this SISPER/PROTEO installation may contain project-specific fields and V1.1 must
not reject them simply because the core schema does not know them yet.

During shadow mode validation reports issues but does not prevent V1 from
loading its existing JSON configuration.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
except ImportError:  # pragma: no cover
    BaseModel = None
    ConfigDict = None
    Field = None
    ValidationError = Exception
    field_validator = None


@dataclass(frozen=True)
class ValidationReport:
    valid: bool
    schema: str
    errors: tuple[str, ...] = ()
    normalized: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "schema": self.schema,
            "errors": list(self.errors),
            "normalized": self.normalized,
        }


def available() -> bool:
    return BaseModel is not None


if BaseModel is not None:
    class _PermissiveModel(BaseModel):
        model_config = ConfigDict(extra="allow")


    class EnvironmentConfig(_PermissiveModel):
        label: str | None = None
        branch: str | None = None
        color: str | None = None
        k8s_dir: str | None = None
        namespace: str | None = None
        description: str | None = None


    class ServiceConfig(_PermissiveModel):
        name: str
        port: int | None = Field(default=None, ge=1, le=65535)
        group: str | None = None
        k8s_file: str | None = None
        k8s_deploy: str | None = None

        @field_validator("name")
        @classmethod
        def name_not_blank(cls, value: str) -> str:
            clean = value.strip()
            if not clean:
                raise ValueError("service name cannot be blank")
            return clean


    class WorkerConfig(_PermissiveModel):
        id: str | None = None
        name: str | None = None
        service: str
        queue: str | None = None
        command: str


    class ServicesCatalog(_PermissiveModel):
        project_name: str | None = None
        environments: dict[str, EnvironmentConfig] = Field(default_factory=dict)
        services_backend: list[ServiceConfig] = Field(default_factory=list)
        services_frontend: list[ServiceConfig] = Field(default_factory=list)
        workers: list[WorkerConfig] = Field(default_factory=list)
        infrastructure: list[dict[str, Any]] = Field(default_factory=list)
        slices: dict[str, Any] = Field(default_factory=dict)


    class InfraContainer(_PermissiveModel):
        container_name: str | None = None
        image: str | None = None
        label: str | None = None
        port: int | None = Field(default=None, ge=1, le=65535)
        run_cmd: list[str] = Field(default_factory=list)


    class PanelConfig(_PermissiveModel):
        project_name: str | None = None
        registry: str | None = None
        local_subnet: str | None = None
        config_repo_dir: str | None = None
        onlyoffice_sync_service: str | None = None
        ports: dict[str, int] = Field(default_factory=dict)
        infra_containers: dict[str, InfraContainer] = Field(default_factory=dict)
        infra_targets: dict[str, Any] = Field(default_factory=dict)
        keycloak: dict[str, Any] = Field(default_factory=dict)
        databases: dict[str, Any] = Field(default_factory=dict)
        seasonal_themes: list[dict[str, Any]] = Field(default_factory=list)

        @field_validator("ports")
        @classmethod
        def valid_ports(cls, value: dict[str, int]) -> dict[str, int]:
            invalid = [name for name, port in value.items() if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535]
            if invalid:
                raise ValueError(f"invalid ports for: {', '.join(sorted(invalid))}")
            return value
else:  # pragma: no cover - names exist for importers even without dependency
    EnvironmentConfig = ServiceConfig = WorkerConfig = ServicesCatalog = InfraContainer = PanelConfig = None


def _format_errors(exc: Exception) -> tuple[str, ...]:
    if available() and isinstance(exc, ValidationError):
        out: list[str] = []
        for error in exc.errors():
            location = ".".join(str(part) for part in error.get("loc", ())) or "root"
            out.append(f"{location}: {error.get('msg', 'invalid value')}")
        return tuple(out)
    return (str(exc),)


def validate_dict(data: dict[str, Any], *, schema: str) -> ValidationReport:
    if not available():
        return ValidationReport(False, schema, ("pydantic unavailable",), None)
    model_cls = {"panel": PanelConfig, "services": ServicesCatalog}.get(schema)
    if model_cls is None:
        return ValidationReport(False, schema, (f"unknown schema: {schema}",), None)
    if not isinstance(data, dict):
        return ValidationReport(False, schema, ("root must be a JSON object",), None)
    try:
        model = model_cls.model_validate(data)
    except Exception as exc:
        return ValidationReport(False, schema, _format_errors(exc), None)
    return ValidationReport(True, schema, (), model.model_dump(mode="json"))


def validate_file(path: str | Path, *, schema: str) -> ValidationReport:
    target = Path(path)
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return ValidationReport(False, schema, (f"file not found: {target}",), None)
    except (OSError, ValueError) as exc:
        return ValidationReport(False, schema, (f"json read error: {exc}",), None)
    return validate_dict(raw, schema=schema)


def validate_installation(root: str | Path) -> dict[str, ValidationReport]:
    root = Path(root)
    config = root / "config"
    panel = config / "panel.json"
    services = config / "services.json"
    return {
        "panel": validate_file(panel, schema="panel") if panel.exists() else ValidationReport(True, "panel", (), None),
        "services": validate_file(services, schema="services") if services.exists() else ValidationReport(True, "services", (), None),
    }
