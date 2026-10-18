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

# 0. Puerto fijo 9099 (el mismo para todos).  Si está ocupado por una
#    instalación previa del mismo usuario, se detiene y se libera; si lo ocupa
#    otro proceso/usuario, se aborta con el detalle (no se elige otro puerto).
SISPER_PORT="${SISPER_PORT:-9099}"
liberar_puerto() {
    local p="$1"
    ss -ltn 2>/dev/null | grep -q ":${p} " || return 0
    echo "[*] El puerto ${p} está ocupado; intentando liberarlo..."
    systemctl --user stop "${SERVICE_NAME}" 2>/dev/null || true
    sleep 1
    # fuser sólo puede matar procesos del propio usuario: nunca toca a otro.
    command -v fuser >/dev/null 2>&1 && fuser -k "${p}/tcp" 2>/dev/null || true
    for _ in $(seq 1 10); do
        ss -ltn 2>/dev/null | grep -q ":${p} " || return 0
        sleep 1
    done
    return 1
}
if ! liberar_puerto "${SISPER_PORT}"; then
    echo "  [!] El puerto ${SISPER_PORT} sigue ocupado por otro proceso/usuario:"
    ss -ltnp 2>/dev/null | grep ":${SISPER_PORT} " | sed 's/^/      /'
    echo "      Ciérralo y reintenta, o usa otro:  SISPER_PORT=9100 ./install_devconsole.sh"
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
ExecStart=/usr/bin/python3 "${SCRIPT_DIR}/dashboard.py"
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

# 5.b Claves hasheadas que vienen en el paquete (sin texto en claro)
DESTINO_CLAVES="${HOME}/.config/sisper-dashboard/secrets.json"
if [ ! -f "${DESTINO_CLAVES}" ] && [ -f "${SCRIPT_DIR}/config/pins.json" ]; then
    mkdir -p "$(dirname "${DESTINO_CLAVES}")"
    cp "${SCRIPT_DIR}/config/pins.json" "${DESTINO_CLAVES}"
    chmod 600 "${DESTINO_CLAVES}"
    echo "[✓] Claves de acceso instaladas (hasheadas) en ${DESTINO_CLAVES}"
    echo "    Pide la tuya a quien administra el equipo; para cambiarla:"
    echo "    cd ${SCRIPT_DIR} && python3 -m devconsole.pins set --role admin|dev"
    INSTALO_CLAVES=1
fi

# 6. Claves de acceso: una por rol y distintas entre sí
echo ""
if [ "${INSTALO_CLAVES:-0}" = "1" ]; then
    echo "  (se conservan las claves hasheadas del paquete)"
elif [ -t 0 ]; then
    echo "[*] Claves de acceso del panel (Administrador y Desarrollador, DISTINTAS)."
    ( cd "${SCRIPT_DIR}" && python3 -m devconsole.pins set --role admin ) || \
        echo "  [!] Sin clave de Administrador: no podrás desplegar ni cambiar entornos."
    ( cd "${SCRIPT_DIR}" && python3 -m devconsole.pins set --role dev ) || \
        echo "  [!] Sin clave de Desarrollador: no podrás lanzar servicios."
else
    echo "[i] Instalación no interactiva: define las claves luego con"
    echo "    cd ${SCRIPT_DIR} && python3 -m devconsole.pins set --role admin"
    echo "    cd ${SCRIPT_DIR} && python3 -m devconsole.pins set --role dev"
fi
echo "  El panel arranca como Soporte/QA (sólo lectura); con tu clave entras"
echo "  como Desarrollador o Administrador."
echo "================================================================="
