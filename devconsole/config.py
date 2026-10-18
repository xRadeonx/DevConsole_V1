# devconsole/config.py
import json
import os
import socket
from pathlib import Path

from devconsole import settings

DASHBOARD_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = DASHBOARD_DIR / "static"
SETTINGS_FILE = DASHBOARD_DIR / "config" / "settings.json"

def get_persisted_base_dir() -> Path:
    if SETTINGS_FILE.exists():
        try:
            cfg = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            custom_dir = cfg.get("base_dir")
            if custom_dir:
                p = Path(custom_dir).expanduser().resolve()
                if p.exists() and p.is_dir():
                    return p
        except Exception:
            pass
    return DASHBOARD_DIR

BASE_DIR = get_persisted_base_dir()
CONFIG_FILE = BASE_DIR / "config" / "services.json"
#: Repositorio de manifiestos por entorno.  Antes estaba fijado a
#: ``<raíz>/backend/config``; ahora la ruta se declara en config/panel.json
#: (``config_repo_dir``), con ``config`` como valor genérico.
CONFIG_REPO_DIR = settings.config_repo_dir(BASE_DIR)
PEAK_FILE = BASE_DIR / "data" / "operational_peak.json"

#: Nombre del proyecto, mostrado en la interfaz.  Se declara en
#: config/panel.json (``project_name``).
PROJECT_NAME = settings.project_name()

#: Registry de imágenes (p. ej. ``registry.example.com:5000``).  Se declara en
#: config/panel.json (``registry``).  Vacío = imágenes locales sin prefijo.
REGISTRY = settings.registry()


def image_ref(name: str, tag: str) -> str:
    """Referencia completa de imagen, con registry sólo si está configurado.

    Evita que un host de registry concreto quede escrito en el código: una
    instalación sin registry propio construye y etiqueta imágenes locales.
    """
    if REGISTRY:
        return f"{REGISTRY}/{name}:{tag}"
    return f"{name}:{tag}"


def default_k8s_dir(env_key: str) -> str:
    """Ruta genérica de manifiestos para un entorno.

    Sólo se usa cuando el catálogo del proyecto no declara ``k8s_dir`` para ese
    entorno.  Se deriva del ``config_repo_dir`` configurado en vez de asumir una
    estructura de carpetas concreta.
    """
    repo = settings.load().get("config_repo_dir") or "config"
    return f"{repo}/k8s/{env_key}"


def env_keys() -> tuple:
    """Nombres de entorno configurados, en orden de declaración.

    El código repetía la tupla ``("develop", "test", "main")`` en seis lugares,
    así que una instalación con otros nombres no podía usar la consola.  Se leen
    del catálogo (``config/services.json`` → ``environments``) y se conservan
    esos tres como respaldo para no quedarse sin vocabulario si todavía no hay
    catálogo.
    """
    keys = tuple(ENVIRONMENTS.keys())
    return keys or ("develop", "test", "main")

PORT = int(os.environ.get("SISPER_PORT", 9099))

# ------------------------------------------------------------------------------
# Bind address (roadmap phase 0C.3)
# ------------------------------------------------------------------------------
# DevConsole used to bind 0.0.0.0 unconditionally, exposing an orchestrator that
# can run arbitrary commands, rewrite .env files and drive kubectl to the whole
# LAN.  The default is now loopback; LAN mode requires an explicit SISPER_HOST.
HOST_ENV = "SISPER_HOST"
DEFAULT_HOST = "127.0.0.1"

#: Names accepted verbatim as loopback.
_LOOPBACK_HOST_NAMES = frozenset({"localhost", "localhost.localdomain"})


