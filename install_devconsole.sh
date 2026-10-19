#!/usr/bin/env bash
# ==============================================================================
# SISPER DevConsole — Instalador Automatizado de Entorno y Lanzador
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="sisper-dashboard.service"
DESKTOP_NAME="sisper-devconsole.desktop"

echo "================================================================="
echo "  Instalador SISPER DevConsole (Tilix & Multi-Entorno Orquestador)"
echo "================================================================="
echo "Directorio base detectado: ${SCRIPT_DIR}"

# 0. Puerto fijo 9099 (el mismo para todos). Si pertenece a una instalación
#    previa de DevConsole, detenemos exclusivamente su unidad systemd y volvemos
#    a comprobar. Nunca se mata por puerto: un proceso ajeno del mismo usuario
#    no demuestra ownership y no debe ser terminado por el instalador.
SISPER_PORT="${SISPER_PORT:-9099}"
preparar_puerto() {
    local p="$1"
    ss -ltn 2>/dev/null | grep -q ":${p} " || return 0

    echo "[*] El puerto ${p} está ocupado; comprobando una instalación previa..."
    systemctl --user stop "${SERVICE_NAME}" 2>/dev/null || true

    for _ in $(seq 1 10); do
        ss -ltn 2>/dev/null | grep -q ":${p} " || return 0
        sleep 0.2
    done
    return 1
}

if ! preparar_puerto "${SISPER_PORT}"; then
    echo "  [!] El puerto ${SISPER_PORT} está ocupado por un proceso que DevConsole no posee:"
    ss -ltnp 2>/dev/null | grep ":${SISPER_PORT} " | sed 's/^/      /' || true
    echo "      Por seguridad el instalador NO terminará ese proceso."
    echo "      Ciérralo explícitamente o usa otro puerto:"
    echo "      SISPER_PORT=9100 ./install_devconsole.sh"
    exit 1
fi
echo "Puerto asignado: ${SISPER_PORT}"

# 1. Verificar dependencias básicas
echo "[*] Verificando dependencias..."
for cmd in python3 git tilix; do
    if ! command -v "${cmd}" &>/dev/null; then
        echo "  [!] Advertencia: '${cmd}' no se encuentra instalado en PATH."
    else
        echo "  [✓] ${cmd}: $(command -v "${cmd}")"
    fi
done

if ! command -v python3 >/dev/null 2>&1; then
    echo "[!] Python 3 es obligatorio para ejecutar DevConsole."
    exit 1
fi

# 1.b Runtime V1.1. Las librerías mejoradas son opcionales para conservar el
# arranque offline, pero el instalador intenta dejarlas activas en un venv
# aislado. Si no hay red/mirror o venv no está disponible, mantiene Python del
# sistema y las rutas fallback V1; nunca deja una instalación inutilizable.
PYTHON_BIN="$(command -v python3)"
V11_VENV="${XDG_DATA_HOME:-${HOME}/.local/share}/sisper-devconsole/venv"
V11_REQUIREMENTS="${SCRIPT_DIR}/requirements-v11.txt"

v11_imports_ok() {
    "$1" -c 'import psutil, pydantic; import ruamel.yaml' >/dev/null 2>&1
}

if v11_imports_ok "${PYTHON_BIN}"; then
    echo "  [✓] Runtime V1.1 disponible en Python del sistema."
elif [ "${SISPER_SKIP_V11_DEP_INSTALL:-0}" = "1" ]; then
    echo "  [i] Instalación de dependencias V1.1 omitida por SISPER_SKIP_V11_DEP_INSTALL=1."
elif [ -f "${V11_REQUIREMENTS}" ]; then
    echo "[*] Preparando runtime Python aislado para capacidades V1.1..."
    if [ ! -x "${V11_VENV}/bin/python" ]; then
        rm -rf "${V11_VENV}" 2>/dev/null || true
        if ! "${PYTHON_BIN}" -m venv "${V11_VENV}" 2>/dev/null; then
            echo "  [!] No se pudo crear venv; se conservará el runtime V1 compatible."
        fi
    fi
    if [ -x "${V11_VENV}/bin/python" ]; then
        if ! v11_imports_ok "${V11_VENV}/bin/python"; then
            if ! "${V11_VENV}/bin/python" -m pip install --disable-pip-version-check -r "${V11_REQUIREMENTS}"; then
                echo "  [!] No se pudieron instalar todas las dependencias V1.1 (posible entorno offline)."
            fi
        fi
        if v11_imports_ok "${V11_VENV}/bin/python"; then
            PYTHON_BIN="${V11_VENV}/bin/python"
            echo "  [✓] Runtime V1.1 activo: ${PYTHON_BIN}"
        else
            echo "  [!] V1.1 funcionará con fallbacks donde falten psutil/Pydantic/ruamel.yaml."
        fi
    fi
else
    echo "  [!] No existe requirements-v11.txt; se conserva runtime V1 compatible."
fi

# 2. Configurar Servicio de Usuario Systemd
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
mkdir -p "${SYSTEMD_USER_DIR}"

