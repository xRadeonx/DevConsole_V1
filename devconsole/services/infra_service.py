# devconsole/services/infra_service.py
import datetime
import json
import os
import re
import socket
import subprocess
import time
from pathlib import Path

from devconsole.services.git_service import get_git_info
from devconsole.services.ttl_cache import ttl_cache
from devconsole import settings
from devconsole.config import (
    BASE_DIR,
    INFRA_CONTAINERS,
    SERVICES_BACKEND,
    SERVICES_FRONTEND,
    get_service_repo_dir,
    is_port_open,
)

#: Secreto JWT de OnlyOffice, leído de config/secrets.json.  Antes estaba
#: escrito en este módulo y en el bloque .env que se genera; una credencial no
#: debe vivir en el código.
ONLYOFFICE_JWT = settings.secret("infra.onlyoffice_jwt_secret")


def _probe_host() -> str:
    """Host de referencia para deducir la IP local; vacío si no hay ninguno.

    La instalación declara sus hosts en config/panel.json (``databases``); el
    código no debe llevar una IP interna escrita.
    """
    for cfg in (settings.database_configs() or {}).values():
        host = (cfg or {}).get("host")
        if host:
            return str(host)
    return ""


def get_local_pc_ip() -> str:
    # 1. Buscar primero en la subred local declarada en config/panel.json
    subnet = settings.local_subnet()
    if subnet:
        try:
            out = subprocess.check_output(["ip", "-4", "addr", "show"], text=True, stderr=subprocess.DEVNULL)
            matches = re.findall(r"inet\s+(" + re.escape(subnet) + r"\.\d+)", out)
            if matches:
                return matches[0]
        except Exception:
            pass
    # 2. Comprobación mediante socket contra el host de referencia configurado
    host = _probe_host()
    if host:
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((host, 5432))
            ip = s.getsockname()[0]
            s.close()
            if ip and not ip.startswith("127."):
                return ip
        except Exception:
            pass
    return "127.0.0.1"

