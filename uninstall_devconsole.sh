#!/usr/bin/env bash
# ==============================================================================
# SISPER DevConsole — Desinstalador (servicio de usuario + lanzador)
#   ./uninstall_devconsole.sh            detiene y quita servicio y acceso directo
#   ./uninstall_devconsole.sh --purge    además borra esta carpeta y el PIN guardado
# ==============================================================================
set -uo pipefail

SERVICE_NAME="sisper-dashboard.service"
DESKTOP_NAME="sisper-devconsole.desktop"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
APPS_DIR="${HOME}/.local/share/applications"
PURGE=0
[ "${1:-}" = "--purge" ] && PURGE=1
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Desinstalando SISPER DevConsole ==="

echo "[*] Deteniendo y deshabilitando ${SERVICE_NAME}..."
systemctl --user disable --now "${SERVICE_NAME}" 2>/dev/null || echo "  (no estaba activo)"
systemctl --user reset-failed "${SERVICE_NAME}" 2>/dev/null || true

echo "[*] Quitando unidad y overrides..."
rm -f "${SYSTEMD_USER_DIR}/${SERVICE_NAME}"
rm -rf "${SYSTEMD_USER_DIR}/${SERVICE_NAME}.d"
systemctl --user daemon-reload

echo "[*] Matando cualquier proceso que siga en el puerto (del propio usuario)..."
if command -v fuser >/dev/null 2>&1; then
    for puerto in 9099 "${SISPER_PORT:-}"; do
        [ -n "${puerto}" ] || continue
        ss -ltn 2>/dev/null | grep -q ":${puerto} " && fuser -k "${puerto}/tcp" 2>/dev/null || true
    done
fi
pkill -u "${USER}" -f "$(printf '%s' "${INSTALL_DIR}")/dashboard.py" 2>/dev/null || true
sleep 1
ss -ltn 2>/dev/null | grep -q ":9099 " && echo "  [!] El 9099 sigue ocupado por OTRO usuario/proceso." || echo "  [✓] Puerto 9099 libre."

echo "[*] Quitando acceso directo del menú..."
rm -f "${APPS_DIR}/${DESKTOP_NAME}"
command -v update-desktop-database >/dev/null && update-desktop-database "${APPS_DIR}" 2>/dev/null || true

echo "[✓] Servicio y lanzador eliminados. La carpeta del proyecto sigue en:"
echo "    ${INSTALL_DIR}"

if [ "${PURGE}" = "1" ]; then
    echo "[*] Purga: se borran la carpeta del proyecto y el PIN guardado."
    echo "    ${INSTALL_DIR}"
    echo "    ${HOME}/.config/sisper-dashboard (PIN hasheado y secretos)"
    if [ "${2:-}" != "--yes" ]; then
        read -r -p "¿Confirmas el borrado? [s/N] " r
        case "${r}" in [sSyY]) ;; *) echo "  Cancelado."; exit 0 ;; esac
    fi
    cd / || exit 1
    rm -rf "${INSTALL_DIR}"
    rm -rf "${HOME}/.config/sisper-dashboard"
    echo "[✓] Purga completada."
else
    echo "    (Para borrar también la carpeta y el PIN: ./uninstall_devconsole.sh --purge)"
fi
