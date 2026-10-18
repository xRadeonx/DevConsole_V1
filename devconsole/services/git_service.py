# devconsole/services/git_service.py
import concurrent.futures
import os
import subprocess
import time
from pathlib import Path

from devconsole.services.ttl_cache import ttl_cache
from devconsole.config import (
    BASE_DIR,
    CONFIG_REPO_DIR,
    REGISTRY,
    SERVICES_BACKEND,
    SERVICES_FRONTEND,
    get_service_repo_dir,
    is_port_open,
)

@ttl_cache(seconds=15)
def get_git_info(directory: Path) -> dict:
    if not directory.exists() or not (directory / ".git").exists():
        return {
            "branch": "N/A", "dirty": 0, "ahead": 0, "behind": 0,
            "has_upstream": False, "unpushed_commits": [], "unpulled_commits": [], "dirty_files": []
        }
    try:
        branch = subprocess.check_output(
            ["git", "-C", str(directory), "branch", "--show-current"],
            stderr=subprocess.DEVNULL, timeout=1
        ).decode().strip() or "HEAD"
    except Exception:
        branch = "N/A"
    try:
        status_lines = subprocess.check_output(
            ["git", "-C", str(directory), "status", "--porcelain"],
            stderr=subprocess.DEVNULL, timeout=1
        ).decode().strip().splitlines()
        dirty = len(status_lines)
        dirty_files = [l.strip() for l in status_lines[:10]]
    except Exception:
        dirty = 0
        dirty_files = []

    has_upstream = True
    try:
        subprocess.check_output(
            ["git", "-C", str(directory), "rev-parse", "--abbrev-ref", "@{u}"],
            stderr=subprocess.DEVNULL, timeout=1
        )
    except Exception:
        has_upstream = False

    upstream_ref = "@{u}" if has_upstream else f"origin/{branch}"

    try:
        ahead = int(subprocess.check_output(
            ["git", "-C", str(directory), "rev-list", "--count", f"{upstream_ref}..HEAD"],
            stderr=subprocess.DEVNULL, timeout=1
        ).decode().strip())
    except Exception:
        ahead = 0
    try:
        behind = int(subprocess.check_output(
            ["git", "-C", str(directory), "rev-list", "--count", f"HEAD..{upstream_ref}"],
            stderr=subprocess.DEVNULL, timeout=1
        ).decode().strip())
    except Exception:
        behind = 0
    try:
        if ahead > 0:
            unpushed_commits = subprocess.check_output(
                ["git", "-C", str(directory), "log", f"{upstream_ref}..HEAD", "--oneline", "-n", "8"],
                stderr=subprocess.DEVNULL, timeout=1
            ).decode().strip().splitlines()
        else:
            unpushed_commits = []
    except Exception:
        unpushed_commits = []
    try:
        if behind > 0:
            unpulled_commits = subprocess.check_output(
                ["git", "-C", str(directory), "log", f"HEAD..{upstream_ref}", "--oneline", "-n", "8"],
                stderr=subprocess.DEVNULL, timeout=1
            ).decode().strip().splitlines()
        else:
            unpulled_commits = []
    except Exception:
        unpulled_commits = []

    return {
        "branch": branch,
        "dirty": dirty,
        "ahead": ahead,
        "behind": behind,
        "has_upstream": has_upstream,
        "unpushed_commits": unpushed_commits,
        "unpulled_commits": unpulled_commits,
        "dirty_files": dirty_files,
    }

def get_service_branches(service_name: str):
    repo = get_service_repo_dir(service_name)
    if not repo.exists() or not (repo / ".git").exists():
        return {"current": "sin git", "branches": []}
    try:
        current = subprocess.check_output(
            ["git", "-C", str(repo), "branch", "--show-current"],
            stderr=subprocess.DEVNULL, timeout=1
        ).decode().strip() or "HEAD"
    except Exception:
        current = "desconocido"
    try:
        raw = subprocess.check_output(
            ["git", "-C", str(repo), "branch", "-a", "--format=%(refname:short)"],
            stderr=subprocess.DEVNULL, timeout=2
        ).decode().splitlines()
        branch_set = set()
        for b in raw:
            b = b.strip()
            if not b or "HEAD" in b or b == "origin":
                continue
            if b.startswith("origin/"):
                b = b[len("origin/"):]
            branch_set.add(b)
        branches = sorted(list(branch_set))
        if current in branches:
            branches.remove(current)
        branches.insert(0, current)
        return {"current": current, "branches": branches}
    except Exception:
        return {"current": current, "branches": [current]}

