"""Transactional guard for workspace-wide environment/branch changes.

The V1 implementation changes repositories one by one.  If repository N fails,
repositories 1..N-1 may already be on the target branch while the rest remain on
the previous environment.  V1.1 adds a non-mutating preflight and best-effort
rollback while delegating the actual successful switch to the legacy function.

No stash/reset/clean operation is ever performed automatically.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from devconsole import v11_git_safety

_INSTALLED = False
_ORIGINAL_SWITCH = None


@dataclass(frozen=True)
class RepoPreflight:
    name: str
    path: str
    current_branch: str = ""
    target_branch: str = ""
    ready: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "current_branch": self.current_branch,
            "target_branch": self.target_branch,
            "ready": self.ready,
            "reason": self.reason,
        }


def _git(repo: Path, *args: str, timeout: float = 3.0) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _target_known(repo: Path, branch: str) -> bool:
    for ref in (f"refs/heads/{branch}", f"refs/remotes/origin/{branch}"):
        try:
            result = _git(repo, "show-ref", "--verify", "--quiet", ref)
        except Exception:
            continue
        if result.returncode == 0:
            return True
    return False


def preflight_repository(repo: Path, name: str, target_branch: str) -> RepoPreflight:
    repo = Path(repo)
    if not repo.is_dir() or not (repo / ".git").exists():
        return RepoPreflight(name, str(repo), target_branch=target_branch, reason="repository_not_found")

    lock = v11_git_safety.lock_status(repo)
    if lock.get("locked"):
        return RepoPreflight(name, str(repo), target_branch=target_branch, reason="index_lock_present")

    try:
        branch_result = _git(repo, "branch", "--show-current")
        current = branch_result.stdout.strip()
    except Exception as exc:
        return RepoPreflight(name, str(repo), target_branch=target_branch, reason=f"branch_probe:{type(exc).__name__}")
    if branch_result.returncode != 0 or not current:
        return RepoPreflight(name, str(repo), target_branch=target_branch, reason="detached_or_unknown_branch")

    try:
        status = _git(repo, "status", "--porcelain")
    except Exception as exc:
        return RepoPreflight(name, str(repo), current, target_branch, reason=f"status_probe:{type(exc).__name__}")
    if status.returncode != 0:
        return RepoPreflight(name, str(repo), current, target_branch, reason="git_status_failed")
    if status.stdout.strip():
        return RepoPreflight(name, str(repo), current, target_branch, reason="working_tree_dirty")

    if current != target_branch and not _target_known(repo, target_branch):
        return RepoPreflight(name, str(repo), current, target_branch, reason="target_branch_not_known")

    return RepoPreflight(name, str(repo), current, target_branch, True, "ready")


def preflight_workspace(env_service, target_env: str) -> tuple[str, list[RepoPreflight]]:
    target_branch = env_service.ENVIRONMENTS.get(target_env, {}).get("branch", target_env)
    rows: list[RepoPreflight] = []
    for service in list(env_service.SERVICES_BACKEND) + list(env_service.SERVICES_FRONTEND):
        name = str(service.get("name") or "").strip()
        if not name:
            continue
        repo = env_service.get_service_repo_dir(name)
        rows.append(preflight_repository(Path(repo), name, target_branch))
    return target_branch, rows


def _rollback(rows: list[RepoPreflight]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for row in reversed(rows):
        if not row.current_branch:
            continue
        repo = Path(row.path)
        try:
            current = _git(repo, "branch", "--show-current").stdout.strip()
            if current == row.current_branch:
                results.append({"name": row.name, "status": "unchanged", "branch": current})
                continue
            result = _git(repo, "checkout", row.current_branch, timeout=8)
            results.append({
                "name": row.name,
                "status": "restored" if result.returncode == 0 else "rollback_error",
                "branch": row.current_branch,
                "message": result.stderr.strip() or result.stdout.strip(),
            })
        except Exception as exc:
            results.append({
                "name": row.name,
                "status": "rollback_error",
                "branch": row.current_branch,
                "message": str(exc),
            })
    return results


def switch_guarded(env_service, original, target_env: str, force_pull: bool = False) -> dict[str, Any]:
    """Run a workspace switch only after every repository passes preflight."""
    if target_env not in env_service.ENVIRONMENTS:
        return {
            "target_env": target_env,
            "target_branch": "",
            "aborted": True,
            "transactional": True,
            "reason": "unknown_environment",
            "results": [],
        }

    target_branch, rows = preflight_workspace(env_service, target_env)
    blockers = [row for row in rows if not row.ready]
    if blockers:
        return {
            "target_env": target_env,
            "target_branch": target_branch,
            "aborted": True,
            "transactional": True,
            "reason": "preflight_failed",
            "preflight": [row.to_dict() for row in rows],
            "results": [
                {
                    "name": row.name,
                    "status": "protected",
                    "message": row.reason,
                }
                for row in blockers
            ],
        }

    result = original(target_env, force_pull)
    result = dict(result) if isinstance(result, dict) else {"results": []}
    result.setdefault("target_env", target_env)
    result.setdefault("target_branch", target_branch)
    result["transactional"] = True
    result["preflight"] = [row.to_dict() for row in rows]

    operation_results = result.get("results") or []
    failed = [item for item in operation_results if item.get("status") != "success"]
    if failed:
        rollback = _rollback(rows)
        result["aborted"] = True
        result["reason"] = "execution_failed_rolled_back"
        result["rollback"] = rollback
        result["rollback_ok"] = all(item.get("status") in {"restored", "unchanged"} for item in rollback)
    else:
        result["aborted"] = False
        result["reason"] = "committed"
        result["rollback"] = []
        result["rollback_ok"] = True
    return result


def install() -> None:
    global _INSTALLED, _ORIGINAL_SWITCH
    if _INSTALLED:
        return

    from devconsole.services import env_service

    _ORIGINAL_SWITCH = env_service.switch_workspace_environment

    def switch_workspace_environment_v11(target_env: str, force_pull: bool = False):
        return switch_guarded(env_service, _ORIGINAL_SWITCH, target_env, force_pull)

    env_service.switch_workspace_environment = switch_workspace_environment_v11
    _INSTALLED = True


def status() -> dict[str, Any]:
    return {"installed": _INSTALLED, "policy": "preflight-and-rollback"}
