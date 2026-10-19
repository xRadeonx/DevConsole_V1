#!/usr/bin/env bash
# DevConsole V1.1 safe wrapper for the existing, feature-rich Tilix runner.
#
# tmux already classifies ownership before creating/respawning a session.  The
# legacy runner nevertheless calls `fuser -k` immediately before launch.  This
# wrapper keeps every other legacy runner capability but makes destructive
# fuser invocations impossible on the tmux-owned path.
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

fuser() {
    local arg
    for arg in "$@"; do
        if [ "$arg" = "-k" ] || [ "$arg" = "--kill" ]; then
            echo "[V1.1 SAFETY] fuser kill bloqueado: tmux/runtime decide ownership; no se mata por puerto." >&2
            return 1
        fi
    done
    command fuser "$@"
}
export -f fuser
export SISPER_SAFE_RUNTIME=1

# Source rather than exec so the protected fuser function remains in scope.
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/tilix_runner.sh"
