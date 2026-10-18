#!/usr/bin/env bash
# ==============================================================================
# Script: start_tilix.sh
# Lanza automáticamente los microservicios y microfrontends en paneles de Tilix
# ==============================================================================
set -euo pipefail

# Auto-detect graphical display and dbus if called from daemon or service
export PATH="$HOME/.local/bin:$HOME/.bun/bin:$HOME/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"

if [ -z "${WAYLAND_DISPLAY:-}" ] && [ -S "/run/user/$(id -u)/wayland-0" ]; then
    export WAYLAND_DISPLAY="wayland-0"
fi
if [ -z "${DISPLAY:-}" ]; then
    export DISPLAY=":0"
fi
if [ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ] && [ -S "/run/user/$(id -u)/bus" ]; then
    export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"
fi

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SESSION_B1="$BASE_DIR/backend/backend-terminal-auto.json"
SESSION_B2="$BASE_DIR/backend/backend-terminal-2-auto.json"
SESSION_FRONT="$BASE_DIR/frontend_terminal_auto.json"
SESSION_SINGLE="$BASE_DIR/sisper_all_single_session_auto.json"

normalize_session() {
    local src="$1"
    local dst="/tmp/tilix_norm_${USER}_$(basename "$src")"
    if [ -f "$src" ]; then
        sed -E "s|\"[^\"]*/(backend/[^\"]*)\"|\"$BASE_DIR/\1\"|g; s|\"[^\"]*/(frontend/[^\"]*)\"|\"$BASE_DIR/\1\"|g" "$src" > "$dst"
        echo "$dst"
    else
        echo "$src"
    fi
}

PORTS_BACKEND=(8000 8001 8002 8003 8004 8006 8007 8008 8009 8010 8012 8016 8018 8019 8020 8021 8100)
PORTS_FRONTEND=(3000 3001 3002 3003 3004 3006 3007 3008 3009 3010)

check_status() {
    echo "=========================================================="
    echo "              ESTADO DE SERVICIOS LOCALES                 "
    echo "=========================================================="
    echo "--- BACKEND (Django / Daphne) ---"
    for p in "${PORTS_BACKEND[@]}"; do
        if ss -tulpn 2>/dev/null | grep -q ":$p "; then
            printf "  [🟢 ACTIVO  ] Puerto %-5s\n" "$p"
        else
            printf "  [🔴 APAGADO ] Puerto %-5s\n" "$p"
        fi
    done

    echo ""
    echo "--- FRONTEND (Webpack Dev Server) ---"
    for p in "${PORTS_FRONTEND[@]}"; do
        if ss -tulpn 2>/dev/null | grep -q ":$p "; then
            printf "  [🟢 ACTIVO  ] Puerto %-5s\n" "$p"
        else
            printf "  [🔴 APAGADO ] Puerto %-5s\n" "$p"
        fi
    done
    echo "=========================================================="
}

stop_services() {
    echo "[!] Deteniendo microservicios de desarrollo (Backend y Frontend)..."
    
    # 1. Matar procesos Django / Daphne y Webpack / Node por nombre de comando
    pkill -f "manage.py runserver" 2>/dev/null || true
    pkill -f "webpack serve" 2>/dev/null || true
    pkill -f "concurrently" 2>/dev/null || true
    pkill -f "node.*webpack" 2>/dev/null || true
    pkill -f "npm.*start" 2>/dev/null || true

    # 2. Liberar puertos Backend y Frontend por socket (fuser) para garantizar cierre de procesos en ventanas hijas
    ALL_PORTS=("${PORTS_BACKEND[@]}" "${PORTS_FRONTEND[@]}")
    for p in "${ALL_PORTS[@]}"; do
        fuser -k -n tcp "$p" 2>/dev/null || true
    done

    sleep 1
    echo "[✓] Todos los servidores de desarrollo (Backend y Frontend) detenidos correctamente."
}

stop_and_close() {
    echo "[!] Deteniendo todos los servicios y cerrando ventanas de Tilix..."
    touch /tmp/sisper_close_all 2>/dev/null || true
    stop_services
    sleep 0.5
    pkill -f "tilix" 2>/dev/null || true
    rm -f /tmp/sisper_close_all 2>/dev/null || true
    echo "[✓] Todos los servicios detenidos y ventanas de Tilix cerradas."
}

