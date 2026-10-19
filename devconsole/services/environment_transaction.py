"""Transactional multi-repository environment switching for DevConsole V1.1.

Unlike the legacy loop, this module performs a complete preflight before the
first checkout and restores every repository already changed if a later step
fails. Missing/non-git services are reported but do not block repositories that
actually participate in the workspace.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import devconsole.config as dcfg


@dataclass(frozen=True)
class RepoState:
    name: str
    path: Path
    branch: str
    commit: str
    target_branch: str
    target_local: bool
    target_remote: bool
    target_commit_before: str | None = None


def _git(repo: Path, *args: str, timeout: int = 10) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _output(result: subprocess.CompletedProcess) -> str:
    return (result.stderr or result.stdout or "").strip()


def _ref_commit(repo: Path, ref: str) -> str | None:
    result = _git(repo, "rev-parse", "--verify", ref, timeout=5)
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def _repo_state(name: str, repo: Path, target_branch: str, *, force_pull: bool) -> tuple[RepoState | None, dict]:
    if not repo.exists():
        return None, {"name": name, "status": "skipped", "message": "No encontrado"}
    probe = _git(repo, "rev-parse", "--is-inside-work-tree")
    if probe.returncode != 0:
        return None, {"name": name, "status": "skipped", "message": "No es repositorio Git"}

    git_dir = _git(repo, "rev-parse", "--git-dir")
    if git_dir.returncode != 0:
        return None, {"name": name, "status": "error", "message": "No se pudo resolver .git"}
    git_path = Path(git_dir.stdout.strip())
    if not git_path.is_absolute():
        git_path = (repo / git_path).resolve()
    lock = git_path / "index.lock"
    if lock.exists():
        return None, {
            "name": name,
            "status": "protected",
            "message": f"Git index.lock activo ({lock}); no se elimina automáticamente.",
        }

    dirty = _git(repo, "status", "--porcelain", timeout=4)
    if dirty.returncode != 0:
        return None, {"name": name, "status": "error", "message": _output(dirty) or "No se pudo leer git status"}
    dirty_lines = [line for line in dirty.stdout.splitlines() if line.strip()]
    if dirty_lines:
        return None, {
            "name": name,
            "status": "protected",
            "message": f"{len(dirty_lines)} cambios sin commitear (Protegido)",
        }

    branch = _git(repo, "branch", "--show-current").stdout.strip() or "HEAD"
    commit_result = _git(repo, "rev-parse", "HEAD")
    if commit_result.returncode != 0:
        return None, {"name": name, "status": "error", "message": "No se pudo resolver HEAD"}
    commit = commit_result.stdout.strip()

    local_ref = f"refs/heads/{target_branch}"
    remote_ref = f"refs/remotes/origin/{target_branch}"
    local = _git(repo, "show-ref", "--verify", "--quiet", local_ref).returncode == 0
    remote = _git(repo, "show-ref", "--verify", "--quiet", remote_ref).returncode == 0
    target_commit_before = _ref_commit(repo, local_ref) if local else None
    if not local and not remote and force_pull:
        fetch = _git(repo, "fetch", "origin", target_branch, timeout=30)
        if fetch.returncode == 0:
            remote = _git(repo, "show-ref", "--verify", "--quiet", remote_ref).returncode == 0
    if not local and not remote:
        return None, {
            "name": name,
            "status": "error",
            "message": f"Rama '{target_branch}' no existe localmente ni en origin.",
        }

    return RepoState(
        name,
        repo,
        branch,
        commit,
        target_branch,
        local,
        remote,
        target_commit_before,
    ), {
        "name": name,
        "status": "ready",
        "message": f"Listo para '{target_branch}'",
    }


def _checkout(state: RepoState) -> subprocess.CompletedProcess:
    if state.target_local:
        return _git(state.path, "checkout", state.target_branch, timeout=15)
    return _git(
        state.path,
        "checkout",
        "-b",
        state.target_branch,
        "--track",
        f"origin/{state.target_branch}",
        timeout=15,
    )


def _restore_target_ref(state: RepoState) -> tuple[bool, str]:
    """Restore/delete the target local branch created or moved by the transaction."""
    # If the target was the original checked-out branch, restoring HEAD below
    # already restores the same ref to ``state.commit``.
    if state.target_branch == state.branch:
        return True, "Target coincide con rama original"

    if state.target_local:
        if not state.target_commit_before:
            return False, "No se registró el commit original de la rama destino"
        result = _git(
            state.path,
            "branch",
            "-f",
            state.target_branch,
            state.target_commit_before,
            timeout=15,
        )
        return (result.returncode == 0, "Rama destino restaurada" if result.returncode == 0 else _output(result))

    # The transaction created this local tracking branch. Once the original
    # branch/commit is active again, remove the branch so rollback leaves no
    # local ref that did not exist before the operation.
    exists = _git(
        state.path,
        "show-ref",
        "--verify",
        "--quiet",
        f"refs/heads/{state.target_branch}",
        timeout=5,
    ).returncode == 0
    if not exists:
        return True, "Rama destino temporal ya no existe"
    result = _git(state.path, "branch", "-D", state.target_branch, timeout=15)
    return (result.returncode == 0, "Rama destino temporal eliminada" if result.returncode == 0 else _output(result))


def _rollback(state: RepoState) -> tuple[bool, str]:
    try:
        if state.branch != "HEAD":
            result = _git(state.path, "checkout", state.branch, timeout=15)
            if result.returncode != 0:
                return False, _output(result)
            if _git(state.path, "rev-parse", "HEAD").stdout.strip() != state.commit:
                reset = _git(state.path, "reset", "--hard", state.commit, timeout=15)
                if reset.returncode != 0:
                    return False, _output(reset)
        else:
            result = _git(state.path, "checkout", "--detach", state.commit, timeout=15)
            if result.returncode != 0:
                return False, _output(result)

        ref_ok, ref_message = _restore_target_ref(state)
        if not ref_ok:
            return False, ref_message
        return True, "Restaurado (HEAD y refs locales)"
    except Exception as exc:
        return False, str(exc)


def switch_workspace_environment_transactional(
    target_env: str,
    force_pull: bool = False,
    *,
    services: Iterable[dict] | None = None,
) -> dict:
    env_cfg = dcfg.ENVIRONMENTS.get(target_env, {})
    target_branch = str(env_cfg.get("branch") or target_env).strip()
    if not target_branch:
        return {
            "target_env": target_env,
            "target_branch": "",
            "transaction": "aborted",
            "results": [],
            "message": "Entorno/rama de destino inválido.",
        }

    configured = list(services) if services is not None else list(dcfg.SERVICES_BACKEND) + list(dcfg.SERVICES_FRONTEND)
    states: list[RepoState] = []
    preflight_results: list[dict] = []
    blocking = False

    for service in configured:
        name = str(service.get("name") or "").strip()
        if not name:
            continue
        repo = Path(dcfg.get_service_repo_dir(name)).resolve()
        try:
            state, result = _repo_state(name, repo, target_branch, force_pull=force_pull)
        except (OSError, subprocess.SubprocessError) as exc:
            state = None
            result = {"name": name, "status": "error", "message": str(exc)}
        preflight_results.append(result)
        if state is not None:
            states.append(state)
        elif result["status"] in {"error", "protected"}:
            blocking = True

    if blocking:
        return {
            "target_env": target_env,
            "target_branch": target_branch,
            "transaction": "aborted",
            "preflight": preflight_results,
            "results": preflight_results,
            "message": "Preflight falló; ningún checkout ni rama local fue modificado.",
        }

    changed: list[RepoState] = []
    results: list[dict] = []
    try:
        for state in states:
            checkout = _checkout(state)
            if checkout.returncode != 0:
                raise RuntimeError(f"{state.name}: {_output(checkout) or 'checkout falló'}")
            changed.append(state)

            pull_msg = ""
            if force_pull:
                pull = _git(state.path, "pull", "--ff-only", timeout=30)
                if pull.returncode != 0:
                    raise RuntimeError(f"{state.name}: {_output(pull) or 'pull --ff-only falló'}")
                pull_msg = " + Pull OK"
            results.append({
                "name": state.name,
                "status": "success",
                "message": f"Alineado a '{target_branch}'{pull_msg}",
            })
    except Exception as exc:
        rollback = []
        for state in reversed(changed):
            ok, message = _rollback(state)
            rollback.append({"name": state.name, "success": ok, "message": message})
        return {
            "target_env": target_env,
            "target_branch": target_branch,
            "transaction": "rolled_back",
            "preflight": preflight_results,
            "results": results,
            "rollback": rollback,
            "rollback_ok": all(item["success"] for item in rollback),
            "message": str(exc),
        }

    return {
        "target_env": target_env,
        "target_branch": target_branch,
        "transaction": "committed",
        "preflight": preflight_results,
        "results": results + [r for r in preflight_results if r["status"] == "skipped"],
    }
