"""Configuración del sitio por entorno (pestaña «Sitio»).

Reúne lo que es administración del sitio y **depende del entorno**: el tema
estacional del cluster y la carpeta de manifiestos k8s (YAML) que alimenta la
matriz de despliegues.

El problema que resuelve: la carpeta de manifiestos se configuraba sólo en
``config/services.json`` (``environments.<env>.k8s_dir``) sin ninguna forma de
verla ni cambiarla desde la interfaz, y sin saber qué YAML faltaban respecto al
catálogo.  Aquí se expone el inventario (presentes, esperados por servicio y
sobrantes) y se permite fijar otra carpeta.

Solo lectura salvo :func:`set_k8s_dir`, que escribe el catálogo por petición
explícita del usuario y deja copia ``.bak``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from devconsole import settings
from devconsole.config import (
    BASE_DIR,
    CONFIG_FILE,
    catalog_services,
    env_keys,
    k8s_dir_for,
    save_k8s_dir,
)

__all__ = ["site_config", "browse_directories", "set_k8s_dir"]

#: Extensiones consideradas manifiestos.
_YAML_SUFFIXES = (".yaml", ".yml")
#: Topes para no volcar una carpeta enorme en la interfaz.
_MAX_FILES = 400
_MAX_DIRS = 200
#: Carpetas que nunca interesa listar (ruido de modelos/binarios).
_SKIP_DIRS = {"__pycache__", "node_modules", ".git", "ollama-models"}

#: Manifiestos que no pertenecen a un servicio concreto del catálogo.
_KNOWN_EXTRAS = ("ingress", "onlyoffice", "keydb", "grafana", "prometheus", "ollama", "namespace", "volumes")


def _yaml_files(root: Path) -> list[dict[str, Any]]:
    """Manifiestos bajo ``root`` (relativos), acotados y sin carpetas de ruido."""
    out: list[dict[str, Any]] = []
    if not root.is_dir():
        return out
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS and not d.startswith("."))
        for name in sorted(filenames):
            if not name.lower().endswith(_YAML_SUFFIXES):
                continue
            full = Path(dirpath) / name
            try:
                st = full.stat()
            except OSError:
                continue
            out.append({
                "rel": str(full.relative_to(root)),
                "name": name,
                "size": st.st_size,
                "mtime": int(st.st_mtime),
            })
            if len(out) >= _MAX_FILES:
                return out
    return out


def _expected(env_key: str, base: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """YAML que el catálogo espera para este entorno, y los que no son de servicio."""
    esperados: list[dict[str, Any]] = []
    referenciados: set[str] = set()
    for svc in catalog_services():
        rel = svc.get("k8s_file")
        if not rel:
            continue
        referenciados.add(rel)
        esperados.append({
            "service": svc.get("name", ""),
            "file": rel,
            "present": (base / rel).is_file(),
        })
    return esperados, sorted(referenciados)


def _expected_in(carpeta: Path) -> tuple[int, int]:
    """Cuántos YAML del catálogo están **directamente** en esta carpeta.

    Es el criterio que decide si una carpeta sirve: el despliegue busca
    ``k8s_dir / k8s_file`` (``backend/ms_sesion.yaml``), así que apuntar a un
    padre tipo ``k8s/`` da 0 aciertos aunque tenga más YAML debajo.  Se cuenta
    leyendo el catálogo (sin recorrer el sistema de ficheros completo).
    """
    esperados = [s.get("k8s_file") for s in catalog_services() if s.get("k8s_file")]
    if not esperados:
        return 0, 0
    presentes = sum(1 for rel in esperados if (carpeta / rel).is_file())
    return presentes, len(esperados)


def _relative_to_base(path: Path) -> str:
    """Ruta relativa a la raíz del panel si está dentro; si no, absoluta."""
    try:
        return str(path.relative_to(BASE_DIR))
    except ValueError:
        return str(path)


def site_config(env_key: str = "develop") -> dict[str, Any]:
    """Estado de la configuración de sitio para un entorno (solo lectura)."""
    entornos = list(env_keys())
    if env_key not in entornos:
        env_key = entornos[0] if entornos else "develop"

    k8s_dir_rel = k8s_dir_for(env_key)
    k8s_dir = Path(k8s_dir_rel)
    if not k8s_dir.is_absolute():
        k8s_dir = BASE_DIR / k8s_dir_rel
    k8s_dir = k8s_dir.expanduser()

    archivos = _yaml_files(k8s_dir)
    esperados, referenciados = _expected(env_key, k8s_dir)
    faltan = [e for e in esperados if not e["present"]]

    por_carpeta: dict[str, int] = {}
    for f in archivos:
        carpeta = str(Path(f["rel"]).parent)
        carpeta = "." if carpeta == "." else carpeta
        por_carpeta[carpeta] = por_carpeta.get(carpeta, 0) + 1

    # El nombre y el namespace del entorno viven en el catálogo, no en panel.json:
    # se leen del módulo `config` (que `reload_config()` reasigna).
    from devconsole import config as dcfg
    env_cfg = (dcfg.CONFIG.get("environments") or {}).get(env_key) or {}
    extras = sorted({
        f["rel"] for f in archivos
        if f["rel"] not in referenciados
        and any(f["name"].lower().startswith(x) for x in _KNOWN_EXTRAS)
    })

    return {
        "env": env_key,
        "entornos": entornos,
        "namespace": env_cfg.get("namespace", env_key),
        "label": env_cfg.get("label", env_key),
        "k8s_dir": k8s_dir_rel,
        "k8s_dir_abs": str(k8s_dir),
        "exists": k8s_dir.is_dir(),
        "es_por_defecto": str(k8s_dir_abs_default(env_key)) == str(k8s_dir),
        "base_dir": str(BASE_DIR),
        "catalogo": str(CONFIG_FILE),
        "yaml_total": len(archivos),
        "yaml_por_carpeta": [{"carpeta": k, "total": v} for k, v in sorted(por_carpeta.items())],
        "yaml": archivos,
        "esperados": esperados,
        "esperados_total": len(esperados),
        "esperados_presentes": len(esperados) - len(faltan),
        "faltantes": faltan,
        "extras": extras,
    }


def k8s_dir_abs_default(env_key: str) -> Path:
    """Carpeta que se usaría sin configuración explícita (para poder comparar)."""
    from devconsole.config import default_k8s_dir
    candidata = Path(default_k8s_dir(env_key))
    return candidata if candidata.is_absolute() else BASE_DIR / candidata


def browse_directories(path: str = "") -> dict[str, Any]:
    """Lista subcarpetas de ``path`` con cuántos YAML contiene cada una.

    Solo directorios: no se devuelve el contenido de ningún fichero.
    """
    destino = Path(path).expanduser() if path else Path(BASE_DIR)
    if not destino.is_absolute():
        destino = BASE_DIR / destino
    try:
        destino = destino.resolve()
    except OSError:
        pass

    if not destino.exists() or not destino.is_dir():
        return {"valid": False, "path": str(destino), "error": "La carpeta no existe.",
                "dirs": [], "parent": str(destino.parent), "yaml_total": 0}

    try:
        entradas = sorted(destino.iterdir(), key=lambda p: p.name.lower())
    except OSError as exc:
        return {"valid": False, "path": str(destino), "error": f"No se pudo leer: {exc}",
                "dirs": [], "parent": str(destino.parent), "yaml_total": 0}

    dirs: list[dict[str, Any]] = []
    for entrada in entradas:
        if not entrada.is_dir() or entrada.name.startswith(".") or entrada.name in _SKIP_DIRS:
            continue
        try:
            yaml_aqui = sum(1 for f in entrada.iterdir()
                            if f.is_file() and f.name.lower().endswith(_YAML_SUFFIXES))
        except OSError:
            yaml_aqui = 0
        presentes, total = _expected_in(entrada)
        dirs.append({
            "name": entrada.name,
            "path": str(entrada),
            "yaml": yaml_aqui,
            "esperados": presentes,
            "esperados_total": total,
        })
        if len(dirs) >= _MAX_DIRS:
            break

    yaml_aqui = sum(1 for f in destino.iterdir()
                    if f.is_file() and f.name.lower().endswith(_YAML_SUFFIXES))
    # Recursivo: informativo (un padre puede tener todo debajo), pero quien
    # decide si la carpeta sirve es `esperados`: los manifiestos que el catálogo
    # espera EN ESTE nivel.
    presentes, total = _expected_in(destino)

    # Ficheros del propio nivel: el explorador sólo listaba carpetas, así que
    # al entrar en una carpeta «no se veían los archivos encontrados».
    ficheros: list[dict[str, Any]] = []
    try:
        for f in sorted(destino.iterdir(), key=lambda x: x.name.lower()):
            if not f.is_file() or not f.name.lower().endswith(_YAML_SUFFIXES):
                continue
            try:
                st = f.stat()
            except OSError:
                continue
            ficheros.append({"name": f.name, "size": st.st_size, "mtime": int(st.st_mtime)})
            if len(ficheros) >= _MAX_FILES:
                break
    except OSError:
        pass

    # Árbol completo bajo la carpeta explorada: la lista por nivel mostraba sólo
    # lo de ese directorio (en `backend/` únicamente `ms_*`, en `frontend/`
    # únicamente `mf_*`), así que parecía que faltaban ficheros.
    arbol = _yaml_files(destino)

    return {
        "valid": True,
        "path": str(destino),
        "parent": str(destino.parent),
        "dirs": dirs,
        "files": ficheros,
        "tree": arbol,
        "yaml_total": yaml_aqui,
        "yaml_recursivo": len(arbol),
        "esperados": presentes,
        "esperados_total": total,
        "es_base_dir": destino == BASE_DIR,
    }


def set_k8s_dir(env_key: str, path: str) -> dict[str, Any]:
    """Fija la carpeta de manifiestos de un entorno y devuelve el estado nuevo."""
    if not path or not str(path).strip():
        return {"success": False, "message": "Indica una carpeta."}
    destino = Path(str(path).strip()).expanduser()
    if not destino.is_absolute():
        destino = BASE_DIR / destino
    if not destino.is_dir():
        return {"success": False, "message": f"La carpeta no existe: {destino}"}
    if not _yaml_files(destino):
        return {"success": False,
                "message": f"No hay manifiestos (.yaml/.yml) en {destino}; elige la carpeta que los contiene."}
    presentes, total = _expected_in(destino)
    if total and presentes == 0:
        return {"success": False,
                "message": (f"En {destino} no está ninguno de los {total} manifiestos del catálogo "
                            "(el despliegue los busca en este mismo nivel). Entra en la subcarpeta del entorno.")}

    ok, msg = save_k8s_dir(env_key, _relative_to_base(destino))
    if not ok:
        return {"success": False, "message": msg}
    return {"success": True, "message": msg, "config": site_config(env_key)}
