"""Framework-agnostic project/capability discovery for DevConsole V1.1."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ProjectProfile:
    name: str
    path: str
    kind: str
    frameworks: tuple[str, ...] = ()
    package_manager: str | None = None
    capabilities: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        data = asdict(self)
        data["frameworks"] = list(self.frameworks)
        data["capabilities"] = list(self.capabilities)
        data["evidence"] = list(self.evidence)
        return data


def _read_text(path: Path, limit: int = 512_000) -> str:
    try:
        if path.stat().st_size > limit:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _python_dependencies(path: Path) -> str:
    parts: list[str] = []
    for name in ("Pipfile", "pyproject.toml", "requirements.txt", "requirements-dev.txt"):
        file = path / name
        if file.is_file():
            parts.append(_read_text(file).lower())
    return "\n".join(parts)


def _package_json(path: Path) -> dict:
    file = path / "package.json"
    if not file.is_file():
        return {}
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _package_manager(path: Path, package: dict) -> str | None:
    if (path / "uv.lock").exists():
        return "uv"
    if (path / "poetry.lock").exists():
        return "poetry"
    if (path / "Pipfile").exists():
        return "pipenv"
    if (path / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (path / "yarn.lock").exists():
        return "yarn"
    if (path / "bun.lockb").exists() or (path / "bun.lock").exists():
        return "bun"
    if (path / "package-lock.json").exists() or package:
        return "npm"
    if (path / "requirements.txt").exists() or (path / "pyproject.toml").exists():
        return "pip"
    return None


def detect_project(path: Path | str) -> ProjectProfile | None:
    root = Path(path).resolve()
    if not root.is_dir() or root.name.startswith("."):
        return None

    frameworks: set[str] = set()
    capabilities: set[str] = {"git"} if (root / ".git").exists() else set()
    evidence: list[str] = []
    pydeps = _python_dependencies(root)
    package = _package_json(root)
    deps = {}
    if package:
        deps.update(package.get("dependencies") or {})
        deps.update(package.get("devDependencies") or {})

    if (root / "manage.py").is_file() or "django" in pydeps:
        frameworks.add("django")
        capabilities.update({"run", "test", "migrate", "shell"})
        evidence.append("manage.py/django dependency")
    if "djangorestframework" in pydeps or "rest_framework" in pydeps:
        frameworks.add("drf")
        evidence.append("DRF dependency")
    celery_markers = ("celery" in pydeps or (root / "celery.py").exists())
    if celery_markers:
        frameworks.add("celery")
        capabilities.update({"worker", "beat"})
        evidence.append("Celery dependency/config")
    if package:
        frameworks.add("node")
        capabilities.update({"run", "test"})
        evidence.append("package.json")
    if "react" in deps:
        frameworks.add("react")
        evidence.append("React dependency")
    if (root / "Dockerfile").is_file():
        capabilities.add("build")
        evidence.append("Dockerfile")
    manifests = list(root.glob("*.yaml")) + list(root.glob("*.yml"))
    if (root / "k8s").is_dir() or any("kind:" in _read_text(p, 128_000) for p in manifests[:10]):
        capabilities.add("deploy")
        evidence.append("Kubernetes manifest")

    if not frameworks and not capabilities:
        return None
    if "django" in frameworks:
        kind = "backend"
    elif "react" in frameworks or package:
        kind = "frontend"
    else:
        kind = "service"
    return ProjectProfile(
        name=root.name,
        path=str(root),
        kind=kind,
        frameworks=tuple(sorted(frameworks)),
        package_manager=_package_manager(root, package),
        capabilities=tuple(sorted(capabilities)),
        evidence=tuple(evidence),
    )


def _candidate_dirs(root: Path) -> Iterable[Path]:
    seen: set[Path] = set()
    for container in (root / "backend", root / "frontend", root):
        if not container.is_dir():
            continue
        if container == root:
            candidates = [p for p in container.iterdir() if p.is_dir() and p.name not in {"backend", "frontend", ".git", "node_modules", "venv", ".venv"}]
        else:
            candidates = [p for p in container.iterdir() if p.is_dir()]
        for path in candidates:
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                yield path


def detect_workspace(root: Path | str) -> list[ProjectProfile]:
    base = Path(root).resolve()
    profiles = [p for path in _candidate_dirs(base) if (p := detect_project(path)) is not None]
    return sorted(profiles, key=lambda item: (item.kind, item.name.lower()))