def sync_contracts_onlyoffice_env(auto_fix: bool = False) -> dict:
    # El servicio destino es un dato del proyecto: antes su nombre estaba escrito
    # tanto aquí como en los mensajes que ve el usuario.
    service = settings.onlyoffice_sync_service()
    env_file = BASE_DIR / "backend" / service / ".env" if service else None
    if not service or not env_file.exists():
        return {
            "success": False,
            "pc_ip": "127.0.0.1",
            "synced": False,
            "allowed_hosts_ok": False,
            "updated": False,
            "message": (
                "No hay un servicio configurado para el sincronizado de OnlyOffice "
                "(config/panel.json → onlyoffice_sync_service)."
                if not service
                else f"Archivo backend/{service}/.env no encontrado."
            ),
        }

    try:
        content = env_file.read_text(encoding="utf-8")
    except Exception as e:
        return {
            "success": False,
            "pc_ip": "127.0.0.1",
            "synced": False,
            "allowed_hosts_ok": False,
            "updated": False,
            "message": f"Error al leer .env: {e}"
        }

    pc_ip = get_local_pc_ip()

    # 1. Verificar host.containers.internal en ALLOWED_HOSTS
    allowed_hosts_ok = "host.containers.internal" in content

    # 2. Verificar variables ONLYOFFICE requeridas
    expected_vars = [
        "ONLYOFFICE_ENVIRONMENT=local",
        f"ONLYOFFICE_JWT_SECRET={ONLYOFFICE_JWT}",
        "ONLYOFFICE_JWT_ALGORITHM=HS256",
        "ONLYOFFICE_JWT_ENABLED=True",
        "ONLYOFFICE_FORCE_SAVE_WAIT_SECONDS=8",
        f"ONLYOFFICE_DOCUMENTSERVER_URL=http://{pc_ip}:8082",
        f"ONLYOFFICE_CONVERTER_URL=http://{pc_ip}:8082/ConvertService.ashx",
        f"ONLYOFFICE_COMMAND_SERVICE_URL=http://{pc_ip}:8082/command",
        "ONLYOFFICE_BACKEND_BASE_URL=http://host.containers.internal:8006/sisper/api/v1/ms-contratos",
        f'ONLYOFFICE_API_URL="http://{pc_ip}:8082/web-apps/apps/api/documents/api.js"'
    ]

    missing_vars = [v for v in expected_vars if v not in content]
    is_synced = allowed_hosts_ok and (len(missing_vars) == 0)
    was_updated = False

    if auto_fix and not is_synced:
        new_content = content

        # Asegurar host.containers.internal en ALLOWED_HOSTS
        if not allowed_hosts_ok:
            m_ah = re.search(r'(ALLOWED_HOSTS\s*=\s*"[^"]*)(")', new_content)
            if m_ah:
                new_content = new_content[:m_ah.start(2)] + "host.containers.internal\n" + new_content[m_ah.start(2):]
                allowed_hosts_ok = True
            else:
                m_single = re.search(r'(ALLOWED_HOSTS\s*=\s*[^\n]+)', new_content)
                if m_single:
                    new_content = new_content[:m_single.end(1)] + ",host.containers.internal" + new_content[m_single.end(1):]
                    allowed_hosts_ok = True

        expected_block = f"""# ==========================
# ONLYOFFICE
# ==========================
# Ambiente activo para desarrollo local.
ONLYOFFICE_ENVIRONMENT=local

# JWT debe coincidir con el secret configurado en OnlyOffice DocumentServer.
ONLYOFFICE_JWT_SECRET={ONLYOFFICE_JWT}
ONLYOFFICE_JWT_ALGORITHM=HS256
ONLYOFFICE_JWT_ENABLED=True
ONLYOFFICE_FORCE_SAVE_WAIT_SECONDS=8
# LOCAL - valores activos para tu ambiente actual
ONLYOFFICE_DOCUMENTSERVER_URL=http://{pc_ip}:8082
ONLYOFFICE_CONVERTER_URL=http://{pc_ip}:8082/ConvertService.ashx
ONLYOFFICE_COMMAND_SERVICE_URL=http://{pc_ip}:8082/command
# Backend ms-contratos visto desde OnlyOffice local
ONLYOFFICE_BACKEND_BASE_URL=http://host.containers.internal:8006/sisper/api/v1/ms-contratos
ONLYOFFICE_API_URL="http://{pc_ip}:8082/web-apps/apps/api/documents/api.js"
"""
        pattern = r"(#\s*={5,}\s*\n#\s*ONLYOFFICE\s*\n#\s*={5,}.*?)(?=\n#\s*DEVELOP\s*-\s*plantilla|\Z)"
        if re.search(pattern, new_content, re.DOTALL):
            new_content = re.sub(pattern, expected_block.strip() + "\n", new_content, flags=re.DOTALL)
        else:
            new_content = new_content.rstrip() + "\n\n" + expected_block

        try:
            env_file.write_text(new_content, encoding="utf-8")
            was_updated = True
            is_synced = True
            missing_vars = []
        except Exception as e:
            return {
                "success": False,
                "pc_ip": pc_ip,
                "synced": False,
                "allowed_hosts_ok": allowed_hosts_ok,
                "updated": False,
                "message": f"Error al escribir en .env: {e}"
            }

    msg = f"Variables ONLYOFFICE sincronizadas con IP {pc_ip} y host.containers.internal en ALLOWED_HOSTS." if is_synced else f"Faltan {len(missing_vars)} variable(s) por sincronizar en .env."
    return {
        "success": True,
        "pc_ip": pc_ip,
        "synced": is_synced,
        "allowed_hosts_ok": allowed_hosts_ok,
        "updated": was_updated,
        "missing": missing_vars,
        "message": msg
    }

