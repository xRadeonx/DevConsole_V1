#!/usr/bin/env bash
# ==============================================================================
# Tilix Runner automático para SISPER
# Se ejecuta en cada panel de Tilix cuando usa el perfil SISPER-Auto
# ==============================================================================

# Asegurar PATH completo con binarios de usuario (~/.local/bin para pipenv, bun, etc.)
export PATH="$HOME/.local/bin:$HOME/.bun/bin:$HOME/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# Integración VTE para Tilix
if [ -f /etc/profile.d/vte.sh ]; then
    source /etc/profile.d/vte.sh 2>/dev/null || true
fi

if command -v pipenv &>/dev/null; then
    PIPENV_BIN="pipenv"
elif [ -x "$HOME/.local/bin/pipenv" ]; then
    PIPENV_BIN="$HOME/.local/bin/pipenv"
elif command -v python3 &>/dev/null && python3 -m pipenv --version &>/dev/null; then
    PIPENV_BIN="python3 -m pipenv"
else
    PIPENV_BIN="pipenv"
fi

SVC="$(basename "$PWD")"

case "$SVC" in
    ms_sisper_sesion) PORT=8000 ;;
    ms_sisper_adm_usuario) PORT=8001 ;;
    ms_sisper_identificacion) PORT=8002 ;;
    ms_sisper_bitacora) PORT=8003 ;;
    ms_sisper_solicitudes) PORT=8004 ;;
    ms_sisper_contratos) PORT=8006 ;;
    ms_sisper_promocion) PORT=8007 ;;
    ms_sisper_destinaciones) PORT=8008 ;;
    ms_sisper_beneficios) PORT=8009 ;;
    ms_sisper_retiros) PORT=8010 ;;
    ms_sisper_form_acad) PORT=8012 ;;
    ms_sisper_documentos) PORT=8016 ;;
    ms_sisper_perfiles_riesgo) PORT=8018 ;;
    ms_sisper_promocion_desempeno) PORT=8019 ;;
    ms_sisper_promocion_proyec) PORT=8020 ;;
    ms_sisper_promocion_otros) PORT=8021 ;;
    ms_sisper_asistente) PORT=8100 ;;
    ms_sisper_firmador) PORT=8022 ;;
    ms_sisper_tto_datos_privado) PORT=8040 ;;
    mf_sisper_sesion) PORT=3000 ;;
    mf_sisper_adm_usuario) PORT=3001 ;;
    mf_sisper_identificacion) PORT=3002 ;;
    mf_sisper_bitacora) PORT=3003 ;;
    mf_sisper_solicitudes) PORT=3004 ;;
    mf_sisper_contratos) PORT=3006 ;;
    mf_sisper_documentos) PORT=3007 ;;
    mf_sisper_perfiles_de_riesgo) PORT=3008 ;;
    mf_sisper_carrera_correct_comp) PORT=3009 ;;
    mf_sisper_promocion_otros) PORT=3010 ;;
    *) PORT="" ;;
esac

# Fallback dinámico para microservicios nuevos o descubiertos dinámicamente
if [ -z "$PORT" ]; then
    PORT="$(python3 -c "from devconsole.config import SERVICES_BACKEND, SERVICES_FRONTEND; all_s = SERVICES_BACKEND + SERVICES_FRONTEND; print(next((s['port'] for s in all_s if s['name'] == '$SVC'), ''))" 2>/dev/null || echo "")"
fi

ENV_TAG="${SISPER_ENV:-}"
if [ -n "$ENV_TAG" ]; then
    ENV_UPPER="$(echo "$ENV_TAG" | tr '[:lower:]' '[:upper:]')"
    if [ -n "$PORT" ]; then
        TITLE="[$ENV_UPPER] ${SVC} (:${PORT})"
    else
        TITLE="[$ENV_UPPER] ${SVC}"
    fi
else
    if [ -n "$PORT" ]; then
        TITLE="${SVC} (:${PORT})"
    else
        TITLE="${SVC}"
    fi
fi

set_terminal_title() {
    # Secuencias OSC para actualizar el título del panel en Tilix / VTE
    printf '\033]0;%s\007' "$TITLE"
    printf '\033]1;%s\007' "$TITLE"
    printf '\033]2;%s\007' "$TITLE"
    printf '\033]0;%s\033\\' "$TITLE"
    printf '\033]2;%s\033\\' "$TITLE"
}

