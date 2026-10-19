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

# Nunca se mata un proceso únicamente por ocupar un puerto. Si quedó una
# instancia exacta de este checkout después de detener systemd, se termina sólo
# esa instancia identificada por su ruta completa; cualquier otro listener se
# reporta para que el operador decida.
echo "[*] Cerrando únicamente procesos de este checkout, si quedaran activos..."
while IFS= read -r pid; do
    [ -n "${pid}" ] || continue
    cmdline="$(tr '\0' ' ' < "/proc/${pid}/cmdline" 2>/dev/null || true)"
    case "${cmdline}" in
        *"${INSTALL_DIR}/dashboard.py"*)
            kill "${pid}" 2>/dev/null || true
            ;;
    esac
done < <(pgrep -u "${USER}" -f "${INSTALL_DIR}/dashboard.py" 2>/dev/null || true)

sleep 1
for puerto in 9099 "${SISPER_PORT:-}"; do
    [ -n "${puerto}" ] || continue
    if ss -ltn 2>/dev/null | grep -q ":${puerto} "; then
        echo "  [i] Puerto ${puerto} sigue ocupado por otro proceso; no se modifica."
    else
        echo "  [✓] Puerto ${puerto} libre."
    fi
done

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