def resolve_host(raw: str | None = None) -> tuple[str, bool]:
    """Validate ``SISPER_HOST`` and return ``(host, is_loopback)``.

    Fail-closed: anything that is not ``localhost`` or a valid IP literal falls
    back to ``127.0.0.1`` rather than being passed to ``bind()``.  A malformed
    value must never widen the listener, and must never be silently honoured.

    ``0.0.0.0`` / ``::`` are honoured because the operator asked for them
    explicitly; that is the documented LAN mode.
    """
    import ipaddress

    candidate = (raw if raw is not None else os.environ.get(HOST_ENV, "")).strip()
    if not candidate:
        return DEFAULT_HOST, True

    if candidate in _LOOPBACK_HOST_NAMES:
        return candidate, True

    # Strip an optional IPv6 bracket form, e.g. "[::1]".
    bare = candidate[1:-1] if candidate.startswith("[") and candidate.endswith("]") else candidate
    try:
        address = ipaddress.ip_address(bare)
    except ValueError:
        # Not a name we recognise and not an IP literal → refuse to widen.
        return DEFAULT_HOST, True

    return candidate, bool(address.is_loopback)


HOST, HOST_IS_LOOPBACK = resolve_host()

user_local_bin = str(Path.home() / ".local" / "bin")
bun_bin = str(Path.home() / ".bun" / "bin")
current_path = os.environ.get("PATH", "")
if user_local_bin not in current_path:
    os.environ["PATH"] = f"{user_local_bin}:{bun_bin}:{current_path}"


#: Andamiaje genérico de catálogo.  Deliberadamente VACÍO: el catálogo real
#: sale del descubrimiento del espacio de trabajo y de config/services.json.
#: Antes este diccionario embebía el catálogo completo de una instalación
#: concreta, lo que impedía reutilizar el proyecto tal cual.
DEFAULT_CONFIG = {
    "project_name": PROJECT_NAME,
    "environments": {},
    "services_backend": [],
    "services_frontend": [],
    "slices": {},
}


def _ports_from_settings() -> dict:
    """Tabla de puertos declarada en config/panel.json bajo ``ports``."""
    raw = settings.load().get("ports") or {}
    return {
        str(name): int(port)
        for name, port in raw.items()
        if isinstance(port, (int, float)) and not isinstance(port, bool)
    }


#: Tabla de puertos de la instalación.  Sustituye a la tabla fija que vivía en
#: este módulo: una instalación nueva declara sus puertos en su propio archivo
#: (o simplemente los deja al descubrimiento) sin editar código Python.
KNOWN_PORTS: dict[str, int] = _ports_from_settings()


def k8s_dir_for(env_key: str) -> str:
    """Carpeta de manifiestos k8s del entorno, leída EN VIVO.

    ``k8s_service`` importa ``ENVIRONMENTS`` por valor, así que tras cambiar la
    carpeta desde la pestaña «Sitio» su binding quedaría obsoleto.  Esta función
    lee el ``CONFIG`` del módulo (que ``reload_config()`` sí reasigna), de modo
    que el cambio se aplica sin reiniciar el panel.
    """
    env_cfg = (CONFIG.get("environments") or {}).get(env_key) or {}
    return env_cfg.get("k8s_dir") or default_k8s_dir(env_key)


def catalog_services() -> list[dict]:
    """Servicios del catálogo vigente (leído en vivo; ver ``k8s_dir_for``)."""
    out: list[dict] = []
    for key in ("services_backend", "services_frontend", "workers"):
        out.extend(CONFIG.get(key) or [])
    return out


