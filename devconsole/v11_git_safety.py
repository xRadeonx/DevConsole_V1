"""Non-destructive Git safety guards for the V1.1 migration.

The legacy checkout implementation removes ``.git/index.lock`` after a very
short age threshold.  A lock file does not prove that the writer is dead; it may
belong to a legitimate Git process.  V1.1 therefore blocks checkout while any
index lock exists and leaves recovery to the operator/Git.

All normal checkout behaviour remains delegated to the V1 implementation.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

_INSTALLED = False
_ORIGINAL_CHECKOUT = None


def _repo_for(git_service, service_name: str) -> Path | None:
    try:
        repo = git_service.get_service_repo_dir(service_name)
    except Exception:
        return None
    if repo is None:
        return None
    try:
        return Path(repo).expanduser().resolve()
    except (OSError, RuntimeError):
        return Path(repo).expanduser()


def lock_status(repo: str | Path) -> dict[str, Any]:
    """Return diagnostic information without mutating the repository."""
    root = Path(repo)
    lock = root / ".git" / "index.lock"
    if not lock.exists():
        return {"locked": False, "path": str(lock), "age_seconds": None}
    try:
        age = max(0.0, time.time() - lock.stat().st_mtime)
    except OSError:
        age = None
    return {
        "locked": True,
        "path": str(lock),
        "age_seconds": round(age, 3) if age is not None else None,
    }


def checkout_guarded(git_service, original, service_name: str, branch: str):
    """Block checkout when Git's own index lock is present."""
    repo = _repo_for(git_service, service_name)
    if repo is not None:
        status = lock_status(repo)
        if status["locked"]:
            age = status["age_seconds"]
            age_text = f" ({age:.1f}s)" if isinstance(age, (int, float)) else ""
            return False, (
                f"Git está ocupado o dejó un index.lock en {service_name}{age_text}. "
                "DevConsole no eliminará el lock automáticamente. Verifica que no haya "
                "otro proceso Git activo y resuelve el lock de forma explícita antes de "
                "cambiar de rama."
            )
    return original(service_name, branch)


def install() -> None:
    """Install the guard before API handlers import checkout by value."""
    global _INSTALLED, _ORIGINAL_CHECKOUT
    if _INSTALLED:
        return

    from devconsole.services import git_service

    _ORIGINAL_CHECKOUT = git_service.checkout_service_branch

    def checkout_service_branch_v11(service_name: str, branch: str):
        return checkout_guarded(git_service, _ORIGINAL_CHECKOUT, service_name, branch)

    git_service.checkout_service_branch = checkout_service_branch_v11
    _INSTALLED = True


def status() -> dict[str, Any]:
    return {
        "policy": "never-delete-index-lock",
        "installed": _INSTALLED,
    }
