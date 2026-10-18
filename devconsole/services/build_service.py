# devconsole/services/build_service.py
import datetime
import json
import os
import re
import subprocess
import threading
import time
import socket
import getpass
from pathlib import Path

from devconsole.config import (
    BASE_DIR,
    CONFIG_REPO_DIR,
    ENVIRONMENTS,
    SERVICES_BACKEND,
    SERVICES_FRONTEND,
    default_k8s_dir,
    get_service_repo_dir,
    image_ref,
)
from devconsole.services.git_service import get_git_info
from devconsole.services.k8s_service import (
    update_yaml_version,
    k8s_deploy_service,
    k8s_rollout_restart,
)

def inspect_image_labels(image_name: str, tag: str = "latest") -> dict:
    full_ref = image_ref(image_name, tag)
    # 1. Inspección local de Podman
    try:
        res = subprocess.run(
            ["podman", "image", "inspect", full_ref, "--format", "{{json .}}"],
            capture_output=True, text=True, timeout=2.5
        )
        if res.returncode == 0:
            data = json.loads(res.stdout)
            cfg = data.get("Config", {}) or {}
            labels = cfg.get("Labels") or data.get("Labels") or {}
            # `created` no se calculaba en esta rama: el NameError lo tragaba el
            # `except` de abajo, así que la imagen local NUNCA se reportaba y se
            # pagaba siempre el intento remoto al registry (hasta 3,5 s).
            created = (labels.get("org.opencontainers.image.created")
                       or data.get("Created") or "No Disponible")
            builder = (labels.get("build.builder") or labels.get("ci.triggered_by")
                       or labels.get("org.opencontainers.image.authors") or labels.get("build.author") or data.get("Author") or "No Disponible")
            commit_author = labels.get("git.commit.author") or "No Disponible"
            return {
                "success": True,
                "source": "podman-local",
                "image": full_ref,
                "created": created,
                "author": builder,
                "builder": builder,
                "commit_author": commit_author,
                "host": labels.get("build.host", "N/A"),
                "runner": labels.get("ci.runner.description", "N/A"),
                "labels": labels
            }
    except Exception as exc:
        # No silenciar: un fallo aquí sólo se notaba porque el resultado salía
        # por la rama remota, más lenta.
        print(f"[!] Inspección local de imagen omitida ({image_name}:{tag}): {exc}")
    
    # 2. Inspección remota vía Skopeo en Registry GitLab
    try:
        res = subprocess.run(
            ["skopeo", "inspect", f"docker://{full_ref}"],
            capture_output=True, text=True, timeout=3.5
        )
        if res.returncode == 0:
            data = json.loads(res.stdout)
            labels = data.get("Labels") or {}
            created = labels.get("org.opencontainers.image.created") or data.get("Created") or "No Disponible"
            builder = (labels.get("build.builder") or labels.get("ci.triggered_by")
                       or labels.get("org.opencontainers.image.authors") or labels.get("build.author") or data.get("Author") or "No Disponible")
            commit_author = labels.get("git.commit.author") or "No Disponible"
            return {
                "success": True,
                "source": "registry-skopeo",
                "image": full_ref,
                "created": created,
                "author": builder,
                "builder": builder,
                "commit_author": commit_author,
                "host": labels.get("build.host", "N/A"),
                "runner": labels.get("ci.runner.description", "N/A"),
                "labels": labels
            }
    except Exception as exc:
        print(f"[!] Inspección remota (registry) omitida ({image_name}:{tag}): {exc}")

    return {
        "success": False,
        "source": "none",
        "image": full_ref,
        "created": "No Disponible",
        "author": "No Disponible",
        "host": "N/A",
        "runner": "N/A",
        "labels": {}
    }

# ------------------------------------------------------------------------------
# CI/CD: Runner de Construcción de Imágenes (Podman / Docker) y Despliegue
# ------------------------------------------------------------------------------
BUILD_TASKS = {}
BUILD_LOCK = threading.Lock()

