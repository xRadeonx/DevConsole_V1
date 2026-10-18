#!/usr/bin/env bash
# ==============================================================================
# Script: switch_env.sh
# Alterna variables entre 'local' (offline) e 'intranet' (normal)
# Soporta modo sesión por defecto o '--all' para todos los microservicios/frontends.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 - << 'EOF' "$@"
import json
import sys
import re
from pathlib import Path

args = sys.argv[1:]

flag_all = False
filtered_args = []
for a in args:
    if a in ("--all", "-a"):
        flag_all = True
    else:
        filtered_args.append(a)

base_dir = Path(__file__).resolve().parent if "__file__" in locals() else Path(".").resolve()
# Fallback si se ejecuta por stdin
if not (base_dir / "backend").exists():
    # Carpeta configurada en el panel (config/settings.json) o el propio
    # directorio del script.  Antes era una ruta fija de otra máquina.
    _cfg = Path("config/settings.json")
    try:
        _bd = json.loads(_cfg.read_text(encoding="utf-8")).get("base_dir")
        if _bd and Path(_bd).expanduser().is_dir():
            base_dir = Path(_bd).expanduser().resolve()
    except Exception:
        pass

BACKEND_DIR = base_dir / "backend"
FRONTEND_DIR = base_dir / "frontend"

