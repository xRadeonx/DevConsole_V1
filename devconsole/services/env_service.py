# devconsole/services/env_service.py
import datetime
import os
import re
import time
import json
import subprocess
from pathlib import Path

from devconsole.config import (
    BASE_DIR,
    CONFIG_REPO_DIR,
    ENVIRONMENTS,
    SERVICES_BACKEND,
    SERVICES_FRONTEND,
    env_keys,
    get_service_repo_dir,
    is_port_open,
)
from devconsole.services.git_service import checkout_service_branch, get_git_info
from devconsole.services.terminal import get_terminal_backend
from devconsole.services.ttl_cache import ttl_cache

ENV_WATCHER_ENABLED = True
ENV_WATCHER_LAST_MTIME: dict[str, float] = {}
ENV_WATCHER_EVENTS: list[dict] = []


def _observe_restart_safety(service_name: str, port: int) -> None:
    """Shadow-mode observation of a restart, introduced by roadmap phase 0B.

    Computes what a *safe* process-identity resolver would target and compares
    it against what the legacy mechanism (``fuser -k -n tcp <port>``) is about
    to act on, recording the outcome for later analysis.

    Safety properties, all deliberate:

    * Runs **only** when ``SISPER_PROCESS_MODE=shadow``.  The default is
      ``legacy``, where this is a single environment lookup and nothing else.
    * **Never acts.**  It cannot terminate, signal or restart anything; the
      runtime package has no destructive capability at all.
    * **Never raises.**  Any failure is swallowed, so the legacy restart path
      cannot be perturbed by the observation.
    """
    try:
        from devconsole.services.runtime import Operation, shadow

        if not shadow.shadow_enabled():
            return
        shadow.observe_operation(
            service=service_name, operation=Operation.RESTART, port=port)
    except Exception:
        # Observation must never affect the legacy behaviour.
        pass


def get_service_env_map() -> dict:
    mapping = {}
    for s in SERVICES_BACKEND:
        p = BASE_DIR / "backend" / s["name"] / ".env"
        mapping[s["name"]] = {"port": s["port"], "type": "backend", "path": p}
    for s in SERVICES_FRONTEND:
        p = BASE_DIR / "frontend" / s["name"] / ".env"
        mapping[s["name"]] = {"port": s["port"], "type": "frontend", "path": p}
    return mapping

def read_service_env(svc_name: str) -> dict:
    svc_map = get_service_env_map()
    info = svc_map.get(svc_name)
    if not info:
        return {"success": False, "error": f"Servicio '{svc_name}' no registrado."}
    p: Path = info["path"]
    rel_p = str(p.relative_to(BASE_DIR))
    if not p.exists():
        return {
            "success": True,
            "service": svc_name,
            "port": info["port"],
            "type": info["type"],
            "path": rel_p,
            "content": "",
            "exists": False
        }
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        return {
            "success": True,
            "service": svc_name,
            "port": info["port"],
            "type": info["type"],
            "path": rel_p,
            "content": content,
            "exists": True
        }
    except Exception as e:
        return {"success": False, "error": f"Error leyendo {rel_p}: {str(e)}"}

def write_service_env(svc_name: str, content: str, restart: bool = True) -> tuple[bool, str]:
    svc_map = get_service_env_map()
    info = svc_map.get(svc_name)
    if not info:
        return False, f"Servicio '{svc_name}' no registrado."
    p: Path = info["path"]
    rel_p = str(p.relative_to(BASE_DIR))
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        try:
            ENV_WATCHER_LAST_MTIME[str(p)] = p.stat().st_mtime
        except Exception:
            pass

        msg = f"Archivo {rel_p} guardado con éxito."
        if restart:
            port = info["port"]
            # Phase 0B: observational only; inert unless SISPER_PROCESS_MODE=shadow.
            _observe_restart_safety(svc_name, port)
            try:
                # Phase 2: routed through the terminal backend.  Same launcher,
                # same argv, same check/timeout — only the seam changed.
                get_terminal_backend().run_action(
                    "restart-single", (svc_name, str(port)),
                    wait=True, check=False, timeout=5, base_dir=BASE_DIR)
                msg += f" Servicio reiniciado automáticamente (puerto {port})."
            except Exception as ex:
                msg += f" (Aviso reinicio: {ex})"
        return True, msg
    except Exception as e:
        return False, f"Error escribiendo {rel_p}: {str(e)}"