echo "[*] Configurando servicio systemd de usuario: ${SYSTEMD_USER_DIR}/${SERVICE_NAME}..."
cat <<EOF > "${SYSTEMD_USER_DIR}/${SERVICE_NAME}"
[Unit]
Description=Dashboard Web Orquestador SISPER (Tilix & Microservicios)
Documentation=http://localhost:${SISPER_PORT}
After=graphical-session.target network.target
PartOf=graphical-session.target
# Si el panel no arranca (puerto ocupado, error de configuración…), se detiene
# tras varios intentos en vez de reiniciarse sin fin (eso disparaba avisos
# constantes de "Unit recovered").
# La ruta del script va entre comillas: la carpeta puede tener espacios y
# systemd partiría el comando (fallaba con status=2/INVALIDARGUMENT).
# Ojo: WorkingDirectory= NO admite comillas, por eso no se usa.
StartLimitIntervalSec=60
StartLimitBurst=4

[Service]
Type=simple
ExecStart="${PYTHON_BIN}" "${SCRIPT_DIR}/dashboard.py"
Restart=on-failure
RestartSec=5
KillMode=process
TimeoutStopSec=3s
Environment=PYTHONUNBUFFERED=1
Environment=PATH=${HOME}/.local/bin:${HOME}/.bun/bin:${HOME}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
# Fase 0C.5: bind explicito al loopback. DevConsole es un orquestador que
# ejecuta comandos, reescribe .env y opera kubectl; no debe quedar expuesto
# a la LAN. Para modo LAN (solo en redes de confianza) usar SISPER_HOST=0.0.0.0.
Environment=SISPER_HOST=127.0.0.1
Environment=SISPER_PORT=${SISPER_PORT}
PassEnvironment=DISPLAY WAYLAND_DISPLAY XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS

[Install]
WantedBy=graphical-session.target
EOF

# 3. Configurar Lanzador .desktop en GNOME/KDE
APPS_DIR="${HOME}/.local/share/applications"
mkdir -p "${APPS_DIR}"

echo "[*] Creando acceso directo en el menú de aplicaciones: ${APPS_DIR}/${DESKTOP_NAME}..."
cat <<EOF > "${APPS_DIR}/${DESKTOP_NAME}"
[Desktop Entry]
Version=1.0
Type=Application
Name=SISPER DevConsole
GenericName=Orquestador de Microservicios y Tilix
Comment=Panel de control local, CI/CD y gestión de entornos SISPER
Exec=xdg-open http://localhost:${SISPER_PORT}
Icon=utilities-terminal
Terminal=false
Categories=Development;IDE;
StartupNotify=false
EOF

# 4. Habilitar y recargar servicios de usuario
echo "[*] Recargando systemd user daemon..."
systemctl --user daemon-reload

echo "[*] Habilitando e iniciando servicio ${SERVICE_NAME}..."
systemctl --user enable --now "${SERVICE_NAME}"

# 5. Comprobar que arrancó de verdad (y decir por qué si no)
sleep 2
if systemctl --user is-active --quiet "${SERVICE_NAME}"; then
    echo "  [✓] Servicio activo."
else
    echo "  [!] El servicio no quedó activo. Últimas líneas:"
    systemctl --user status "${SERVICE_NAME}" --no-pager -n 12 | sed 's/^/      /' || true
    echo "      Revisa el puerto (SISPER_PORT) y 'journalctl --user -u ${SERVICE_NAME}'."
fi

echo ""
echo "================================================================="
echo "  [✓] Instalación completada."
echo "  El servicio inicia automáticamente con tu sesión gráfica."
echo "  Acceso Web: http://localhost:${SISPER_PORT}"
echo "  Acceso Menú: Busca 'SISPER DevConsole' en tus aplicaciones."

# 5.b Credenciales de producto.
# Viewer/QA no necesita credencial. Developer y Administrator se desbloquean
# contra verificadores hasheados distribuidos con el producto; el instalador no
# crea claves distintas por máquina ni solicita claves interactivamente.
DESTINO_CLAVES="${HOME}/.config/sisper-dashboard/secrets.json"
if [ ! -f "${DESTINO_CLAVES}" ] && [ -f "${SCRIPT_DIR}/config/pins.json" ]; then
    mkdir -p "$(dirname "${DESTINO_CLAVES}")"
    cp "${SCRIPT_DIR}/config/pins.json" "${DESTINO_CLAVES}"
    chmod 600 "${DESTINO_CLAVES}"
    echo "[✓] Verificadores de acceso del producto instalados en ${DESTINO_CLAVES}"
elif [ -f "${DESTINO_CLAVES}" ]; then
    chmod 600 "${DESTINO_CLAVES}" 2>/dev/null || true
    echo "[i] Se conservan los verificadores de acceso existentes en ${DESTINO_CLAVES}"
else
    echo "[!] No se encontró config/pins.json; Viewer/QA seguirá disponible,"
    echo "    pero Developer/Admin no podrán desbloquearse hasta instalar verificadores."
fi

echo "  El panel arranca como Soporte/QA (sólo lectura)."
echo "  Developer y Administrator se habilitan únicamente con su clave de producto."
echo "================================================================="