launch_b1() {
    echo "[+] Abriendo Backend 1 en Tilix (12 microservicios)..."
    local s; s="$(normalize_session "$SESSION_B1")"
    tilix --session="$s" >/dev/null 2>&1 &
}

launch_b2() {
    echo "[+] Abriendo Backend 2 en Tilix (5 microservicios)..."
    local s; s="$(normalize_session "$SESSION_B2")"
    tilix --session="$s" >/dev/null 2>&1 &
}

launch_front() {
    echo "[+] Abriendo Frontend en Tilix (8 microfrontends de frontend_terminal.json)..."
    local s; s="$(normalize_session "$SESSION_FRONT")"
    tilix --session="$s" >/dev/null 2>&1 &
}

launch_single_tab() {
    local env_name="${1:-${SISPER_ENV:-develop}}"
    export SISPER_ENV="$env_name"
    echo "[+] Abriendo TODOS los servicios en 1 SOLA VENTANA (Entorno: $env_name)..."
    local s; s="$(normalize_session "$SESSION_SINGLE")"
    tilix --session="$s" >/dev/null 2>&1 &
    echo "[✓] Ventana con 1 pestaña lanzada para entorno $env_name."
}

launch_tabs() {
    local env_name="${1:-${SISPER_ENV:-develop}}"
    export SISPER_ENV="$env_name"
    echo "[+] Abriendo TODOS los servicios en 1 SOLA VENTANA (3 pestañas, Entorno: $env_name)..."
    local s1; s1="$(normalize_session "$SESSION_B1")"
    local s2; s2="$(normalize_session "$SESSION_B2")"
    local s3; s3="$(normalize_session "$SESSION_FRONT")"
    tilix -s "$s1" -s "$s2" -s "$s3" >/dev/null 2>&1 &
    echo "[✓] Ventana unificada de Tilix lanzada con 3 pestañas."
}

launch_all() {
    launch_single_tab "${1:-develop}"
}

launch_single() {
    local svc="$1"
    local port="${2:-}"

    if [ -d "$BASE_DIR/backend/$svc" ]; then
        echo "[+] Lanzando $svc (backend :$port) en Tilix..."
        tilix -w "$BASE_DIR/backend/$svc" -p "c8e01000-0000-0000-0000-000000000001" -t "$svc ($port)" >/dev/null 2>&1 &
    elif [ -d "$BASE_DIR/frontend/$svc" ]; then
        echo "[+] Lanzando $svc (frontend :$port) en Tilix..."
        tilix -w "$BASE_DIR/frontend/$svc" -p "c8e01000-0000-0000-0000-000000000001" -t "$svc ($port)" >/dev/null 2>&1 &
    else
        echo "[-] Servicio no encontrado: $svc"
    fi
}

stop_single_port() {
    local port="$1"
    echo "[!] Liberando puerto $port..."
    fuser -k -n tcp "$port" 2>/dev/null || true
    sleep 0.5
    echo "[✓] Puerto $port detenido."
}

restart_single() {
    local svc="$1"
    local port="${2:-}"
    echo "[!] Reiniciando $svc (puerto $port)..."
    touch "/tmp/sisper_restart_${svc}"
    fuser -k -n tcp "$port" 2>/dev/null || true
    sleep 0.5
    echo "[✓] Señal de reinicio enviada. Si la consola Tilix está abierta, se refrescará sola."
}

restart_all() {
    echo "[!] Reiniciando todos los servicios en las consolas abiertas..."
    touch /tmp/sisper_restart_all
    stop_services
    (sleep 4 && rm -f /tmp/sisper_restart_all 2>/dev/null || true) &
    echo "[✓] Servicios reiniciados. Las consolas Tilix activas se refrescan automáticamente."
}

