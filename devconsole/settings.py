# devconsole/settings.py
"""Configuración externa de la instalación.

El código no debe contener datos de una instalación concreta: nombre del
proyecto, registry de imágenes, contenedores de infraestructura, endpoints
internos ni credenciales.  Todo eso vive en dos archivos dentro de ``config/``:

* ``config/panel.json``   — datos del proyecto.  Versionable.
* ``config/secrets.json`` — **sólo credenciales.  No versionar.**

Cualquiera de los dos puede faltar: en ese caso la aplicación arranca con
valores genéricos y el descubrimiento de servicios como única fuente de
catálogo, de modo que un proyecto nuevo funciona sin escribir configuración.

Las credenciales nunca se escriben en ``panel.json``.  En su lugar se usa un
marcador ``__SECRET__ruta.dentro.de.secrets__`` que este módulo resuelve al
cargar.  Así ``panel.json`` se puede compartir tal cual, sin exponer nada, y a
la vez la estructura completa (incluidos los argumentos que llevan la
credencial) sigue siendo legible y versionable.

Uso::

    from devconsole import settings

    settings.registry()            # "registry.example.com:5000" o ""
    settings.infra_containers()    # dict con la forma histórica de INFRA_CONTAINERS
    settings.reload()              # tras editar los archivos en caliente
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

DASHBOARD_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = DASHBOARD_DIR / "config"
PANEL_FILE = CONFIG_DIR / "panel.json"
SECRETS_FILE = CONFIG_DIR / "secrets.json"

# Si falta config/secrets.json pero está la plantilla, se crea con la estructura
# de ejemplo: así sólo hay que rellenar valores (antes había que adivinar el
# formato, que es justo lo que dejaba el panel a medias).
try:
    _plantilla = CONFIG_DIR / "secrets.example.json"
    if not SECRETS_FILE.exists() and _plantilla.exists():
        SECRETS_FILE.write_text(_plantilla.read_text(encoding="utf-8"), encoding="utf-8")
        SECRETS_FILE.chmod(0o600)
        print(f"[*] Creado {SECRETS_FILE} desde la plantilla; rellena tus credenciales.")
except Exception as _exc:  # nunca debe impedir que el panel arranque
    print(f"[!] No se pudo preparar {SECRETS_FILE}: {_exc}")

_SECRET_TOKEN = re.compile(r"__SECRET__([A-Za-z0-9_.\-]+)__")

#: Exclusiones genéricas del descubrimiento: directorios que nunca son un
#: servicio (metadatos, entornos virtuales, artefactos de build).
DEFAULT_DISCOVERY: dict[str, Any] = {
    "exclude_names": [
        "config", "__pycache__", "venv", ".venv", "env",
        "node_modules", "dist", "build",
    ],
    "exclude_prefixes": ["."],
}

#: Valores genéricos.  Un proyecto sin ``panel.json`` debe funcionar igual: el
#: catálogo sale del descubrimiento y no se asume ningún servicio ni endpoint.
DEFAULT_PANEL: dict[str, Any] = {
    "project_name": "",
    "registry": "",
    "local_subnet": "",
    "config_repo_dir": "config",
    "discovery": DEFAULT_DISCOVERY,
    "infra_containers": {},
    "keycloak": {},
    "databases": {},
    "seasonal_themes": [
        {"id": "none", "label": "Base", "description": "Diseño institucional estándar"},
        {"id": "auto", "label": "Automático según calendario", "description": "Activa temas según la fecha"},
    ],
}

_MISSING = object()

_cache: dict[str, Any] | None = None
_unresolved: list[str] = []


def _read_json(path: Path) -> dict:
    """Lee un JSON de configuración; su ausencia no es un error."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except Exception as exc:
        print(f"[!] No se pudo leer {path.name}: {exc}")
        return {}
    return data if isinstance(data, dict) else {}


def _lookup(tree: Any, dotted: str) -> Any:
    node = tree
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return _MISSING
        node = node[part]
    return node


def _resolve_secrets(node: Any, secrets: dict, unresolved: list[str]) -> Any:
    """Sustituye los marcadores ``__SECRET__…__`` por su valor real.

    Un marcador sin valor se sustituye por cadena vacía y se registra, de modo
    que una instalación a la que le falte una credencial arranca e informa en
    lugar de romper al cargar el módulo.
    """
    if isinstance(node, dict):
        return {k: _resolve_secrets(v, secrets, unresolved) for k, v in node.items()}
    if isinstance(node, list):
        return [_resolve_secrets(v, secrets, unresolved) for v in node]
    if isinstance(node, str) and _SECRET_TOKEN.search(node):
        def _sub(match: re.Match) -> str:
            value = _lookup(secrets, match.group(1))
            if value is _MISSING:
                unresolved.append(match.group(1))
                return ""
            return str(value)

        return _SECRET_TOKEN.sub(_sub, node)
    return node


def _merge_defaults(base: dict, override: dict) -> dict:
    """Fusiona ``override`` sobre ``base`` (un nivel de profundidad basta aquí)."""
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


