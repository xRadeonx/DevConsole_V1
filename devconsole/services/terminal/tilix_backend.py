# devconsole/services/terminal/tilix_backend.py
"""Tilix implementation of the terminal backend contract.

This module is the Phase 2 home of what used to live in
``devconsole/services/tilix_service.py``.  The module-level functions below are
the *moved verbatim* legacy implementation: parsing, layout generation, the
generated session JSON and every ``subprocess`` invocation are byte-for-byte
what they were before, so Tilix behaviour is unchanged by construction rather
than by re-derivation.

:class:`TilixBackend` is a thin adapter presenting them through
:class:`~devconsole.services.terminal.base.TerminalBackend`.  It contains no
Tilix logic of its own — that is the point: the seam is introduced without
rewriting the proven code underneath it.

Tilix-specific concepts (session JSON, ``Paned`` nodes, terminal ``uuid``,
``overrideCommand``, the fixed profile id) stay inside this file and are never
visible through the backend interface.

Patchability contract
---------------------
``BASE_DIR`` and ``Path`` are module-level names here on purpose.  The
characterization suite patches ``tilix_service.BASE_DIR`` and
``tilix_service.Path`` on the *module object*, so the implementation must
resolve both from a module global at call time.  Do not convert them to
function-local imports or to constants captured elsewhere; see
``devconsole/services/tilix_service.py`` for how the legacy import path is kept
pointing at this very namespace.
"""

import json
import os
import subprocess
import uuid
from pathlib import Path

from devconsole.config import BASE_DIR
from devconsole.services.terminal.base import TerminalBackend


def count_terminals_in_node(node) -> int:
    if not isinstance(node, dict):
        return 0
    count = 1 if node.get("type") == "Terminal" else 0
    for k in ("child", "child1", "child2"):
        if k in node:
            count += count_terminals_in_node(node[k])
    return count

def scan_tilix_sessions() -> list:
    sessions = []
    search_dirs = [BASE_DIR, BASE_DIR / "backend", BASE_DIR / "frontend", BASE_DIR / "config" / "sessions"]
    seen = set()
    for d in search_dirs:
        if not d.exists():
            continue
        for p in d.glob("*.json"):
            if p.name in ("package.json", "package-lock.json", "tsconfig.json", "skills-lock.json", "services.json"):
                continue
            if str(p) in seen:
                continue
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict) and ("child" in data or "child1" in data or data.get("type") == "Terminal"):
                    seen.add(str(p))
                    rel = str(p.relative_to(BASE_DIR)) if str(p).startswith(str(BASE_DIR)) else p.name
                    sessions.append({
                        "name": p.name,
                        "rel_path": rel,
                        "abs_path": str(p),
                        "terminals": count_terminals_in_node(data),
                        "is_default": (p.name == "sisper_all_single_session_auto.json")
                    })
            except Exception:
                pass
    sessions.sort(key=lambda x: (not x["is_default"], -x["terminals"]))
    return sessions


def normalize_session_dict(node, base_dir: Path):
    if isinstance(node, dict):
        if "directory" in node and isinstance(node["directory"], str):
            orig = node["directory"]
            if "/backend/" in orig:
                rel = orig.split("/backend/", 1)[1]
                node["directory"] = str(base_dir / "backend" / rel)
            elif "/frontend/" in orig:
                rel = orig.split("/frontend/", 1)[1]
                node["directory"] = str(base_dir / "frontend" / rel)
            elif orig.endswith("/backend"):
                node["directory"] = str(base_dir / "backend")
            elif orig.endswith("/frontend"):
                node["directory"] = str(base_dir / "frontend")
        for v in node.values():
            normalize_session_dict(v, base_dir)
    elif isinstance(node, list):
        for item in node:
            normalize_session_dict(item, base_dir)

def _prepare_tilix_env(target_env: str = "develop") -> dict:
    env = os.environ.copy()
    env["SISPER_ENV"] = target_env
    user_id = os.getuid()
    if not env.get("WAYLAND_DISPLAY") and Path(f"/run/user/{user_id}/wayland-0").exists():
        env["WAYLAND_DISPLAY"] = "wayland-0"
    if not env.get("DISPLAY"):
        env["DISPLAY"] = ":0"
    if not env.get("DBUS_SESSION_BUS_ADDRESS") and Path(f"/run/user/{user_id}/bus").exists():
        env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{user_id}/bus"
    user_home = Path.home()
    local_bin = str(user_home / ".local" / "bin")
    if local_bin not in env.get("PATH", ""):
        env["PATH"] = f"{local_bin}:{env.get('PATH', '')}"
    return env


