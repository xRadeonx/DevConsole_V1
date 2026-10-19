"""Temporary git worktrees for non-destructive builds."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from devconsole.local_trust import runtime_dir


class WorktreeError(RuntimeError):
    pass


def _git(repo: Path, *args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=timeout)


@contextmanager
def temporary_worktree(repo: Path | str, ref: str = "HEAD") -> Iterator[Path]:
    """Yield a detached worktree and always remove it afterwards.

    The developer's active branch and uncommitted files are never modified.
    """
    repo_path = Path(repo).resolve()
    if not (repo_path / ".git").exists():
        probe = _git(repo_path, "rev-parse", "--git-dir")
        if probe.returncode != 0:
            raise WorktreeError(f"No es un repositorio git: {repo_path}")
    base = runtime_dir() / "worktrees"
    base.mkdir(parents=True, exist_ok=True)
    target = Path(tempfile.mkdtemp(prefix=f"{repo_path.name}-", dir=str(base)))
    try:
        # mkdtemp creates the directory, while git worktree add requires the
        # destination not to exist.
        target.rmdir()
        result = _git(repo_path, "worktree", "add", "--detach", str(target), ref, timeout=90)
        if result.returncode != 0:
            raise WorktreeError((result.stderr or result.stdout or "git worktree add falló").strip())
        yield target
    finally:
        try:
            _git(repo_path, "worktree", "remove", "--force", str(target), timeout=30)
        except Exception:
            pass
        shutil.rmtree(target, ignore_errors=True)
        try:
            _git(repo_path, "worktree", "prune", timeout=15)
        except Exception:
            pass