def checkout_service_branch(service_name: str, branch: str):
    repo = get_service_repo_dir(service_name)
    if not repo.exists() or not (repo / ".git").exists():
        return False, f"Repositorio no encontrado para {service_name}"
    
    # 1. Limpiar lock obsoleto si existe
    lock_file = repo / ".git" / "index.lock"
    if lock_file.exists():
        try:
            if time.time() - lock_file.stat().st_mtime > 5:
                lock_file.unlink(missing_ok=True)
        except Exception:
            pass

    # 2. Verificar archivos con modificaciones sin confirmar
    try:
        dirty_lines = subprocess.check_output(
            ["git", "-C", str(repo), "status", "--porcelain"],
            stderr=subprocess.DEVNULL, timeout=2
        ).decode().strip().splitlines()
        if dirty_lines:
            return False, f"Hay {len(dirty_lines)} archivo(s) modificado(s) sin confirmar en {service_name}. Haz commit o stash antes de cambiar de rama."
    except Exception:
        pass

    try:
        res = subprocess.run(
            ["git", "-C", str(repo), "checkout", branch],
            capture_output=True, text=True, timeout=8
        )
        if res.returncode == 0:
            return True, f"Rama cambiada a '{branch}' con éxito."
        
        # Si falló porque la rama no existe localmente pero sí en origin
        out = (res.stderr + " " + res.stdout)
        if "did not match any file(s) known to git" in out or "error: pathspec" in out:
            res2 = subprocess.run(
                ["git", "-C", str(repo), "checkout", "-b", branch, "--track", f"origin/{branch}"],
                capture_output=True, text=True, timeout=8
            )
            if res2.returncode == 0:
                return True, f"Rama '{branch}' creada y vinculada desde origin con éxito."
            return False, f"Git error: {res2.stderr.strip() or res2.stdout.strip()}"

        return False, f"Git error: {res.stderr.strip() or res.stdout.strip()}"
    except Exception as e:
        return False, str(e)

def _nombre_rama_valido(nombre: str) -> tuple[bool, str]:
    """Valida el nombre con la propia regla de git (``check-ref-format``)."""
    nombre = (nombre or "").strip()
    if not nombre:
        return False, "Indica el nombre de la rama."
    try:
        res = subprocess.run(["git", "check-ref-format", "--branch", nombre],
                             capture_output=True, text=True, timeout=5)
    except Exception as exc:
        return False, f"No se pudo validar el nombre: {exc}"
    if res.returncode != 0:
        return False, f"Nombre de rama inválido: '{nombre}'."
    return True, ""


def _repo_git(service_name: str):
    repo = get_service_repo_dir(service_name)
    if not repo.exists() or not (repo / ".git").exists():
        return None, f"Repositorio no encontrado para {service_name}"
    return repo, ""


def create_service_branch(service_name: str, branch: str, from_branch: str | None = None):
    """Crea una rama (desde la actual o desde ``from_branch``) y se cambia a ella."""
    ok, msg = _nombre_rama_valido(branch)
    if not ok:
        return False, msg
    repo, err = _repo_git(service_name)
    if repo is None:
        return False, err

    existencia = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
                                capture_output=True, text=True, timeout=5)
    if existencia.returncode == 0:
        return False, f"La rama '{branch}' ya existe en {service_name}."

    base = (from_branch or "").strip()
    argumentos = ["git", "-C", str(repo), "checkout", "-b", branch]
    if base:
        argumentos.append(base)
    try:
        res = subprocess.run(argumentos, capture_output=True, text=True, timeout=10)
    except Exception as exc:
        return False, str(exc)
    if res.returncode != 0:
        return False, f"Git error: {res.stderr.strip() or res.stdout.strip()}"
    origen = f" desde '{base}'" if base else " desde la rama actual"
    return True, f"Rama '{branch}' creada{origen} en {service_name}."