def launch_tilix_session_normalized(session_path: Path, target_env: str = "develop") -> bool:
    try:
        raw_data = json.loads(session_path.read_text(encoding="utf-8"))
        normalize_session_dict(raw_data, BASE_DIR)
        
        user_name = os.environ.get("USER", "user")
        norm_file = Path(f"/tmp/tilix_norm_{user_name}_{session_path.stem}.json")
        norm_file.write_text(json.dumps(raw_data, indent=2), encoding="utf-8")

        env = _prepare_tilix_env(target_env)
        subprocess.Popen(["tilix", f"--session={str(norm_file)}"], env=env, cwd=str(BASE_DIR))
        return True
    except Exception as e:
        print(f"[!] Error lanzando Tilix normalizado: {e}")
        return False


def build_tilix_session_tree(directories: list[str], session_name: str = "Servicios Seleccionados", commands: dict[str, str] = None) -> dict:
    if not directories:
        return {}

    commands = commands or {}
    from devconsole import config as dev_config

    def build_node(items, depth=0):
        if len(items) == 1:
            d = items[0]
            cmd = commands.get(d)
            if not cmd:
                runner_path = (dev_config.BASE_DIR / "tilix_runner.sh").resolve()
                cmd = f"bash -c 'cd \"{d}\" && exec \"{runner_path}\"'"
            return {
                "directory": d,
                "height": 420,
                "profile": "c8e01000-0000-0000-0000-000000000001",
                "readOnly": False,
                "synchronizedInput": False,
                "type": "Terminal",
                "uuid": str(uuid.uuid4()),
                "width": 640,
                "overrideCommand": cmd
            }
        mid = len(items) // 2
        return {
            "child1": build_node(items[:mid], depth + 1),
            "child2": build_node(items[mid:], depth + 1),
            "orientation": 0 if depth % 2 == 0 else 1,
            "position": 50,
            "ratio": 0.5,
            "type": "Paned"
        }

    return {
        "child": build_node(directories),
        "height": 1080,
        "width": 1920,
        "name": f"SISPER - {session_name}",
        "synchronizedInput": False,
        "type": "Session",
        "uuid": str(uuid.uuid4()),
        "version": "1.0"
    }


def launch_custom_services_tilix(service_names: list[str] = None, target_env: str = "develop", base_dir: Path = None) -> tuple[bool, str, int]:
    try:
        from devconsole import config as dev_config
        root = base_dir or dev_config.BASE_DIR

        # Si no se especificaron nombres, usar todos los servicios descubiertos en el directorio activo
        if not service_names:
            service_names = [s["name"] for s in dev_config.SERVICES_BACKEND] + [s["name"] for s in dev_config.SERVICES_FRONTEND]

        dirs = []
        found_names = []
        for s in service_names:
            d = root / "backend" / s
            if not d.exists() or not d.is_dir():
                d = root / "frontend" / s
            if not d.exists() or not d.is_dir():
                d = root / s
            if d.exists() and d.is_dir():
                dirs.append(str(d.resolve()))
                found_names.append(s)

        if not dirs:
            return False, "No se encontraron directorios válidos para los servicios seleccionados.", 0

        env = _prepare_tilix_env(target_env)

        # Generar árbol de sesión Tilix garantizado tanto para 1 como para múltiples servicios
        title_label = f"{found_names[0]} ({target_env.upper()})" if len(dirs) == 1 else f"{len(dirs)} Servicios ({target_env.upper()})"
        session_data = build_tilix_session_tree(dirs, title_label)
        user_name = os.environ.get("USER", "user")
        session_file = Path(f"/tmp/tilix_dynamic_{user_name}_selected.json")
        session_file.write_text(json.dumps(session_data, indent=2), encoding="utf-8")

        subprocess.Popen(["tilix", f"--session={str(session_file)}"], env=env, cwd=dirs[0])
        return True, f"Ventana Tilix lanzada con {len(dirs)} servicio(s) en {target_env.upper()}.", len(dirs)
    except Exception as e:
        print(f"[!] Error lanzando Tilix personalizado: {e}")
        return False, f"Error lanzando Tilix: {e}", 0