def save_k8s_dir(env_key: str, new_dir: str) -> tuple[bool, str]:
    """Fija ``environments.<env>.k8s_dir`` en el catálogo del proyecto.

    Escribe con copia de seguridad (``.bak``) y reemplazo atómico, y recarga la
    configuración para que el resto del panel la vea sin reiniciar.
    """
    if env_key not in env_keys():
        return False, f"Entorno desconocido: {env_key}"
    if not CONFIG_FILE.is_file():
        return False, f"No se encontró el catálogo: {CONFIG_FILE}"
    try:
        raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return False, f"No se pudo leer el catálogo: {exc}"
    if not isinstance(raw, dict):
        return False, "El catálogo no tiene el formato esperado."
    entornos = raw.setdefault("environments", {})
    if not isinstance(entornos, dict):
        return False, "La sección 'environments' del catálogo es inválida."
    entornos.setdefault(env_key, {})
    if not isinstance(entornos[env_key], dict):
        return False, f"La sección 'environments.{env_key}' del catálogo es inválida."
    entornos[env_key]["k8s_dir"] = new_dir

    tmp = CONFIG_FILE.with_suffix(".json.tmp")
    try:
        backup = CONFIG_FILE.with_suffix(".json.bak")
        backup.write_text(CONFIG_FILE.read_text(encoding="utf-8"), encoding="utf-8")
        tmp.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(CONFIG_FILE)
    except OSError as exc:
        return False, f"No se pudo guardar el catálogo: {exc}"
    reload_config()
    try:
        from devconsole import settings as _settings
        _settings.reload()
    except Exception:
        pass
    return True, f"Carpeta de manifiestos de {env_key} fijada en {new_dir}"


def reload_known_ports() -> dict:
    """Vuelve a leer la tabla de puertos desde la configuración externa."""
    global KNOWN_PORTS
    settings.reload()
    KNOWN_PORTS = _ports_from_settings()
    return KNOWN_PORTS


def _is_excluded_dir(name: str) -> bool:
    """¿Este directorio debe ignorarse al descubrir servicios?

    Las exclusiones se declaran en config/panel.json (``discovery``).  Antes
    estaban escritas aquí con nombres concretos de una instalación
    (directorios de metadatos propios, un prefijo de carpeta de QA), así que
    otra instalación no podía ajustarlas sin editar código.
    """
    names, prefixes = settings.discovery_exclusions()
    return name in names or (bool(prefixes) and name.startswith(prefixes))


def read_catalog_file() -> dict:
    """Lee el catálogo del proyecto (``config/services.json``).

    Se usa tanto para descubrir servicios como para completar los metadatos que
    no se pueden deducir del sistema de archivos (``k8s_file``, ``k8s_deploy``,
    ``group``).  Antes esos mapeos vivían embebidos en este módulo, lo que
    obligaba a editar Python para cada proyecto.
    """
    if not CONFIG_FILE.exists():
        return {}
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[!] Error leyendo config/services.json: {e}")
        return {}
    return data if isinstance(data, dict) else {}


def _catalog_meta_maps() -> tuple[dict, dict]:
    """Metadatos por nombre de servicio, desde el catálogo del proyecto."""
    file_cfg = read_catalog_file()

    def _index(key: str) -> dict:
        return {
            s["name"]: s
            for s in (file_cfg.get(key) or [])
            if isinstance(s, dict) and s.get("name")
        }

    return _index("services_backend"), _index("services_frontend")