set_terminal_title
export PROMPT_COMMAND="set_terminal_title 2>/dev/null || true"

TRIGGER_SVC="/tmp/sisper_restart_${SVC}"
TRIGGER_ALL="/tmp/sisper_restart_all"
TRIGGER_BACKENDS="/tmp/sisper_restart_backends"
TRIGGER_FRONTENDS="/tmp/sisper_restart_frontends"
TRIGGER_CLOSE="/tmp/sisper_close_all"

# Escalonamiento inicial inteligente para evitar congelamiento de CPU y disco al abrir múltiples terminales
if [ -n "$PORT" ] && [ -z "${NO_STAGGER:-}" ]; then
    if [[ "$SVC" =~ ^ms_sisper_ ]]; then
        OFFSET=$(( (PORT - 8000) % 6 ))
        if [ "$OFFSET" -gt 0 ]; then
            WAIT_SEC=$(( OFFSET * 3 / 10 ))
            echo "=========================================================="
            echo " 🚀 SISPER BACKEND: $SVC ${ENV_UPPER:+[$ENV_UPPER]}"
            echo " 🌐 Puerto: $PORT | Rama Git: $(git branch --show-current 2>/dev/null || echo 'N/A')"
            echo " ⏳ Inicio escalonado: esperando ${WAIT_SEC}s para balancear CPU..."
            echo "=========================================================="
            sleep "$WAIT_SEC"
        fi
    elif [[ "$SVC" =~ ^mf_sisper_ ]]; then
        OFFSET=$(( PORT - 3000 ))
        if [ "$OFFSET" -gt 0 ]; then
            WAIT_SEC=$(( OFFSET * 14 / 10 ))
            echo "=========================================================="
            echo " 🎨 SISPER FRONTEND: $SVC ${ENV_UPPER:+[$ENV_UPPER]}"
            echo " 🌐 Puerto: $PORT | Rama Git: $(git branch --show-current 2>/dev/null || echo 'N/A')"
            echo " ⏳ Inicio escalonado: esperando ${WAIT_SEC}s para balancear Webpack..."
            echo "=========================================================="
            sleep "$WAIT_SEC"
        fi
    fi
fi

