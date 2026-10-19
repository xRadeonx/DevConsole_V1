"""V1.1 startup diagnostics.  Validation is observational and never rewrites config."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from devconsole.config_models import validate_panel_config, validate_service_catalog


def dependency_status() -> dict[str, bool]:
    return {
        "psutil": importlib.util.find_spec("psutil") is not None,
        "pydantic": importlib.util.find_spec("pydantic") is not None,
        "ruamel.yaml": importlib.util.find_spec("ruamel.yaml") is not None,
    }


def _json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except Exception as exc:
        return {"__load_error__": str(exc)}


def configuration_diagnostics(base_dir: Path | str) -> dict:
    root = Path(base_dir)
    panel = _json(root / "config" / "panel.json")
    services = _json(root / "config" / "services.json")
    result = {"dependencies": dependency_status(), "panel": None, "services": None}
    if isinstance(panel, dict):
        if "__load_error__" in panel:
            result["panel"] = {"valid": False, "errors": [panel["__load_error__"]], "warnings": []}
        else:
            result["panel"] = validate_panel_config(panel).to_dict()
    if isinstance(services, dict):
        catalog = services.get("services") or services.get("backend", []) + services.get("frontend", [])
        if isinstance(catalog, list):
            result["services"] = validate_service_catalog(catalog).to_dict()
    elif isinstance(services, list):
        result["services"] = validate_service_catalog(services).to_dict()
    return result


def print_startup_diagnostics(base_dir: Path | str) -> None:
    diag = configuration_diagnostics(base_dir)
    deps = diag["dependencies"]
    available = ", ".join(name for name, ok in deps.items() if ok) or "ninguna opcional"
    print(f"[*] V1.1 dependencias disponibles: {available}")
    for key in ("panel", "services"):
        report = diag.get(key)
        if report and not report.get("valid", True):
            print(f"[!] Configuración {key} con observaciones: {'; '.join(report.get('errors', []))}")