def discover_services() -> tuple[list[dict], list[dict]]:
    backend_svcs = []
    frontend_svcs = []

    # Los metadatos declarados por el proyecto mandan sobre cualquier heurística;
    # lo que no esté en el catálogo se completa por descubrimiento.
    default_b_map, default_f_map = _catalog_meta_maps()

    # 1. Escanear directorio backend
    backend_dir = BASE_DIR / "backend"
    if backend_dir.exists() and backend_dir.is_dir():
        for d in sorted(backend_dir.iterdir()):
            if not d.is_dir() or _is_excluded_dir(d.name):
                continue
            if d.name.startswith("ms_") or (d / "manage.py").exists():
                base = dict(default_b_map.get(d.name, {}))
                port = base.get("port") or KNOWN_PORTS.get(d.name)
                env_file = d / ".env"
                if env_file.exists():
                    try:
                        content = env_file.read_text(encoding="utf-8", errors="ignore")
                        for line in content.splitlines():
                            line = line.strip()
                            if line.startswith("PORT=") or line.startswith("DAPHNE_PORT="):
                                try:
                                    port = int(line.split("=", 1)[1].strip().strip('"').strip("'"))
                                except Exception:
                                    pass
                    except Exception:
                        pass
                if not port:
                    port = 8000 + len(backend_svcs) + 20

                clean_name = d.name.replace("_", "-")
                k8s_deploy = base.get("k8s_deploy") or clean_name.replace("ms-sisper-", "ms-")
                group = base.get("group") or ("Backend 2" if len(backend_svcs) >= 12 else "Backend 1")
                k8s_file = base.get("k8s_file") or f"backend/{d.name}.yaml"
                has_consumer = bool(list(d.glob("**/start_consumer.py")) or list(d.glob("**/run_consumer.py")))
                has_worker = (d / "config" / "celery.py").exists() or bool(list(d.glob("**/tasks.py")))
                backend_svcs.append({
                    "name": d.name,
                    "port": port,
                    "group": group,
                    "k8s_file": k8s_file,
                    "k8s_deploy": k8s_deploy,
                    "has_consumer": has_consumer,
                    "has_worker": has_worker
                })

    # 2. Escanear directorio frontend
    frontend_dir = BASE_DIR / "frontend"
    if frontend_dir.exists() and frontend_dir.is_dir():
        for d in sorted(frontend_dir.iterdir()):
            if not d.is_dir() or _is_excluded_dir(d.name):
                continue
            if (d / "package.json").exists() or (d / ".git").exists() or d.name.startswith("mf_"):
                base = dict(default_f_map.get(d.name, {}))
                port = base.get("port") or KNOWN_PORTS.get(d.name)
                env_file = d / ".env"
                if env_file.exists():
                    try:
                        content = env_file.read_text(encoding="utf-8", errors="ignore")
                        for line in content.splitlines():
                            line = line.strip()
                            if line.startswith("PORT="):
                                try:
                                    port = int(line.split("=", 1)[1].strip().strip('"').strip("'"))
                                except Exception:
                                    pass
                    except Exception:
                        pass
                if not port:
                    port = 3000 + len(frontend_svcs) + 12
                clean_name = d.name.replace("_", "-")
                k8s_deploy = base.get("k8s_deploy") or clean_name.replace("mf-sisper-", "mf-")
                k8s_file = base.get("k8s_file") or f"frontend/{d.name}.yaml"
                frontend_svcs.append({
                    "name": d.name,
                    "port": port,
                    "k8s_file": k8s_file,
                    "k8s_deploy": k8s_deploy
                })

    return backend_svcs, frontend_svcs


def _merge_services(discovered: list[dict], declared: list[dict] | None) -> list[dict]:
    """Fusiona lo descubierto en disco con lo declarado en el catálogo.

    El catálogo del proyecto manda sobre los metadatos que no se pueden deducir
    del sistema de archivos (``k8s_file``, ``k8s_deploy``, ``group``).  Lo
    declarado pero ausente del disco se conserva, para poder operar un servicio
    que todavía no se ha clonado.
    """
    declared_map = {
        s["name"]: s for s in (declared or []) if isinstance(s, dict) and s.get("name")
    }
    merged: list[dict] = []
    seen: set[str] = set()

    for svc in discovered:
        name = svc["name"]
        seen.add(name)
        if name in declared_map:
            merged.append({**svc, **declared_map[name]})
        else:
            merged.append(svc)

    for svc in declared or []:
        if isinstance(svc, dict) and svc.get("name") not in seen:
            merged.append(svc)

    return merged


def load_config() -> dict:
    discovered_backend, discovered_frontend = discover_services()
    file_cfg = read_catalog_file()

    cfg = dict(DEFAULT_CONFIG)
    cfg["services_backend"] = _merge_services(
        discovered_backend, file_cfg.get("services_backend")
    )
    cfg["services_frontend"] = _merge_services(
        discovered_frontend, file_cfg.get("services_frontend")
    )

    # El catálogo del proyecto puede sobrescribir el nombre mostrado, que por
    # defecto viene de config/panel.json.
    if file_cfg.get("project_name"):
        cfg["project_name"] = file_cfg["project_name"]

    if "slices" in file_cfg:
        cfg["slices"] = file_cfg["slices"]
    if "environments" in file_cfg:
        cfg["environments"] = file_cfg["environments"]

    return cfg