#: Maximum number of *finished* build tasks retained in memory (BR-12).
#:
#: Measured real usage before choosing this value: 6 tasks accumulated over
#: 7.4 hours of uptime, the busiest single task reaching the 2 500-line log cap.
#: 50 keeps roughly six times the observed peak-to-date, i.e. several days of
#: history for a developer workstation, while bounding both the memory held by
#: ``BUILD_TASKS`` and the size of the ``/api/deployments/build_status`` payload
#: (which returns every retained task).
MAX_BUILD_TASK_HISTORY = 50

#: Task states that may be pruned.  A task still running is never a candidate.
_FINISHED_TASK_STATES = frozenset({"completed", "failed"})


def prune_build_tasks(tasks: dict | None = None,
                      max_history: int = MAX_BUILD_TASK_HISTORY) -> list[str]:
    """Drop the oldest *finished* tasks beyond ``max_history``.

    Returns the ids removed.  Guarantees:

    * running tasks are never pruned;
    * the most recent history is always preserved, whatever the interleaving of
      start and finish times;
    * per-task log caps are untouched (that is a separate, already-correct
      bound).

    Callers must hold ``BUILD_LOCK``; this function does not acquire it so it
    stays safe to call from inside an existing critical section.
    """
    registry = BUILD_TASKS if tasks is None else tasks
    if max_history < 0:
        return []

    finished = [
        (tid, task) for tid, task in registry.items()
        if isinstance(task, dict) and task.get("status") in _FINISHED_TASK_STATES
    ]
    if len(finished) <= max_history:
        return []

    # Oldest first; tasks without a timestamp sort as oldest so a malformed
    # record can never pin the registry open.
    finished.sort(key=lambda item: (item[1].get("created_at") or 0.0, item[0]))

    removed: list[str] = []
    for tid, _task in finished[:len(finished) - max_history]:
        registry.pop(tid, None)
        removed.append(tid)
    return removed


def running_build_task_count(tasks: dict | None = None) -> int:
    """Number of tasks still running (never pruned)."""
    registry = BUILD_TASKS if tasks is None else tasks
    return sum(1 for t in registry.values()
               if isinstance(t, dict) and t.get("status") not in _FINISHED_TASK_STATES)