INTRANET_BACKEND_CONFIGS = {
    "ms_sisper_sesion": {
        "DATABASE_USER": "ms_sisper_sesion",
        "DATABASE_PASSWORD": "CAMBIAR_ESTA_CLAVE",
        "DATABASE_HOST": "172.30.23.71",
        "KEYCLOAK_SERVER_URL": "https://sisperkeydes.direcpers.armada.cl/",
    },
    "ms_sisper_adm_usuario": {
        "DATABASE_USER": "ms_sisper_adm_usuario",
        "DATABASE_PASSWORD": "CAMBIAR_ESTA_CLAVE",
        "DATABASE_HOST": "172.30.23.71",
        "KEYCLOAK_SERVER_URL": "https://sisperkeydes.armada.cl/",
    },
    "ms_sisper_asistente": {
        "DATABASE_USER": "ms_sisper_contratos",
        "DATABASE_PASSWORD": "CAMBIAR_ESTA_CLAVE",
        "DATABASE_HOST": "172.30.23.71",
        "KEYCLOAK_SERVER_URL": "https://sisperkeydes.direcpers.armada.cl/",
    },
    "ms_sisper_beneficios": {
        "DATABASE_USER": "ms_sisper_beneficios",
        "DATABASE_PASSWORD": "CAMBIAR_ESTA_CLAVE",
        "DATABASE_HOST": "172.30.23.71",
        "KEYCLOAK_SERVER_URL": "https://sisperkeydes.direcpers.armada.cl/",
    },
    "ms_sisper_bitacora": {
        "DATABASE_USER": "ms_sisper_bitacora",
        "DATABASE_PASSWORD": "CAMBIAR_ESTA_CLAVE",
        "DATABASE_HOST": "172.30.23.71",
        "KEYCLOAK_SERVER_URL": "https://sisperkeydes.direcpers.armada.cl/",
    },
    "ms_sisper_contratos": {
        "DATABASE_USER": "ms_sisper_contratos",
        "DATABASE_PASSWORD": "CAMBIAR_ESTA_CLAVE",
        "DATABASE_HOST": "172.30.23.71",
        "KEYCLOAK_SERVER_URL": "https://sisperkeydes.direcpers.armada.cl/",
    },
    "ms_sisper_destinaciones": {
        "DATABASE_USER": "ms_sisper_destinaciones",
        "DATABASE_PASSWORD": "CAMBIAR_ESTA_CLAVE",
        "DATABASE_HOST": "172.30.23.71",
        "KEYCLOAK_SERVER_URL": "https://sisperkeydes.direcpers.armada.cl/",
    },
    "ms_sisper_documentos": {
        "DATABASE_USER": "ms_sisper_documentos",
        "DATABASE_PASSWORD": "CAMBIAR_ESTA_CLAVE",
        "DATABASE_HOST": "172.30.23.71",
        "KEYCLOAK_SERVER_URL": "https://sisperkeydes.direcpers.armada.cl/",
    },
    "ms_sisper_form_acad": {
        "DATABASE_USER": "ms_sisper_form_acad",
        "DATABASE_PASSWORD": "CAMBIAR_ESTA_CLAVE",
        "DATABASE_HOST": "172.30.23.71",
        "KEYCLOAK_SERVER_URL": "https://sisperkeydes.direcpers.armada.cl/",
    },
    "ms_sisper_identificacion": {
        "DATABASE_USER": "ms_sisper_identificacion",
        "DATABASE_PASSWORD": "CAMBIAR_ESTA_CLAVE",
        "DATABASE_HOST": "172.30.23.71",
        "KEYCLOAK_SERVER_URL": "https://lbkeydes.direcpers.armada.cl/",
    },
    "ms_sisper_perfiles_riesgo": {
        "DATABASE_USER": "ms_sisper_perfiles_riesgo",
        "DATABASE_PASSWORD": "CAMBIAR_ESTA_CLAVE",
        "DATABASE_HOST": "172.30.23.71",
        "KEYCLOAK_SERVER_URL": "https://sisperkeydes.direcpers.armada.cl/",
    },
    "ms_sisper_promocion": {
        "DATABASE_USER": "ms_sisper_promocion",
        "DATABASE_PASSWORD": "CAMBIAR_ESTA_CLAVE",
        "DATABASE_HOST": "172.30.23.71",
        "KEYCLOAK_SERVER_URL": "https://sisperkeydes.direcpers.armada.cl/",
    },
    "ms_sisper_promocion_desempeno": {
        "DATABASE_USER": "ms_sisper_promocion_desemp",
        "DATABASE_PASSWORD": "CAMBIAR_ESTA_CLAVE",
        "DATABASE_HOST": "172.30.23.71",
        "KEYCLOAK_SERVER_URL": "https://sisperkeydes.armada.cl/",
    },
    "ms_sisper_promocion_otros": {
        "DATABASE_USER": "ms_sisper_promocion_otros",
        "DATABASE_PASSWORD": "CAMBIAR_ESTA_CLAVE",
        "DATABASE_HOST": "172.30.23.71",
        "KEYCLOAK_SERVER_URL": "https://sisperkeydes.armada.cl/",
    },
    "ms_sisper_promocion_proyec": {
        "DATABASE_USER": "ms_sisper_promocion_proyec",
        "DATABASE_PASSWORD": "CAMBIAR_ESTA_CLAVE",
        "DATABASE_HOST": "172.30.23.71",
        "KEYCLOAK_SERVER_URL": "https://sisperkeydes.armada.cl/",
    },
    "ms_sisper_retiros": {
        "DATABASE_USER": "ms_sisper_retiros",
        "DATABASE_PASSWORD": "CAMBIAR_ESTA_CLAVE",
        "DATABASE_HOST": "172.30.23.71",
        "KEYCLOAK_SERVER_URL": "https://sisperkeydes.direcpers.armada.cl/",
    },
    "ms_sisper_solicitudes": {
        "DATABASE_USER": "ms_sisper_solicitudes",
        "DATABASE_PASSWORD": "CAMBIAR_ESTA_CLAVE",
        "DATABASE_HOST": "172.30.23.71",
        "KEYCLOAK_SERVER_URL": "https://sisperkeydes.direcpers.armada.cl/",
    },
}

INTRANET_FRONTEND_CONFIGS = {
    "mf_sisper_sesion": {
        "MS_KEYCLOAK": '"http://sisperkeydes.direcpers.armada.cl/"',
    },
    "mf_sisper_perfiles_de_riesgo": {
        "MS_KEYCLOAK": '"http://sisperkeydes.direcpers.armada.cl/"',
    },
}

LOCAL_BACKEND_COMMON = {
    "DATABASE_USER": "postgres",
    "DATABASE_PASSWORD": "CAMBIAR_ESTA_CLAVE",
    "DATABASE_HOST": "127.0.0.1",
    "KEYCLOAK_SERVER_URL": '"http://localhost:8080/"',
}

LOCAL_FRONTEND_COMMON = {
    "MS_KEYCLOAK": '"http://localhost:8080/"',
}

def get_var(path: Path, key: str) -> str:
    if not path.exists():
        return "<no existe>"
    text = path.read_text(encoding="utf-8")
    m = re.search(rf"^{key}\s*=\s*(.*)$", text, re.MULTILINE)
    return m.group(1).strip() if m else "<no configurada>"