def launch_auxiliary_console(service_name: str, aux_type: str = "consumer", target_env: str = "develop", base_dir: Path = None) -> tuple[bool, str]:
    try:
        from devconsole import config as dev_config
        root = base_dir or dev_config.BASE_DIR

        d = root / "backend" / service_name
        if not d.exists() or not d.is_dir():
            d = root / "frontend" / service_name
        if not d.exists() or not d.is_dir():
            d = root / service_name
        if not d.exists() or not d.is_dir():
            return False, f"Directorio no encontrado para el servicio: {service_name}"

        service_dir = str(d.resolve())
        env = _prepare_tilix_env(target_env)

        if aux_type == "consumer":
            title = f"🐰 Consumer: {service_name}"
            runner_cmd = "pipenv run python manage.py start_consumer || python manage.py start_consumer"
            desc = "Consumidor RabbitMQ"
        elif aux_type == "worker":
            title = f"⚙️ Worker: {service_name}"
            runner_cmd = "pipenv run celery -A config worker -l info || celery -A config worker -l info"
            desc = "Celery Worker"
        elif aux_type == "beat":
            title = f"⏰ Beat: {service_name}"
            runner_cmd = "pipenv run celery -A config beat -l info || celery -A config beat -l info"
            desc = "Celery Beat"
        elif aux_type == "shell":
            title = f"💻 Shell: {service_name}"
            runner_cmd = "pipenv shell || exec bash"
            desc = "Pipenv Shell"
        else:
            return False, f"Tipo de auxiliar no reconocido: {aux_type}"

        user_name = os.environ.get("USER", "user")
        script_file = Path(f"/tmp/sisper_aux_{user_name}_{service_name}_{aux_type}.sh")
        bash_script = f"""#!/usr/bin/env bash
cd "{service_dir}" || exit 1
export PATH="$HOME/.local/bin:$HOME/.bun/bin:$HOME/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export SISPER_ENV="{target_env}"

echo "=========================================================="
echo " 🚀 SISPER AUXILIAR: {desc} ({service_name})"
echo " 📂 Directorio: {service_dir}"
echo " ⚙️ Comando: {runner_cmd}"
echo " 🌐 Entorno: {target_env.upper()}"
echo "=========================================================="
echo ""
{runner_cmd}
RET=$?
echo ""
echo "----------------------------------------------------------"
echo "[!] Proceso finalizado (código $RET)."
echo "  * Presiona ENTER para salir a bash interactivo..."
read -r
exec bash
"""
        script_file.write_text(bash_script, encoding="utf-8")
        script_file.chmod(0o755)

        session_data = build_tilix_session_tree(
            [service_dir],
            f"{desc} - {service_name}",
            commands={service_dir: str(script_file)}
        )
        session_file = Path(f"/tmp/tilix_aux_sess_{user_name}_{service_name}_{aux_type}.json")
        session_file.write_text(json.dumps(session_data, indent=2), encoding="utf-8")

        subprocess.Popen(["tilix", f"--session={str(session_file)}"], env=env, cwd=service_dir)
        return True, f"Consola {desc} lanzada para {service_name}."
    except Exception as e:
        print(f"[!] Error lanzando auxiliar {aux_type} para {service_name}: {e}")
        return False, f"Error lanzando auxiliar: {e}"