def run_build_task(task_id: str, payload: dict):
    with BUILD_LOCK:
        task = BUILD_TASKS.get(task_id)
    if not task:
        return

    def log(msg: str):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {msg}"
        with BUILD_LOCK:
            task["logs"].append(formatted)
            if len(task["logs"]) > 2500:
                task["logs"] = task["logs"][-2500:]
            cur_svc = task.get("current_service")
            if cur_svc:
                if "svc_logs" not in task:
                    task["svc_logs"] = {}
                if cur_svc not in task["svc_logs"]:
                    task["svc_logs"][cur_svc] = []
                task["svc_logs"][cur_svc].append(formatted)
                if len(task["svc_logs"][cur_svc]) > 2500:
                    task["svc_logs"][cur_svc] = task["svc_logs"][cur_svc][-2500:]

    services = payload.get("services", [])
    branch_option = payload.get("branch", "current")
    custom_branch = payload.get("custom_branch", "").strip()
    target_branch = custom_branch if branch_option == "custom" and custom_branch else branch_option
    version_override = payload.get("version_tag", "").strip()
    do_push = payload.get("push", True)
    update_yaml = payload.get("update_yaml", False)
    do_deploy = payload.get("deploy", False)
    do_rollout = payload.get("rollout", False)
    target_envs = payload.get("target_envs", [])
    if not target_envs:
        target_envs = [payload.get("target_env", "develop")]
    target_env = target_envs[0]
    no_cache = payload.get("no_cache", False)

    env_cfg = ENVIRONMENTS.get(target_env, {})
    namespace = env_cfg.get("namespace", "develop")
    env_labels = [f"{e.upper()} (ns: {ENVIRONMENTS.get(e, {}).get('namespace', e)})" for e in target_envs]

    log(f"🚀 Iniciando ciclo de CI/CD para {len(services)} microservicio(s)...")
    log(f"📋 Entorno(s) destino: {', '.join(env_labels)}")
    log(f"🌿 Estrategia de rama: '{target_branch}'")
    log(f"⚙️ Opciones: NoCache={no_cache}, Push={do_push}, Actualizar YAML={update_yaml}, Desplegar={do_deploy}, Rollout={do_rollout}")
    log("=" * 70)

    all_svcs = SERVICES_BACKEND + SERVICES_FRONTEND
    success_count = 0
    fail_count = 0

    for idx, svc_name in enumerate(services, 1):
        with BUILD_LOCK:
            task["current_service"] = svc_name
            task["current_step"] = f"[{idx}/{len(services)}] Procesando {svc_name}..."
            task["progress"] = int(((idx - 1) / len(services)) * 100)
            if "service_status" not in task:
                task["service_status"] = {}
            task["service_status"][svc_name] = "building"

        svc_meta = next((s for s in all_svcs if s["name"] == svc_name), None)
        repo_dir = get_service_repo_dir(svc_name)
        dockerfile_path = repo_dir / "Dockerfile"

        log(f"\n▶ [{idx}/{len(services)}] MICROSERVICIO: {svc_name}")

        if not repo_dir.exists():
            log(f"   ❌ Error: Directorio no encontrado ({repo_dir})")
            fail_count += 1
            with BUILD_LOCK:
                task["service_status"][svc_name] = "failed"
            continue

        if not dockerfile_path.exists():
            log(f"   ⚠️ Advertencia: No existe Dockerfile en {repo_dir}. Saltando construcción.")
            fail_count += 1
            with BUILD_LOCK:
                task["service_status"][svc_name] = "failed"
            continue

        # 1. Gestión de Rama Git
        curr_branch = get_git_info(repo_dir).get("branch", "N/A")
        log(f"   🌿 Rama actual del repo: '{curr_branch}'")

        if target_branch not in ["current", ""] and target_branch != curr_branch:
            status_out = subprocess.run(["git", "-C", str(repo_dir), "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
            if status_out:
                log(f"   ⚠️ Repositorio con cambios locales sin commitear. Por seguridad se construye en '{curr_branch}' para no perder cambios.")
            else:
                log(f"   🔄 Cambiando a rama '{target_branch}'...")
                co_res = subprocess.run(["git", "-C", str(repo_dir), "checkout", target_branch], capture_output=True, text=True)
                if co_res.returncode == 0:
                    log(f"   ✅ Checkout a '{target_branch}' exitoso.")
                    curr_branch = target_branch
                else:
                    err_msg = co_res.stderr.strip() or co_res.stdout.strip()
                    log(f"   ❌ Fallo al cambiar a rama '{target_branch}': {err_msg}")
                    fail_count += 1
                    with BUILD_LOCK:
                        task["service_status"][svc_name] = "failed"
                    continue

        # 2. Determinar Nombre de Imagen y Versión
        img_name = svc_name
        version_tag = version_override
        k8s_dir_rel = env_cfg.get("k8s_dir", default_k8s_dir(target_env))
        yaml_path = BASE_DIR / k8s_dir_rel / svc_meta.get("k8s_file", "") if svc_meta and svc_meta.get("k8s_file") else None

        if yaml_path and yaml_path.exists():
            try:
                content = yaml_path.read_text(encoding="utf-8")
                # Acepta cualquier registry, o ninguno (mismo criterio que
                # k8s_service.get_deployment_versions).
                refs = re.findall(
                    r'image:\s*([^\s#"\']+):([A-Za-z0-9_.\-]+)(?=\s*(?:#|$))',
                    content,
                    re.MULTILINE,
                )
                imgs = [
                    (ref.rsplit("/", 1)[-1], tag)
                    for ref, tag in refs
                    if "nginx" not in ref and "@sha256:" not in ref
                ]
                if imgs:
                    img_name = imgs[0][0]
                    if not version_tag:
                        version_tag = imgs[0][1]
            except Exception:
                pass

        if not version_tag:
            ver_file = repo_dir / "version.txt"
            if ver_file.exists():
                version_tag = ver_file.read_text().strip().lstrip("v")
            else:
                version_tag = "latest"

        full_image = image_ref(img_name, version_tag)
        log(f"   🏷️ Tag de imagen: {full_image}")

        # 3. Podman Build (Con metadatos institucionales del Senior / GitLab CI)
        author_name = payload.get("author", "").strip()
        if not author_name:
            author_name = os.environ.get("GITLAB_USER_NAME") or os.environ.get("USER") or getpass.getuser()

        # Resolver nombre y correo institucional del usuario que construye la imagen
        git_user_name = ""
        git_user_email = ""
        try:
            git_user_name = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, timeout=1).stdout.strip()
            git_user_email = subprocess.run(["git", "config", "user.email"], capture_output=True, text=True, timeout=1).stdout.strip()
        except Exception:
            pass

        builder_display = f"{git_user_name} <{git_user_email}>" if git_user_name and git_user_email else (git_user_name or author_name)
        author_label = builder_display if author_name in ["dgomezh", "proteo", getpass.getuser(), ""] else author_name

        try:
            commit_author = subprocess.run(
                ["git", "-C", str(repo_dir), "log", "-1", "--format=%an <%ae>"],
                capture_output=True, text=True, timeout=2
            ).stdout.strip() or "No Disponible"
        except Exception:
            commit_author = "No Disponible"

        build_created_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        build_host = socket.getfqdn() or socket.gethostname() or "localhost"

        build_cmd = ["podman", "build"]
        if no_cache:
            build_cmd.append("--no-cache")

        target_env_upper = (target_envs[0] if target_envs else target_env or "develop").upper()
        build_cmd.extend([
            "--env", f"DJANGO_ENV={target_env_upper}",
            "--env", f"SISPER_ENVIRONMENT={target_env_upper}",
            "--env", f"ENVIRONMENT={target_env_upper}",
            "--label", f"org.opencontainers.image.authors={author_label}",
            "--label", f"org.opencontainers.image.created={build_created_iso}",
            "--label", f"git.commit.author={commit_author}",
            "--label", f"ci.triggered_by={author_name}",
            "--label", f"build.builder={builder_display}",
            "--label", "ci.runner.description=DevConsole Web UI",
            "--label", "ci.runner.id=local-devconsole",
            "--label", f"build.host={build_host}",
            "-t", full_image,
            "-f", "Dockerfile", "."
        ])
        log(f"   🔨 Ejecutando podman build con metadatos institucionales:")
        log(f"      • Construida por (Builder): {builder_display} (login: {author_name})")
        log(f"      • Git Commit Author (repo local): {commit_author}")
        log(f"      • Fecha Creación: {build_created_iso}")
        log(f"      • Host: {build_host}")
        try:
            proc = subprocess.Popen(
                build_cmd, cwd=str(repo_dir),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1
            )
            for line in proc.stdout:
                line_str = line.strip()
                if line_str:
                    log(f"      [build] {line_str}")
            proc.wait()
            if proc.returncode != 0:
                log(f"   ❌ podman build falló con código {proc.returncode}")
                fail_count += 1
                with BUILD_LOCK:
                    task["service_status"][svc_name] = "failed"
                continue
            log(f"   ✅ podman build completado con éxito.")
        except Exception as e:
            log(f"   ❌ Error al ejecutar podman build: {e}")
            fail_count += 1
            with BUILD_LOCK:
                task["service_status"][svc_name] = "failed"
            continue

        # 4. Podman Push
        if do_push:
            log(f"   📤 Ejecutando: podman push {full_image}...")
            push_cmd = ["podman", "push", full_image]
            try:
                proc = subprocess.Popen(
                    push_cmd, cwd=str(repo_dir),
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1
                )
                for line in proc.stdout:
                    line_str = line.strip()
                    if line_str:
                        log(f"      [push] {line_str}")
                proc.wait()
                if proc.returncode != 0:
                    log(f"   ❌ podman push falló con código {proc.returncode}")
                    fail_count += 1
                    with BUILD_LOCK:
                        task["service_status"][svc_name] = "failed"
                    continue
                log(f"   ✅ podman push completado con éxito.")
            except Exception as e:
                log(f"   ❌ Error al ejecutar podman push: {e}")
                fail_count += 1
                with BUILD_LOCK:
                    task["service_status"][svc_name] = "failed"
                continue

        # 5. Actualizar YAML si se indicó
        if update_yaml and version_tag:
            for t_env in target_envs:
                ok_yaml, msg_yaml = update_yaml_version(svc_name, version_tag, t_env)
                if ok_yaml:
                    log(f"   📝 [{t_env.upper()}] Manifiesto YAML actualizado a {version_tag}.")
                else:
                    log(f"   ℹ️ [{t_env.upper()}] Manifiesto YAML: {msg_yaml}")

        # 6. Desplegar en Kubernetes si se solicitó
        if do_deploy:
            deploy_failed = False
            for t_env in target_envs:
                t_cfg = ENVIRONMENTS.get(t_env, {})
                t_ns = t_cfg.get("namespace", t_env)
                log(f"   🚀 [{t_env.upper()}] Desplegando en Kubernetes (Namespace '{t_ns}')...")
                ok_dep, msg_dep = k8s_deploy_service(svc_name, t_env)
                if ok_dep:
                    log(f"   ✅ [{t_env.upper()}] Manifiesto aplicado con kubectl apply: {msg_dep}")
                else:
                    log(f"   ❌ [{t_env.upper()}] Error en kubectl apply: {msg_dep}")
                    deploy_failed = True
            if deploy_failed:
                fail_count += 1
                with BUILD_LOCK:
                    task["service_status"][svc_name] = "failed"
                continue

        # 7. Rollout Restart si se solicitó explícitamente (k8s_deploy_service ya lo hace si hubo deploy)
        if do_rollout and not do_deploy and svc_meta and svc_meta.get("k8s_deploy"):
            dep_name = svc_meta["k8s_deploy"]
            for t_env in target_envs:
                t_cfg = ENVIRONMENTS.get(t_env, {})
                t_ns = t_cfg.get("namespace", t_env)
                log(f"   🔄 [{t_env.upper()}] Ejecutando rollout restart en deployment '{dep_name}'...")
                ok_ro, msg_ro = k8s_rollout_restart(dep_name, t_ns)
                if ok_ro:
                    log(f"   ✅ [{t_env.upper()}] Rollout restart iniciado exitosamente.")
                else:
                    log(f"   ⚠️ [{t_env.upper()}] Advertencia en rollout: {msg_ro}")

        success_count += 1
        log(f"   🎉 Microservicio {svc_name} completado con éxito.")
        with BUILD_LOCK:
            task["service_status"][svc_name] = "completed"

    log("\n" + "=" * 70)
    log(f"🏁 Proceso finalizado: {success_count} exitoso(s), {fail_count} con error(es).")
    with BUILD_LOCK:
        task["status"] = "completed" if fail_count == 0 else "failed"
        task["current_step"] = "Finalizado"
        task["progress"] = 100
        if "service_status" in task:
            for s, st in task["service_status"].items():
                if st == "building":
                    task["service_status"][s] = "completed" if fail_count == 0 else "failed"

# ------------------------------------------------------------------------------
# Infraestructura Local & Entorno
# ------------------------------------------------------------------------------