if [ -n "$PORT" ] && [[ "$SVC" =~ ^ms_sisper_ ]]; then
    while true; do
        set_terminal_title
        CURR_BRANCH="$(git branch --show-current 2>/dev/null || echo "N/A")"
        echo "=========================================================="
        echo " 🚀 SISPER BACKEND: $SVC ${ENV_UPPER:+[$ENV_UPPER]}"
        echo " 🌐 Puerto: $PORT | Rama Git: $CURR_BRANCH"
        echo "=========================================================="

        # Limpiar cualquier proceso zombi que ocupe el puerto antes de iniciar
        if [ -n "$PORT" ]; then
            fuser -k -n tcp "$PORT" 2>/dev/null || true
            sleep 0.2
        fi

        # Chequeo preventivo de dependencias Pipenv (silencioso sin trabar terminal)
        if ! "$PIPENV_BIN" run python -c "import dotenv, django" 2>/dev/null; then
            echo ""
            echo "=========================================================="
            echo " ⚠️ DEPENDENCIAS FALTANTES EN PIPENV ($SVC)"
            echo " Falta dotenv / django en el entorno virtual."
            echo "=========================================================="
            read -t 6 -rp "Instalar ahora? [i=Instalar dependencias / ENTER=Continuar]: " inst_opt || inst_opt=""
            if [ "$inst_opt" = "i" ] || [ "$inst_opt" = "install" ]; then
                echo "[📦] Ejecutando: $PIPENV_BIN install..."
                "$PIPENV_BIN" install || "$PIPENV_BIN" run pip install -r requirements.txt || true
            fi
        fi

        T_START=$(date +%s)
        "$PIPENV_BIN" run python manage.py runserver 0.0.0.0:$PORT || true
        EXIT_CODE=$?
        T_END=$(date +%s)
        DURATION=$(( T_END - T_START ))

        # Si fue solicitado cierre total, salir inmediatamente
        if [ -f "$TRIGGER_CLOSE" ]; then
            exit 0
        fi

        # Si fue solicitado reinicio desde dashboard, reiniciar de inmediato en la misma consola
        if [ -f "$TRIGGER_SVC" ] || [ -f "$TRIGGER_ALL" ] || [ -f "$TRIGGER_BACKENDS" ]; then
            rm -f "$TRIGGER_SVC" 2>/dev/null || true
            echo ""
            echo "[🔄] Señal de reinicio recibida desde DevConsole. Recargando servidor..."
            sleep 0.8
            clear
            continue
        fi

        echo ""
        echo "=========================================================="
        if [ "$DURATION" -lt 4 ]; then
            echo " 🛑 [MODO STANDBY] El microservicio falló inmediatamente al arrancar."
            echo "    * Código de salida: $EXIT_CODE | Duración activa: ${DURATION}s"
            echo "    * La consola queda en PAUSA a la espera de tu decisión para evitar bucles o procesos colgados."
            echo "----------------------------------------------------------"
            echo " Acciones disponibles:"
            echo "   [r] Reintentar arranque"
            echo "   [s] Entrar a Pipenv Shell interactivo para depurar"
            echo "   [i] Instalar / Reinstalar dependencias (pipenv install)"
            echo "   [q] Salir a terminal bash libre"
            echo "   (O pulsa '🔄 Reiniciar' en el DevConsole una vez corregido)"
        else
            echo " [!] Servidor detenido (código: $EXIT_CODE, tiempo activo: ${DURATION}s)."
            echo "----------------------------------------------------------"
            echo "   * Presiona [ENTER] o 'r' para reiniciar"
            echo "   * Escribe 's' o 'shell' para entrar a Pipenv shell"
            echo "   * Escribe 'i' para instalar dependencias"
            echo "   * Escribe 'q' para salir a bash libre"
        fi
        echo "=========================================================="

        printf "\nOpción [r=reintentar / s=shell / i=instalar / q=bash]: "

        # Bucle de espera reactivo en Standby
        while true; do
            if [ -f "$TRIGGER_CLOSE" ]; then
                exit 0
            fi
            if [ -f "$TRIGGER_SVC" ] || [ -f "$TRIGGER_ALL" ] || [ -f "$TRIGGER_BACKENDS" ]; then
                rm -f "$TRIGGER_SVC" 2>/dev/null || true
                echo ""
                echo "[🔄] Señal de reinicio recibida desde DevConsole. Recargando..."
                sleep 0.5
                clear
                break
            fi

            # Espera sin flooding: timeout 2s para revisar archivos trigger
            if read -t 2 -r opt 2>/dev/null; then
                opt="$(echo "$opt" | tr '[:upper:]' '[:lower:]' | xargs)"
                if [ "$opt" = "q" ] || [ "$opt" = "quit" ] || [ "$opt" = "exit" ]; then
                    exec bash
                elif [ "$opt" = "s" ] || [ "$opt" = "shell" ]; then
                    echo "[💻] Iniciando Pipenv Shell..."
                    "$PIPENV_BIN" shell || exec bash
                    printf "\nOpción [r=reintentar / s=shell / i=instalar / q=bash]: "
                elif [ "$opt" = "i" ] || [ "$opt" = "install" ]; then
                    echo "[📦] Ejecutando: $PIPENV_BIN install..."
                    "$PIPENV_BIN" install || "$PIPENV_BIN" run pip install -r requirements.txt || true
                    printf "\nOpción [r=reintentar / s=shell / i=instalar / q=bash]: "
                elif [ "$opt" = "r" ] || [ "$opt" = "retry" ] || [ "$opt" = "restart" ]; then
                    echo "[🔄] Reintentando arranque..."
                    clear
                    break
                elif [ -z "$opt" ]; then
                    if [ "$DURATION" -ge 4 ]; then
                        clear
                        break
                    else
                        echo " [!] Terminal en STANDBY por falla rápida. Escribe 'r' para reintentar o 's' para shell."
                        printf "Opción [r=reintentar / s=shell / i=instalar / q=bash]: "
                    fi
                else
                    printf "Opción '%s' no válida. Escribe r, s, i o q: " "$opt"
                fi
            else
                READ_ERR=$?
                if [ "$READ_ERR" -eq 1 ]; then
                    # EOF en stdin (no interactivo o cerrado) -> dormir 2s para evitar 100% CPU
                    sleep 2
                fi
            fi
        done
    done
    exec bash
