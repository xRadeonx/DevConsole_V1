#!/usr/bin/env bash
# =============================================================================
# venvs.sh — salud y reparación de los virtualenvs de los microservicios
#
# POR QUÉ EXISTE
# Los venvs de este entorno se crearon con el intérprete **sin versión**
# (`bin/python -> /usr/bin/python`).  El 30-sep el sistema pasó `/usr/bin/python`
# a 3.14: desde entonces esos venvs ejecutan 3.14 mientras sus paquetes siguen
# en `lib/python3.11/site-packages/`, así que `import dotenv` falla, el servicio
# muere al arrancar y el lanzador se queda en el prompt STANDBY.  Además, cada
# reescritura de `.env` (modo entorno) reinicia el servicio vía ENV-WATCHER, con
# lo que el fallo se propaga a todo el muro de consolas.
#
# QUÉ HACE
#   check     (por omisión) informe de salud. Sale 1 si algo está desalineado.
#   list      tabla: intérprete declarado en pyvenv.cfg, intérprete real y enlace.
#   fix       repara `bin/python` apuntando al intérprete de su propio
#             pyvenv.cfg.  Offline, idempotente y sin tocar paquetes.
#   rebuild   reconstruye el venv con `pipenv --python <intérprete versionado>`,
#             que es la forma correcta de crearlo.  REQUIERE RED (PyPI) y se
#             limita a los servicios que nombres.
#
# No toca código de la aplicación, ni `.env`, ni bases de datos.
# =============================================================================
set -uo pipefail

WORKON_HOME="${WORKON_HOME:-$HOME/.local/share/virtualenvs}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

rojo()  { printf '\033[31m%s\033[0m\n' "$*"; }
verde() { printf '\033[32m%s\033[0m\n' "$*"; }
amar()  { printf '\033[33m%s\033[0m\n' "$*"; }

# Intérprete con el que se creó el venv, según su propio pyvenv.cfg.
base_de() {
  sed -n 's/^base-executable *= *//p' "$1/pyvenv.cfg" 2>/dev/null | tr -d ' '
}

# Versión real que ejecuta el venv (X.Y).
real_de() {
  "$1/bin/python" -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null || echo "?"
}

# Intérprete que pide el Pipfile del servicio (X.Y).
pipfile_de() {
  grep -m1 'python_version' "$1/Pipfile" 2>/dev/null | grep -oE '[0-9]+\.[0-9]+'
}