def load() -> dict:
    """Carga (y cachea) la configuración efectiva de la instalación."""
    global _cache, _unresolved
    if _cache is not None:
        return _cache

    secrets = _read_json(SECRETS_FILE)
    unresolved: list[str] = []
    panel = _resolve_secrets(_read_json(PANEL_FILE), secrets, unresolved)

    _unresolved = sorted(set(unresolved))
    if _unresolved:
        print("[!] Secretos referenciados por panel.json sin valor en secrets.json: "
              + ", ".join(_unresolved))

    _cache = _merge_defaults(DEFAULT_PANEL, panel)
    return _cache


def reload() -> dict:
    """Descarta la caché y vuelve a leer los archivos."""
    global _cache
    _cache = None
    return load()


def unresolved_secrets() -> list[str]:
    """Marcadores ``__SECRET__…__`` que no se pudieron resolver."""
    load()
    return list(_unresolved)


# ------------------------------------------------------------------------------
# Accesores
# ------------------------------------------------------------------------------
# Se ofrecen funciones en vez de exponer el dict para que los consumidores no
# dependan de la forma interna y para poder recargar sin reimportar.

def project_name() -> str:
    return str(load().get("project_name") or "")


def registry() -> str:
    """Registry de imágenes, sin barra final.  Vacío = imágenes locales."""
    return str(load().get("registry") or "").rstrip("/")


def local_subnet() -> str:
    """Prefijo de la subred local, p. ej. ``10.0.0``.  Vacío = autodetectar."""
    return str(load().get("local_subnet") or "").rstrip(".")


def config_repo_dir(base_dir: Path | None = None) -> Path:
    """Ruta del repositorio de manifiestos por entorno.

    ``base_dir`` se recibe como argumento para que ``devconsole.config`` pueda
    resolverla durante su propia carga sin una importación circular.
    """
    if base_dir is None:
        from devconsole.config import BASE_DIR

        base_dir = BASE_DIR

    return Path(base_dir) / str(load().get("config_repo_dir") or "config")


def infra_containers() -> dict:
    return dict(load().get("infra_containers") or {})


def keycloak_configs() -> dict:
    return dict(load().get("keycloak") or {})


def database_configs() -> dict:
    return dict(load().get("databases") or {})


def infra_targets() -> dict:
    """Destinos de infraestructura por entorno (hosts, URLs, comandos de prueba).

    Son datos de la instalación: antes vivían escritos en el JavaScript de la
    interfaz, con direcciones internas y comandos de una instalación concreta.
    """
    targets = load().get("infra_targets")
    return dict(targets) if isinstance(targets, dict) else {}


def discovery_exclusions() -> tuple[set, tuple]:
    """Nombres y prefijos de directorio que el descubrimiento debe ignorar.

    Se declaran en config/panel.json (``discovery``).  Antes estaban escritos en
    ``config.py`` con nombres de una instalación concreta —directorios de
    metadatos propios, un prefijo de carpeta de QA—, de modo que otra
    instalación no podía ajustarlos sin editar código.

    Devuelve ``(nombres, prefijos)``.
    """
    cfg = load().get("discovery") or {}
    names = cfg.get("exclude_names")
    prefixes = cfg.get("exclude_prefixes")
    if not isinstance(names, list):
        names = DEFAULT_DISCOVERY["exclude_names"]
    if not isinstance(prefixes, list):
        prefixes = DEFAULT_DISCOVERY["exclude_prefixes"]
    return {str(n) for n in names}, tuple(str(p) for p in prefixes)


def onlyoffice_sync_service() -> str:
    """Servicio cuyo ``.env`` recibe las variables de OnlyOffice.

    Es un dato del proyecto: antes el nombre del servicio estaba escrito en la
    lógica y también en los mensajes que ve el usuario.
    """
    return str(load().get("onlyoffice_sync_service") or "")


def seasonal_themes() -> list:
    themes = load().get("seasonal_themes")
    return list(themes) if isinstance(themes, list) else list(DEFAULT_PANEL["seasonal_themes"])


def secret(dotted: str, default: str = "") -> str:
    """Valor puntual de ``config/secrets.json``, por ruta con puntos.

    Para el código que necesita una credencial suelta (por ejemplo, el secreto
    JWT con el que se genera un ``.env``) sin pasar por un marcador.
    """
    value = _lookup(_read_json(SECRETS_FILE), dotted)
    return default if value is _MISSING else str(value)


# --------------------------------------------------------------------------- #
# Editor de secretos (interfaz)
# --------------------------------------------------------------------------- #
def referenced_secret_keys() -> list[str]:
    """Claves de ``secrets.json`` que la configuración reclama.

    Se apoya en la misma resolución que usa el aviso de arranque
    (``_resolve_secrets``): pasando un almacén vacío, todo lo referenciado queda
    como «no resuelto», que es justo la lista de claves necesarias.
    """
    faltan: list[str] = []
    try:
        # Se parte del panel.json **sin resolver** (load() ya sustituye los
        # secretos por sus valores, así que ahí no queda ninguna referencia).
        panel = _read_json(CONFIG_DIR / "panel.json")
        _resolve_secrets(panel, {}, faltan)
    except Exception:
        pass
    return sorted({k for k in faltan if k})