def rename_service_branch(service_name: str, old: str, new: str):
    """Renombra una rama local (``git branch -m``).  El remoto no se toca."""
    ok, msg = _nombre_rama_valido(new)
    if not ok:
        return False, msg
    old = (old or "").strip()
    if not old:
        return False, "Indica la rama a renombrar."
    if old == new:
        return False, "El nombre nuevo es igual al actual."
    repo, err = _repo_git(service_name)
    if repo is None:
        return False, err

    existe_vieja = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", f"refs/heads/{old}"],
                                  capture_output=True, text=True, timeout=5)
    if existe_vieja.returncode != 0:
        return False, f"La rama '{old}' no existe en {service_name}."
    existe_nueva = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", f"refs/heads/{new}"],
                                  capture_output=True, text=True, timeout=5)
    if existe_nueva.returncode == 0:
        return False, f"Ya existe una rama '{new}' en {service_name}."
    try:
        res = subprocess.run(["git", "-C", str(repo), "branch", "-m", old, new],
                             capture_output=True, text=True, timeout=10)
    except Exception as exc:
        return False, str(exc)
    if res.returncode != 0:
        return False, f"Git error: {res.stderr.strip() or res.stdout.strip()}"
    return True, f"Rama '{old}' renombrada a '{new}' en {service_name} (el remoto conserva el nombre anterior)."


def get_running_services_info() -> list:
    running = []
    for s in SERVICES_BACKEND + SERVICES_FRONTEND:
        if is_port_open(s["port"]):
            running.append({"name": s["name"], "port": s["port"]})
    return running


def get_config_git_status() -> dict:
    if not CONFIG_REPO_DIR.exists() or not (CONFIG_REPO_DIR / ".git").exists():
        return {"online": False, "error": "Repositorio backend/config no encontrado"}
    try:
        branch = subprocess.check_output(
            ["git", "-C", str(CONFIG_REPO_DIR), "branch", "--show-current"],
            stderr=subprocess.DEVNULL, timeout=2
        ).decode().strip() or "HEAD"
    except Exception:
        branch = "desconocida"

    try:
        status_lines = subprocess.check_output(
            ["git", "-C", str(CONFIG_REPO_DIR), "status", "--porcelain"],
            stderr=subprocess.DEVNULL, timeout=2
        ).decode().strip().splitlines()
    except Exception:
        status_lines = []

    try:
        ahead = int(subprocess.check_output(
            ["git", "-C", str(CONFIG_REPO_DIR), "rev-list", "--count", "@{u}..HEAD"],
            stderr=subprocess.DEVNULL, timeout=2
        ).decode().strip())
    except Exception:
        ahead = 0

    try:
        behind = int(subprocess.check_output(
            ["git", "-C", str(CONFIG_REPO_DIR), "rev-list", "--count", "HEAD..@{u}"],
            stderr=subprocess.DEVNULL, timeout=2
        ).decode().strip())
    except Exception:
        behind = 0

    parsed_files = []
    for l in status_lines:
        s_line = l.strip()
        if not s_line:
            continue
        p = s_line.split(maxsplit=1)
        parsed_files.append({"status": p[0] if p else "", "path": p[1] if len(p) > 1 else ""})

    return {
        "online": True,
        "repo_path": str(CONFIG_REPO_DIR),
        "branch": branch,
        "dirty": len(status_lines),
        "dirty_count": len(status_lines),
        "dirty_files": status_lines,
        "files": parsed_files,
        "ahead": ahead,
        "behind": behind
    }

def run_config_git_pull() -> tuple[bool, str]:
    if not CONFIG_REPO_DIR.exists():
        return False, "Repositorio backend/config no existe"
    try:
        res = subprocess.run(
            ["git", "-C", str(CONFIG_REPO_DIR), "pull", "origin", "main"],
            capture_output=True, text=True, timeout=20
        )
        if res.returncode == 0:
            return True, res.stdout.strip() or "Pull completado correctamente."
        return False, res.stderr.strip() or res.stdout.strip()
    except Exception as e:
        return False, str(e)

def run_config_git_push(commit_msg: str = "Actualización de manifiestos K8s desde Dashboard") -> tuple[bool, str]:
    if not CONFIG_REPO_DIR.exists():
        return False, "Repositorio backend/config no existe"
    try:
        subprocess.run(["git", "-C", str(CONFIG_REPO_DIR), "add", "-A"], check=True, timeout=5)
        status = subprocess.check_output(["git", "-C", str(CONFIG_REPO_DIR), "status", "--porcelain"]).decode().strip()
        if status:
            c = subprocess.run(
                ["git", "-C", str(CONFIG_REPO_DIR), "commit", "-m", commit_msg],
                capture_output=True, text=True, timeout=10
            )
            if c.returncode != 0:
                return False, f"Error al hacer commit: {c.stderr.strip()}"
        p = subprocess.run(
            ["git", "-C", str(CONFIG_REPO_DIR), "push", "origin", "main"],
            capture_output=True, text=True, timeout=25
        )
        if p.returncode == 0:
            return True, "Push a origin/main realizado con éxito."
        return False, p.stderr.strip() or p.stdout.strip()
    except Exception as e:
        return False, str(e)