CONFIG = load_config()
SERVICES_BACKEND = CONFIG.get("services_backend", DEFAULT_CONFIG["services_backend"])
SERVICES_FRONTEND = CONFIG.get("services_frontend", DEFAULT_CONFIG["services_frontend"])
SLICES = CONFIG.get("slices", DEFAULT_CONFIG["slices"])
ENVIRONMENTS = CONFIG.get("environments", DEFAULT_CONFIG["environments"])


def reload_config() -> dict:
    global CONFIG, SERVICES_BACKEND, SERVICES_FRONTEND, SLICES, ENVIRONMENTS
    CONFIG = load_config()
    SERVICES_BACKEND = CONFIG.get("services_backend", DEFAULT_CONFIG["services_backend"])
    SERVICES_FRONTEND = CONFIG.get("services_frontend", DEFAULT_CONFIG["services_frontend"])
    SLICES = CONFIG.get("slices", DEFAULT_CONFIG["slices"])
    ENVIRONMENTS = CONFIG.get("environments", DEFAULT_CONFIG["environments"])
    return CONFIG


def inspect_directory(dir_path: str | Path) -> dict:
    p = Path(dir_path).expanduser().resolve()
    if not p.exists():
        return {
            "valid": False,
            "error": f"La ruta especificada no existe: {p}",
            "path": str(p),
            "folder_name": p.name or str(p)
        }
    if not p.is_dir():
        return {
            "valid": False,
            "error": f"La ruta no es un directorio: {p}",
            "path": str(p),
            "folder_name": p.name or str(p)
        }

    backend_dir = p / "backend"
    frontend_dir = p / "frontend"
    has_backend_dir = backend_dir.exists() and backend_dir.is_dir()
    has_frontend_dir = frontend_dir.exists() and frontend_dir.is_dir()
    has_config_json = (p / "config" / "services.json").exists()

    b_svcs = []
    if has_backend_dir:
        try:
            for d in sorted(backend_dir.iterdir()):
                if not d.is_dir() or _is_excluded_dir(d.name):
                    continue
                if d.name.startswith("ms_") or (d / "manage.py").exists():
                    b_svcs.append(d.name)
        except Exception:
            pass

    f_svcs = []
    if has_frontend_dir:
        try:
            for d in sorted(frontend_dir.iterdir()):
                if not d.is_dir() or _is_excluded_dir(d.name):
                    continue
                if (d / "package.json").exists() or (d / ".git").exists() or d.name.startswith("mf_"):
                    f_svcs.append(d.name)
        except Exception:
            pass

    subdirs = []
    try:
        for item in sorted(p.iterdir()):
            if item.is_dir() and not _is_excluded_dir(item.name):
                subdirs.append({
                    "name": item.name,
                    "path": str(item)
                })
    except Exception:
        pass

    parent_dir = str(p.parent) if p.parent != p else None

    return {
        "valid": True,
        "path": str(p),
        "folder_name": p.name or str(p),
        "has_backend_dir": has_backend_dir,
        "has_frontend_dir": has_frontend_dir,
        "has_config_json": has_config_json,
        "backend_services": b_svcs,
        "frontend_services": f_svcs,
        "backend_count": len(b_svcs),
        "frontend_count": len(f_svcs),
        "subdirs": subdirs[:40],
        "parent_dir": parent_dir
    }


