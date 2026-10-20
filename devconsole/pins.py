"""PINs de acceso (Administrador / Desarrollador) almacenados como hashes scrypt.

DevConsole V1.1 usa tres niveles de producto:

* Viewer/QA: acceso base, sin credencial.
* Developer: requiere su clave de producto.
* Admin: requiere su clave de producto y obtiene una sesión administrativa.

Las claves de producto pueden distribuirse como hashes scrypt (por ejemplo
``config/pins.json`` copiado por el instalador).  Nunca existe una contraseña
incorporada en texto claro como fallback del producto.

Orden de resolución para un rol:

1. credencial de systemd (``$CREDENTIALS_DIRECTORY/<rol>_pin``),
2. hash en el almacén (``SISPER_SECRETS_FILE`` o
   ``~/.config/sisper-dashboard/secrets.json``),
3. variable de entorno explícita ``SISPER_ADMIN_PIN`` / ``SISPER_DEV_PIN``.

Si ninguna de las anteriores existe, el rol queda bloqueado.  La interfaz de
línea de órdenes permite crear/rotar un hash sin dejar la clave en el historial::

    python3 -m devconsole.pins set --role admin
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

_SCRYPT_N = 2 ** 14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_LEN = 32
_SALT_BYTES = 16

_MAX_FALLOS = 5
_BLOQUEO_S = 30.0

_FALLOS: dict[str, list[float]] = {}


def ruta_secretos() -> Path:
    """Fichero del almacén de hashes (0600, fuera del repositorio activo)."""
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
    derivado = hashlib.scrypt(
        pin.encode("utf-8"),
        salt=sal,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_LEN,
    )
    return {
        "algo": "scrypt",
        "n": _SCRYPT_N,
        "r": _SCRYPT_R,
        "p": _SCRYPT_P,
        "salt": sal.hex(),
        "hash": derivado.hex(),
    }


def set_pin(rol: str, pin: str) -> None:
    """Guarda (hasheado) el PIN de un rol. El PIN en claro no se persiste."""
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


def _pin_entorno(rol: str) -> str:
    """Compatibilidad explícita: una variable sólo habilita su propio rol."""
    return os.environ.get(f"SISPER_{rol.upper()}_PIN", "")


def hay_claves_configuradas() -> bool:
    """¿Hay al menos una clave utilizable? Sirve para diagnóstico de instalación."""
    return any(estado()[rol] != "sin credencial (rol bloqueado)" for rol in ROLES)


def _bloqueado(rol: str) -> float:
    """Segundos que quedan de bloqueo por fallos recientes (0 si no hay)."""
    ahora = time.time()
    fallos = [t for t in _FALLOS.get(rol, []) if ahora - t < _BLOQUEO_S]
    _FALLOS[rol] = fallos
    return max(0.0, _BLOQUEO_S - (ahora - fallos[-1])) if len(fallos) >= _MAX_FALLOS else 0.0


def _anotar_fallo(rol: str) -> None:
    if rol in ROLES:
        _FALLOS.setdefault(rol, []).append(time.time())


def verify(rol: str, pin: str) -> bool:
    """Comprueba el PIN del rol en tiempo constante, con bloqueo por fallos."""
    if rol not in ROLES or not pin or not isinstance(pin, str):
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
            derivado = hashlib.scrypt(
                pin.encode("utf-8"),
                salt=sal,
                n=int(registro.get("n", _SCRYPT_N)),
                r=int(registro.get("r", _SCRYPT_R)),
                p=int(registro.get("p", _SCRYPT_P)),
                dklen=len(esperado),
            )
        except (KeyError, ValueError, TypeError):
            _anotar_fallo(rol)
            return False
        if hmac.compare_digest(derivado, esperado):
            _FALLOS.pop(rol, None)
            return True
        _anotar_fallo(rol)
        return False

    env_pin = _pin_entorno(rol)
    if env_pin and hmac.compare_digest(pin, env_pin):
        _FALLOS.pop(rol, None)
        return True

    _anotar_fallo(rol)
    return False


def estado() -> dict:
    """Qué método de PIN tiene configurado cada rol, sin revelar secretos."""
    almacen = _leer_almacen().get("roles") or {}
    salida = {}
    for rol in ROLES:
        if _pin_de_credencial(rol):
            salida[rol] = "credencial systemd (cifrada en reposo)"
        elif isinstance(almacen.get(rol), dict) and almacen[rol].get("hash"):
            salida[rol] = f"scrypt en {ruta_secretos()}"
        elif os.environ.get(f"SISPER_{rol.upper()}_PIN"):
            salida[rol] = "variable de entorno (en claro)"
        else:
            salida[rol] = "sin credencial (rol bloqueado)"
    return salida


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="devconsole.pins",
        description="PINs del panel (hasheados con scrypt).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_set = sub.add_parser("set", help="fija el PIN de un rol")
    p_set.add_argument("--role", choices=ROLES, required=True)
    p_set.add_argument(
        "--stdin",
        action="store_true",
        help="lee el PIN de la entrada estándar (para scripts; no queda en el historial)",
    )

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
