"""Comprobaciones previas y diagnóstico de servicios — **sólo lectura**.

Dos usos, ambos sin efectos secundarios:

* :func:`preflight` responde "¿puedo lanzar esto?" antes de arrancar nada:
  infraestructura que el modo de entorno necesita (en local, KeyDB y OnlyOffice;
  en intranet se añaden Keycloak y la BD de bitácora) y, por servicio, el
  directorio, el ``.env``, el entorno de **pipenv** y el puerto.
* :func:`diagnose` responde "¿por qué no arranca o se queda colgado?" para un
  servicio concreto: estado real en tmux, salud del virtualenv de pipenv y
  firmas conocidas en su salida (``ModuleNotFoundError``, ``Cannot find
  module``, ``ImproperlyConfigured``, ``EADDRINUSE``…), cada una con el comando
  que la arregla.

Ninguna de las dos ejecuta el arreglo: los comandos sugeridos los corre el
usuario.  El entorno es de **pipenv** (``pipenv install``) y los virtualenvs
viven en ``WORKON_HOME`` (``~/.local/share/virtualenvs``), que es lo que audita
``scripts/venvs.sh``.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable, Sequence

from devconsole.config import BASE_DIR, get_service_repo_dir, is_port_open

__all__ = ["preflight", "diagnose", "infra_requerida"]

#: Virtualenvs de pipenv (misma variable que usa ``scripts/venvs.sh``).
WORKON_HOME = Path(os.environ.get("WORKON_HOME") or (Path.home() / ".local" / "share" / "virtualenvs"))

#: Infra imprescindible según el modo de entorno.  En local bastan KeyDB y
#: OnlyOffice; en intranet se suman Keycloak y la BD de bitácora.
INFRA_POR_MODO: dict[str, tuple[str, ...]] = {
    "LOCAL": ("keydb", "onlyoffice-local"),
    "INTRANET": ("keydb", "onlyoffice-local", "keycloak", "bitacora"),
}

#: Puerto y host de cada pieza de infraestructura (``bitacora`` usa el host de BD).
_PUERTO_INFRA: dict[str, tuple[int, str]] = {
    "keydb": (6379, "127.0.0.1"),
    "onlyoffice-local": (8082, "127.0.0.1"),
    "keycloak": (8080, "127.0.0.1"),
    "bitacora": (5432, "127.0.0.1"),
}

_ETIQUETA_INFRA = {
    "keydb": "KeyDB (caché/colas)",
    "onlyoffice-local": "OnlyOffice (documentos)",
    "keycloak": "Keycloak (SSO)",
    "bitacora": "BD de bitácora",
}


def infra_requerida(env_mode: str = "") -> tuple[str, ...]:
    """Piezas de infraestructura que exige el modo de entorno indicado."""
    modo = (env_mode or "").upper()
    if "INTRANET" in modo:
        return INFRA_POR_MODO["INTRANET"]
    return INFRA_POR_MODO["LOCAL"]


# --------------------------------------------------------------------------- #
# entorno de pipenv
# --------------------------------------------------------------------------- #
def venv_de(servicio: str) -> Path | None:
    """Virtualenv de pipenv del servicio, si existe.

    pipenv los nombra ``<proyecto>-<hash>`` en ``WORKON_HOME``; se exige el guion
    para que ``ms_x`` no capture el de ``ms_x_otros``.
    """
    if not WORKON_HOME.is_dir():
        return None
    prefijo = f"{servicio.lower()}-"
    candidatos = [d for d in WORKON_HOME.iterdir() if d.is_dir() and d.name.lower().startswith(prefijo)]
    if not candidatos:
        return None
    return sorted(candidatos, key=lambda d: len(d.name))[0]


def salud_venv(venv: Path) -> dict[str, Any]:
    """¿El virtualenv de pipenv es utilizable? (interprete y site-packages).

    Reproduce el criterio de ``scripts/venvs.sh check``: si ``bin/python`` apunta
    a un intérprete cuya versión no tiene los paquetes instalados, el servicio
    muere con ``ModuleNotFoundError`` aunque el venv «exista».
    """
    info: dict[str, Any] = {"existe": venv.is_dir(), "ruta": str(venv)}
    python = venv / "bin" / "python"
    if not python.exists():
        info.update(problema="el virtualenv no tiene bin/python",
                    comando=f"pipenv --rm && pipenv install  # en {venv.parent}")
        return info
    try:
        real = subprocess.check_output(
            [str(python), "-c", "import sys;print('%d.%d' % sys.version_info[:2])"],
            stderr=subprocess.DEVNULL, timeout=10,
        ).decode().strip()
    except (OSError, subprocess.SubprocessError):
        info.update(problema="bin/python no se puede ejecutar (enlace roto)",
                    comando="scripts/venvs.sh fix")
        return info
    info["interprete"] = real
    site = venv / "lib" / f"python{real}" / "site-packages"
    info["site_packages"] = str(site)
    if not site.is_dir():
        otras = sorted(p.name for p in (venv / "lib").glob("python*")) if (venv / "lib").is_dir() else []
        info.update(
            problema=(f"el intérprete es {real} pero los paquetes están en "
                      f"{', '.join(otras) or 'ninguna carpeta pythonX.Y'}"),
            comando="scripts/venvs.sh fix   # realinea bin/python con su site-packages",
        )
        return info
    info["problema"] = ""
    return info


# --------------------------------------------------------------------------- #
# preflight
# --------------------------------------------------------------------------- #
def _revisar_infra(env_info: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    bloqueantes: list[dict[str, Any]] = []
    avisos: list[dict[str, Any]] = []
    modo = str(env_info.get("env_mode", "")).upper()
    for clave in infra_requerida(modo):
        puerto, host = _PUERTO_INFRA[clave]
        if clave == "bitacora":
            host = (env_info.get("database_host") or host).strip() or host
        if not is_port_open(puerto, host):
            bloqueantes.append({
                "codigo": "infra_caida",
                "pieza": clave,
                "mensaje": f"{_ETIQUETA_INFRA.get(clave, clave)} no responde en {host}:{puerto}.",
                "comando": {
                    "keydb": "podman start keydb",
                    "onlyoffice-local": "podman start onlyoffice-local",
                    "keycloak": "docker start keycloak-sisper-local",
                    "bitacora": "revisa la conectividad con la BD de bitácora",
                }.get(clave, ""),
            })
    return {"bloqueantes": bloqueantes, "avisos": avisos}


def _revisar_servicio(nombre: str, puerto: int | None, tipo: str,
                      activo: bool) -> dict[str, list[dict[str, Any]]]:
    bloqueantes: list[dict[str, Any]] = []
    avisos: list[dict[str, Any]] = []

    repo = get_service_repo_dir(nombre)
    if not repo.is_dir():
        bloqueantes.append({"codigo": "sin_repo", "mensaje": f"No existe el directorio de {nombre}.",
                            "comando": ""})
        return {"bloqueantes": bloqueantes, "avisos": avisos}

    if not (repo / ".env").is_file():
        bloqueantes.append({
            "codigo": "sin_env", "servicio": nombre,
            "mensaje": f"{nombre} no tiene .env.",
            "comando": f"cp {repo}/.env.example {repo}/.env   # y rellénalo",
        })

    if tipo == "frontend":
        if not (repo / "node_modules").is_dir():
            bloqueantes.append({
                "codigo": "sin_node_modules", "servicio": nombre,
                "mensaje": f"{nombre} no tiene node_modules.",
                "comando": f"cd {repo} && npm install",
            })
    else:
        if not (repo / "Pipfile").is_file():
            avisos.append({"codigo": "sin_pipfile", "servicio": nombre,
                           "mensaje": f"{nombre} no tiene Pipfile.",
                           "comando": f"cd {repo} && pipenv install"})
        elif not (repo / "Pipfile.lock").is_file():
            avisos.append({"codigo": "sin_lock", "servicio": nombre,
                           "mensaje": f"{nombre} no tiene Pipfile.lock.",
                           "comando": f"cd {repo} && pipenv lock"})
        venv = venv_de(nombre)
        if venv is None:
            bloqueantes.append({
                "codigo": "sin_venv", "servicio": nombre,
                "mensaje": f"{nombre} no tiene entorno de pipenv creado.",
                "comando": f"cd {repo} && pipenv install",
            })
        else:
            salud = salud_venv(venv)
            if salud.get("problema"):
                bloqueantes.append({
                    "codigo": "venv_desalineado", "servicio": nombre,
                    "mensaje": f"{nombre}: {salud['problema']}.",
                    "comando": salud.get("comando", "scripts/venvs.sh fix"),
                })

    if puerto and is_port_open(int(puerto)) and not activo:
        bloqueantes.append({
            "codigo": "puerto_ocupado", "servicio": nombre,
            "mensaje": f"El puerto {puerto} de {nombre} está ocupado por otro proceso.",
            "comando": f"ss -tlnp | grep {puerto}   # identifica quién lo tiene",
        })
    return {"bloqueantes": bloqueantes, "avisos": avisos}


def preflight(servicios: Sequence[str] | None = None, env_key: str = "develop") -> dict[str, Any]:
    """Comprobación previa al lanzamiento (sólo lectura)."""
    from devconsole.config import SERVICES_BACKEND, SERVICES_FRONTEND
    from devconsole.services.env_service import get_env_info
    from devconsole.services.terminal import get_terminal_backend

    env_info = get_env_info() or {}
    infra = _revisar_infra(env_info)

    catalogo: list[dict[str, Any]] = []
    catalogo.extend({**s, "tipo": "backend"} for s in SERVICES_BACKEND)
    catalogo.extend({**s, "tipo": "frontend"} for s in SERVICES_FRONTEND)
    por_nombre = {s["name"]: s for s in catalogo}
    objetivos = [por_nombre[n] for n in (servicios or []) if n in por_nombre] or catalogo

    backend = get_terminal_backend()
    activos = {s.metadata.get("@sisper_service") for s in backend.managed_sessions()}

    bloqueantes = list(infra["bloqueantes"])
    avisos = list(infra["avisos"])
    for svc in objetivos:
        hallazgos = _revisar_servicio(svc["name"], svc.get("port"), svc.get("tipo"),
                                      svc["name"] in activos)
        bloqueantes.extend(hallazgos["bloqueantes"])
        avisos.extend(hallazgos["avisos"])

    return {
        "env_key": env_key,
        "env_mode": env_info.get("env_mode", "DESCONOCIDO"),
        "infra_requerida": list(infra_requerida(str(env_info.get("env_mode", "")))),
        "servicios_revisados": len(objetivos),
        "bloqueantes": bloqueantes,
        "avisos": avisos,
        "ok": not bloqueantes,
    }


# --------------------------------------------------------------------------- #
# diagnóstico de un servicio
# --------------------------------------------------------------------------- #
#: (expresión regular, código, mensaje, comando sugerido)
_FIRMAS: tuple[tuple[str, str, str, str], ...] = (
    (r"ModuleNotFoundError|ImportError: No module named",
     "faltan_dependencias_python",
     "Faltan dependencias de Python en el entorno de pipenv.",
     "cd <repo> && pipenv install"),
    (r"Cannot find module|ERR_MODULE_NOT_FOUND|webpack: not found|command not found: (npm|webpack|node)",
     "faltan_dependencias_node",
     "Faltan dependencias de Node.",
     "cd <repo> && npm install"),
    (r"ImproperlyConfigured|SECRET_KEY|KeyError: '(DATABASE|KEYCLOAK|REDIS)",
     "env_incompleto",
     "El .env falta o está incompleto.",
     "cp <repo>/.env.example <repo>/.env  # y complétalo"),
    (r"Address already in use|EADDRINUSE",
     "puerto_ocupado",
     "El puerto ya está en uso por otro proceso.",
     "ss -tlnp | grep <puerto>"),
    (r"could not connect|OperationalError|Connection refused|ConnectionError",
     "dependencia_caida",
     "No puede conectar con una dependencia (BD, caché o SSO).",
     "revisa la comprobación previa: keydb / onlyoffice / keycloak / BD"),
    (r"Permission denied|EACCES",
     "permisos",
     "Problema de permisos.",
     "ls -la <repo>"),
    (r"No such file or directory: '.*\.env|\.env: No such file",
     "sin_env",
     "Falta el archivo .env.",
     "cp <repo>/.env.example <repo>/.env"),
)


def _ultimas_lineas(servicio: str, lineas: int = 120) -> list[str]:
    """Últimas líneas de la consola del servicio (lectura, sin tocar nada)."""
    from devconsole.services.terminal import get_terminal_backend

    backend = get_terminal_backend()
    sess = backend.session_name(servicio)
    try:
        proc = backend.runtime._run(  # noqa: SLF001 - mismo paquete, sólo lectura
            ["capture-pane", "-p", "-t", sess, "-S", f"-{int(lineas)}"], check=False
        )
        if proc.returncode != 0:
            return []
        return [l for l in proc.stdout.splitlines() if l.strip()]
    except Exception:
        return []


def diagnose(servicio: str) -> dict[str, Any]:
    """Por qué un servicio no arranca o se queda colgado (sólo lectura)."""
    from devconsole.config import SERVICES_BACKEND, SERVICES_FRONTEND
    from devconsole.services.terminal import get_terminal_backend

    catalogo = list(SERVICES_BACKEND) + list(SERVICES_FRONTEND)
    svc = next((s for s in catalogo if s["name"] == servicio), None)
    if svc is None:
        return {"servicio": servicio, "ok": False, "hallazgos": [
            {"codigo": "desconocido", "severidad": "error",
             "mensaje": f"{servicio} no está en el catálogo.", "comando": ""}]}

    tipo = "frontend" if svc in SERVICES_FRONTEND else "backend"
    puerto = svc.get("port")
    backend = get_terminal_backend()
    try:
        estado = backend.classify(servicio)
        estado_txt = estado.state.value
        razon = estado.reason
    except Exception as exc:  # nunca debe reventar el panel
        estado_txt, razon = "DESCONOCIDO", str(exc)

    hallazgos: list[dict[str, Any]] = []
    repo = get_service_repo_dir(servicio)

    # 1) el entorno (pipenv / node_modules / .env)
    for h in _revisar_servicio(servicio, puerto, tipo, estado_txt == "TMUX_RUNNING").get("bloqueantes", []):
        hallazgos.append({**h, "severidad": "error"})

    # 2) la salida de la consola
    lineas = _ultimas_lineas(servicio)
    texto = "\n".join(lineas)
    for patron, codigo, mensaje, comando in _FIRMAS:
        if re.search(patron, texto, re.IGNORECASE):
            if any(h["codigo"] == codigo for h in hallazgos):
                continue
            hallazgos.append({
                "codigo": codigo, "severidad": "error", "mensaje": mensaje,
                "comando": comando.replace("<repo>", str(repo)).replace("<puerto>", str(puerto or "")),
            })

    # 3) el estado real en tmux
    if estado_txt == "TMUX_STALE":
        hallazgos.append({
            "codigo": "consola_muerta", "severidad": "aviso",
            "mensaje": f"La sesión existe pero su panel no está vivo ({razon}).",
            "comando": f"reinicia la consola de {servicio} (botón Reiniciar)",
        })
    elif estado_txt == "STOPPED":
        hallazgos.append({
            "codigo": "no_arrancado", "severidad": "info",
            "mensaje": f"{servicio} no está en marcha.",
            "comando": f"lanza {servicio} desde su tarjeta (▶ Iniciar)",
        })
    elif estado_txt == "LEGACY_RUNNING":
        hallazgos.append({
            "codigo": "fuera_de_tmux", "severidad": "aviso",
            "mensaje": f"{servicio} corre como proceso propio (fuera de tmux): el panel no lo gestiona.",
            "comando": "deténlo y lánzalo desde el panel para que quede gestionado",
        })
    elif estado_txt in ("EXTERNAL_CONFLICT", "AMBIGUOUS"):
        hallazgos.append({
            "codigo": "conflicto", "severidad": "aviso",
            "mensaje": f"Estado {estado_txt} ({razon}): hay procesos o sesiones que el panel no reconoce como suyos.",
            "comando": "revisa quién ocupa el puerto o la sesión",
        })

    if not hallazgos:
        hallazgos.append({
            "codigo": "sin_hallazgos", "severidad": "ok",
            "mensaje": ("No se detecta ningún problema conocido: el servicio está en marcha "
                        if estado_txt == "TMUX_RUNNING" else "No se detecta ningún problema conocido."),
            "comando": "",
        })

    return {
        "servicio": servicio,
        "puerto": puerto,
        "tipo": tipo,
        "estado": estado_txt,
        "razon": razon,
        "repo": str(repo),
        "venv": str(venv_de(servicio) or ""),
        "lineas_leidas": len(lineas),
        "hallazgos": hallazgos,
        "ok": not any(h["severidad"] == "error" for h in hallazgos),
    }
