"""Safe Git branch switching used by DevConsole V1.1 runtime.

A Git index lock is evidence that another Git operation may be active.  It is
never safe for an orchestrator to infer that the lock is stale from age alone.
V1.1 therefore reports the lock and leaves it untouched.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from devconsole.config import get_service_repo_dir


def _git(repo: Path, *args: str, timeout: int = 10) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=timeout)


def _git_dir(repo: Path) -> Path | None:
    result = _git(repo, "rev-parse", "--git-dir", timeout=5)
    if result.returncode != 0:
        return None
    path = Path(result.stdout.strip())
    return path if path.is_absolute() else (repo / path).resolve()


def checkout_service_branch_safe(service_name: str, branch: str):
    repo = Path(get_service_repo_dir(service_name)).resolve()
    if not repo.exists():
        return False, f"Repositorio no encontrado para {service_name}"
    git_dir = _git_dir(repo)
    if git_dir is None:
        return False, f"Repositorio Git inválido para {service_name}"
    lock = git_dir / "index.lock"
    if lock.exists():
        return False, (
            f"Git está ocupado en {service_name}: existe {lock}. "
            "DevConsole no elimina locks automáticamente; verifica el proceso Git activo."
        )

    dirty = _git(repo, "status", "--porcelain", timeout=5)
    if dirty.returncode != 0:
        return False, (dirty.stderr or dirty.stdout or "No se pudo leer git status").strip()
    changes = [line for line in dirty.stdout.splitlines() if line.strip()]
    if changes:
        return False, (
            f"Hay {len(changes)} archivo(s) modificado(s) sin confirmar en {service_name}. "
            "Haz commit o stash antes de cambiar de rama."
        )

    target = (branch or "").strip()
    if not target:
        return False, "Indica la rama de destino."
    local = _git(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{target}", timeout=5).returncode == 0
    remote = _git(repo, "show-ref", "--verify", "--quiet", f"refs/remotes/origin/{target}", timeout=5).returncode == 0
    if local:
        result = _git(repo, "checkout", target, timeout=15)
    elif remote:
        result = _git(repo, "checkout", "-b", target, "--track", f"origin/{target}", timeout=15)
    else:
        return False, f"La rama '{target}' no existe localmente ni en origin."
    if result.returncode != 0:
        return False, f"Git error: {(result.stderr or result.stdout).strip()}"
    return True, f"Rama cambiada a '{target}' con éxito."


def install_checkout_guard() -> None:
    """Patch the legacy call site after modules are loaded, idempotently."""
    from devconsole.services import git_service
    from devconsole.api import handlers

    git_service.checkout_service_branch = checkout_service_branch_safe
    handlers.checkout_service_branch = checkout_service_branch_safe
