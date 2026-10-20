#!/usr/bin/env bash
# ==============================================================================
# SISPER DevConsole — Desinstalador (servicio de usuario + lanzador)
#   ./uninstall_devconsole.sh            detiene y quita servicio y acceso directo
#   ./uninstall_devconsole.sh --purge    además borra carpeta y credenciales locales
# ==============================================================================
set -uo pipefail

SERVICE_NAME="sisper-dashboard.service"
DESKTOP_NAME="sisper-devconsole.desktop"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
APPS_DIR="${HOME}/.local/share/applications"
PURGE=0
[ "${1:-}" = "--purge" ] && PURGE=1
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SISPER_PORT="${SISPER_PORT:-9099}"

echo "=== Desinstalando SISPER DevConsole ==="

echo "[*] Deteniendo y deshabilitando ${SERVICE_NAME}..."
systemctl --user disable --now "${SERVICE_NAME}" 2>/dev/null || echo "  (no estaba activo)"
systemctl --user reset-failed "${SERVICE_NAME}" 2>/dev/null || true

echo "[*] Quitando unidad y overrides..."
rm -f "${SYSTEMD_USER_DIR}/${SERVICE_NAME}"
rm -rf "${SYSTEMD_USER_DIR}/${SERVICE_NAME}.d"
systemctl --user daemon-reload

# No se usa fuser/pkill. El servicio systemd es la identidad autoritativa del
# proceso instalado. Si el puerto permanece ocupado después de detener la unidad,
# asumir que pertenece a otro proceso evita matar trabajo ajeno por accidente.
if ss -ltn 2>/dev/null | grep -q ":${SISPER_PORT} "; then
    echo "  [!] El puerto ${SISPER_PORT} sigue ocupado después de detener ${SERVICE_NAME}."
    echo "      No se ha matado ningún proceso externo. Propietario observado:"
    ss -ltnp 2>/dev/null | grep ":${SISPER_PORT} " | sed 's/^/      /' || true
else
    echo "  [✓] Puerto ${SISPER_PORT} libre."
fi

echo "[*] Quitando acceso directo del menú..."
rm -f "${APPS_DIR}/${DESKTOP_NAME}"
command -v update-desktop-database >/dev/null && update-desktop-database "${APPS_DIR}" 2>/dev/null || true

echo "[✓] Servicio y lanzador eliminados. La carpeta del proyecto sigue en:"
echo "    ${INSTALL_DIR}"

if [ "${PURGE}" = "1" ]; then
    echo "[*] Purga: se borran la carpeta del proyecto y las credenciales/configuración locales."
    echo "    ${INSTALL_DIR}"
    echo "    ${HOME}/.config/sisper-dashboard"
    if [ "${2:-}" != "--yes" ]; then
        read -r -p "¿Confirmas el borrado? [s/N] " r
        case "${r}" in [sSyY]) ;; *) echo "  Cancelado."; exit 0 ;; esac
    fi
    cd / || exit 1
    rm -rf "${INSTALL_DIR}"
    rm -rf "${HOME}/.config/sisper-dashboard"
    echo "[✓] Purga completada."
else
    echo "    (Para borrar también carpeta y configuración: ./uninstall_devconsole.sh --purge)"
fi
