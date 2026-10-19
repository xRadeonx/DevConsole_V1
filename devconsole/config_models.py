"""Typed, backwards-compatible configuration validation for DevConsole V1.1."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

try:
    from pydantic import BaseModel, ConfigDict, Field, ValidationError
except ImportError:  # pragma: no cover - minimal/offline installation fallback
    BaseModel = None  # type: ignore[assignment]
    ConfigDict = None  # type: ignore[assignment]
    Field = None  # type: ignore[assignment]
    ValidationError = Exception  # type: ignore[assignment]


@dataclass(frozen=True)
class ValidationReport:
    valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "errors": list(self.errors), "warnings": list(self.warnings)}


if BaseModel is not None:
    class ServiceConfigModel(BaseModel):
        model_config = ConfigDict(extra="allow")
        name: str
        port: int | None = Field(default=None, ge=1, le=65535)
        path: str | None = None
        type: str | None = None
        kind: str | None = None
        k8s_file: str | None = None
        k8s_deploy: str | None = None


    class PanelConfigModel(BaseModel):
        model_config = ConfigDict(extra="allow")
        project_name: str | None = None
        registry: str | None = None
        local_subnet: str | None = None
        backend_default_port: int | None = Field(default=None, ge=1, le=65535)
        frontend_default_port: int | None = Field(default=None, ge=1, le=65535)
else:
    ServiceConfigModel = None  # type: ignore[assignment,misc]
    PanelConfigModel = None  # type: ignore[assignment,misc]


def _format_validation_error(exc: Exception) -> tuple[str, ...]:
    if hasattr(exc, "errors"):
        out: list[str] = []
        for err in exc.errors():  # type: ignore[attr-defined]
            loc = ".".join(str(x) for x in err.get("loc", ())) or "<root>"
            out.append(f"{loc}: {err.get('msg', 'valor inválido')}")
        return tuple(out)
    return (str(exc),)


def validate_panel_config(data: dict[str, Any]) -> ValidationReport:
    if BaseModel is None:
        return ValidationReport(True, warnings=("pydantic no instalado; validación tipada omitida",))
    try:
        PanelConfigModel.model_validate(data)
        return ValidationReport(True)
    except ValidationError as exc:
        return ValidationReport(False, _format_validation_error(exc))


def validate_service_catalog(services: Iterable[dict[str, Any]]) -> ValidationReport:
    if BaseModel is None:
        return ValidationReport(True, warnings=("pydantic no instalado; validación tipada omitida",))
    errors: list[str] = []
    names: set[str] = set()
    ports: dict[int, str] = {}
    for index, raw in enumerate(services):
        try:
            item = ServiceConfigModel.model_validate(raw)
        except ValidationError as exc:
            errors.extend(f"services[{index}].{msg}" for msg in _format_validation_error(exc))
            continue
        if item.name in names:
            errors.append(f"services[{index}].name: servicio duplicado {item.name!r}")
        names.add(item.name)
        if item.port is not None:
            previous = ports.get(item.port)
            if previous and previous != item.name:
                errors.append(f"services[{index}].port: {item.port} también pertenece a {previous}")
            ports[item.port] = item.name
    return ValidationReport(not errors, tuple(errors))