@ttl_cache(seconds=45)
def get_infra_info() -> dict:
    keydb_open = is_port_open(6379)
    onlyoffice_open = is_port_open(8082)
    keycloak_open = is_port_open(8080)
    postgres_local_open = is_port_open(5432, "127.0.0.1")
    postgres_intranet_open = is_port_open(5432, _probe_host()) if _probe_host() else False
    mongo_local_open = is_port_open(27017, "127.0.0.1")
    rabbitmq_local_open = is_port_open(5672, "127.0.0.1")

    keydb_status = "desconocido"
    onlyoffice_status = "desconocido"
    keycloak_status = "desconocido"

    keydb_cfg = INFRA_CONTAINERS["keydb"]
    keydb_img_exists = False
    try:
        out = subprocess.check_output(
            ["podman", "inspect", "--format", "{{.State.Status}}", "keydb"],
            stderr=subprocess.DEVNULL, timeout=2
        ).decode().strip()
        keydb_status = out or "not_found"
    except Exception:
        keydb_status = "not_found"

    try:
        keydb_img_exists = (subprocess.run(["podman", "image", "exists", keydb_cfg["image"]], stderr=subprocess.DEVNULL, timeout=2).returncode == 0)
    except Exception:
        keydb_img_exists = False

    oo_cfg = INFRA_CONTAINERS["onlyoffice-local"]
    oo_img_exists = False
    try:
        out = subprocess.check_output(
            ["podman", "inspect", "--format", "{{.State.Status}}", "onlyoffice-local"],
            stderr=subprocess.DEVNULL, timeout=2
        ).decode().strip()
        onlyoffice_status = out or "not_found"
    except Exception:
        onlyoffice_status = "not_found"

    try:
        oo_img_exists = (subprocess.run(["podman", "image", "exists", oo_cfg["image"]], stderr=subprocess.DEVNULL, timeout=2).returncode == 0)
    except Exception:
        oo_img_exists = False

    try:
        out = subprocess.check_output(
            ["docker", "inspect", "--format", "{{.State.Status}}", "keycloak-sisper-local"],
            stderr=subprocess.DEVNULL, timeout=2
        ).decode().strip()
        keycloak_status = out or "not_found"
    except Exception:
        keycloak_status = "not_found"

    k8s_infra = {"develop": {}, "test": {}, "prod": {}}
    try:
        out = subprocess.check_output(
            ["kubectl", "get", "pods", "-A", "--no-headers"],
            stderr=subprocess.DEVNULL, timeout=2
        ).decode()
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 4:
                ns, pod_name, status = parts[0], parts[1], parts[3]
                if ns in k8s_infra:
                    if "keydb" in pod_name:
                        k8s_infra[ns]["keydb"] = status
                    elif "onlyoffice" in pod_name:
                        k8s_infra[ns]["onlyoffice"] = status
    except Exception:
        pass

    contracts_env = sync_contracts_onlyoffice_env(auto_fix=False)

    return {
        "keydb": {
            "port_open": keydb_open,
            "container": keydb_status,
            "image_exists": keydb_img_exists,
            "image": keydb_cfg["image"]
        },
        "onlyoffice": {
            "port_open": onlyoffice_open,
            "container": onlyoffice_status,
            "image_exists": oo_img_exists,
            "image": oo_cfg["image"],
            "contracts_env": contracts_env
        },
        "keycloak": {"port_open": keycloak_open, "container": keycloak_status},
        "postgres_local": {"port_open": postgres_local_open},
        "postgres_intranet": {"port_open": postgres_intranet_open},
        "mongo_local": {"port_open": mongo_local_open},
        "rabbitmq_local": {"port_open": rabbitmq_local_open},
        "k8s_infra": k8s_infra
    }

def get_service_detail(service_name: str, port: int):
    repo = get_service_repo_dir(service_name)
    is_backend = (BASE_DIR / "backend" / service_name).exists()
    group = "Backend (Django / Daphne)" if is_backend else "Frontend (Webpack Dev Server)"
    
    online = is_port_open(port)
    pid_info = "No detectado"
    if online:
        try:
            res = subprocess.check_output(f"fuser {port}/tcp 2>/dev/null", shell=True).decode().strip()
            pids = res.split()
            if pids:
                pid_info = ", ".join(pids)
        except Exception:
            pid_info = "Activo"

    git_data = get_git_info(repo)
    return {
        "name": service_name,
        "port": port,
        "group": group,
        "online": online,
        "pid": pid_info,
        "git": git_data,
        "path": str(repo)
    }


