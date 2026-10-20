"""Manifest-driven project and capability detection for DevConsole V1.1.

The detector intentionally prefers standard project manifests over naming
conventions.  SISPER names (``ms_*`` / ``mf_*``) remain useful signals, but are
never the only way a project is recognized.

No command is executed while detecting.  The module is therefore safe to run on
an arbitrary workspace and can be used before any service is started.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

try:  # Python 3.11+
    import tomllib
except ImportError:  # pragma: no cover
    tomllib = None


IGNORED_DIRS = frozenset({
    ".git", ".hg", ".svn", ".idea", ".vscode", ".venv", "venv", "env",
    "node_modules", "dist", "build", "coverage", ".pytest_cache", "__pycache__",
})


@dataclass(frozen=True)
class ProjectProfile:
    name: str
    path: str
    kind: str
    languages: tuple[str, ...] = ()
    frameworks: tuple[str, ...] = ()
    package_manager: str | None = None
    manifests: tuple[str, ...] = ()
    capabilities: dict[str, bool] = field(default_factory=dict)
    commands: dict[str, str] = field(default_factory=dict)
    signals: tuple[str, ...] = ()
    confidence: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _read_text(path: Path, *, limit: int = 512_000) -> str:
    try:
        if not path.is_file() or path.stat().st_size > limit:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _read_json(path: Path) -> dict[str, Any]:
    text = _read_text(path)
    if not text:
        return {}
    try:
        value = json.loads(text)
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _read_pyproject(path: Path) -> dict[str, Any]:
    if tomllib is None:
        return {}
    try:
        with path.open("rb") as fh:
            value = tomllib.load(fh)
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _flatten_strings(value: Any) -> list[str]:
    out: list[str] = []
    if isinstance(value, str):
        out.append(value)
    elif isinstance(value, dict):
        for key, child in value.items():
            out.append(str(key))
            out.extend(_flatten_strings(child))
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            out.extend(_flatten_strings(child))
    return out


def _python_dependency_blob(root: Path, pyproject: dict[str, Any]) -> str:
    pieces = _flatten_strings(pyproject)
    for name in ("requirements.txt", "requirements-dev.txt", "Pipfile", "setup.py"):
        pieces.append(_read_text(root / name))
    return "\n".join(pieces).lower()


def _node_dependencies(package: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        values = package.get(key)
        if isinstance(values, dict):
            result.update(str(name).lower() for name in values)
    return result


def _package_manager(root: Path, pyproject: dict[str, Any], package: dict[str, Any]) -> str | None:
    declared = package.get("packageManager")
    if isinstance(declared, str) and declared:
        return declared.split("@", 1)[0]
    if (root / "pnpm-lock.yaml").is_file():
        return "pnpm"
    if (root / "yarn.lock").is_file():
        return "yarn"
    if (root / "package-lock.json").is_file():
        return "npm"
    if (root / "Pipfile").is_file():
        return "pipenv"
    if (root / "poetry.lock").is_file() or isinstance((pyproject.get("tool") or {}).get("poetry"), dict):
        return "poetry"
    if (root / "uv.lock").is_file():
        return "uv"
    if (root / "pdm.lock").is_file() or isinstance((pyproject.get("tool") or {}).get("pdm"), dict):
        return "pdm"
    if (root / "pyproject.toml").is_file() or (root / "requirements.txt").is_file():
        return "pip"
    return None


def _has_kubernetes(root: Path) -> bool:
    for dirname in ("k8s", "kubernetes", "deploy", "deployment"):
        candidate = root / dirname
        if candidate.is_dir() and any(candidate.rglob("*.yaml")):
            return True
    config = root / "config"
    if config.is_dir():
        for path in config.rglob("*.yaml"):
            text = _read_text(path, limit=128_000)
            if "apiVersion:" in text and "kind:" in text:
                return True
    return False


def _has_celery_files(root: Path) -> bool:
    if (root / "celery.py").is_file() or (root / "config" / "celery.py").is_file():
        return True
    try:
        for path in root.glob("*/celery.py"):
            if path.is_file():
                return True
        for path in root.glob("*/tasks.py"):
            if path.is_file():
                return True
    except OSError:
        pass
    return False


def _manifest_names(root: Path) -> tuple[str, ...]:
    names = (
        "manage.py", "pyproject.toml", "Pipfile", "requirements.txt",
        "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
        "Dockerfile", "Containerfile", "docker-compose.yml", "compose.yml",
        "vite.config.js", "vite.config.ts", "next.config.js", "next.config.mjs",
        "angular.json", "go.mod", "Cargo.toml", "pom.xml", "build.gradle",
    )
    return tuple(name for name in names if (root / name).exists())


def detect_project(path: str | Path) -> ProjectProfile:
    root = Path(path).expanduser().resolve()
    package = _read_json(root / "package.json")
    pyproject = _read_pyproject(root / "pyproject.toml")
    python_blob = _python_dependency_blob(root, pyproject)
    node_deps = _node_dependencies(package)
    scripts = package.get("scripts") if isinstance(package.get("scripts"), dict) else {}

    signals: list[str] = []
    languages: set[str] = set()
    frameworks: set[str] = set()
    commands: dict[str, str] = {}
    capabilities = {
        "run": False,
        "test": False,
        "migrate": False,
        "worker": False,
        "build": False,
        "container": False,
        "kubernetes": False,
        "git": (root / ".git").exists(),
        "backend": False,
        "frontend": False,
    }
    confidence = 0

    # Python / Django / DRF -------------------------------------------------
    python_manifest = any((root / n).is_file() for n in ("pyproject.toml", "Pipfile", "requirements.txt", "setup.py"))
    manage_py = (root / "manage.py").is_file()
    if python_manifest or manage_py:
        languages.add("Python")
        signals.append("python-manifest")
        confidence += 15

    if manage_py:
        frameworks.add("Django")
        capabilities.update(run=True, test=True, migrate=True, backend=True)
        commands.setdefault("run", "python manage.py runserver 127.0.0.1:{port}")
        commands.setdefault("test", "python manage.py test")
        commands.setdefault("migrate", "python manage.py migrate")
        signals.append("manage.py")
        confidence += 35
    elif re.search(r"(^|[^a-z])django([^a-z]|$)", python_blob):
        frameworks.add("Django")
        capabilities["backend"] = True
        signals.append("django-dependency")
        confidence += 20

    if "djangorestframework" in python_blob or "rest_framework" in python_blob:
        frameworks.add("Django REST Framework")
        signals.append("drf-dependency")
        confidence += 5

    celery = "celery" in python_blob or _has_celery_files(root)
    if celery:
        frameworks.add("Celery")
        capabilities["worker"] = True
        commands.setdefault("worker", "celery -A config worker -l info")
        signals.append("celery")
        confidence += 8

    # Node / frontend -------------------------------------------------------
    if package:
        languages.add("JavaScript/TypeScript")
        capabilities["frontend"] = True
        signals.append("package.json")
        confidence += 15

        if "react" in node_deps:
            frameworks.add("React")
            signals.append("react-dependency")
            confidence += 20
        if "vite" in node_deps or (root / "vite.config.js").is_file() or (root / "vite.config.ts").is_file():
            frameworks.add("Vite")
            signals.append("vite")
            confidence += 8
        if "next" in node_deps or (root / "next.config.js").is_file() or (root / "next.config.mjs").is_file():
            frameworks.add("Next.js")
            signals.append("next")
            confidence += 10
        if (root / "angular.json").is_file() or "@angular/core" in node_deps:
            frameworks.add("Angular")
            signals.append("angular")
            confidence += 10

        for source, target in (("start", "run"), ("dev", "run"), ("test", "test"), ("build", "build")):
            if source in scripts and target not in commands:
                commands[target] = f"npm run {source}"
                capabilities[target] = True

    # Other ecosystems ------------------------------------------------------
    if (root / "go.mod").is_file():
        languages.add("Go")
        capabilities.update(run=True, test=True, backend=True)
        commands.setdefault("run", "go run .")
        commands.setdefault("test", "go test ./...")
        signals.append("go.mod")
        confidence += 25
    if (root / "Cargo.toml").is_file():
        languages.add("Rust")
        capabilities.update(run=True, test=True)
        commands.setdefault("run", "cargo run")
        commands.setdefault("test", "cargo test")
        signals.append("Cargo.toml")
        confidence += 25

    # Container / K8s -------------------------------------------------------
    container_manifest = next((name for name in ("Containerfile", "Dockerfile") if (root / name).is_file()), None)
    if container_manifest:
        capabilities["container"] = True
        capabilities["build"] = True
        commands.setdefault("container_build", f"podman build -f {container_manifest} .")
        signals.append(container_manifest)
        confidence += 8

    if _has_kubernetes(root):
        capabilities["kubernetes"] = True
        signals.append("kubernetes-manifest")
        confidence += 5

    # SISPER compatibility signals ----------------------------------------
    if root.name.startswith("ms_") or root.name.startswith("ms-"):
        capabilities["backend"] = True
        signals.append("sisper-ms-name")
        confidence += 3
    if root.name.startswith("mf_") or root.name.startswith("mf-"):
        capabilities["frontend"] = True
        signals.append("sisper-mf-name")
        confidence += 3

    if capabilities["backend"] and capabilities["frontend"]:
        kind = "fullstack"
    elif capabilities["backend"]:
        kind = "backend"
    elif capabilities["frontend"]:
        kind = "frontend"
    elif languages:
        kind = "application"
    else:
        kind = "unknown"

    manager = _package_manager(root, pyproject, package)
    if manager == "pipenv" and manage_py:
        commands["run"] = "pipenv run python manage.py runserver 127.0.0.1:{port}"
        commands["test"] = "pipenv run python manage.py test"
        commands["migrate"] = "pipenv run python manage.py migrate"
        if capabilities["worker"]:
            commands["worker"] = "pipenv run celery -A config worker -l info"
    elif manager in {"pnpm", "yarn"}:
        executable = manager
        for action in ("run", "test", "build"):
            command = commands.get(action)
            if command and command.startswith("npm run "):
                commands[action] = command.replace("npm run ", f"{executable} ", 1)

    return ProjectProfile(
        name=root.name,
        path=str(root),
        kind=kind,
        languages=tuple(sorted(languages)),
        frameworks=tuple(sorted(frameworks)),
        package_manager=manager,
        manifests=_manifest_names(root),
        capabilities=capabilities,
        commands=commands,
        signals=tuple(signals),
        confidence=min(100, confidence),
    )


def _candidate_dirs(workspace: Path) -> Iterable[Path]:
    """Yield likely project roots without recursively walking dependency trees."""
    seen: set[Path] = set()

    def emit(path: Path):
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            return resolved
        return None

    root_candidate = emit(workspace)
    if root_candidate is not None:
        yield root_candidate

    for container_name in ("backend", "frontend", "services", "apps"):
        container = workspace / container_name
        if not container.is_dir():
            continue
        try:
            children = sorted(container.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_dir() and child.name not in IGNORED_DIRS:
                candidate = emit(child)
                if candidate is not None:
                    yield candidate

    try:
        direct_children = sorted(workspace.iterdir())
    except OSError:
        direct_children = []
    for child in direct_children:
        if not child.is_dir() or child.name in IGNORED_DIRS or child.name in {"backend", "frontend", "services", "apps"}:
            continue
        if _manifest_names(child):
            candidate = emit(child)
            if candidate is not None:
                yield candidate


def detect_workspace(path: str | Path) -> list[ProjectProfile]:
    workspace = Path(path).expanduser().resolve()
    profiles: list[ProjectProfile] = []
    for candidate in _candidate_dirs(workspace):
        profile = detect_project(candidate)
        if profile.kind != "unknown" or profile.manifests:
            profiles.append(profile)
    return profiles


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detect DevConsole project capabilities without executing commands.")
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("--workspace", action="store_true", help="scan common workspace child directories")
    args = parser.parse_args(argv)

    if args.workspace:
        payload = [profile.to_dict() for profile in detect_workspace(args.path)]
    else:
        payload = detect_project(args.path).to_dict()
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