def run_git_action(service_name: str, action: str, username: str = None, password: str = None, save_credentials: bool = False, pull_strategy: str = "default"):
    repo = get_service_repo_dir(service_name)
    if not repo.exists() or not (repo / ".git").exists():
        return False, f"Repositorio no encontrado para {service_name}"

    if action == "pull":
        try:
            curr_b = subprocess.check_output(
                ["git", "-C", str(repo), "branch", "--show-current"],
                stderr=subprocess.DEVNULL, timeout=1
            ).decode().strip()
            up_test = subprocess.run(
                ["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "@{u}"],
                capture_output=True, timeout=1
            )
            if up_test.returncode != 0 and curr_b:
                subprocess.run(
                    ["git", "-C", str(repo), "branch", f"--set-upstream-to=origin/{curr_b}", curr_b],
                    capture_output=True, timeout=2
                )
        except Exception:
            pass

    cmd = ["git", "-C", str(repo)]
    if action == "pull":
        cmd.append("pull")
        if pull_strategy == "rebase":
            cmd.append("--rebase")
        elif pull_strategy == "ff-only":
            cmd.append("--ff-only")
        elif pull_strategy == "no-ff":
            cmd.append("--no-ff")
        elif pull_strategy == "merge":
            cmd.append("--no-rebase")
        # default = sin banderas (git pull puro)
    elif action in ("push", "fetch"):
        cmd.append(action)
    elif action == "stash":
        cmd.extend(["stash", "push", "-m", "Guardado desde Dashboard"])
    else:
        return False, f"Acción Git desconocida: {action}"

    env = os.environ.copy()
    env["GIT_MERGE_AUTOEDIT"] = "no"
    askpass_script = str(BASE_DIR / ".git_askpass.sh")
    if username and password:
        env["GIT_USERNAME"] = username
        env["GIT_PASSWORD"] = password
        env["GIT_ASKPASS"] = askpass_script
        env["GIT_TERMINAL_PROMPT"] = "0"

        if save_credentials:
            try:
                subprocess.run(["git", "config", "--global", "credential.helper", "store"], check=False)
                # El host sale del registry configurado (sin puerto): antes estaba
                # escrito en el código y no servía para otra instalación.
                git_host = REGISTRY.split(":")[0] if REGISTRY else ""
                if git_host:
                    cred_payload = f"protocol=http\nhost={git_host}\nusername={username}\npassword={password}\n\n"
                    subprocess.run(["git", "credential", "approve"], input=cred_payload, text=True, check=False)
            except Exception:
                pass
    else:
        env["GIT_TERMINAL_PROMPT"] = "0"

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)
        msg = res.stdout.strip() or res.stderr.strip() or "Comando ejecutado."
        return res.returncode == 0, msg
    except subprocess.TimeoutExpired:
        return False, "Tiempo de espera agotado al conectar con GitLab."
    except Exception as e:
        return False, str(e)

def run_git_fetch_all() -> dict:
    targets = []
    for s in SERVICES_BACKEND:
        d = BASE_DIR / "backend" / s["name"]
        if d.exists() and (d / ".git").exists():
            targets.append((s["name"], d))
    for s in SERVICES_FRONTEND:
        d = BASE_DIR / "frontend" / s["name"]
        if d.exists() and (d / ".git").exists():
            targets.append((s["name"], d))

    def _fetch_repo(item):
        name, repo_dir = item
        try:
            res = subprocess.run(
                ["git", "-C", str(repo_dir), "fetch", "--prune"],
                capture_output=True, text=True, timeout=12
            )
            return name, (res.returncode == 0)
        except Exception:
            return name, False

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        for name, ok in executor.map(_fetch_repo, targets):
            results[name] = ok

    successful = sum(1 for v in results.values() if v)
    return {
        "success": True,
        "total": len(targets),
        "updated": successful,
        "results": results
    }

# ------------------------------------------------------------------------------
# Normalizador y Gestor de Sesiones Tilix
# ------------------------------------------------------------------------------