def env_file_watcher_loop():
    print("[ENV-WATCHER] 👁️ Monitor de archivos .env activo...")
    svc_map = get_service_env_map()
    for svc_name, info in svc_map.items():
        p: Path = info["path"]
        if p.exists():
            try:
                ENV_WATCHER_LAST_MTIME[str(p)] = p.stat().st_mtime
            except Exception:
                pass

    while ENV_WATCHER_ENABLED:
        try:
            time.sleep(1.2)
            svc_map = get_service_env_map()
            for svc_name, info in svc_map.items():
                p: Path = info["path"]
                if not p.exists():
                    continue
                try:
                    curr_mtime = p.stat().st_mtime
                except Exception:
                    continue

                prev_mtime = ENV_WATCHER_LAST_MTIME.get(str(p))
                if prev_mtime is not None and curr_mtime > prev_mtime:
                    time.sleep(0.4)
                    try:
                        curr_mtime = p.stat().st_mtime
                    except Exception:
                        pass
                    ENV_WATCHER_LAST_MTIME[str(p)] = curr_mtime
                    port = info["port"]
                    rel_p = str(p.relative_to(BASE_DIR))
                    print(f"[ENV-WATCHER] 🔄 Modificación detectada en {rel_p}. Recargando servicio '{svc_name}' (: {port})...")
                    event_info = {
                        "service": svc_name,
                        "port": port,
                        "file": rel_p,
                        "timestamp": time.time(),
                        "time_str": datetime.datetime.now().strftime("%H:%M:%S")
                    }
                    ENV_WATCHER_EVENTS.append(event_info)
                    if len(ENV_WATCHER_EVENTS) > 30:
                        ENV_WATCHER_EVENTS.pop(0)

                    # Phase 0B: observational only; inert unless SISPER_PROCESS_MODE=shadow.
                    _observe_restart_safety(svc_name, port)
                    try:
                        # Phase 2: same launcher/argv/check/timeout via the backend.
                        get_terminal_backend().run_action(
                            "restart-single", (svc_name, str(port)),
                            wait=True, check=False, timeout=5, base_dir=BASE_DIR)
                    except Exception as ex:
                        print(f"[ENV-WATCHER] ⚠️ Error reiniciando {svc_name}: {ex}")
        except Exception:
            time.sleep(2)


@ttl_cache(seconds=20)
def get_all_environments_status() -> dict:
    all_svcs = SERVICES_BACKEND + SERVICES_FRONTEND
    aligned_counts = {key: 0 for key in env_keys()}
    dirty_counts = {key: 0 for key in env_keys()}
    services_state = []

    for s in all_svcs:
        name = s["name"]
        repo = get_service_repo_dir(name)
        if not repo.exists() or not (repo / ".git").exists():
            continue
        try:
            curr_b = subprocess.check_output(
                ["git", "-C", str(repo), "branch", "--show-current"],
                stderr=subprocess.DEVNULL, timeout=1
            ).decode().strip() or "HEAD"
        except Exception:
            curr_b = "N/A"
        try:
            dirty = len(subprocess.check_output(
                ["git", "-C", str(repo), "status", "--porcelain"],
                stderr=subprocess.DEVNULL, timeout=1
            ).decode().strip().splitlines())
        except Exception:
            dirty = 0

        for env_key in env_keys():
            if curr_b == env_key or (env_key == "main" and curr_b == "master"):
                aligned_counts[env_key] += 1
                if dirty > 0:
                    dirty_counts[env_key] += 1

        git_info = get_git_info(repo)
        services_state.append({
            "name": name,
            "port": s["port"],
            "type": "backend" if name.startswith("ms_") else "frontend",
            "branch": curr_b,
            "dirty": dirty,
            "ahead": git_info.get("ahead", 0),
            "behind": git_info.get("behind", 0),
            "has_upstream": git_info.get("has_upstream", True),
            "aligned_develop": curr_b == "develop",
            "aligned_test": curr_b == "test",
            "aligned_main": curr_b in ("main", "master")
        })

    return {
        "total_services": len(services_state),
        "aligned_counts": aligned_counts,
        "dirty_counts": dirty_counts,
        "environments": ENVIRONMENTS,
        "services": services_state
    }