def set_base_dir(new_path: str | Path) -> tuple[bool, str, dict]:
    global BASE_DIR, CONFIG_FILE, CONFIG_REPO_DIR, PEAK_FILE
    global CONFIG, SERVICES_BACKEND, SERVICES_FRONTEND, SLICES, ENVIRONMENTS
    
    p = Path(new_path).expanduser().resolve()
    if not p.exists():
        return False, f"La ruta especificada no existe: {p}", {}
    if not p.is_dir():
        return False, f"La ruta no es un directorio: {p}", {}

    # Persistir en settings.json
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if SETTINGS_FILE.exists():
            try:
                data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        data["base_dir"] = str(p)
        SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        return False, f"No se pudo guardar la configuración: {e}", {}

    # Actualizar globales en config
    BASE_DIR = p
    CONFIG_FILE = BASE_DIR / "config" / "services.json"
    CONFIG_REPO_DIR = settings.config_repo_dir(p)
    PEAK_FILE = BASE_DIR / "data" / "operational_peak.json"

    # Propagar a todos los submódulos cargados en sys.modules
    import sys
    for mod_name, mod in list(sys.modules.items()):
        if mod_name.startswith("devconsole") and mod:
            for attr, val in [("BASE_DIR", BASE_DIR), ("CONFIG_FILE", CONFIG_FILE), ("CONFIG_REPO_DIR", CONFIG_REPO_DIR), ("PEAK_FILE", PEAK_FILE)]:
                if hasattr(mod, attr):
                    try:
                        setattr(mod, attr, val)
                    except Exception:
                        pass

    # Recargar servicios dinámicamente con la nueva ruta
    reload_config()
    
    # Propagar nuevas listas de servicios a los módulos importados
    for mod_name, mod in list(sys.modules.items()):
        if mod_name.startswith("devconsole") and mod:
            for attr, val in [("SERVICES_BACKEND", SERVICES_BACKEND), ("SERVICES_FRONTEND", SERVICES_FRONTEND), ("SLICES", SLICES), ("ENVIRONMENTS", ENVIRONMENTS), ("CONFIG", CONFIG)]:
                if hasattr(mod, attr):
                    try:
                        setattr(mod, attr, val)
                    except Exception:
                        pass

    return True, f"Directorio raíz actualizado a: {p}", {
        "base_dir": str(p),
        "backend_count": len(SERVICES_BACKEND),
        "frontend_count": len(SERVICES_FRONTEND),
        "folder_name": p.name or str(p)
    }


# ------------------------------------------------------------------------------
# Métodos de Red, Puertos y Git
# ------------------------------------------------------------------------------

def is_port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.10)
        return s.connect_ex((host, port)) == 0


def get_service_repo_dir(service_name: str) -> Path:
    repo = BASE_DIR / "backend" / service_name
    if not repo.exists():
        repo = BASE_DIR / "frontend" / service_name
    return repo



#: Temas estacionales ofrecidos por la interfaz.  Se declaran en
#: config/panel.json (``seasonal_themes``); por defecto sólo los genéricos,
#: para no imponer el calendario de un país concreto.
AVAILABLE_SEASONAL_THEMES = settings.seasonal_themes()


#: Contenedores de infraestructura local.  Se declaran en config/panel.json
#: (``infra_containers``).  Los argumentos que llevan credenciales usan el
#: marcador ``__SECRET__…__``, que se resuelve desde secrets.json.
INFRA_CONTAINERS = settings.infra_containers()


#: Configuración de Keycloak por entorno: endpoints y client_id en panel.json;
#: ``client_secret`` en secrets.json, referenciado con un marcador.
KEYCLOAK_ENV_CONFIGS = settings.keycloak_configs()


#: Datos de conexión a bases por entorno: host, puerto y usuarios en
#: panel.json; las contraseñas en secrets.json vía marcador.
DATABASE_ENV_CONFIGS = settings.database_configs()


def normalize_env_key(env_key: str) -> str:
    k = (env_key or "develop").strip().lower()
    if k in ("main", "prod", "produccion"):
        return "main"
    if k in ("test", "qa", "testing"):
        return "test"
    if k in ("dev", "develop", "desarrollo"):
        return "develop"
    return k


