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

# 0. Puerto fijo 9099 (el mismo para todos). Si está ocupado, únicamente se
#    detiene el servicio systemd que este instalador administra. Nunca se mata
#    un proceso arbitrario por puerto: si el conflicto persiste, se aborta y se
#    muestra el dueño para que el operador decida qué hacer.
SISPER_PORT="${SISPER_PORT:-9099}"
liberar_servicio_propio() {
    local p="$1"
    ss -ltn 2>/dev/null | grep -q ":${p} " || return 0

    echo "[*] El puerto ${p} está ocupado; deteniendo ${SERVICE_NAME} si existe..."
    systemctl --user stop "${SERVICE_NAME}" 2>/dev/null || true

    for _ in $(seq 1 10); do
        ss -ltn 2>/dev/null | grep -q ":${p} " || return 0
        sleep 0.5
    done
    return 1
}

if ! liberar_servicio_propio "${SISPER_PORT}"; then
    echo "  [!] El puerto ${SISPER_PORT} está ocupado por un proceso que DevConsole no administra:"
    ss -ltnp 2>/dev/null | grep ":${SISPER_PORT} " | sed 's/^/      /' || true
    echo "      No se ha matado ningún proceso. Resuelve el conflicto y reintenta,"
    echo "      o instala en otro puerto: SISPER_PORT=9100 ./install_devconsole.sh"
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
# DevConsole ejecuta operaciones de desarrollo/DevOps: el listener queda sólo
# en loopback salvo que el operador decida explícitamente otra cosa.
Environment=SISPER_HOST=127.0.0.1
Environment=SISPER_PORT=${SISPER_PORT}
# En instalación gestionada se exige el token local efímero. El browser recibe
# la cookie HttpOnly al cargar la UI; clientes API usan el token 0600 del runtime.
Environment=SISPER_LOCAL_TOKEN_REQUIRED=1
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

# 5.b Credenciales de producto: Viewer/QA siempre está disponible. Developer y
#     Admin se habilitan con las claves cuyo hash viene en el paquete. El
#     instalador NO genera claves nuevas ni cambia las ediciones del producto.
DESTINO_CLAVES="${HOME}/.config/sisper-dashboard/secrets.json"
if [ ! -f "${DESTINO_CLAVES}" ] && [ -f "${SCRIPT_DIR}/config/pins.json" ]; then
    mkdir -p "$(dirname "${DESTINO_CLAVES}")"
    cp "${SCRIPT_DIR}/config/pins.json" "${DESTINO_CLAVES}"
    chmod 600 "${DESTINO_CLAVES}"
    echo "[✓] Credenciales de producto instaladas (sólo hashes) en ${DESTINO_CLAVES}"
elif [ -f "${DESTINO_CLAVES}" ]; then
    echo "[i] Se conserva el almacén de credenciales existente: ${DESTINO_CLAVES}"
else
    echo "[!] El paquete no contiene config/pins.json."
    echo "    Viewer/QA seguirá disponible; Developer y Admin permanecerán bloqueados"
    echo "    hasta instalar explícitamente sus credenciales."
fi

# 6. Modelo de acceso
echo ""
echo "  Nivel predeterminado: Viewer/QA (sin clave, sólo lectura)."
echo "  Developer: requiere clave de producto Developer."
echo "  Admin: requiere clave de producto Admin."
echo "  El instalador no solicita ni fabrica claves nuevas."
echo "================================================================="