restart_backends() {
    echo "[!] Reiniciando todos los microservicios BACKEND (17)..."
    touch /tmp/sisper_restart_backends
    pkill -f "manage.py runserver" 2>/dev/null || true
    for p in "${PORTS_BACKEND[@]}"; do
        fuser -k -n tcp "$p" 2>/dev/null || true
    done
    (sleep 4 && rm -f /tmp/sisper_restart_backends 2>/dev/null || true) &
    echo "[✓] Backends reiniciados. Las consolas se refrescan automáticamente."
}

restart_frontends() {
    echo "[!] Reiniciando todos los microfrontends FRONTEND (10)..."
    touch /tmp/sisper_restart_frontends
    pkill -f "webpack serve" 2>/dev/null || true
    pkill -f "concurrently" 2>/dev/null || true
    pkill -f "node.*webpack" 2>/dev/null || true
    pkill -f "npm.*start" 2>/dev/null || true
    for p in "${PORTS_FRONTEND[@]}"; do
        fuser -k -n tcp "$p" 2>/dev/null || true
    done
    (sleep 4 && rm -f /tmp/sisper_restart_frontends 2>/dev/null || true) &
    echo "[✓] Frontends reiniciados. Las consolas se refrescan automáticamente."
}

show_menu() {
    echo "=========================================================="
    echo "          SISPER - LANZADOR AUTOMÁTICO TILIX              "
    echo "=========================================================="
    echo " 1) Abrir TODO en 1 Sola Pestaña (25 Paneles)"
    echo " 2) Abrir TODO en 3 Pestañas (Backend 1, 2 y Frontend)"
    echo " 3) Backend 1   (Puertos 8000-8016)"
    echo " 4) Backend 2   (Puertos 8018-8100)"
    echo " 5) Frontend    (frontend_terminal.json)"
    echo " 6) Reiniciar consolas abiertas (sin abrir ventanas nuevas)"
    echo " 7) Estado      (Ver puertos activos / apagados)"
    echo " 8) Detener Todo     (Parar servidores, mantener consolas abiertas)"
    echo " 9) Detener y Cerrar (Parar servidores y cerrar todas las ventanas Tilix)"
    echo " 10) Salir"
    echo "=========================================================="
    read -rp "Selecciona una opción [1-10]: " opt
    case "$opt" in
        1) launch_single_tab ;;
        2) launch_tabs ;;
        3) launch_b1 ;;
        4) launch_b2 ;;
        5) launch_front ;;
        6) restart_all ;;
        7) check_status ;;
        8) stop_services ;;
        9) stop_and_close ;;
        10) exit 0 ;;
        *) echo "Opción no válida." ;;
    esac
}

ACTION="${1:-}"

case "$ACTION" in
    "develop"|"dev")
        launch_single_tab "develop"
        ;;
    "test"|"qa")
        launch_single_tab "test"
        ;;
    "main"|"prod")
        launch_single_tab "main"
        ;;
    "single"|"all"|"-a"|"--all")
        launch_single_tab "${2:-develop}"
        ;;
    "tabs")
        launch_tabs "${2:-develop}"
        ;;
    "b1"|"backend1")
        launch_b1
        ;;
    "b2"|"backend2")
        launch_b2
        ;;
    "front"|"frontend")
        launch_front
        ;;
    "start")
        launch_single "${2:-}" "${3:-}"
        ;;
    "stop-port")
        stop_single_port "${2:-}"
        ;;
    "restart-single")
        restart_single "${2:-}" "${3:-}"
        ;;
    "restart-backends"|"restart-backend"|"reload-backends"|"reload-backend")
        restart_backends
        ;;
    "restart-frontends"|"restart-frontend"|"reload-frontends"|"reload-frontend")
        restart_frontends
        ;;
    "restart"|"reload")
        restart_all
        ;;
    "status"|"check")
        check_status
        ;;
    "stop-close"|"close"|"kill-all")
        stop_and_close
        ;;
    "stop"|"kill")
        stop_services
        ;;
    "web"|"dashboard")
        python3 "$BASE_DIR/dashboard.py"
        ;;
    "")
        show_menu
        ;;
    *)
        echo "Uso: $0 [single | tabs | b1 | b2 | front | restart | start <svc> <port> | stop-port <port> | status | stop | stop-close | web]"
        exit 1
        ;;
esac