def detect_backend_mode(path: Path) -> str:
    host = get_var(path, "DATABASE_HOST").strip('"\'')
    kc = get_var(path, "KEYCLOAK_SERVER_URL").strip('"\'')
    if "127.0.0.1" in host and "localhost:8080" in kc:
        return "LOCAL"
    elif "172.30.23.71" in host and ("armada.cl" in kc or "direcpers" in kc):
        return "INTRANET"
    return "MIXTO"

def detect_frontend_mode(path: Path) -> str:
    kc = get_var(path, "MS_KEYCLOAK").strip('"\'')
    if "localhost:8080" in kc:
        return "LOCAL"
    elif "armada.cl" in kc or "direcpers" in kc:
        return "INTRANET"
    return "MIXTO"

def apply_mode(path: Path, replacements: dict):
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    for key, val in replacements.items():
        pattern = rf"^{key}\s*=.*$"
        if re.search(pattern, text, re.MULTILINE):
            text = re.sub(pattern, f"{key}={val}", text, flags=re.MULTILINE)
        else:
            text += f"\n{key}={val}\n"
    path.write_text(text, encoding="utf-8")

BITACORA_ORIG = '''        request_data, ip, metodo, url_full = extract_request_data(request)
        publicar_en_bitacora.delay(
            data=request_data,
            ip=ip,
            modulo="MOD. SESIÓN",
            metodo=metodo,
            url_full=url_full,
            response_code=status.HTTP_200_OK,
            user_id_ejecutor=user_id,
            run_ejecutor=username,
            primer_nombre_ejecutor=user_info.get("firstName") or "No Disponible",
            primer_apellido_ejecutor=user_info.get("lastName") or "No Disponible",
            segundo_apellido_ejecutor="No Disponible",
            fec_bitacora=dt.datetime.now(),
        )
        logger.info("SISPER_INFO: ===> Transacción enviada a Broker")'''

BITACORA_PATCH = '''        try:
            request_data, ip, metodo, url_full = extract_request_data(request)
            publicar_en_bitacora.delay(
                data=request_data,
                ip=ip,
                modulo="MOD. SESIÓN",
                metodo=metodo,
                url_full=url_full,
                response_code=status.HTTP_200_OK,
                user_id_ejecutor=user_id,
                run_ejecutor=username,
                primer_nombre_ejecutor=user_info.get("firstName") or "No Disponible",
                primer_apellido_ejecutor=user_info.get("lastName") or "No Disponible",
                segundo_apellido_ejecutor="No Disponible",
                fec_bitacora=dt.datetime.now(),
            )
            logger.info("SISPER_INFO: ===> Transacción enviada a Broker")
        except Exception as e:
            logger.warning("SISPER_WARN: No se pudo registrar en bitácora (broker no disponible): %s", e)'''

def detect_bitacora_status() -> str:
    views_path = BACKEND_DIR / "ms_sisper_sesion" / "core" / "ms_sesion" / "v1" / "views.py"
    if not views_path.exists():
        return "<no encontrado>"
    text = views_path.read_text(encoding="utf-8")
    if BITACORA_PATCH in text:
        return "PARCHE LOCAL (try/except)"
    elif BITACORA_ORIG in text:
        return "ORIGINAL INTRANET (limpio)"
    return "DESCONOCIDO / MODIFICADO"

def toggle_bitacora_patch(mode: str):
    views_path = BACKEND_DIR / "ms_sisper_sesion" / "core" / "ms_sesion" / "v1" / "views.py"
    if not views_path.exists():
        return
    text = views_path.read_text(encoding="utf-8")
    if mode == "local":
        if BITACORA_ORIG in text:
            views_path.write_text(text.replace(BITACORA_ORIG, BITACORA_PATCH), encoding="utf-8")
            print("[+] ms_sisper_sesion: Parche defensivo de bitácora APLICADO (try/except RabbitMQ).")
        elif BITACORA_PATCH in text:
            print("[=] ms_sisper_sesion: Parche de bitácora ya estaba activo.")
    elif mode == "intranet":
        if BITACORA_PATCH in text:
            views_path.write_text(text.replace(BITACORA_PATCH, BITACORA_ORIG), encoding="utf-8")
            print("[-] ms_sisper_sesion: Parche de bitácora REMOVIDO (código original restaurado para git).")
        elif BITACORA_ORIG in text:
            print("[=] ms_sisper_sesion: Código original de bitácora ya estaba limpio.")