# Recorre los venvs y llama a la función indicada con (venv, base, real, link).
recorrer() {
  local fn="$1"; shift
  local v base real link
  for v in "$WORKON_HOME"/*/; do
    [ -d "$v" ] || continue
    [ -L "$v/bin/python" ] || continue
    base="$(base_de "$v")"
    real="$(real_de "$v")"
    link="$(readlink "$v/bin/python")"
    "$fn" "${v%/}" "$base" "$real" "$link"
  done
}

# --------------------------------------------------------------------------- #
# subcomandos
# --------------------------------------------------------------------------- #
malos=0

_c_check() {
  local v="$1" base="$2" real="$3" link="$4"
  local nombre esperado
  nombre="$(basename "$v")"
  esperado="$(echo "$base" | grep -oE '[0-9]+\.[0-9]+$')"
  if [ -z "$base" ]; then
    amar "  ?   $nombre  (pyvenv.cfg sin base-executable)"; malos=$((malos + 1)); return
  fi
  if [ ! -x "$base" ]; then
    rojo "  ✗   $nombre  intérprete base inexistente: $base"; malos=$((malos + 1)); return
  fi
  if [ "$link" != "$base" ]; then
    rojo "  ✗   $nombre  enlace=$link  esperado=$base  (ejecuta: $0 fix)"; malos=$((malos + 1)); return
  fi
  if [ -n "$esperado" ] && [ "$real" != "$esperado" ]; then
    rojo "  ✗   $nombre  ejecuta $real pero su base declara $esperado"; malos=$((malos + 1)); return
  fi
  printf '  ok  %s  (%s)\n' "$nombre" "$real"
}

_c_list() {
  printf '  %-46s %-22s %-6s %s\n' "VENV" "BASE (pyvenv.cfg)" "REAL" "ENLACE"
  printf '  %-46s %-22s %-6s %s\n' "----" "----------------" "----" "------"
  local v="$1" base="$2" real="$3" link="$4"
  printf '  %-46s %-22s %-6s %s\n' "$(basename "$v")" "${base:-?}" "$real" "$link"
}

_c_fix() {
  local v="$1" base="$2" real="$3" link="$4"
  local nombre; nombre="$(basename "$v")"
  if [ -z "$base" ] || [ ! -x "$base" ]; then
    amar "  saltado  $nombre  (base inválida: '${base:-vacía}')"; return
  fi
  if [ "$link" = "$base" ]; then
    printf '  ya ok   %s  (%s)\n' "$nombre" "$real"; return
  fi
  ln -sfn "$base" "$v/bin/python"
  printf '  reparado %-44s -> %s (ahora %s)\n' "$nombre" "$base" "$(real_de "$v")"
}

cmd_check() {
  echo "Venvs en $WORKON_HOME"
  recorrer _c_check
  echo "---"
  if [ "$malos" -eq 0 ]; then
    verde "Todos los venvs están alineados con el intérprete que declara su pyvenv.cfg."
    return 0
  fi
  rojo "$malos venv(s) desalineados.  Repara con: $0 fix"
  return 1
}

cmd_fix() {
  echo "Reparando enlaces de $WORKON_HOME (offline, no toca paquetes)"
  recorrer _c_fix
  echo "---"
  cmd_check
}

# Uso: rebuild [servicio ...]   (sin argumentos: informa y pide --todos)
cmd_rebuild() {
  local svcs=("$@")
  if [ "${#svcs[@]}" -eq 0 ]; then
    amar "Indica qué servicios reconstruir, o pasa --todos."
    echo "  Ejemplos:  $0 rebuild ms_sisper_bitacora"
    echo "             $0 rebuild --todos"
    return 2
  fi
  if [ "${svcs[0]}" = "--todos" ]; then
    svcs=()
    for d in "$REPO_ROOT"/backend/ms_* "$REPO_ROOT"/backend/mf_*; do
      [ -f "$d/Pipfile" ] && svcs+=("$(basename "$d")")
    done
  fi
  echo "AVISO: 'rebuild' borra el venv y descarga dependencias de PyPI."
  echo "       Detén antes esos servicios en el DevConsole."
  local s d base ver
  for s in "${svcs[@]}"; do
    d="$REPO_ROOT/backend/$s"
    [ -f "$d/Pipfile" ] || { amar "  $s: sin Pipfile en $d"; continue; }
    ver="$(pipfile_de "$d")"
    base="/usr/bin/python${ver:-3}"
    if [ ! -x "$base" ]; then
      rojo "  $s: no existe $base (¿la versión del Pipfile está instalada?)"; continue
    fi
    echo "  -> $s  (Pipfile pide ${ver:-?}; se usa $base)"
    ( cd "$d" && pipenv --rm >/dev/null 2>&1
      pipenv --python "$base" install ) || { rojo "  $s: falló la reconstrucción"; continue; }
    ( cd "$d" && pipenv run python -c "import dotenv, django" >/dev/null 2>&1 ) \
      && verde "  $s: OK (dotenv + django)" \
      || amar "  $s: instala, pero no importa dotenv+django (revisa su Pipfile)"
  done
}

case "${1:-check}" in
  check)   shift || true; cmd_check ;;
  list)    shift || true; echo "Venvs en $WORKON_HOME"; recorrer _c_list ;;
  fix)     shift || true; cmd_fix ;;
  rebuild) shift;        cmd_rebuild "$@" ;;
  -h|--help|help)
    sed -n '2,22p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//' ;;
  *)
    rojo "Subcomando no reconocido: $1"; echo "Usa: $0 [check|list|fix|rebuild]"; exit 2 ;;
esac
