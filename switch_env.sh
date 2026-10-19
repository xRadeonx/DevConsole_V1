#!/usr/bin/env bash
# ==============================================================================
# DevConsole V1.1 — compatibilidad del comando switch_env.sh
#
# La interfaz CLI histórica se conserva para la UI V1 y scripts existentes,
# pero LOCAL/INTRANET ya no parchean código Python como efecto lateral. Los
# valores de dominio viven en config/environment_profiles*.json y el motor
# genérico está en devconsole.services.env_profile_service.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"
exec python3 -m devconsole.services.env_profile_service "$@"
