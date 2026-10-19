"""Read-only GO/NO-GO acceptance check for DevConsole V1.1.

Run on the real workstation before merging/releasing::

    python3 -m devconsole.acceptance
    python3 -m devconsole.acceptance --json
    python3 -m devconsole.acceptance --strict

The command never launches/stops services, changes Git branches, edits .env/YAML,
builds images or contacts Kubernetes.  It only inspects the local installation
and reports which host-dependent capabilities are available for manual smoke
validation.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Check:
    name: str
    status: str  # pass | warn | fail
    detail: str


@dataclass(frozen=True)
class AcceptanceReport:
    verdict: str
    checks: tuple[Check, ...]
    workspace: str
    python: str

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "workspace": self.workspace,
            "python": self.python,
            "checks": [asdict(check) for check in self.checks],
        }


def _tool(name: str) -> str | None:
    return shutil.which(name)


def _check_file(root: Path, relative: str) -> Check:
    path = root / relative
    return Check(
        f"file:{relative}",
        "pass" if path.is_file() else "fail",
        str(path) if path.is_file() else "archivo requerido ausente",
    )


def _dependency(name: str) -> Check:
    available = importlib.util.find_spec(name) is not None
    return Check(
        f"python:{name}",
        "pass" if available else "warn",
        "disponible" if available else "no instalado; V1 fallback seguirá operativo",
    )


def _system_tool(name: str, *, capability: str) -> Check:
    path = _tool(name)
    return Check(
        f"tool:{name}",
        "pass" if path else "warn",
        path or f"no disponible; capacidad {capability} no puede validarse en este host",
    )


def _append_config_checks(checks: list[Check], root: Path) -> None:
    try:
        from devconsole.startup import configuration_diagnostics

        diagnostics = configuration_diagnostics(root)
        for section in ("panel", "services"):
            report = diagnostics.get(section)
            if report is None:
                checks.append(Check(f"config:{section}", "warn", "archivo no presente; se usarán defaults/descubrimiento"))
            elif report.get("valid", True):
                warnings = report.get("warnings") or []
                checks.append(Check(f"config:{section}", "pass", "; ".join(warnings) or "válida"))
            else:
                checks.append(Check(f"config:{section}", "fail", "; ".join(report.get("errors") or ["inválida"])))
    except Exception as exc:
        checks.append(Check("config:diagnostics", "fail", f"{type(exc).__name__}: {exc}"))


def _append_workspace_checks(checks: list[Check], workspace: Path) -> None:
    try:
        from devconsole.services.project_detector import detect_workspace

        projects = detect_workspace(workspace)
        if projects:
            frameworks = sorted({fw for project in projects for fw in project.frameworks})
            checks.append(Check(
                "workspace:projects",
                "pass",
                f"{len(projects)} proyecto(s) detectados; frameworks={','.join(frameworks) or 'genérico'}",
            ))
        else:
            checks.append(Check(
                "workspace:projects",
                "warn",
                "no se detectaron proyectos; selecciona el workspace real antes de la aceptación funcional",
            ))
    except Exception as exc:
        checks.append(Check("workspace:projects", "fail", f"{type(exc).__name__}: {exc}"))


def _append_terminal_checks(checks: list[Check], static_dir: Path) -> None:
    try:
        from devconsole.services.terminal.capabilities import terminal_capabilities

        caps = terminal_capabilities(static_dir)
        checks.append(Check("terminal:xterm", "pass" if caps.get("xterm") else "fail", "asset xterm.js autoalojado" if caps.get("xterm") else "asset xterm.js ausente"))
        checks.append(Check("terminal:tmux", "pass" if caps.get("tmux") else "warn", "disponible como owner de sesión" if caps.get("tmux") else "no instalado; se usará fallback Tilix"))
        checks.append(Check("terminal:tilix", "pass" if caps.get("tilix") else "warn", "disponible como visor/fallback" if caps.get("tilix") else "no instalado en este host"))
        addons = caps.get("addons") or {}
        for addon in ("fit", "search"):
            checks.append(Check(f"terminal:addon:{addon}", "pass" if addons.get(addon) else "warn", "autoalojado" if addons.get(addon) else "asset no disponible"))
    except Exception as exc:
        checks.append(Check("terminal:capabilities", "fail", f"{type(exc).__name__}: {exc}"))


def _append_security_checks(checks: list[Check]) -> None:
    try:
        from devconsole.services.tls_policy import keycloak_tls_policy

        tls = keycloak_tls_policy()
        checks.append(Check(
            "security:keycloak-tls",
            "warn" if tls.insecure else "pass",
            "TLS inseguro habilitado explícitamente" if tls.insecure else f"verificación TLS activa ({tls.source})",
        ))
    except Exception as exc:
        checks.append(Check("security:keycloak-tls", "fail", f"{type(exc).__name__}: {exc}"))

    handler = os.environ.get("SISPER_V11_HANDLER", "1").strip()
    checks.append(Check(
        "security:v11-handler",
        "warn" if handler == "0" else "pass",
        "rollback V1 explícitamente activo" if handler == "0" else "facade V1.1 activo por defecto",
    ))

    trust = os.environ.get("SISPER_LOCAL_TOKEN_REQUIRED")
    if trust == "0":
        checks.append(Check("security:local-trust", "warn", "deshabilitado explícitamente por entorno"))
    else:
        checks.append(Check("security:local-trust", "pass", "el servidor lo habilita por defecto"))


def run_acceptance(root: Path | None = None, *, strict: bool = False) -> AcceptanceReport:
    package_root = Path(__file__).resolve().parents[1]
    repo_root = (root or package_root).resolve()

    checks: list[Check] = []
    version = sys.version_info
    checks.append(Check(
        "python:version",
        "pass" if version >= (3, 11) else "fail",
        platform.python_version(),
    ))

    for relative in (
        "dashboard.py",
        "static/index.html",
        "static/js/dashboard.js",
        "static/js/app-v11.js",
        "tmux_safe_runner.sh",
        "requirements-v11.txt",
    ):
        checks.append(_check_file(repo_root, relative))

    for dependency in ("psutil", "pydantic", "ruamel.yaml"):
        checks.append(_dependency(dependency))

    checks.append(_system_tool("git", capability="Git"))
    checks.append(_system_tool("kubectl", capability="Kubernetes"))
    podman = _tool("podman")
    docker = _tool("docker")
    checks.append(Check(
        "tool:container-engine",
        "pass" if podman or docker else "warn",
        podman or docker or "ni Podman ni Docker disponibles",
    ))

    _append_config_checks(checks, repo_root)

    try:
        import devconsole.config as dcfg
        workspace = Path(dcfg.BASE_DIR).resolve()
        static_dir = Path(dcfg.STATIC_DIR).resolve()
    except Exception:
        workspace = repo_root
        static_dir = repo_root / "static"

    _append_workspace_checks(checks, workspace)
    _append_terminal_checks(checks, static_dir)
    _append_security_checks(checks)

    has_fail = any(check.status == "fail" for check in checks)
    has_warn = any(check.status == "warn" for check in checks)
    verdict = "NO-GO" if has_fail or (strict and has_warn) else ("GO-WITH-WARNINGS" if has_warn else "GO")
    return AcceptanceReport(verdict, tuple(checks), str(workspace), platform.python_version())


def _print_human(report: AcceptanceReport) -> None:
    symbols = {"pass": "✓", "warn": "!", "fail": "✗"}
    print("DevConsole V1.1 — aceptación local (solo lectura)")
    print(f"Workspace: {report.workspace}")
    print(f"Python:    {report.python}")
    print()
    for check in report.checks:
        print(f"[{symbols.get(check.status, '?')}] {check.name}: {check.detail}")
    print()
    print(f"VEREDICTO: {report.verdict}")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aceptación no destructiva de DevConsole V1.1")
    parser.add_argument("--json", action="store_true", help="imprime el reporte como JSON")
    parser.add_argument("--strict", action="store_true", help="trata advertencias como NO-GO")
    parser.add_argument("--root", type=Path, help="raíz del checkout DevConsole (default: autodetectada)")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = run_acceptance(args.root, strict=args.strict)
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        _print_human(report)
    return 2 if report.verdict == "NO-GO" else 0


if __name__ == "__main__":
    raise SystemExit(main())
