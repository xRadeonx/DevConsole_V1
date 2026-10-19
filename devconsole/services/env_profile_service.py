"""Declarative LOCAL/INTRANET profile switching for the legacy V1 UI.

The public ``switch_env.sh`` command remains available, but delegates here.
Changing environment now modifies only .env files.  Source-code modification is
reserved for the two explicit ``bitacora-*`` maintenance commands, preserving
that legacy capability without making it a hidden side effect of environment
switching.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Iterable

import devconsole.config as dcfg

_KEEP = "__KEEP__"
_PROFILE_NAMES = ("environment_profiles.json", "environment_profiles.legacy.json")

BITACORA_ORIG = '''        request_data, ip, metodo, url_full = extract_request_data(request)
        publicar_en_bitacora.delay(
            data=request_data,
            ip=ip,
            modulo="MOD. SESIÓN",
            metodo=metodo,
            url_full=url_full,
            response_code=status.HTTP_200_OK,
            user_id_ejecutor=user_id,
            run_ejecutor=username,
            primer_nombre_ejecutor=user_info.get("firstName") or "No Disponible",
            primer_apellido_ejecutor=user_info.get("lastName") or "No Disponible",
            segundo_apellido_ejecutor="No Disponible",
            fec_bitacora=dt.datetime.now(),
        )
        logger.info("SISPER_INFO: ===> Transacción enviada a Broker")'''

BITACORA_PATCH = '''        try:
            request_data, ip, metodo, url_full = extract_request_data(request)
            publicar_en_bitacora.delay(
                data=request_data,
                ip=ip,
                modulo="MOD. SESIÓN",
                metodo=metodo,
                url_full=url_full,
                response_code=status.HTTP_200_OK,
                user_id_ejecutor=user_id,
                run_ejecutor=username,
                primer_nombre_ejecutor=user_info.get("firstName") or "No Disponible",
                primer_apellido_ejecutor=user_info.get("lastName") or "No Disponible",
                segundo_apellido_ejecutor="No Disponible",
                fec_bitacora=dt.datetime.now(),
            )
            logger.info("SISPER_INFO: ===> Transacción enviada a Broker")
        except Exception as e:
            logger.warning("SISPER_WARN: No se pudo registrar en bitácora (broker no disponible): %s", e)'''


def _profile_path() -> Path:
    config_dir = Path(dcfg.DASHBOARD_DIR) / "config"
    for name in _PROFILE_NAMES:
        path = config_dir / name
        if path.is_file():
            return path
    raise FileNotFoundError(
        "No existe config/environment_profiles.json ni environment_profiles.legacy.json"
    )


def load_profiles() -> dict:
    path = _profile_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("profiles"), dict):
        raise ValueError(f"Perfil de entorno inválido: {path}")
    return data


def _read_var(path: Path, key: str) -> str:
    if not path.is_file():
        return "<no existe>"
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(rf"^{re.escape(key)}\s*=\s*(.*)$", text, re.MULTILINE)
    return match.group(1).strip() if match else "<no configurada>"


def _atomic_apply(path: Path, replacements: dict[str, str], keep_value: str = _KEEP) -> bool:
    """Apply key/value replacements atomically; never create missing service envs."""
    if not path.is_file():
        return False
    original = path.read_text(encoding="utf-8")
    text = original
    for key, value in replacements.items():
        if str(value) == keep_value:
            continue
        pattern = rf"^{re.escape(str(key))}\s*=.*$"
        line = f"{key}={value}"
        if re.search(pattern, text, re.MULTILINE):
            text = re.sub(pattern, line, text, flags=re.MULTILINE)
        else:
            if text and not text.endswith("\n"):
                text += "\n"
            text += line + "\n"
    if text == original:
        return False
    temp = path.with_name(path.name + ".devconsole.tmp")
    temp.write_text(text, encoding="utf-8")
    try:
        temp.chmod(path.stat().st_mode & 0o777)
    except OSError:
        pass
    temp.replace(path)
    return True


def _known_services(data: dict) -> tuple[list[str], list[str]]:
    intranet = data["profiles"].get("intranet") or {}
    backends = list((intranet.get("backend") or {}).keys())
    frontends = list((intranet.get("frontend") or {}).keys())
    return backends, frontends


def _select_services(data: dict, target: str | None, all_services: bool) -> tuple[list[str], list[str]]:
    backends, frontends = _known_services(data)
    if target:
        b = [name for name in backends if name == target or target in name]
        f = [name for name in frontends if name == target or target in name]
        if not b and not f:
            raise ValueError(f"Servicio '{target}' no reconocido por el perfil configurado.")
        return b, f
    if all_services:
        return backends, frontends
    return (
        ["ms_sisper_sesion"] if "ms_sisper_sesion" in backends else backends[:1],
        ["mf_sisper_sesion"] if "mf_sisper_sesion" in frontends else frontends[:1],
    )


def apply_environment_profile(mode: str, *, target: str | None = None, all_services: bool = False) -> dict:
    """Apply LOCAL/INTRANET variables only; source files are never touched."""
    normalized = mode.strip().lower()
    if normalized not in {"local", "intranet"}:
        raise ValueError("mode debe ser 'local' o 'intranet'")

    data = load_profiles()
    keep_value = str(data.get("keep_value") or _KEEP)
    backends, frontends = _select_services(data, target, all_services)
    profile = data["profiles"][normalized]
    root = Path(dcfg.BASE_DIR)
    results: list[dict] = []

    for name in backends:
        env_path = root / "backend" / name / ".env"
        replacements = (
            profile.get("backend_common") or {}
            if normalized == "local"
            else (profile.get("backend") or {}).get(name, {})
        )
        changed = _atomic_apply(env_path, replacements, keep_value)
        results.append({
            "service": name,
            "type": "backend",
            "exists": env_path.is_file(),
            "changed": changed,
        })

    for name in frontends:
        env_path = root / "frontend" / name / ".env"
        replacements = (
            profile.get("frontend_common") or {}
            if normalized == "local"
            else (profile.get("frontend") or {}).get(name, {})
        )
        changed = _atomic_apply(env_path, replacements, keep_value)
        results.append({
            "service": name,
            "type": "frontend",
            "exists": env_path.is_file(),
            "changed": changed,
        })

    return {
        "mode": normalized.upper(),
        "source_patch": False,
        "profile": str(_profile_path()),
        "results": results,
        "changed": sum(1 for item in results if item["changed"]),
    }


def _session_views_path() -> Path:
    return (
        Path(dcfg.BASE_DIR)
        / "backend"
        / "ms_sisper_sesion"
        / "core"
        / "ms_sesion"
        / "v1"
        / "views.py"
    )


def bitacora_status() -> str:
    path = _session_views_path()
    if not path.is_file():
        return "<no encontrado>"
    text = path.read_text(encoding="utf-8", errors="replace")
    if BITACORA_PATCH in text:
        return "PARCHE LOCAL (try/except)"
    if BITACORA_ORIG in text:
        return "ORIGINAL INTRANET (limpio)"
    return "DESCONOCIDO / MODIFICADO"


def set_bitacora_patch(mode: str) -> tuple[bool, str]:
    """Explicit legacy maintenance capability; never called by profile switch."""
    path = _session_views_path()
    if not path.is_file():
        return False, "views.py de ms_sisper_sesion no encontrado"
    text = path.read_text(encoding="utf-8")
    normalized = mode.strip().lower()
    if normalized == "local":
        if BITACORA_PATCH in text:
            return True, "Parche de bitácora ya estaba activo."
        if BITACORA_ORIG not in text:
            return False, "Bloque original de bitácora no coincide; no se modifica código desconocido."
        path.write_text(text.replace(BITACORA_ORIG, BITACORA_PATCH), encoding="utf-8")
        return True, "Parche explícito de bitácora aplicado."
    if normalized == "intranet":
        if BITACORA_ORIG in text:
            return True, "Código original de bitácora ya estaba activo."
        if BITACORA_PATCH not in text:
            return False, "Bloque parcheado no coincide; no se modifica código desconocido."
        path.write_text(text.replace(BITACORA_PATCH, BITACORA_ORIG), encoding="utf-8")
        return True, "Código original de bitácora restaurado."
    return False, "Modo de bitácora inválido."


def environment_status() -> dict:
    session_env = Path(dcfg.BASE_DIR) / "backend" / "ms_sisper_sesion" / ".env"
    host = _read_var(session_env, "DATABASE_HOST")
    keycloak = _read_var(session_env, "KEYCLOAK_SERVER_URL")
    host_clean = host.strip("\"'")
    keycloak_clean = keycloak.strip("\"'")
    if host_clean in {"127.0.0.1", "localhost"} and "localhost:8080" in keycloak_clean:
        mode = "LOCAL"
    elif host_clean not in {"<no existe>", "<no configurada>"} and host_clean not in {"127.0.0.1", "localhost"}:
        mode = "INTRANET"
    else:
        mode = "DESCONOCIDO"
    return {
        "env_mode": mode,
        "bitacora_status": bitacora_status(),
        "database_host": host,
        "keycloak_url": keycloak,
    }


def _print_results(report: dict) -> None:
    print(f"[+] Modo {report['mode']} aplicado mediante perfil declarativo (.env solamente).")
    print(f"[+] Servicios modificados: {report['changed']}")
    for item in report["results"]:
        state = "actualizado" if item["changed"] else ("sin cambio" if item["exists"] else "sin .env")
        print(f"    {item['service']}: {state}")
    print("[✓] Código fuente no modificado por el cambio de entorno.")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("target_or_action", nargs="?")
    parser.add_argument("action", nargs="?")
    parser.add_argument("--all", "-a", action="store_true", dest="all_services")
    args = parser.parse_args(list(argv) if argv is not None else None)

    first = args.target_or_action
    action = args.action
    target = None
    known_actions = {
        "local", "offline", "intranet", "normal", "status", "info", "status-json",
        "bitacora-local", "bitacora-intranet",
    }
    if first is None:
        action = "status"
    elif first.lower() in known_actions and action is None:
        action = first.lower()
    else:
        target = first
        action = (action or "status").lower()

    if action == "offline":
        action = "local"
    elif action == "normal":
        action = "intranet"

    try:
        if action == "status-json":
            print(json.dumps(environment_status(), ensure_ascii=False))
            return 0
        if action in {"status", "info"}:
            status = environment_status()
            print(json.dumps(status, ensure_ascii=False, indent=2))
            return 0
        if action in {"local", "intranet"}:
            report = apply_environment_profile(action, target=target, all_services=args.all_services)
            _print_results(report)
            return 0
        if action in {"bitacora-local", "bitacora-intranet"}:
            mode = "local" if action == "bitacora-local" else "intranet"
            ok, message = set_bitacora_patch(mode)
            print(("[+] " if ok else "[!] ") + message)
            print(f"[*] Estado: {bitacora_status()}")
            return 0 if ok else 1
        print(f"ERROR: acción no soportada: {action}")
        return 2
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
