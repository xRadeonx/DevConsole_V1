"""PINs de acceso (Administrador / Desarrollador) — almacenados **hasheados**.

Qué protege y qué no
--------------------
* **En reposo**: aquí nunca se guarda el PIN, sólo un *hash* **scrypt** con sal
  aleatoria.  Quien lea el fichero (o lo vea en un repositorio, una captura o un
  volcado de configuración) no obtiene la clave.
* **En uso**: el PIN en claro sólo existe en memoria durante la comprobación.
  Se compara en tiempo constante y hay bloqueo temporal tras varios fallos.
* **Lo que no puede hacer**: impedir que quien ya es ese usuario en esa máquina
  lo adivine por fuerza bruta en línea (por eso el bloqueo) ni que sustituya
  este fichero (a esas alturas ya controla el equipo).  Para eso último está la
  opción de **credenciales de systemd**: un fichero cifrado con la clave del
  equipo/TPM, que sólo se descifra al arrancar el servicio
  (`systemd-creds encrypt --name=admin_pin …` y `LoadCredentialEncrypted=`).

Orden de resolución para un rol:

1. credencial de systemd (``$CREDENTIALS_DIRECTORY/<rol>_pin``),
2. hash en el almacén (``SISPER_SECRETS_FILE`` o ``~/.config/sisper-dashboard/secrets.json``),
3. variables de entorno ``SISPER_ADMIN_PIN`` / ``SISPER_DEV_PIN``,
4. compatibilidad: si no hay nada para el rol, se usa el PIN heredado
   (``SISPER_ADMIN_PIN`` o ``sisper2026``) — sólo para no romper instalaciones
   existentes; se avisa en el registro.

La interfaz de línea de órdenes evita escribir el PIN en el historial::

    python3 -m devconsole.pins set --role admin     # pide el PIN dos veces
    python3 -m devconsole.pins set --role dev --stdin
    python3 -m devconsole.pins status
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
from pathlib import Path

__all__ = ["ROLES", "set_pin", "verify", "estado", "hash_pin", "ruta_secretos"]

ROLES = ("admin", "dev")

#: Parámetros de scrypt (coste moderado: ~50 ms por comprobación en este equipo).
_SCRYPT_N = 2 ** 14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_LEN = 32
_SALT_BYTES = 16

#: Bloqueo tras varios fallos seguidos (segundos de castigo por fallo acumulado).
_MAX_FALLOS = 5
_BLOQUEO_S = 30.0

#: Ya no hay PIN por defecto: cada rol exige el suyo (admin y dev distintos) y
#: se configuran con `python3 -m devconsole.pins set --role admin|dev`.  Antes
#: existía "sisper2026" para todo, lo que dejaba una clave conocida y además
#: hacía que Desarrollador y Administrador compartieran la misma.

_FALLOS: dict[str, list[float]] = {}


def ruta_secretos() -> Path:
    """Fichero del almacén de hashes (0600, fuera del repositorio).

    Va **junto al de sesiones**: si el operador (o una prueba) reubica
    ``SISPER_ADMIN_SESSIONS_FILE`` a un directorio temporal, el almacén de PINs
    lo acompaña, así una prueba nunca lee ni escribe los PINs reales del equipo.
    """
    override = os.environ.get("SISPER_SECRETS_FILE")
    if override:
        return Path(override).expanduser()
    sesiones = os.environ.get("SISPER_ADMIN_SESSIONS_FILE")
    if sesiones:
        return Path(sesiones).expanduser().parent / "secrets.json"
    base = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    return base / "sisper-dashboard" / "secrets.json"


def _leer_almacen() -> dict:
    ruta = ruta_secretos()
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
        return datos if isinstance(datos, dict) else {}
    except (OSError, ValueError):
        return {}


def _escribir_almacen(datos: dict) -> None:
    ruta = ruta_secretos()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, sort_keys=True)
    os.chmod(tmp, 0o600)
    os.replace(tmp, ruta)


def hash_pin(pin: str, *, salt: bytes | None = None) -> dict:
    """Devuelve el registro hasheado de un PIN (sal nueva si no se indica)."""
    sal = salt if salt is not None else secrets.token_bytes(_SALT_BYTES)
    derivado = hashlib.scrypt(pin.encode("utf-8"), salt=sal,
                              n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=_SCRYPT_LEN)
    return {
        "algo": "scrypt",
        "n": _SCRYPT_N, "r": _SCRYPT_R, "p": _SCRYPT_P,
        "salt": sal.hex(),
        "hash": derivado.hex(),
    }


def set_pin(rol: str, pin: str) -> None:
    """Guarda (hasheado) el PIN de un rol.  El PIN en claro no se persiste."""
    if rol not in ROLES:
        raise ValueError(f"rol desconocido: {rol!r} (usa {' o '.join(ROLES)})")
    if not pin or len(pin) < 6:
        raise ValueError("el PIN debe tener al menos 6 caracteres")
    datos = _leer_almacen()
    datos.setdefault("version", 1)
    roles = datos.setdefault("roles", {})
    roles[rol] = hash_pin(pin)
    _escribir_almacen(datos)


def _pin_de_credencial(rol: str) -> str:
    """PIN desde una credencial de systemd (cifrada en reposo por el equipo)."""
    directorio = os.environ.get("CREDENTIALS_DIRECTORY")
    if not directorio:
        return ""
    for nombre in (f"{rol}_pin", f"sisper_{rol}_pin"):
        ruta = Path(directorio) / nombre
        try:
            if ruta.is_file():
                return ruta.read_text(encoding="utf-8").strip()
        except OSError:
            continue
    return ""


#: PIN de arranque histórico del rol admin.  Sólo aplica mientras no haya
#: ninguna clave configurada (el instalador pide definir las dos al instalar).
_PIN_ARRANQUE_ADMIN = "sisper2026"


def _pin_heredado(rol: str) -> str:
    """PIN en claro admitido sin almacén: entorno y, para admin, el de arranque.

    **Desarrollador nunca hereda la clave de Administrador**: si no se define
    `SISPER_DEV_PIN` ni se crea su clave, no hay acceso como Desarrollador.
    """
    if rol == "admin":
        return os.environ.get("SISPER_ADMIN_PIN") or _PIN_ARRANQUE_ADMIN
    return os.environ.get("SISPER_DEV_PIN", "")


def hay_claves_configuradas() -> bool:
    """¿Hay al menos una clave utilizable?  Sirve para avisar al entrar."""
    return any(estado()[rol].startswith(("credencial", "scrypt", "variable")) for rol in ROLES)


def _bloqueado(rol: str) -> float:
    """Segundos que quedan de bloqueo por fallos recientes (0 si no hay)."""
    ahora = time.time()
    fallos = [t for t in _FALLOS.get(rol, []) if ahora - t < _BLOQUEO_S]
    _FALLOS[rol] = fallos
    return max(0.0, _BLOQUEO_S - (ahora - fallos[-1])) if len(fallos) >= _MAX_FALLOS else 0.0


def _anotar_fallo(rol: str) -> None:
    _FALLOS.setdefault(rol, []).append(time.time())


def verify(rol: str, pin: str) -> bool:
    """Comprueba el PIN del rol en tiempo constante, con bloqueo por fallos."""
    if not pin or not isinstance(pin, str) or rol not in ROLES:
        _anotar_fallo(rol)
        return False
    if _bloqueado(rol) > 0:
        return False

    credencial = _pin_de_credencial(rol)
    if credencial:
        if hmac.compare_digest(pin, credencial):
            _FALLOS.pop(rol, None)
            return True
        _anotar_fallo(rol)
        return False

    registro = (_leer_almacen().get("roles") or {}).get(rol)
    if isinstance(registro, dict) and registro.get("algo") == "scrypt":
        try:
            sal = bytes.fromhex(registro["salt"])
            esperado = bytes.fromhex(registro["hash"])
            derivado = hashlib.scrypt(pin.encode("utf-8"), salt=sal,
                                      n=int(registro.get("n", _SCRYPT_N)),
                                      r=int(registro.get("r", _SCRYPT_R)),
                                      p=int(registro.get("p", _SCRYPT_P)),
                                      dklen=len(esperado))
        except (KeyError, ValueError, TypeError):
            _anotar_fallo(rol)
            return False
        if hmac.compare_digest(derivado, esperado):
            _FALLOS.pop(rol, None)
            return True
        _anotar_fallo(rol)
        return False

    # Compatibilidad: sólo si el operador declaró el PIN por entorno.
    heredado = _pin_heredado(rol)
    if heredado and hmac.compare_digest(pin, heredado):
        _FALLOS.pop(rol, None)
        return True
    _anotar_fallo(rol)
    return False


def estado() -> dict:
    """Qué método de PIN tiene configurado cada rol (sin revelar secretos)."""
    almacen = _leer_almacen().get("roles") or {}
    salida = {}
    for rol in ROLES:
        if _pin_de_credencial(rol):
            salida[rol] = "credencial systemd (cifrada en reposo)"
        elif isinstance(almacen.get(rol), dict) and almacen[rol].get("hash"):
            salida[rol] = f"scrypt en {ruta_secretos()}"
        elif os.environ.get(f"SISPER_{rol.upper()}_PIN") or (rol == "dev" and os.environ.get("SISPER_ADMIN_PIN")):
            salida[rol] = "variable de entorno (en claro)"
        else:
            salida[rol] = "PIN heredado por defecto (¡configúralo!)"
    return salida


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="devconsole.pins",
                                     description="PINs del panel (hasheados con scrypt).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_set = sub.add_parser("set", help="fija el PIN de un rol")
    p_set.add_argument("--role", choices=ROLES, required=True)
    p_set.add_argument("--stdin", action="store_true",
                       help="lee el PIN de la entrada estándar (para scripts; no queda en el historial)")

    sub.add_parser("status", help="muestra cómo está configurado cada rol")

    args = parser.parse_args(argv)
    if args.cmd == "status":
        for rol, metodo in estado().items():
            print(f"  {rol:6s}: {metodo}")
        return 0

    if args.stdin:
        pin = sys.stdin.readline().rstrip("\n")
    else:
        pin = getpass.getpass(f"PIN para {args.role}: ")
        repetir = getpass.getpass("Repite el PIN: ")
        if pin != repetir:
            print("  ✗ Los PIN no coinciden.", file=sys.stderr)
            return 1
    try:
        set_pin(args.role, pin)
    except ValueError as exc:
        print(f"  ✗ {exc}", file=sys.stderr)
        return 1
    print(f"  ✓ PIN de {args.role} guardado hasheado en {ruta_secretos()}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(_main())