# Determinar target y acción
target_service = None
action = "status"

if len(filtered_args) == 0:
    action = "status"
elif len(filtered_args) == 1:
    arg0 = filtered_args[0].lower()
    if arg0 in ("local", "offline", "intranet", "normal", "status", "info", "status-json", "bitacora-local", "bitacora-intranet"):
        action = arg0
    else:
        target_service = filtered_args[0]
        action = "status"
elif len(filtered_args) >= 2:
    # Ej: switch_env.sh ms_sisper_adm_usuario local
    target_service = filtered_args[0]
    action = filtered_args[1].lower()

# Normalizar alias
if action in ("offline",):
    action = "local"
elif action in ("normal",):
    action = "intranet"

# Lista de servicios a operar
selected_backends = []
selected_frontends = []

if target_service:
    # Buscar servicio específico
    b_match = [s for s in INTRANET_BACKEND_CONFIGS if s == target_service or target_service in s]
    f_match = [s for s in INTRANET_FRONTEND_CONFIGS if s == target_service or target_service in s]
    if not b_match and not f_match:
        print(f"ERROR: Servicio '{target_service}' no reconocido.")
        sys.exit(1)
    selected_backends = b_match
    selected_frontends = f_match
elif flag_all:
    selected_backends = list(INTRANET_BACKEND_CONFIGS.keys())
    selected_frontends = list(INTRANET_FRONTEND_CONFIGS.keys())
else:
    # Default: solo sesión
    selected_backends = ["ms_sisper_sesion"]
    selected_frontends = ["mf_sisper_sesion"]

if action == "status-json":
    import json
    p = BACKEND_DIR / "ms_sisper_sesion" / ".env"
    mode = detect_backend_mode(p)
    bit_st = detect_bitacora_status()
    print(json.dumps({
        "env_mode": mode,
        "bitacora_status": bit_st,
        "database_host": get_var(p, "DATABASE_HOST"),
        "keycloak_url": get_var(p, "KEYCLOAK_SERVER_URL")
    }))
    sys.exit(0)

if action in ("bitacora-local", "bitacora-intranet"):
    mode = "local" if action == "bitacora-local" else "intranet"
    toggle_bitacora_patch(mode)
    print(f"[*] ms_sisper_sesion bitácora code: {detect_bitacora_status()}")
    sys.exit(0)

if action in ("local", "intranet"):
    target_mode = "LOCAL" if action == "local" else "INTRANET"
    print(f"\n[+] Aplicando modo {target_mode} a ({'TODOS' if flag_all else ', '.join(selected_backends + selected_frontends)})...")
    
    for s in selected_backends:
        env_path = BACKEND_DIR / s / ".env"
        if action == "local":
            apply_mode(env_path, LOCAL_BACKEND_COMMON)
        else:
            apply_mode(env_path, INTRANET_BACKEND_CONFIGS[s])
            
    for f in selected_frontends:
        env_path = FRONTEND_DIR / f / ".env"
        if action == "local":
            apply_mode(env_path, LOCAL_FRONTEND_COMMON)
        else:
            apply_mode(env_path, INTRANET_FRONTEND_CONFIGS[f])

    if "ms_sisper_sesion" in selected_backends:
        toggle_bitacora_patch(action)

print("\n=== ESTADO DE VARIABLES ===")
print("--- Backend ---")
for s in selected_backends:
    p = BACKEND_DIR / s / ".env"
    mode = detect_backend_mode(p)
    host = get_var(p, "DATABASE_HOST")
    user = get_var(p, "DATABASE_USER")
    kc = get_var(p, "KEYCLOAK_SERVER_URL")
    print(f"[{mode:8}] {s:30} DB: {user}@{host} | KC: {kc}")

if "ms_sisper_sesion" in selected_backends:
    bit_st = detect_bitacora_status()
    print(f"[*] ms_sisper_sesion bitácora code: {bit_st}")

print("\n--- Frontend ---")
for f in selected_frontends:
    p = FRONTEND_DIR / f / ".env"
    mode = detect_frontend_mode(p)
    kc = get_var(p, "MS_KEYCLOAK")
    print(f"[{mode:8}] {f:30} KC: {kc}")

print()
EOF
