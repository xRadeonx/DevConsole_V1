# devconsole/services/k8s_service.py
import json
import re
import subprocess
from pathlib import Path

from devconsole.config import (
    k8s_dir_for,
    BASE_DIR,
    AVAILABLE_SEASONAL_THEMES,
    ENVIRONMENTS,
    SERVICES_BACKEND,
    SERVICES_FRONTEND,
    get_service_repo_dir,
)
from devconsole.services.git_service import get_git_info
from devconsole.services.ttl_cache import ttl_cache

def get_k8s_sesion_deployment(namespace: str = "develop") -> str:
    try:
        out = subprocess.check_output(
            ["kubectl", "get", "deployment", "-n", namespace, "-o", "jsonpath={.items[*].metadata.name}"],
            stderr=subprocess.DEVNULL, timeout=4
        ).decode().strip()
        names = out.split()
        if "mf-sesion-deployment" in names:
            return "mf-sesion-deployment"
        if "mf-sesion" in names:
            return "mf-sesion"
        for n in names:
            if "mf" in n and "sesion" in n:
                return n
    except Exception:
        pass
    return "mf-sesion-deployment"

@ttl_cache(seconds=60)
def get_k8s_theme(namespace: str = "develop") -> dict:
    deploy_name = get_k8s_sesion_deployment(namespace)
    current_theme = "none"
    try:
        out = subprocess.check_output(
            ["kubectl", "set", "env", f"deployment/{deploy_name}", "-n", namespace, "--list"],
            stderr=subprocess.DEVNULL, timeout=5
        ).decode()
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("MF_THEME="):
                current_theme = line.split("=", 1)[1].strip()
                break
    except Exception:
        pass

    return {
        "success": True,
        "namespace": namespace,
        "deployment": deploy_name,
        "current_theme": current_theme,
        "available_themes": AVAILABLE_SEASONAL_THEMES
    }