def switch_workspace_environment(target_env: str, force_pull: bool = False) -> dict:
    target_branch = ENVIRONMENTS.get(target_env, {}).get("branch", target_env)
    all_svcs = SERVICES_BACKEND + SERVICES_FRONTEND
    results = []

    for s in all_svcs:
        name = s["name"]
        repo = get_service_repo_dir(name)
        if not repo.exists() or not (repo / ".git").exists():
            results.append({"name": name, "status": "error", "message": "No encontrado"})
            continue
        try:
            dirty_lines = subprocess.check_output(
                ["git", "-C", str(repo), "status", "--porcelain"],
                stderr=subprocess.DEVNULL, timeout=1
            ).decode().strip().splitlines()
            if dirty_lines:
                results.append({"name": name, "status": "protected", "message": f"{len(dirty_lines)} cambios sin commitear (Protegido)"})
                continue
        except Exception:
            pass

        try:
            ck = subprocess.run(
                ["git", "-C", str(repo), "checkout", target_branch],
                capture_output=True, text=True, timeout=8
            )
            if ck.returncode != 0:
                results.append({"name": name, "status": "error", "message": ck.stderr.strip() or "Error checkout"})
                continue
            
            pull_msg = ""
            if force_pull:
                pl = subprocess.run(
                    ["git", "-C", str(repo), "pull", "--ff-only"],
                    capture_output=True, text=True, timeout=15
                )
                pull_msg = " + Pull OK" if pl.returncode == 0 else " (Pull error)"

            results.append({"name": name, "status": "success", "message": f"Alineado a '{target_branch}'{pull_msg}"})
        except Exception as e:
            results.append({"name": name, "status": "error", "message": str(e)})

    return {"target_env": target_env, "target_branch": target_branch, "results": results}


#: Un sondeo de 3 s en la interfaz ejecutaba `switch_env.sh status-json` cada
#: vez (13 bash en 20 s medidos).  La caché se invalida con `invalidate_all()`
#: tras las acciones de entorno, así que un cambio de modo se refleja igual.
@ttl_cache(seconds=5)
def get_env_info():
    # Sin caché a propósito: lee el modo de entorno vigente desde
    # switch_env.sh, y tras un cambio de entorno la interfaz debe reflejarlo
    # de inmediato.  Su coste (un script local) es marginal frente a la
    # perdida de frescura.
    try:
        script = str(BASE_DIR / "switch_env.sh")
        if os.path.exists(script):
            out = subprocess.check_output([script, "status-json"], timeout=3).decode("utf-8")
            return json.loads(out)
    except Exception as e:
        return {"env_mode": "DESCONOCIDO", "bitacora_status": str(e), "database_host": "", "keycloak_url": ""}
    return {"env_mode": "INTRANET", "bitacora_status": "ORIGINAL", "database_host": "", "keycloak_url": ""}

# ------------------------------------------------------------------------------
# Mapa Operativo & Conectividad Multi-Entorno (Zonas Navales & Keycloak SSO)
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# Mapa Operativo & Conexiones Activas Reales (Keycloak SSO -> Reparticiones/Zonas)
# ------------------------------------------------------------------------------