def secret_values_present() -> set[str]:
    """Claves de ``secrets.json`` que ya tienen valor (no se revelan)."""
    datos = {}
    try:
        if SECRETS_FILE.exists():
            datos = json.loads(SECRETS_FILE.read_text(encoding="utf-8")) or {}
    except Exception:
        datos = {}
    presentes: set[str] = set()

    def _walk(nodo, ruta=""):
        if isinstance(nodo, dict):
            for k, v in nodo.items():
                _walk(v, f"{ruta}.{k}" if ruta else str(k))
        elif isinstance(nodo, str) and nodo.strip():
            presentes.add(ruta)

    _walk(datos)
    return presentes


def set_secrets(valores: dict) -> tuple[bool, str]:
    """Escribe valores en ``config/secrets.json`` (0600), creando el fichero."""
    if not isinstance(valores, dict) or not valores:
        return False, "No hay valores que guardar."
    datos = {}
    try:
        if SECRETS_FILE.exists():
            datos = json.loads(SECRETS_FILE.read_text(encoding="utf-8")) or {}
    except Exception:
        datos = {}
    for ruta, valor in valores.items():
        if not isinstance(ruta, str) or not ruta.strip():
            continue
        partes = [x for x in ruta.split(".") if x]
        nodo = datos
        for parte in partes[:-1]:
            nodo = nodo.setdefault(parte, {})
            if not isinstance(nodo, dict):
                return False, f"La ruta {ruta} choca con un valor existente."
        nodo[partes[-1]] = valor
    try:
        SECRETS_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = SECRETS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(datos, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.chmod(0o600)
        tmp.replace(SECRETS_FILE)
    except Exception as exc:
        return False, f"No se pudo guardar: {exc}"
    return True, f"{len(valores)} secreto(s) guardados en {SECRETS_FILE}."


# --------------------------------------------------------------------------- #
# Búsqueda de secretos en los .env de los microservicios
# --------------------------------------------------------------------------- #
#: Variable del .env de un servicio → clave que el panel necesita.
_MAPA_SECRETOS_SERVICIOS = (
    ("ONLYOFFICE_JWT_SECRET", "infra.onlyoffice_jwt_secret"),
    ("KEYCLOAK_CLIENT_SECRET_KEY", "keycloak.{env}.client_secret"),
    ("KEYCLOAK_CLIENT_SECRET", "keycloak.{env}.client_secret"),
)
#: Servicio cuyo .env guarda la clave de cada base de datos.
_SERVICIO_POR_BD = {"bitacora": "ms_sisper_bitacora",
                    "contratos": "ms_sisper_contratos",
                    "destinaciones": "ms_sisper_destinaciones"}


def _leer_env(ruta: Path) -> dict:
    datos = {}
    try:
        for linea in ruta.read_text(encoding="utf-8", errors="ignore").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            datos[clave.strip()] = valor.strip().strip('"').strip("'")
    except Exception:
        pass
    return datos


def _enmascarar(valor: str) -> str:
    v = valor or ""
    return (v[:2] + "…" + v[-2:]) if len(v) > 6 else "…"


def buscar_secretos_en_servicios(env_key: str = "develop") -> list[dict]:
    """Busca en los ``.env`` de los servicios lo que el panel necesita.

    Devuelve candidatos con su origen; **no** escribe nada (el guardado lo hace
    el usuario desde el editor).  Sólo lectura de ``<carpeta>/backend|frontend``.
    """
    from devconsole import config as _cfg  # import perezoso: evita ciclos

    requeridas = set(referenced_secret_keys())
    hallazgos: list[dict] = []
    raiz = _cfg.BASE_DIR

    for base, prefijo in ((raiz / "backend", "ms_"), (raiz / "frontend", "mf_")):
        if not base.is_dir():
            continue
        for servicio in sorted(base.iterdir()):
            if not servicio.is_dir() or not servicio.name.startswith(prefijo):
                continue
            env = _leer_env(servicio / ".env")
            if not env:
                continue
            candidatos: list[tuple[str, str]] = []
            for var, plantilla in _MAPA_SECRETOS_SERVICIOS:
                if env.get(var):
                    candidatos.append((plantilla.format(env=env_key), env[var]))
            if env.get("DATABASE_PASSWORD"):
                nombre = servicio.name
                for bd, svc in _SERVICIO_POR_BD.items():
                    if svc == nombre:
                        candidatos.append((f"databases.{env_key}.{bd}_pass", env["DATABASE_PASSWORD"]))
            for clave, valor in candidatos:
                if clave in requeridas and valor.strip():
                    hallazgos.append({
                        "clave": clave,
                        "valor": valor.strip(),
                        "pista": _enmascarar(valor.strip()),
                        "origen": f"{servicio.name}/.env",
                    })
    # Sin duplicados: se conserva el primero que aparezca.
    vistos, unicos = set(), []
    for h in hallazgos:
        if h["clave"] not in vistos:
            vistos.add(h["clave"])
            unicos.append(h)
    return unicos