def set_k8s_theme(namespace: str, theme: str) -> tuple[bool, str]:
    deploy_name = get_k8s_sesion_deployment(namespace)
    theme = theme.strip()
    if not theme:
        theme = "none"
    try:
        cmd = ["kubectl", "set", "env", f"deployment/{deploy_name}", "-n", namespace, f"MF_THEME={theme}"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode == 0:
            return True, f"Tema '{theme}' aplicado exitosamente en deployment/{deploy_name} ({namespace})."
        return False, f"Error kubectl: {res.stderr.strip() or res.stdout.strip()}"
    except Exception as e:
        return False, str(e)


def get_k8s_status(namespace: str = "develop") -> dict:
    try:
        res = subprocess.run(
            ["kubectl", "get", "pods", "-n", namespace, "-o", "json"],
            capture_output=True, text=True, timeout=3.5
        )
        if res.returncode != 0:
            stderr = (res.stderr or "").strip()
            return {
                "online": False,
                "namespace": namespace,
                "pods": [],
                "error": f"kubectl falló al listar los pods del namespace '{namespace}'.",
                "detail": stderr or f"kubectl get pods -n {namespace} -o json",
                "hint": "Revisa que el namespace exista y que el contexto apunte al cluster correcto.",
            }

        data = json.loads(res.stdout)
        pods = []
        for item in data.get("items", []):
            name = item["metadata"]["name"]
            phase = item["status"].get("phase", "Unknown")
            c_statuses = item["status"].get("containerStatuses", [])
            containers = [c.get("name") for c in c_statuses if c.get("name")]
            ready_count = sum(1 for c in c_statuses if c.get("ready", False))
            total_count = len(c_statuses)
            restarts = sum(c.get("restartCount", 0) for c in c_statuses)
            created = item["metadata"].get("creationTimestamp", "")
            pod_ip = item["status"].get("podIP", "-")
            pods.append({
                "name": name,
                "status": phase,
                "ready": f"{ready_count}/{total_count}",
                "restarts": restarts,
                "created": created,
                "ip": pod_ip,
                "containers": containers
            })
        return {"online": True, "namespace": namespace, "pods": pods}
    except subprocess.TimeoutExpired:
        return {
            "online": False,
            "namespace": namespace,
            "pods": [],
            "error": f"El cluster no respondió en 3,5 s (namespace '{namespace}').",
            "detail": f"kubectl get pods -n {namespace} -o json",
            "hint": "Comprueba el contexto activo y la conectividad con el API server.",
        }
    except FileNotFoundError:
        return {
            "online": False,
            "namespace": namespace,
            "pods": [],
            "error": "No se encontró el binario 'kubectl' en el PATH.",
            "detail": "kubectl version --client",
            "hint": "Instálalo o ajusta el PATH del servicio.",
        }
    except Exception as e:
        # El detalle técnico viaja aparte: la interfaz no debe mostrar la
        # representación cruda de una excepción de Python.
        return {
            "online": False,
            "namespace": namespace,
            "pods": [],
            "error": "No se pudo consultar el cluster.",
            "detail": str(e),
        }

def k8s_rollout_restart(deploy_name: str, namespace: str = "develop") -> tuple:
    # Si es nombre de pod con hashes de K8s (ej: mf-perfiles-riesgo-deployment-55ff47f97b-wnpz7), limpiamos los hashes
    clean_target = re.sub(r'-[0-9a-f]{7,10}-[a-z0-9]{5}$', '', deploy_name)
    target = clean_target if clean_target.endswith("-deployment") else f"{clean_target}-deployment"
    try:
        res = subprocess.run(
            ["kubectl", "rollout", "restart", f"deployment/{target}", "-n", namespace],
            capture_output=True, text=True, timeout=15
        )
        return (res.returncode == 0, res.stdout.strip() or res.stderr.strip())
    except Exception as e:
        return False, str(e)

def k8s_rollout_status(deploy_name: str, namespace: str = "develop") -> dict:
    clean_target = re.sub(r'-[0-9a-f]{7,10}-[a-z0-9]{5}$', '', deploy_name)
    target = clean_target if clean_target.endswith("-deployment") else f"{clean_target}-deployment"
    try:
        res = subprocess.run(
            ["kubectl", "rollout", "status", f"deployment/{target}", "-n", namespace, "--timeout=3s"],
            capture_output=True, text=True, timeout=4
        )
        msg = res.stdout.strip() or res.stderr.strip()
        is_complete = ("successfully rolled out" in msg.lower()) or ("completado" in msg.lower())
        return {
            "success": True,
            "target": target,
            "complete": is_complete,
            "message": msg,
            "returncode": res.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "success": True,
            "target": target,
            "complete": False,
            "message": "Rollout en progreso... inicializando nuevos pods (esperando que alcancen Ready 1/1)",
            "returncode": 0
        }
    except Exception as e:
        return {"success": False, "target": target, "complete": False, "message": str(e), "returncode": -1}

def k8s_rollout_all(namespace: str = "develop") -> tuple:
    try:
        res = subprocess.run(
            ["kubectl", "rollout", "restart", "deployment", "-n", namespace],
            capture_output=True, text=True, timeout=25
        )
        return (res.returncode == 0, res.stdout.strip() or res.stderr.strip())
    except Exception as e:
        return False, str(e)

def k8s_get_logs(target_name: str, namespace: str = "develop", tail: int = 100, container: str = None) -> str:
    cmd = ["kubectl", "logs", target_name, "-n", namespace, f"--tail={tail}"]
    if container:
        cmd.extend(["-c", container])
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        return res.stdout if res.returncode == 0 else res.stderr
    except Exception as e:
        return f"Error: {e}"

def get_pod_containers(pod_name: str, namespace: str = "develop") -> list:
    try:
        out = subprocess.check_output(
            ["kubectl", "get", "pod", pod_name, "-n", namespace, "-o", "jsonpath={.spec.containers[*].name}"],
            stderr=subprocess.DEVNULL, timeout=2
        ).decode().strip()
        return out.split() if out else []
    except Exception:
        return []

# ------------------------------------------------------------------------------
# CI/CD: Matriz de Versiones (YAML local vs K8s Deployed) & Despliegue
# ------------------------------------------------------------------------------
@ttl_cache(seconds=20)
def get_deployment_versions(env_key: str = "develop") -> dict:
    env_cfg = ENVIRONMENTS.get(env_key, {})
    namespace = env_cfg.get("namespace", "develop")
    target_branch = env_cfg.get("branch", env_key)
    k8s_dir_rel = k8s_dir_for(env_key)
    k8s_dir = BASE_DIR / k8s_dir_rel

    # 1. Versiones en K8s activo
    deployed_map = {}
    try:
        k8s_res = subprocess.run(
            ["kubectl", "get", "deployments", "-n", namespace, "-o", "json"],
            capture_output=True, text=True, timeout=3.5
        )
        if k8s_res.returncode == 0:
            for item in json.loads(k8s_res.stdout).get("items", []):
                dep_name = item["metadata"]["name"]
                containers = item["spec"]["template"]["spec"]["containers"]
                imgs = [c["image"] for c in containers if "nginx" not in c["image"]]
                if imgs:
                    tag = imgs[0].split(":")[-1] if ":" in imgs[0] else "latest"
                    deployed_map[dep_name] = tag
    except Exception:
        pass

    # 2. Versiones en YAML local
    items = []
    all_svcs = SERVICES_BACKEND + SERVICES_FRONTEND
    for s in all_svcs:
        name = s["name"]
        k8s_file = s.get("k8s_file", "")
        k8s_deploy = s.get("k8s_deploy", "")
        dep_full = k8s_deploy if k8s_deploy.endswith("-deployment") else f"{k8s_deploy}-deployment"
        
        repo_dir = get_service_repo_dir(name)
        has_dockerfile = (repo_dir / "Dockerfile").exists() if repo_dir.exists() else False
        git_info = get_git_info(repo_dir) if repo_dir.exists() else {"branch": "N/A", "dirty": 0}

        yaml_path = k8s_dir / k8s_file if k8s_file else None
        yaml_ver = "-"
        img_name = name
        if yaml_path and yaml_path.exists():
            try:
                content = yaml_path.read_text(encoding="utf-8")
                # Acepta cualquier registry, o ninguno.  Antes el patrón exigía
                # un host de registry concreto, así que un manifiesto local o de
                # otro registry no se reconocía.
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
                    yaml_ver = imgs[0][1]
            except Exception:
                pass

        k8s_ver = deployed_map.get(dep_full, "-")
        is_synced = (yaml_ver != "-" and k8s_ver != "-" and yaml_ver == k8s_ver)

        items.append({
            "name": name,
            "port": s["port"],
            "type": "backend" if name.startswith("ms_") else "frontend",
            "k8s_file": k8s_file,
            "k8s_deploy": dep_full,
            "image_name": img_name,
            "yaml_version": yaml_ver,
            "k8s_version": k8s_ver,
            "is_synced": is_synced,
            "yaml_exists": bool(yaml_path and yaml_path.exists()),
            "has_dockerfile": has_dockerfile,
            "target_branch": target_branch,
            "current_branch": target_branch,
            "local_branch": git_info.get("branch", "N/A"),
            "git_dirty": git_info.get("dirty", 0) > 0
        })

    # Manifiestos del entorno que el catálogo NO referencia.  La matriz sólo
    # listaba microservicios, así que ingress, onlyoffice, keydb, volumes… —y los
    # YAML de servicios con otro nombre— no aparecían en ninguna parte.
    referenciados = {s.get("k8s_file") for s in all_svcs if s.get("k8s_file")}
    extra_manifests: list[dict] = []
    if k8s_dir.is_dir():
        for f in sorted(k8s_dir.rglob("*")):
            if not f.is_file() or f.suffix.lower() not in (".yaml", ".yml"):
                continue
            rel = f.relative_to(k8s_dir).as_posix()
            if rel in referenciados:
                continue
            try:
                size = f.stat().st_size
            except OSError:
                size = 0
            resumen = _resumen_manifiesto(f)
            dep_name = resumen.get("name", "")
            # ¿Es un YAML de servicio que el catálogo referencia con otro nombre?
            sugerido = _servicio_para_manifiesto(rel, all_svcs)
            repo_dir = get_service_repo_dir(sugerido) if sugerido else None
            dockerfile = (repo_dir / "Dockerfile") if repo_dir else None
            construible = bool(dockerfile is not None and dockerfile.is_file())
            extra_manifests.append({
                "file": rel,
                "size": size,
                "categoria": _categoria_manifiesto(rel),
                "kind": resumen.get("kind", ""),
                "deploy": dep_name,
                # Servicio del catálogo al que corresponde (si lo hay) y por qué
                # se puede construir o no: hace falta un repo con Dockerfile.
                "servicio_sugerido": sugerido,
                "construible": construible,
                "motivo_build": ("repo con Dockerfile disponible" if construible
                                 else ("no hay repo/Dockerfile para ese servicio" if sugerido
                                       else "no es un servicio del catálogo")),
                "yaml_version": resumen.get("version", ""),
                # La versión en el clúster sale del listado de deployments que ya
                # se pidió para los servicios: sin llamadas extra a kubectl.
                "k8s_version": deployed_map.get(dep_name, "") if dep_name else "",
            })

    return {
        "env": env_key,
        "env_branch": target_branch,
        "namespace": namespace,
        "k8s_dir": str(k8s_dir_rel),
        "services": items,
        "extra_manifests": extra_manifests
    }

#: Tipos que representan una carga de trabajo desplegable.
_KINDS_TRABAJO = ("Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob")


def _resumen_manifiesto(path: Path) -> dict:
    """``kind``, ``metadata.name`` y versión de imagen de un manifiesto.

    Se leen sólo las primeras claves de cada documento con expresiones regulares
    (no se interpreta el YAML completo ni se sigue ningún ancla): es lo justo
    para rellenar la fila de la matriz.  Si el fichero tiene varios documentos se
    prefiere el de carga de trabajo (``Deployment``…), que es el desplegable.
    """
    try:
        texto = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    kind = name = imagen = ""
    for doc in texto.split("\n---"):
        m_kind = re.search(r"^\s*kind:\s*([A-Za-z]+)", doc, re.M)
        if not m_kind:
            continue
        k = m_kind.group(1)
        m_name = re.search(r"^\s*name:\s*([^\s#]+)", doc, re.M)
        n = (m_name.group(1).strip("\"'") if m_name else "")
        m_img = re.search(r"^\s*image:\s*([^\s#]+)", doc, re.M)
        img = (m_img.group(1).strip("\"'") if m_img else "")
        if k in _KINDS_TRABAJO:
            kind, name, imagen = k, n, img
            break
        if not kind:
            kind, name, imagen = k, n, img
    version = ""
    if imagen:
        cola = imagen.rsplit("/", 1)[-1]
        if ":" in cola:
            version = cola.rsplit(":", 1)[-1]
    return {"kind": kind, "name": name, "image": imagen, "version": version}


def _clave_servicio(nombre: str) -> str:
    """Nombre normalizado para emparejar un YAML suelto con un servicio.

    El caso real de esta instalación: el catálogo referencia
    ``backend/ms_sisper_tto_datos_privado.yaml`` y en la carpeta está
    ``backend/ms_tto_datos_privado.yaml``.  Quitando el token ``sisper`` ambos
    quedan igual.
    """
    partes = [p for p in str(nombre).lower().replace("-", "_").split("_") if p and p != "sisper"]
    return "_".join(partes)


def _servicio_para_manifiesto(rel: str, servicios: list[dict]) -> str:
    """Servicio del catálogo al que probablemente pertenece este YAML (o "")."""
    clave = _clave_servicio(Path(rel).stem)
    for svc in servicios:
        if _clave_servicio(svc.get("name", "")) == clave:
            return svc.get("name", "")
    return ""


def _categoria_manifiesto(rel: str) -> str:
    """Categoría legible de un manifiesto que no pertenece a un servicio."""
    nombre = rel.rsplit("/", 1)[-1].lower()
    if nombre.startswith(("ms_", "mf_")):
        return "Manifiesto de servicio (no referenciado por el catálogo)"
    for clave, etiqueta in (
        ("ingress", "Ingress"),
        ("onlyoffice", "OnlyOffice"),
        ("keydb", "KeyDB"),
        ("grafana", "Observabilidad"),
        ("prometheus", "Observabilidad"),
        ("namespace", "Namespace"),
        ("ollama", "Ollama / IA"),
        ("pv", "Almacenamiento"),
    ):
        if clave in nombre:
            return etiqueta
    return "Otros"


def deploy_manifest(rel_file: str, env_key: str = "develop") -> tuple[bool, str]:
    """Aplica un manifiesto del entorno con ``kubectl apply -f``.

    Pensado para los YAML que no son de un microservicio (ingress, onlyoffice,
    keydb, volumes…): se despliegan igual que los servicios, pero por fichero.
    La ruta se valida dentro de la carpeta de manifiestos del entorno.
    """
    env_cfg = ENVIRONMENTS.get(env_key, {})
    namespace = env_cfg.get("namespace", "develop")
    k8s_dir_rel = k8s_dir_for(env_key)
    k8s_dir = BASE_DIR / k8s_dir_rel
    try:
        destino = (k8s_dir / rel_file).resolve()
        destino.relative_to(k8s_dir.resolve())
    except (ValueError, OSError):
        return False, "Ruta fuera de la carpeta de manifiestos del entorno."
    if not destino.is_file() or destino.suffix.lower() not in (".yaml", ".yml"):
        return False, f"Manifiesto no encontrado: {rel_file}"
    try:
        res = subprocess.run(
            ["kubectl", "apply", "-f", str(destino), "-n", namespace],
            capture_output=True, text=True, timeout=60,
        )
    except subprocess.TimeoutExpired:
        return False, f"kubectl apply excedió 60 s ({rel_file})."
    except OSError as exc:
        return False, f"No se pudo ejecutar kubectl: {exc}"
    salida = (res.stdout or res.stderr or "").strip().splitlines()
    detalle = " · ".join(salida[-3:]) if salida else ""
    if res.returncode == 0:
        return True, f"{rel_file} aplicado en el namespace {namespace}. {detalle}".strip()
    return False, f"Error aplicando {rel_file}: {detalle or 'sin salida de kubectl'}"


def update_yaml_version(service_name: str, new_version: str, env_key: str = "develop") -> tuple:
    env_cfg = ENVIRONMENTS.get(env_key, {})
    k8s_dir_rel = k8s_dir_for(env_key)
    k8s_dir = BASE_DIR / k8s_dir_rel

    all_svcs = SERVICES_BACKEND + SERVICES_FRONTEND
    svc_meta = next((s for s in all_svcs if s["name"] == service_name), None)
    if not svc_meta or not svc_meta.get("k8s_file"):
        return False, "Servicio sin archivo de manifiesto K8s mapeado"

    yaml_path = k8s_dir / svc_meta["k8s_file"]
    if not yaml_path.exists():
        return False, f"Archivo no encontrado: {yaml_path}"

    content = yaml_path.read_text(encoding="utf-8")

    def repl(m):
        prefix = m.group(1)
        if "nginx" in prefix:
            return m.group(0)
        return f"image: {prefix}:{new_version}"

    new_content = re.sub(
        r'image:\s*([^\s#"\']+):([A-Za-z0-9_.\-]+)(?=\s*(?:#|$))',
        repl,
        content,
        flags=re.MULTILINE,
    )
    if new_content != content:
        yaml_path.write_text(new_content, encoding="utf-8")
        return True, f"Versión cambiada a {new_version} en {yaml_path.name}"
    return False, "No se encontraron etiquetas de imagen para actualizar"

def k8s_deploy_service(service_name: str, env_key: str = "develop") -> tuple:
    env_cfg = ENVIRONMENTS.get(env_key, {})
    k8s_dir_rel = k8s_dir_for(env_key)
    namespace = env_cfg.get("namespace", "develop")
    k8s_dir = BASE_DIR / k8s_dir_rel

    all_svcs = SERVICES_BACKEND + SERVICES_FRONTEND
    svc_meta = next((s for s in all_svcs if s["name"] == service_name), None)
    if not svc_meta or not svc_meta.get("k8s_file"):
        return False, f"Servicio {service_name} no tiene archivo K8s mapeado."

    yaml_path = k8s_dir / svc_meta["k8s_file"]
    if not yaml_path.exists():
        return False, f"Archivo YAML no encontrado: {yaml_path}"

    try:
        res = subprocess.run(
            ["kubectl", "apply", "-f", str(yaml_path), "-n", namespace],
            capture_output=True, text=True, timeout=20
        )
        if res.returncode == 0:
            apply_msg = res.stdout.strip() or "Manifiesto aplicado"
            dep_name = svc_meta.get("k8s_deploy", "")
            ro_msg = ""
            if dep_name:
                ok_ro, msg_ro = k8s_rollout_restart(dep_name, namespace)
                ro_msg = f" • Rollout: {'iniciado' if ok_ro else msg_ro}"
            return (True, f"{apply_msg}{ro_msg}")
        return (False, res.stderr.strip() or res.stdout.strip())
    except Exception as e:
        return False, str(e)