elif [[ "$SVC" =~ ^mf_sisper_ ]]; then
    while true; do
        set_terminal_title
        CURR_BRANCH="$(git branch --show-current 2>/dev/null || echo "N/A")"
        echo "=========================================================="
        echo " 🎨 SISPER FRONTEND: $SVC ${ENV_UPPER:+[$ENV_UPPER]}"
        echo " 🌐 Puerto: $PORT | Rama Git: $CURR_BRANCH"
        echo "=========================================================="

        if [ -n "$PORT" ]; then
            fuser -k -n tcp "$PORT" 2>/dev/null || true
            sleep 0.2
        fi

        T_START=$(date +%s)
        npm start || true
        EXIT_CODE=$?
        T_END=$(date +%s)
        DURATION=$(( T_END - T_START ))

        if [ -f "$TRIGGER_CLOSE" ]; then
            exit 0
        fi

        if [ -f "$TRIGGER_SVC" ] || [ -f "$TRIGGER_ALL" ] || [ -f "$TRIGGER_FRONTENDS" ]; then
            rm -f "$TRIGGER_SVC" 2>/dev/null || true
            echo ""
            echo "[🔄] Señal de reinicio recibida desde DevConsole. Recargando frontend..."
            sleep 0.8
            clear
            continue
        fi

        echo ""
        echo "=========================================================="
        if [ "$DURATION" -lt 4 ]; then
            echo " 🛑 [MODO STANDBY] El frontend falló inmediatamente al arrancar."
            echo "    * Código de salida: $EXIT_CODE | Duración activa: ${DURATION}s"
            echo "    * La consola queda en PAUSA a la espera de tu decisión para evitar bucles o procesos colgados."
            echo "----------------------------------------------------------"
            echo " Acciones disponibles:"
            echo "   [r] Reintentar arranque (npm start)"
            echo "   [i] Instalar paquetes (npm install)"
            echo "   [q] Salir a terminal bash libre"
            echo "   (O pulsa '🔄 Reiniciar' en el DevConsole una vez corregido)"
        else
            echo " [!] Frontend detenido (código: $EXIT_CODE, tiempo activo: ${DURATION}s)."
            echo "----------------------------------------------------------"
            echo "   * Presiona [ENTER] o 'r' para reiniciar"
            echo "   * Escribe 'i' para npm install"
            echo "   * Escribe 'q' para salir a bash libre"
        fi
        echo "=========================================================="

        printf "\nOpción [r=reintentar / i=instalar / q=bash]: "

        while true; do
            if [ -f "$TRIGGER_CLOSE" ]; then
                exit 0
            fi
            if [ -f "$TRIGGER_SVC" ] || [ -f "$TRIGGER_ALL" ] || [ -f "$TRIGGER_FRONTENDS" ]; then
                rm -f "$TRIGGER_SVC" 2>/dev/null || true
                echo ""
                echo "[🔄] Señal de reinicio recibida desde DevConsole. Recargando..."
                sleep 0.5
                clear
                break
            fi

            if read -t 2 -r opt 2>/dev/null; then
                opt="$(echo "$opt" | tr '[:upper:]' '[:lower:]' | xargs)"
                if [ "$opt" = "q" ] || [ "$opt" = "quit" ] || [ "$opt" = "exit" ]; then
                    exec bash
                elif [ "$opt" = "i" ] || [ "$opt" = "install" ]; then
                    echo "[📦] Ejecutando: npm install..."
                    npm install || true
                    printf "\nOpción [r=reintentar / i=instalar / q=bash]: "
                elif [ "$opt" = "r" ] || [ "$opt" = "retry" ] || [ "$opt" = "restart" ]; then
                    echo "[🔄] Reintentando arranque de frontend..."
                    clear
                    break
                elif [ -z "$opt" ]; then
                    if [ "$DURATION" -ge 4 ]; then
                        clear
                        break
                    else
                        echo " [!] Terminal en STANDBY por falla rápida. Escribe 'r' para reintentar o 'i' para npm install."
                        printf "Opción [r=reintentar / i=instalar / q=bash]: "
                    fi
                else
                    printf "Opción '%s' no válida. Escribe r, i o q: " "$opt"
                fi
            else
                READ_ERR=$?
                if [ "$READ_ERR" -eq 1 ]; then
                    sleep 2
                fi
            fi
        done
    done
    exec bash
else
    exec bash
fi