def launch_selected_auxiliaries(service_names: list[str], aux_type: str = "consumer", target_env: str = "develop", base_dir: Path = None) -> tuple[bool, str, int]:
    try:
        if not service_names:
            return False, "No se seleccionaron servicios.", 0

        from devconsole import config as dev_config
        root = base_dir or dev_config.BASE_DIR

        dirs = []
        found_names = []
        commands = {}
        user_name = os.environ.get("USER", "user")

        for s in service_names:
            d = root / "backend" / s
            if not d.exists() or not d.is_dir():
                d = root / "frontend" / s
            if not d.exists() or not d.is_dir():
                d = root / s
            if d.exists() and d.is_dir():
                sdir = str(d.resolve())
                dirs.append(sdir)
                found_names.append(s)

                if aux_type == "consumer":
                    runner_cmd = "pipenv run python manage.py start_consumer || python manage.py start_consumer"
                    desc = "RabbitMQ Consumer"
                elif aux_type == "worker":
                    runner_cmd = "pipenv run celery -A config worker -l info || celery -A config worker -l info"
                    desc = "Celery Worker"
                elif aux_type == "beat":
                    runner_cmd = "pipenv run celery -A config beat -l info || celery -A config beat -l info"
                    desc = "Celery Beat"
                elif aux_type == "shell":
                    runner_cmd = "pipenv shell || exec bash"
                    desc = "Pipenv Shell"
                else:
                    runner_cmd = "exec bash"
                    desc = "Terminal"

                script_file = Path(f"/tmp/sisper_aux_{user_name}_{s}_{aux_type}.sh")
                bash_script = f"""#!/usr/bin/env bash
cd "{sdir}" || exit 1
export PATH="$HOME/.local/bin:$HOME/.bun/bin:$HOME/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export SISPER_ENV="{target_env}"

echo "=========================================================="
echo " 🚀 SISPER AUXILIAR: {desc} ({s})"
echo " 📂 Directorio: {sdir}"
echo " ⚙️ Comando: {runner_cmd}"
echo " 🌐 Entorno: {target_env.upper()}"
echo "=========================================================="
echo ""
{runner_cmd}
RET=$?
echo ""
echo "----------------------------------------------------------"
echo "[!] Proceso finalizado (código $RET)."
echo "  * Presiona ENTER para salir a bash interactivo..."
read -r
exec bash
"""
                script_file.write_text(bash_script, encoding="utf-8")
                script_file.chmod(0o755)
                commands[sdir] = str(script_file)

        if not dirs:
            return False, "No se encontraron directorios válidos para los servicios seleccionados.", 0

        env = _prepare_tilix_env(target_env)
        title_label = f"{len(dirs)} {aux_type.capitalize()}s ({target_env.upper()})"
        session_data = build_tilix_session_tree(dirs, title_label, commands=commands)
        session_file = Path(f"/tmp/tilix_aux_sess_{user_name}_{aux_type}_selected.json")
        session_file.write_text(json.dumps(session_data, indent=2), encoding="utf-8")

        subprocess.Popen(["tilix", f"--session={str(session_file)}"], env=env, cwd=dirs[0])
        return True, f"Ventana Tilix lanzada con {len(dirs)} consola(s) de tipo '{aux_type}'.", len(dirs)
    except Exception as e:
        print(f"[!] Error lanzando auxiliares seleccionados ({aux_type}): {e}")
        return False, f"Error lanzando auxiliares: {e}", 0


# --------------------------------------------------------------------------- #
# Backend adapter
# --------------------------------------------------------------------------- #

#: Name of the launcher script Tilix uses for lifecycle actions.
LAUNCHER_SCRIPT = "start_tilix.sh"


class TilixBackend(TerminalBackend):
    """Adapter exposing the legacy Tilix implementation as a backend.

    Every method is a direct delegation to the module-level function above, so
    the observable behaviour — return values, messages, generated files,
    ``subprocess`` argv/cwd/env and exception propagation — is identical to
    calling those functions directly.
    """

    name = "tilix"

    def scan_sessions(self) -> list:
        return scan_tilix_sessions()

    def launch_session(self, session_path: Path, environment: str = "develop") -> bool:
        return launch_tilix_session_normalized(session_path, environment)

    def launch_services(self, services=None, environment: str = "develop", base_dir: Path = None):
        return launch_custom_services_tilix(services, environment, base_dir)

    def launch_auxiliary(self, service: str, aux_type: str = "consumer", environment: str = "develop", base_dir: Path = None):
        return launch_auxiliary_console(service, aux_type, environment, base_dir)

    def launch_selected_auxiliaries(self, services=None, aux_type: str = "consumer", environment: str = "develop", base_dir: Path = None):
        return launch_selected_auxiliaries(services, aux_type, environment, base_dir)

    def run_action(
        self,
        action: str,
        args=() ,
        *,
        wait: bool,
        check: bool = False,
        timeout: float = None,
        base_dir: Path = None,
    ):
        """Run ``start_tilix.sh <action> [args...]`` exactly as before.

        ``BASE_DIR`` and ``Path`` are read from this module's globals at call
        time, which is what keeps the characterization suite's patching of the
        legacy import path effective.
        """
        launcher = str(Path(base_dir or BASE_DIR) / LAUNCHER_SCRIPT)
        cmd = [launcher, action, *args]

        if not wait:
            # Fire and forget: no kwargs at all, matching the previous
            # subprocess.Popen([launcher, action, ...]) call sites.
            return subprocess.Popen(cmd)

        kwargs = {"check": check}
        if timeout is not None:
            kwargs["timeout"] = timeout
        return subprocess.run(cmd, **kwargs)
