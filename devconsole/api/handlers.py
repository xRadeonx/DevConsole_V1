import http
import urllib
# devconsole/api/handlers.py
import http.server
import json
import os
import subprocess
import time
import urllib.parse
import urllib.request
import re
import threading
import uuid
from pathlib import Path

import devconsole.config as dcfg
from devconsole.config import (
    BASE_DIR,
    DASHBOARD_DIR,
    STATIC_DIR,
    SERVICES_BACKEND,
    SERVICES_FRONTEND,
    SLICES,
    ENVIRONMENTS,
    INFRA_CONTAINERS,
    is_port_open,
    get_service_repo_dir,
    inspect_directory,
    set_base_dir,
)
from devconsole.auth import (
    _load_admin_sessions,
    _save_admin_sessions,
    verify_admin_pin,
    verify_pin,
    is_valid_admin_token,
    is_admin_request,
    is_viewer_request,
    invalidate_admin_token,
    build_admin_cookie,
    build_admin_cookie_clear,
    ADMIN_SESSIONS_FILE,
    SESSION_TTL_HOURS,
)
from devconsole import local_trust
from devconsole import settings
from devconsole.security import (
    ADMIN_ACTIONS,
    ADMIN_PATHS,
    INFRA_EXEMPT_CONTAINERS,
    MUTATING_PATHS,
    PUBLIC_PATHS,
    SIDE_EFFECTING_GETS,
    Role,
    authorize_post,
    resolve_caller,
    require_client_trust,
)
from devconsole.services.git_service import (
    get_git_info,
    get_service_branches,
    checkout_service_branch,
    create_service_branch,
    rename_service_branch,
    get_running_services_info,
    get_config_git_status,
    run_config_git_pull,
    run_config_git_push,
    run_git_action,
    run_git_fetch_all,
)
from devconsole.services.terminal import get_terminal_backend
from devconsole.services.ttl_cache import invalidate_all
from devconsole.services.env_service import (
    get_service_env_map,
    read_service_env,
    write_service_env,
    get_all_environments_status,
    switch_workspace_environment,
    get_env_info,
    ENV_WATCHER_EVENTS,
)
from devconsole.services.k8s_service import (
    get_k8s_sesion_deployment,
    get_k8s_theme,
    set_k8s_theme,
    get_k8s_status,
    k8s_rollout_restart,
    k8s_rollout_status,
    k8s_rollout_all,
    k8s_get_logs,
    get_deployment_versions,
    update_yaml_version,
    k8s_deploy_service,
)
from devconsole.services.build_service import (
    inspect_image_labels,
    run_build_task,
    BUILD_TASKS,
    BUILD_LOCK,
    prune_build_tasks,
)
from devconsole.services.infra_service import (
    get_infra_info,
    get_service_detail,
    sync_contracts_onlyoffice_env,
)
from devconsole.services.telemetry_service import (
    get_operational_map_data,
    get_live_activity_data,
    get_activity_detail,
    get_user_live_session_info,
    LIVE_FRONTEND_TELEMETRY,
    LIVE_SCREEN_MIRROR,
    ACTIVE_MIRROR_SUBSCRIPTIONS,
)

# --------------------------------------------------------------------------- #
# Security headers (roadmap phase 0C.8)
# --------------------------------------------------------------------------- #
#: Applied to every response.  These are zero-risk for the bundled UI and close
#: real classes of attack (MIME sniffing, clickjacking, referrer leakage,
#: cross-origin embedding of API responses).
SECURITY_HEADERS = (
    ("X-Content-Type-Options", "nosniff"),
    ("Referrer-Policy", "no-referrer"),
    ("X-Frame-Options", "SAMEORIGIN"),
    ("Cross-Origin-Resource-Policy", "same-origin"),
    ("Cross-Origin-Opener-Policy", "same-origin"),
    ("Permissions-Policy", "geolocation=(), microphone=(), camera=(), payment=()"),
)

#: Content-Security-Policy shaped by characterising the bundled UI:
#:   * 0 uses of eval()/new Function()  -> 'unsafe-eval' is NOT needed
#:   * 268 inline event handlers        -> 'unsafe-inline' IS required
#:   * 0 inline <script> blocks
#:   * icons from cdn.jsdelivr.net and cdn.simpleicons.org
#:   * the screen mirror writes an iframe via srcdoc, which inherits this policy
#:     from the parent document
#:   * infra probes http://127.0.0.1:8082 and http://localhost:8080
CSP_VALUE = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: https://cdn.jsdelivr.net https://cdn.simpleicons.org; "
    "font-src 'self' data:; "
    "connect-src 'self' http://127.0.0.1:* http://localhost:*; "
    "frame-src 'self'; "
    "frame-ancestors 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)

#: ``enforce`` | ``report-only`` | ``off``.
#:
#: Defaults to ``report-only`` on purpose: the screen-mirror iframe renders DOM
#: captured from *another* browser through ``srcdoc``, and that content inherits
#: this policy.  Enforcing a policy that silently broke the mirror would violate
#: the "do not break the UI" rule of this phase, so enforcement is a one-line
#: opt-in after the manual browser verification in step 0C.13.
CSP_MODE_ENV = "SISPER_CSP_MODE"

#: Allowed characters for an imported Tilix session file name.
SAFE_SESSION_NAME = re.compile(r"^[A-Za-z0-9._-]{1,96}\.json$")


def _csp_mode() -> str:
    value = os.environ.get(CSP_MODE_ENV, "report-only").strip().lower()
    return value if value in ("enforce", "report-only", "off") else "report-only"


def _audit_denial(path: str, ctx, decision, payload=None) -> None:
    """Record a refused request.

    Logs only the route, the resolved context and the reason.  No token, cookie,
    header dump or payload content is ever written.
    """
    import logging

    if getattr(decision, "requires_admin", False) or not getattr(decision, "allowed", False):
        logging.getLogger("devconsole.security.audit").warning(
            "denied path=%s role=%s origin=%s host_ok=%s local_token_ok=%s "
            "reason=%s spoof=%s notes=%s",
            path,
            getattr(ctx, "role", None).value if getattr(ctx, "role", None) else "?",
            getattr(ctx, "origin", None) or "-",
            getattr(ctx, "host_allowed", None),
            getattr(ctx, "local_token_valid", None),
            getattr(decision, "reason", "?"),
            getattr(ctx, "role_spoof_attempted", False),
            ",".join(getattr(ctx, "notes", ())) or "-",
        )


#: Versión (mtime) de los estáticos que referencia index.html, para el `?v=`.
_VERSION_ESTATICOS: dict[str, tuple[str, str]] = {}
_ESTATICOS_INDEX = ("css/dashboard.css", "css/themes.css", "css/console-wall.css",
                    "js/theme.js", "js/dashboard.js")


def _version_estaticos() -> dict[str, str]:
    """Devuelve ``{ruta: versión}`` a partir de la fecha de cada fichero.

    Se añade como ``?v=`` al servir index.html: un navegador con una copia vieja
    de dashboard.js en caché dejaría la interfaz a medias (por ejemplo, un botón
    nuevo sin responder porque su función no existe en la copia antigua).
    """
    versiones: dict[str, str] = {}
    for nombre in _ESTATICOS_INDEX:
        try:
            clave = str((STATIC_DIR / nombre).stat().st_mtime_ns)
        except OSError:
            clave = "0"
        guardado = _VERSION_ESTATICOS.get(nombre)
        if not guardado or guardado[0] != clave:
            _VERSION_ESTATICOS[nombre] = (clave, clave[:13])
        versiones[nombre] = _VERSION_ESTATICOS[nombre][1]
    return versiones


class DevConsoleHandler(http.server.BaseHTTPRequestHandler):
    # ------------------------------------------------------------------ #
    # response helpers (roadmap phase 0C.6 / 0C.8)
    # ------------------------------------------------------------------ #

    def _request_origin(self) -> str | None:
        try:
            return self.headers.get("Origin")
        except Exception:
            return None

    def _send_cors_headers(self) -> None:
        """Emit CORS headers only for origins that are actually allowed.

        Pre-0C this always emitted ``Access-Control-Allow-Origin: *`` together
        with ``Access-Control-Allow-Private-Network: true``.  That combination
        let **any web page the developer visited** read
        ``/api/env/get`` -- i.e. every service's database password and Keycloak
        secret -- from this machine.  Echoing only allowlisted origins closes
        that channel while leaving same-origin UI traffic untouched.
        """
        from devconsole.security import allowed_origins

        origin = self._request_origin()
        if origin and origin.rstrip("/") in allowed_origins():
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Credentials", "true")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers",
                             "Content-Type, Authorization, X-Auth-Token, X-Sisper-Local-Token")
            # Private Network Access is a cross-origin permission; never grant
            # it to a client that is not already on the allowlist.

    def _send_security_headers(self) -> None:
        for name, value in SECURITY_HEADERS:
            self.send_header(name, value)
        mode = _csp_mode()
        if mode == "enforce":
            self.send_header("Content-Security-Policy", CSP_VALUE)
        elif mode == "report-only":
            self.send_header("Content-Security-Policy-Report-Only", CSP_VALUE)

    def do_OPTIONS(self):
        """Preflight.

        A preflight from a disallowed origin gets a bare 200 with no CORS
        headers, which the browser treats as a failure.  That is deliberate:
        answering a disallowed origin with permission headers would defeat the
        allowlist.
        """
        self.send_response(200)
        self._send_cors_headers()
        self._send_security_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_HEAD(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self._send_security_headers()
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
        elif path.startswith("/static/"):
            self.send_response(200)
            self._send_security_headers()
            self.end_headers()
        elif path.startswith("/api/"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._send_security_headers()
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def _responder_error(self, exc: Exception, metodo: str) -> None:
        """Último recurso: convertir un fallo del despacho en una respuesta.

        Antes, una excepción no prevista (por ejemplo `int("x")` en un parámetro
        de la query) cortaba la conexión sin respuesta: el journal acumulaba
        `BrokenPipeError` y la interfaz no sabía qué había pasado.
        """
        try:
            print(f"[!] {metodo} {self.path} falló: {type(exc).__name__}: {exc}")
            if isinstance(exc, (ValueError, TypeError)):
                self.send_json({"success": False,
                                "message": f"Parámetro inválido: {exc}"}, status=400)
            else:
                self.send_json({"success": False,
                                "message": f"Error interno: {type(exc).__name__}"}, status=500)
        except Exception:
            pass   # la conexión ya no está: no queda nada que enviar

    def do_GET(self):
        try:
            self._do_GET()
        except (BrokenPipeError, ConnectionResetError):
            pass   # el cliente se fue: no es un fallo del servidor
        except Exception as exc:
            self._responder_error(exc, "GET")

    def _do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # ------------------------------------------------------------------ #
        # Client-trust gate for the whole read API (phase 0C.5)
        # ------------------------------------------------------------------ #
        # Read endpoints stay reachable without a session -- the bundled UI
        # depends on that -- but they must come from an allowed Origin with an
        # accepted Host header.  This is what defeats DNS rebinding, the classic
        # way to read http://127.0.0.1:* from a hostile page: the rebound request
        # arrives carrying "Host: evil.example" and is refused here.
        if path.startswith("/api/"):
            ctx = resolve_caller(self.headers, self.client_address)
            trust = require_client_trust(ctx)
            if not trust.allowed:
                _audit_denial(path, ctx, trust)
                self.send_json(trust.as_response(), status=trust.status)
                return

        if path in ("/", "/index.html"):
            index_file = STATIC_DIR / "index.html"
            if index_file.exists():
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                # Hand the browser the local-trust token over a channel a
                # cross-origin page cannot read: HttpOnly + SameSite=Strict.
                # This is what lets SISPER_LOCAL_TOKEN_REQUIRED=1 be enabled
                # without breaking the same-origin UI and without adding a
                # token-dispensing endpoint.
                if local_trust.token_required():
                    self.send_header("Set-Cookie", local_trust.build_cookie_header())
                self._send_security_headers()
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.end_headers()
                html = index_file.read_text(encoding="utf-8")
                versiones = _version_estaticos()
                for nombre, version in versiones.items():
                    html = html.replace(f'"/static/{nombre}"', f'"/static/{nombre}?v={version}"')
                # Marca de versión de ESTA página: si el JS cargado no es el que
                # el servidor sirve ahora, la interfaz lo avisa (copia en caché).
                marca = ("<script>window.__UI_VERSION="
                         + repr(versiones.get("js/dashboard.js", "")).replace("'", '"')
                         + ";</script>\n  ")
                html = html.replace('<script src="/static/js/dashboard.js', marca + '<script src="/static/js/dashboard.js', 1)
                self.wfile.write(html.encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()

        elif path.startswith("/static/"):
            rel_path = path[len("/static/"):].lstrip("/")
            safe_file = (STATIC_DIR / rel_path).resolve()
            if safe_file.exists() and str(safe_file).startswith(str(STATIC_DIR)):
                mime = "text/plain"
                if safe_file.suffix == ".css":
                    mime = "text/css; charset=utf-8"
                elif safe_file.suffix == ".js":
                    mime = "application/javascript; charset=utf-8"
                elif safe_file.suffix == ".svg":
                    mime = "image/svg+xml; charset=utf-8"
                elif safe_file.suffix == ".png":
                    mime = "image/png"
                elif safe_file.suffix in (".jpg", ".jpeg"):
                    mime = "image/jpeg"
                elif safe_file.suffix == ".html":
                    mime = "text/html; charset=utf-8"
                elif safe_file.suffix == ".json":
                    mime = "application/json; charset=utf-8"

                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.end_headers()
                with open(safe_file, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()

        elif path == "/api/status":
            backend_status = [
                {
                    **s,
                    "online": is_port_open(s["port"]),
                    **get_git_info(dcfg.BASE_DIR / "backend" / s["name"])
                }
                for s in dcfg.SERVICES_BACKEND
            ]
            frontend_status = [
                {
                    **s,
                    "online": is_port_open(s["port"]),
                    **get_git_info(dcfg.BASE_DIR / "frontend" / s["name"])
                }
                for s in dcfg.SERVICES_FRONTEND
            ]
            env_info = get_env_info()
            infra_info = get_infra_info()
            env_summary = get_all_environments_status()

            slices_data = {}
            for k, v in dcfg.SLICES.items():
                slices_data[k] = {
                    "title": v.get("title", k),
                    "description": v.get("description", ""),
                    "services_names": [svc[0] for svc in v.get("services", [])]
                }

            data = {
                # Versión (mtime) del JS de la interfaz: permite detectar que el
                # navegador tiene una copia vieja y avisar en pantalla.
                "ui_version": _version_estaticos().get("js/dashboard.js", ""),
                "css_version": _version_estaticos().get("css/console-wall.css", ""),
                "base_dir": str(dcfg.BASE_DIR),
                "folder_name": dcfg.BASE_DIR.name or str(dcfg.BASE_DIR),
                # Datos de la instalación que la interfaz necesita para no
                # llevar escrito un registry ni un nombre de proyecto propios.
                "registry": dcfg.REGISTRY,
                "project_name": dcfg.PROJECT_NAME,
                "backend": backend_status,
                "frontend": frontend_status,
                "env": env_info,
                "infra": infra_info,
                "env_summary": env_summary,
                "slices": slices_data,
                "env_watcher": {
                    "enabled": True,
                    "recent_events": list(ENV_WATCHER_EVENTS[-5:])
                }
            }
            self.send_json(data)

        elif path == "/api/root_dir/info":
            data = inspect_directory(dcfg.BASE_DIR)
            data["dashboard_dir"] = str(DASHBOARD_DIR)
            data["is_default"] = (str(dcfg.BASE_DIR) == str(DASHBOARD_DIR))
            self.send_json(data)

        elif path == "/api/root_dir/inspect":
            params = urllib.parse.parse_qs(parsed.query)
            target = params.get("path", [str(dcfg.BASE_DIR)])[0]
            data = inspect_directory(target)
            data["dashboard_dir"] = str(DASHBOARD_DIR)
            self.send_json(data)

        elif path == "/api/env/get":
            params = urllib.parse.parse_qs(parsed.query)
            svc = params.get("service", [""])[0]
            data = read_service_env(svc)
            self.send_json(data)

        elif path == "/api/k8s/theme":
            params = urllib.parse.parse_qs(parsed.query)
            ns = params.get("namespace", ["develop"])[0]
            data = get_k8s_theme(ns)
            self.send_json(data)

        elif path == "/api/secrets":
            # Nunca se devuelven los valores: sólo qué claves faltan.
            from devconsole import settings as _st
            requeridas = _st.referenced_secret_keys()
            presentes = _st.secret_values_present()
            self.send_json({
                "archivo": str(_st.SECRETS_FILE),
                "claves": [{"ruta": k, "configurada": k in presentes} for k in requeridas],
                "sin_configurar": [k for k in requeridas if k not in presentes],
            })

        elif path == "/api/preflight":
            # Comprobación previa al lanzamiento: sólo lectura (infra + entorno
            # de pipenv + puertos).  No arranca ni modifica nada.
            params = urllib.parse.parse_qs(parsed.query)
            env_key = params.get("env", ["develop"])[0]
            crudos = params.get("services", [""])[0]
            servicios = [s.strip() for s in crudos.split(",") if s.strip()] or None
            from devconsole.services.preflight_service import preflight
            self.send_json(preflight(servicios, env_key))

        elif path == "/api/service/diagnose":
            params = urllib.parse.parse_qs(parsed.query)
            servicio = params.get("service", [""])[0]
            if not servicio:
                self.send_json({"success": False, "message": "Falta parámetro 'service'."}, status=400)
                return
            from devconsole.services.preflight_service import diagnose
            self.send_json(diagnose(servicio))

        elif path == "/api/site/config":
            params = urllib.parse.parse_qs(parsed.query)
            env_key = params.get("env", ["develop"])[0]
            from devconsole.services.site_service import site_config
            self.send_json(site_config(env_key))

        elif path == "/api/site/yaml":
            params = urllib.parse.parse_qs(parsed.query)
            env_key = params.get("env", ["develop"])[0]
            archivo = params.get("file", [""])[0]
            from devconsole.config import BASE_DIR as _BASE, k8s_dir_for as _k8s_dir_for
            base = Path(_k8s_dir_for(env_key))
            if not base.is_absolute():
                base = _BASE / base
            try:
                destino = (base / archivo).resolve()
                destino.relative_to(base.resolve())
            except (ValueError, OSError):
                self.send_json({"success": False, "message": "Ruta fuera de la carpeta de manifiestos."}, status=400)
                return
            if not destino.is_file() or destino.stat().st_size > 262_144:
                self.send_json({"success": False, "message": "Manifiesto no encontrado o demasiado grande."}, status=404)
                return
            self._send_text(destino.read_text(encoding="utf-8", errors="replace"),
                            "text/plain; charset=utf-8")
            return

        elif path == "/api/site/browse":
            params = urllib.parse.parse_qs(parsed.query)
            destino = params.get("path", [""])[0]
            from devconsole.services.site_service import browse_directories
            self.send_json(browse_directories(destino))

        elif path == "/api/tilix/sessions":
            sessions = get_terminal_backend().scan_sessions()
            self.send_json({"base_dir": str(BASE_DIR), "sessions": sessions})

        elif path == "/api/environment/status":
            env_status = get_all_environments_status()
            self.send_json(env_status)

        elif path == "/api/deployments/versions":
            params = urllib.parse.parse_qs(parsed.query)
            env_key = params.get("env", ["develop"])[0]
            dep_data = get_deployment_versions(env_key)
            self.send_json(dep_data)

        elif path == "/api/auth/validate_session":
            role = self.headers.get("X-Auth-Role", "dev").lower()
            token = self.headers.get("X-Auth-Token", "")
            if role == "admin" and is_valid_admin_token(token):
                self.send_json({"valid": True, "role": "admin"})
            else:
                self.send_json({"valid": False, "role": "dev", "message": "Sesión inválida o expirada"})

        elif path == "/api/deployments/build_status":
            params = urllib.parse.parse_qs(parsed.query)
            task_id = params.get("task_id", [""])[0]
            with BUILD_LOCK:
                if task_id:
                    task = BUILD_TASKS.get(task_id)
                    if task:
                        resp = dict(task)
                    else:
                        resp = {"status": "not_found", "logs": ["Tarea no encontrada"]}
                    self.send_json(resp)
                else:
                    # Retornar resumen de todas las tareas activas y recientes
                    summary = {}
                    for tid, t in BUILD_TASKS.items():
                        summary[tid] = {
                            "task_id": tid,
                            "title": t.get("title", "Construcción"),
                            "status": t.get("status", "running"),
                            "progress": t.get("progress", 0),
                            "current_step": t.get("current_step", ""),
                            "services": t.get("services", []),
                            "current_service": t.get("current_service", ""),
                            "service_status": t.get("service_status", {}),
                            "error": t.get("error", None),
                            "lines_count": len(t.get("logs", []))
                        }
                    self.send_json(summary)

        elif path == "/api/k8s/status":
            params = urllib.parse.parse_qs(parsed.query)
            ns = params.get("namespace", ["develop"])[0]
            k8s_data = get_k8s_status(ns)
            self.send_json(k8s_data)

        elif path == "/api/k8s/rollout_status":
            params = urllib.parse.parse_qs(parsed.query)
            target = params.get("target", [""])[0]
            ns = params.get("namespace", ["develop"])[0]
            st = k8s_rollout_status(target, ns)
            self.send_json(st)

        elif path == "/api/k8s/logs":
            params = urllib.parse.parse_qs(parsed.query)
            target = params.get("target", [""])[0]
            ns = params.get("namespace", ["develop"])[0]
            tail = int(params.get("tail", [100])[0])
            container = params.get("container", [""])[0] or None
            logs = k8s_get_logs(target, ns, tail=tail, container=container)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(logs.encode("utf-8"))

        elif path == "/api/branches":
            params = urllib.parse.parse_qs(parsed.query)
            svc = params.get("service", [""])[0]
            data = get_service_branches(svc)
            self.send_json(data)

        elif path == "/api/config_git/status":
            st = get_config_git_status()
            self.send_json(st)

        elif path == "/api/git/fetch_all":
            # SEC-10: un GET no debe provocar red.  Antes este camino lanzaba
            # `git fetch --prune` sobre ~31 repositorios (8 en paralelo) sin
            # sesión: bastaba abrir la URL.  La interfaz usa POST.
            self.send_json({
                "success": False,
                "message": "Esta ruta sólo acepta POST (ejecuta git fetch). Usa POST /api/git/fetch_all.",
            }, status=405)

        elif path == "/api/services/running":
            running = get_running_services_info()
            self.send_json({"running": running, "count": len(running)})

        elif path == "/api/services/mosaic":
            params = urllib.parse.parse_qs(parsed.query)
            try:
                max_lines = int(params.get("max_lines", [6])[0])
            except ValueError:
                max_lines = 6
            svc_name = params.get("service", [None])[0]
            services_param = params.get("services", [None])[0]
            from devconsole.services.terminal import MosaicService
            mosaic_svc = MosaicService()
            if svc_name:
                item = mosaic_svc.get_service_preview_by_name(svc_name, max_lines=max_lines)
                if not item:
                    self.send_json({"error": f"Service '{svc_name}' not found"}, status=404)
                else:
                    self.send_json(item.to_dict())
            elif services_param:
                names = [n.strip() for n in services_param.split(",") if n.strip()]
                items = mosaic_svc.get_services_batch_preview(names, max_lines=max_lines)
                self.send_json({"services": items, "count": len(items), "timestamp": time.time()})
            else:
                items = mosaic_svc.get_mosaic_overview(max_lines=max_lines)
                self.send_json({"services": items, "count": len(items), "timestamp": time.time()})

        elif path == "/api/services/wall":
            from devconsole.services.terminal.live_broker import get_live_broker
            broker = get_live_broker()
            snapshot = broker.get_snapshot()
            self.send_json(snapshot)

        elif path == "/api/infra/targets":
            # Destinos de infraestructura de la instalación
            # (config/panel.json → infra_targets).  Es dato estático: la
            # interfaz lo pide una sola vez y no viaja en cada sondeo.
            self.send_json({"environments": settings.infra_targets()})

        elif path == "/api/services/catalog":
            from devconsole.services.terminal.live_broker import get_live_broker
            broker = get_live_broker()
            catalog = broker.get_catalog()
            self.send_json({"catalog": catalog, "count": len(catalog)})

        elif path == "/api/services/stream":
            import queue
            from devconsole.services.terminal.live_broker import get_live_broker
            broker = get_live_broker()
            sub_q = queue.Queue(maxsize=100)
            sub_id = broker.subscribe(sub_q)

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self._send_cors_headers()
            self._send_security_headers()
            self.end_headers()

            try:
                while True:
                    try:
                        event = sub_q.get(timeout=3.0)
                        payload = f"data: {json.dumps(event)}\n\n".encode("utf-8")
                        self.wfile.write(payload)
                        self.wfile.flush()
                    except queue.Empty:
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                broker.unsubscribe(sub_id)
            return


        elif path == "/api/service/info":
            params = urllib.parse.parse_qs(parsed.query)
            svc = params.get("service", [""])[0]
            port = int(params.get("port", [0])[0])
            data = get_service_detail(svc, port)
            self.send_json(data)

        elif path == "/api/deployments/inspect":
            params = urllib.parse.parse_qs(parsed.query)
            img = params.get("image", [""])[0]
            tag = params.get("tag", ["latest"])[0]
            data = inspect_image_labels(img, tag)
            self.send_json(data)

        elif path == "/api/map/chile_svg":
            map_file = BASE_DIR / "config" / "chile_naval_map.svg"
            if map_file.exists():
                self.send_response(200)
                self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.end_headers()
                with open(map_file, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()

        elif path == "/api/analytics/connections":
            params = urllib.parse.parse_qs(parsed.query)
            env_key = params.get("env", ["develop"])[0]
            refresh = params.get("refresh", ["false"])[0].lower() in ("true", "1")
            data = get_operational_map_data(env_key=env_key, force_refresh=refresh)
            self.send_json(data)

        elif path == "/api/activity/feed":
            params = urllib.parse.parse_qs(parsed.query)
            env_key = params.get("env", ["develop"])[0]
            limit = int(params.get("limit", [50])[0])
            modulo = params.get("modulo", [""])[0]
            metodo = params.get("metodo", [""])[0]
            search = params.get("search", [""])[0]
            user_filter = params.get("user", [""])[0]
            data = get_live_activity_data(env_key=env_key, limit=limit, modulo=modulo, metodo=metodo, search=search, user_filter=user_filter)
            self.send_json(data)

        elif path == "/api/activity/detail":
            params = urllib.parse.parse_qs(parsed.query)
            env_key = params.get("env", ["develop"])[0]
            id_bit = params.get("id", [""])[0]
            data = get_activity_detail(env_key=env_key, id_bitacora=id_bit)
            self.send_json(data)

        elif path == "/api/telemetry/live":
            now_ts = time.time()
            active_list = []
            for k, v in list(LIVE_FRONTEND_TELEMETRY.items()):
                if now_ts - v.get("received_at", 0) <= 25:
                    active_list.append(v)
            self.send_json({"telemetries": active_list, "timestamp": now_ts})

        elif path == "/api/telemetry/mirror_view":
            params = urllib.parse.parse_qs(parsed.query)
            u_key = params.get("user", [""])[0]
            known_ver_str = params.get("known_ver", ["0"])[0]
            known_ver = int(known_ver_str) if known_ver_str.isdigit() else 0
            mirror_data = LIVE_SCREEN_MIRROR.get(u_key)
            if not mirror_data and u_key:
                uk_clean = u_key.strip().replace(".", "").replace("-", "").lower()
                # Copia explícita: otro hilo (POST mirror_stream) puede insertar
                # mientras se itera y romper el diccionario en pleno recorrido.
                for mk, mv in list(LIVE_SCREEN_MIRROR.items()):
                    if uk_clean in str(mk).lower() or str(mk).lower() in uk_clean:
                        mirror_data = mv
                        break
            resp_mirror = None
            if mirror_data:
                resp_mirror = dict(mirror_data)
                # Si el dashboard ya tiene esta versión de DOM, no reenviar los kilobytes de HTML
                if known_ver and resp_mirror.get("dom_ver", 0) == known_ver:
                    resp_mirror["dom_html"] = None

            self.send_json({
                "user": u_key,
                "mirror": resp_mirror,
                "active_subscription": (u_key in ACTIVE_MIRROR_SUBSCRIPTIONS)
            })

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        try:
            self._do_POST()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as exc:
            self._responder_error(exc, "POST")

    def _do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
        except (TypeError, ValueError):
            length = 0
        body = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            # Malformed input fails closed: refuse rather than run with {}.
            self.send_json({"success": False, "message": "JSON inválido."}, status=400)
            return
        if not isinstance(payload, dict):
            self.send_json({"success": False, "message": "Se esperaba un objeto JSON."},
                           status=400)
            return

        # ------------------------------------------------------------------ #
        # ÚNICA PUERTA DE AUTORIZACIÓN  (roadmap phase 0C.2 / 0C.7)
        # ------------------------------------------------------------------ #
        # Replaces the scattered guards of the pre-0C code, one of which
        # emitted a 403 and then fell through into the protected handler
        # (BR-01).  Every mutating route -- including the ones that previously
        # ran *before* any guard at all -- now passes through here first, and a
        # denial always returns, so exactly one response is ever produced and
        # no protected action can be reached.
        ctx = resolve_caller(self.headers, self.client_address)
        decision = authorize_post(path, ctx, payload)
        if not decision.allowed:
            _audit_denial(path, ctx, decision, payload)
            self.send_json(decision.as_response(), status=decision.status)
            return

        if path == "/api/telemetry/heartbeat":
            u_key = payload.get("user_key", "anonimo")
            if u_key and u_key != "anonimo":
                payload["received_at"] = time.time()
                payload["ip"] = self.client_address[0] if hasattr(self, "client_address") else "127.0.0.1"
                LIVE_FRONTEND_TELEMETRY[u_key] = payload
            now_ts = time.time()
            for k in list(LIVE_FRONTEND_TELEMETRY.keys()):
                if now_ts - LIVE_FRONTEND_TELEMETRY[k].get("received_at", 0) > 30:
                    LIVE_FRONTEND_TELEMETRY.pop(k, None)
            is_mirrored = bool(u_key in ACTIVE_MIRROR_SUBSCRIPTIONS)
            self.send_json({"status": "ok", "mirror_requested": is_mirrored})
            return

        elif path == "/api/telemetry/mirror_stream":
            u_key = payload.get("user_key", "anonimo")
            if u_key and u_key != "anonimo":
                payload["received_at"] = time.time()
                prev = LIVE_SCREEN_MIRROR.get(u_key, {})
                dom_html = payload.get("dom_html")
                if dom_html and len(dom_html) > 512_000:
                    # El contenido lo manda el cliente: sin cota, un espejo grande
                    # se queda en memoria del panel indefinidamente.
                    dom_html = None
                if dom_html:
                    dom_ver = prev.get("dom_ver", 0) + 1
                    payload["dom_ver"] = dom_ver
                else:
                    if "dom_html" in prev:
                        payload["dom_html"] = prev["dom_html"]
                    payload["dom_ver"] = prev.get("dom_ver", 0)
                LIVE_SCREEN_MIRROR[u_key] = payload
                # Poda por antigüedad: las entradas se acumulaban sin límite.
                _ahora = time.time()
                for _k in list(LIVE_SCREEN_MIRROR.keys()):
                    if _ahora - LIVE_SCREEN_MIRROR[_k].get("received_at", 0) > 120:
                        LIVE_SCREEN_MIRROR.pop(_k, None)
            self.send_json({"status": "ok"})
            return

        elif path == "/api/telemetry/mirror_control":
            u_key = payload.get("user_key", "")
            enable = bool(payload.get("enabled", False))
            if u_key:
                if enable:
                    ACTIVE_MIRROR_SUBSCRIPTIONS.add(u_key)
                else:
                    ACTIVE_MIRROR_SUBSCRIPTIONS.discard(u_key)
                    LIVE_SCREEN_MIRROR.pop(u_key, None)
            self.send_json({"status": "ok", "user": u_key, "active": (u_key in ACTIVE_MIRROR_SUBSCRIPTIONS)})
            return

        elif path == "/api/env/save":
            svc = payload.get("service", "")
            content = payload.get("content", "")
            restart = bool(payload.get("restart", True))
            ok, msg = write_service_env(svc, content, restart)
            self.send_json({"success": ok, "message": msg}, status=200 if ok else 400)
            return

        elif path == "/api/site/k8s_dir":
            env_key = payload.get("env", "develop")
            nuevo = payload.get("path", "")
            from devconsole.services.site_service import set_k8s_dir
            resultado = set_k8s_dir(env_key, nuevo)
            self.send_json(resultado, status=200 if resultado.get("success") else 400)
            return

        elif path == "/api/k8s/theme":
            ns = payload.get("namespace", "develop")
            theme = payload.get("theme", "none")
            ok, msg = set_k8s_theme(ns, theme)
            deploy = get_k8s_sesion_deployment(ns)
            self.send_json({"success": ok, "message": msg, "deployment": deploy, "namespace": ns, "theme": theme}, status=200 if ok else 400)
            return

        elif path == "/api/auth/verify_pin":
            raw_pin = payload.get("pin")
            pin = raw_pin.strip() if isinstance(raw_pin, str) else ""
            rol = str(payload.get("role") or "admin").lower()
            if rol not in ("admin", "dev"):
                rol = "admin"
            ok, tok = verify_pin(pin, rol)
            if ok and rol == "dev":
                # Desarrollador entra sin token elevado (no puede administrar).
                self.send_json({"success": True, "token": None, "role": "dev",
                                "message": "Autenticación exitosa como Desarrollador."})
            elif ok:
                # The token is returned to the caller (existing contract) and,
                # in parallel, handed to the browser as an HttpOnly cookie so
                # the UI's bare same-origin fetches carry it automatically.
                self.send_json(
                    {"success": True, "token": tok, "role": "admin",
                     "message": "Autenticación exitosa como Administrador."},
                    extra_headers=[("Set-Cookie", build_admin_cookie(tok))],
                )
            else:
                from devconsole import pins as _pins
                ayuda = ""
                try:
                    if not _pins.hay_claves_configuradas():
                        ayuda = (" No hay ninguna clave configurada todavía: créala con "
                                 "«python3 -m devconsole.pins set --role admin» y "
                                 "«… --role dev» (distintas entre sí).")
                except Exception:
                    ayuda = ""
                self.send_json({
                    "success": False,
                    "message": (("PIN incorrecto. Verifica la clave de administrador."
                                 if rol == "admin" else
                                 "PIN incorrecto. Verifica la clave de desarrollador.") + ayuda),
                }, status=401)
            return

        elif path == "/api/auth/logout":
            from devconsole.auth import admin_token_from
            token = payload.get("token") or admin_token_from(self.headers)
            if token:
                invalidate_admin_token(token)
            self.send_json({"success": True, "message": "Sesión cerrada correctamente."},
                           extra_headers=[("Set-Cookie", build_admin_cookie_clear())])
            return

        # La autorización ya se resolvió arriba, en la puerta única.
        if path == "/api/root_dir/set":
            target_path = payload.get("path")
            if not target_path:
                self.send_json({"success": False, "message": "Falta parámetro 'path'."}, status=400)
                return
            ok, msg, info = set_base_dir(target_path)
            # Al fijar la carpeta se completan los secretos con los .env de los servicios
            # elegidos; lo que no aparezca se rellena a mano en el editor «🔐 Secretos».
            try:
                from devconsole import settings as _st
                hallados = _st.buscar_secretos_en_servicios("develop")
                presentes = _st.secret_values_present()
                nuevos = {h["clave"]: h["valor"] for h in hallados if h["clave"] not in presentes}
                if nuevos:
                    _st.set_secrets(nuevos)
                requeridas = set(_st.referenced_secret_keys())
                faltan = sorted(requeridas - _st.secret_values_present())
                if nuevos:
                    msg += f" Secretos: {len(nuevos)} completados desde los .env de los servicios."
                if faltan:
                    msg += f" Quedan {len(faltan)} por rellenar (editor 🔐 Secretos)."
            except Exception as _exc:
                msg += f" (no se pudieron revisar los secretos: {_exc})"
            self.send_json({"success": ok, "message": msg, **info}, status=200 if ok else 400)
            return

        if path in ("/api/tilix/launch_selected", "/api/tilix/launch_selected_services"):
            selected_svcs = payload.get("services", [])
            target_env = payload.get("env", "develop")
            force = payload.get("force", False)

            if not force:
                running = get_running_services_info()
                running_map = {r["name"]: r for r in running if "name" in r}
                conflicts = []
                if selected_svcs:
                    for s_name in selected_svcs:
                        if s_name in running_map:
                            conflicts.append(running_map[s_name])
                else:
                    conflicts = running

                if len(conflicts) > 0:
                    self.send_json({
                        "success": False,
                        "already_running": True,
                        "active_count": len(conflicts),
                        "active_services": conflicts,
                        "message": f"Ya hay {len(conflicts)} de los servicios seleccionados activos en ejecución."
                    }, status=409)
                    return

            backend = get_terminal_backend()
            ok, msg, count = backend.launch_services(selected_svcs, target_env)
            # La ventana sólo se abre si se pide (open_viewer): el panel puede
            # lanzar las consolas «sólo en el dashboard».
            if ok and selected_svcs and payload.get("open_viewer", True):
                vok, vmsg = backend.attach_viewers(selected_svcs, title="seleccionados")
                msg = f"{msg} {vmsg}" if vok else f"{msg} (visor: {vmsg})"
            self.send_json({"success": ok, "message": msg, "count": count}, status=200 if ok else 400)
            return

        if path == "/api/tilix/launch_auxiliary":
            svc_name = payload.get("service")
            aux_type = payload.get("aux_type", "consumer")
            target_env = payload.get("env", "develop")
            if not svc_name:
                self.send_json({"success": False, "message": "Falta parámetro 'service'."}, status=400)
                return
            ok, msg = get_terminal_backend().launch_auxiliary(svc_name, aux_type, target_env)
            self.send_json({"success": ok, "message": msg}, status=200 if ok else 400)
            return

        if path == "/api/tilix/launch_selected_auxiliary":
            selected_svcs = payload.get("services", [])
            aux_type = payload.get("aux_type", "consumer")
            target_env = payload.get("env", "develop")
            if not selected_svcs:
                self.send_json({"success": False, "message": "No se especificaron servicios."}, status=400)
                return
            ok, msg, count = get_terminal_backend().launch_selected_auxiliaries(selected_svcs, aux_type, target_env)
            self.send_json({"success": ok, "message": msg, "count": count}, status=200 if ok else 400)
            return

        if path == "/api/tilix/attach_viewers":
            svcs = payload.get("services") or []
            titulo = payload.get("title")
            if not svcs:
                self.send_json({"success": False, "message": "Falta parámetro 'services'."}, status=400)
                return
            ok, msg = get_terminal_backend().attach_viewers(svcs, title=titulo)
            self.send_json({"success": ok, "message": msg}, status=200 if ok else 400)
            return

        if path == "/api/tilix/attach_viewer":
            service_name = payload.get("service")
            title = payload.get("title")
            if not service_name:
                self.send_json({"success": False, "message": "Falta parámetro 'service'."}, status=400)
                return
            ok, msg = get_terminal_backend().attach_viewer(service_name, title=title)
            self.send_json({"success": ok, "message": msg}, status=200 if ok else 400)
            return



        if path == "/api/tilix/launch":
            session_str = payload.get("session_path", "")
            target_env = payload.get("env", "develop")
            force = payload.get("force", False)

            if not force:
                running = get_running_services_info()
                if len(running) > 0:
                    self.send_json({
                        "success": False,
                        "already_running": True,
                        "active_count": len(running),
                        "active_services": running,
                        "message": f"Ya hay {len(running)} microservicio(s) activos en ejecución."
                    }, status=409)
                    return

            session_path = Path(session_str)
            if session_path.exists():
                backend = get_terminal_backend()
                ok = backend.launch_session(session_path, target_env)
                mensaje = f"Sesión lanzada en {target_env.upper()}." if ok else "Error al lanzar sesión."
                if ok and payload.get("open_viewer", True):
                    # Misma razón que arriba: la ventana se abre con lo lanzado.
                    nombres = [sess.metadata.get("@sisper_service")
                               for sess in backend.managed_sessions()
                               if sess.metadata.get("@sisper_service")]
                    if nombres:
                        vok, vmsg = backend.attach_viewers(nombres, title="todo")
                        mensaje = f"{mensaje} {vmsg}" if vok else f"{mensaje} (visor: {vmsg})"
                self.send_json({"success": ok, "message": mensaje})
            else:
                self.send_json({"success": False, "message": "Sesión no encontrada."}, status=400)

        elif path == "/api/config_git/pull":
            ok, msg = run_config_git_pull()
            self.send_json({"success": ok, "message": msg}, status=200 if ok else 400)

        elif path == "/api/config_git/push":
            commit_msg = payload.get("message", "Actualización de manifiestos K8s desde Dashboard")
            ok, msg = run_config_git_push(commit_msg)
            self.send_json({"success": ok, "message": msg}, status=200 if ok else 400)

        elif path == "/api/git/fetch_all":
            res = run_git_fetch_all()
            self.send_json(res)

        elif path == "/api/tilix/import":
            raw_name = payload.get("filename")
            filename = raw_name.strip() if isinstance(raw_name, str) else ""
            content = payload.get("content", "")
            content = content.strip() if isinstance(content, str) else ""
            if not filename.endswith(".json"):
                filename += ".json"
            # Confine the write to config/sessions/: the pre-0C code joined the
            # client-supplied name directly, so "../../.." escaped the directory
            # and wrote an arbitrary .json file anywhere the service user could.
            if not SAFE_SESSION_NAME.match(filename):
                self.send_json({"success": False, "message": "Nombre de sesión no válido."},
                               status=400)
                return
            target_file = (BASE_DIR / "config" / "sessions" / filename).resolve()
            sessions_dir = (BASE_DIR / "config" / "sessions").resolve()
            if target_file.parent != sessions_dir:
                self.send_json({"success": False, "message": "Ruta de sesión no permitida."},
                               status=400)
                return
            try:
                parsed_json = json.loads(content)
                target_file.parent.mkdir(parents=True, exist_ok=True)
                target_file.write_text(json.dumps(parsed_json, indent=2), encoding="utf-8")
                self.send_json({"success": True, "message": f"Sesión guardada en {target_file.name}."})
            except Exception as e:
                self.send_json({"success": False, "message": f"JSON inválido: {e}"}, status=400)

        elif path == "/api/environment/switch":
            target_env = payload.get("target_env", "develop")
            force_pull = payload.get("force_pull", False)
            res = switch_workspace_environment(target_env, force_pull)
            self.send_json({"success": True, "data": res})

        elif path == "/api/deployments/build":
            task_id = str(uuid.uuid4())[:8]
            services = payload.get("services", [])
            title = f"Build {services[0]}" if len(services) == 1 else f"Build {len(services)} svcs"
            with BUILD_LOCK:
                # BR-12: bound the retained history.  Only *finished* tasks are
                # ever dropped, never one that is still running.
                prune_build_tasks()
                BUILD_TASKS[task_id] = {
                    "id": task_id,
                    "title": title,
                    "services": services,
                    "current_service": services[0] if services else "",
                    "service_status": {s: "queued" for s in services},
                    "status": "running",
                    "logs": [],
                    "svc_logs": {s: [] for s in services},
                    "current_step": "Iniciando proceso...",
                    "progress": 0,
                    "created_at": time.time()
                }
            t = threading.Thread(target=run_build_task, args=(task_id, payload), daemon=True)
            t.start()
            self.send_json({"success": True, "task_id": task_id, "services": services})

        elif path == "/api/deployments/update_version":
            svc = payload.get("service", "")
            ver = payload.get("version", "").strip()
            env_key = payload.get("env", "develop")
            ok, msg = update_yaml_version(svc, ver, env_key)
            self.send_json({"success": ok, "message": msg}, status=200 if ok else 400)

        elif path == "/api/k8s/restart":
            deploy = payload.get("deploy", "")
            ns = payload.get("namespace", "develop")
            ok, msg = k8s_rollout_restart(deploy, ns)
            self.send_json({"success": ok, "message": msg}, status=200 if ok else 400)

        elif path == "/api/k8s/rollout_all":
            ns = payload.get("namespace", "develop")
            ok, msg = k8s_rollout_all(ns)
            self.send_json({"success": ok, "message": msg}, status=200 if ok else 400)

        elif path == "/api/k8s/restart_multiple":
            deploys = payload.get("deployments", [])
            ns = payload.get("namespace", "develop")
            results = []
            for d in deploys:
                ok, msg = k8s_rollout_restart(d, ns)
                results.append({"deploy": d, "ok": ok, "message": msg})
            self.send_json({"success": True, "results": results})

        elif path == "/api/k8s/deploy":
            svc = payload.get("service", "")
            env_key = payload.get("env", "develop")
            ok, msg = k8s_deploy_service(svc, env_key)
            self.send_json({"success": ok, "message": msg}, status=200 if ok else 400)

        elif path == "/api/k8s/deploy_manifest":
            env_key = payload.get("env", "develop")
            archivo = payload.get("file", "")
            if not archivo:
                self.send_json({"success": False, "message": "Falta parámetro 'file'."}, status=400)
                return
            from devconsole.services.k8s_service import deploy_manifest
            ok, msg = deploy_manifest(archivo, env_key)
            self.send_json({"success": ok, "message": msg}, status=200 if ok else 400)
            return

        elif path == "/api/secrets/buscar":
            # Entrega credenciales leídas de los .env: POST y sólo Administrador.
            from devconsole import settings as _st
            env_key = payload.get("env", "develop")
            try:
                hallazgos = _st.buscar_secretos_en_servicios(env_key)
            except Exception as exc:
                self.send_json({"success": False, "message": str(exc)}, status=500)
                return
            requeridas = set(_st.referenced_secret_keys())
            self.send_json({
                "env": env_key,
                "hallazgos": [{k: v for k, v in h.items() if k != "valor"} for h in hallazgos],
                "valores": {h["clave"]: h["valor"] for h in hallazgos},
                "pendientes": sorted(requeridas - {h["clave"] for h in hallazgos}),
            })

        elif path == "/api/secrets/guardar":
            from devconsole import settings as _st
            valores = payload.get("valores") or {}
            valores = {k: str(v) for k, v in valores.items() if isinstance(k, str) and str(v).strip()}
            ok, msg = _st.set_secrets(valores)
            self.send_json({"success": ok, "message": msg}, status=200 if ok else 400)

        elif path == "/api/onlyoffice/sync_env":
            res = sync_contracts_onlyoffice_env(auto_fix=True)
            self.send_json(res)

        elif path == "/api/action":
            act = payload.get("action")
            force = payload.get("force", False)

            # La autorización de las acciones de infraestructura se resolvió en
            # la puerta única (security.ADMIN_ACTIONS), con la misma excepción
            # operativa para keydb / onlyoffice-local.
            # Phase 2: las acciones de consola pasan por el backend abstracto;
            # el launcher concreto (start_tilix.sh) ya no se nombra aquí.
            terminal = get_terminal_backend()
            env_script = str(BASE_DIR / "switch_env.sh")
            msg = "Acción ejecutada"
            report: dict | None = None

            if not force and act in (*dcfg.env_keys(), "single", "all", "tabs"):
                running = get_running_services_info()
                if len(running) > 0:
                    self.send_json({
                        "success": False,
                        "already_running": True,
                        "active_count": len(running),
                        "active_services": running,
                        "message": f"Ya hay {len(running)} microservicio(s) activos en ejecución."
                    }, status=409)
                    return

            if act in (*dcfg.env_keys(), "single", "all"):
                env_name = act if act in dcfg.env_keys() else dcfg.env_keys()[0]
                ok, msg, count = terminal.launch_services(None, env_name)
                if not ok:
                    terminal.run_action(act, wait=False, base_dir=BASE_DIR)
                    msg = f"Orden '{act}' enviada a Tilix."
                else:
                    msg = f"Ventana Tilix lanzada con todos los {count} servicios descubiertos ({env_name.upper()})."
            elif act in ("tabs", "b1", "b2", "front", "stop"):
                # El informe del backend trae el resultado por servicio ("12 de 12
                # en tmux"): descartarlo dejaba a la interfaz sin forma de saber
                # si la orden hizo algo, y parecía que el botón no funcionaba.
                report = terminal.run_action(act, wait=False, base_dir=BASE_DIR)
                if isinstance(report, dict):
                    msg = report.get("message") or f"Orden '{act}' ejecutada."
                    if report.get("ok") is False and not report.get("results"):
                        self.send_json({"success": False, "message": msg}, status=400)
                        return
                else:
                    msg = f"Orden '{act}' enviada al backend de terminales."
            elif act == "stop-close":
                terminal.run_action("stop-close", wait=False, base_dir=BASE_DIR)
                msg = "Deteniendo todos los servidores y cerrando consolas Tilix..."
            elif act == "restart":
                terminal.run_action("restart", wait=True, check=True, base_dir=BASE_DIR)
                msg = "Consolas activas refrescadas en su lugar."
            elif act in ("restart-backend", "restart-backends"):
                terminal.run_action("restart-backends", wait=True, check=True, base_dir=BASE_DIR)
                msg = "Todos los microservicios Backend (17) reiniciados."
            elif act in ("restart-frontend", "restart-frontends"):
                terminal.run_action("restart-frontends", wait=True, check=True, base_dir=BASE_DIR)
                msg = "Todos los microfrontends Frontend (10) reiniciados."
            elif act == "restart-single":
                svc = payload.get("service")
                port = str(payload.get("port", ""))
                terminal.run_action("restart-single", (svc, port),
                                    wait=True, check=True, base_dir=BASE_DIR)
                msg = f"Señal enviada a {svc} (: {port}): recargando en su consola."
            elif act == "stop-single":
                svc = payload.get("service")
                port = str(payload.get("port", ""))
                salida = terminal.run_action("stop-single", (svc, port),
                                             wait=True, check=False, base_dir=BASE_DIR)
                ok = bool(salida.get("ok")) if isinstance(salida, dict) else True
                msg = (salida.get("message") if isinstance(salida, dict) else None) or f"{svc} detenido."
                if not ok:
                    self.send_json({"success": False, "message": msg}, status=409)
                    return
            elif act == "start-slice":
                slice_key = payload.get("slice")
                slice_data = SLICES.get(slice_key)
                if slice_data:
                    started = []
                    for svc, port in slice_data["services"]:
                        if not is_port_open(port):
                            terminal.run_action("start", (svc, str(port)),
                                                wait=False, base_dir=BASE_DIR)
                            started.append(svc)
                            time.sleep(0.3)
                    msg = f"Flujo '{slice_data['title']}': se lanzaron {len(started)} servicios." if started else f"Flujo '{slice_data['title']}': todos activos."
            elif act == "docker-keycloak":
                subaction = payload.get("subaction", "restart")
                subprocess.run(["docker", subaction, "keycloak-sisper-local"], check=True, timeout=10)
                msg = f"Contenedor Keycloak: orden '{subaction}' ejecutada."
            elif act == "podman-container":
                container = payload.get("container")
                subaction = payload.get("subaction", "start")
                force_pull = payload.get("force_pull", False)
                cfg = INFRA_CONTAINERS.get(container)

                if cfg and subaction == "start":
                    c_exists = False
                    try:
                        c_exists = (subprocess.run(["podman", "container", "exists", container], stderr=subprocess.DEVNULL, timeout=3).returncode == 0)
                    except Exception:
                        c_exists = False

                    if c_exists:
                        try:
                            res = subprocess.run(["podman", "start", container], capture_output=True, text=True, timeout=30)
                            if res.returncode == 0:
                                msg = f"Contenedor Podman ({container}) iniciado con éxito."
                                if container == "onlyoffice-local":
                                    s_res = sync_contracts_onlyoffice_env(auto_fix=True)
                                    if s_res.get("updated"):
                                        msg += f" (Variables .env {settings.onlyoffice_sync_service() or 'del servicio'} sincronizadas con IP {s_res.get('pc_ip')})."
                            else:
                                self.send_json({"success": False, "message": f"Error al iniciar {container}: {res.stderr.strip()}"}, status=400)
                                return
                        except Exception as e:
                            self.send_json({"success": False, "message": f"Excepción al iniciar {container}: {e}"}, status=500)
                            return
                    else:
                        img_exists = False
                        try:
                            img_exists = (subprocess.run(["podman", "image", "exists", cfg["image"]], stderr=subprocess.DEVNULL, timeout=3).returncode == 0)
                        except Exception:
                            img_exists = False

                        if not img_exists and not force_pull:
                            self.send_json({
                                "success": False,
                                "needs_pull": True,
                                "container": container,
                                "image": cfg["image"],
                                "message": f"La imagen institucional '{cfg['image']}' no existe en el equipo local. ¿Deseas descargarla desde el Registry y desplegar el contenedor?"
                            })
                            return

                        if not img_exists and force_pull:
                            pull_res = subprocess.run(["podman", "pull", cfg["image"]], capture_output=True, text=True, timeout=600)
                            if pull_res.returncode != 0:
                                self.send_json({"success": False, "message": f"Error al descargar imagen {cfg['image']}: {pull_res.stderr.strip()}"}, status=500)
                                return

                        run_cmd = cfg["run_cmd"]
                        run_res = subprocess.run(run_cmd, capture_output=True, text=True, timeout=120)
                        if run_res.returncode == 0:
                            msg = f"Contenedor {container} desplegado e iniciado con éxito con configuración oficial."
                            if container == "onlyoffice-local":
                                s_res = sync_contracts_onlyoffice_env(auto_fix=True)
                                if s_res.get("updated"):
                                    msg += f" (Variables .env {settings.onlyoffice_sync_service() or 'del servicio'} sincronizadas con IP {s_res.get('pc_ip')})."
                        else:
                            self.send_json({"success": False, "message": f"Error al desplegar {container}: {run_res.stderr.strip()}"}, status=500)
                            return
                elif cfg and subaction == "pull":
                    pull_res = subprocess.run(["podman", "pull", cfg["image"]], capture_output=True, text=True, timeout=600)
                    if pull_res.returncode == 0:
                        msg = f"Imagen {cfg['image']} descargada con éxito desde el Registry institucional."
                    else:
                        self.send_json({"success": False, "message": f"Error al descargar imagen: {pull_res.stderr.strip()}"}, status=500)
                        return
                else:
                    try:
                        res = subprocess.run(["podman", subaction, container], capture_output=True, text=True, timeout=30)
                        if res.returncode == 0:
                            msg = f"Contenedor Podman ({container}): orden '{subaction}' ejecutada."
                        else:
                            self.send_json({"success": False, "message": f"Error en {subaction} {container}: {res.stderr.strip()}"}, status=400)
                            return
                    except Exception as e:
                        self.send_json({"success": False, "message": f"Error al ejecutar podman {subaction} {container}: {e}"}, status=500)
                        return
            elif act == "env-local":
                subprocess.run([env_script, "local", "--all"], check=True)
                msg = "Modo cambiado a LOCAL (--all) y parche de bitácora aplicado."
            elif act == "env-intranet":
                subprocess.run([env_script, "intranet", "--all"], check=True)
                msg = "Modo cambiado a INTRANET (--all) y parche de bitácora removido (git limpio)."
            elif act == "env-local-restart":
                subprocess.run([env_script, "local", "--all"], check=True)
                time.sleep(0.5)
                get_terminal_backend().run_action("restart", wait=True, check=True, base_dir=BASE_DIR)
                msg = "Cambiado a LOCAL y refrescando consolas activas en su lugar."
            elif act == "env-intranet-restart":
                subprocess.run([env_script, "intranet", "--all"], check=True)
                time.sleep(0.5)
                get_terminal_backend().run_action("restart", wait=True, check=True, base_dir=BASE_DIR)
                msg = "Cambiado a INTRANET y refrescando consolas activas en su lugar."
            elif act == "bitacora-local":
                subprocess.run([env_script, "bitacora-local"], check=True)
                msg = "Parche defensivo de bitácora activado en ms_sisper_sesion."
            elif act == "bitacora-intranet":
                subprocess.run([env_script, "bitacora-intranet"], check=True)
                msg = "Código original de bitácora restaurado (git limpio)."
            elif act == "git-action":
                svc = payload.get("service")
                subaction = payload.get("subaction")
                u = payload.get("username")
                p = payload.get("password")
                save = payload.get("save_credentials", False)
                pull_strat = payload.get("pull_strategy", "default")
                ok, git_res = run_git_action(svc, subaction, u, p, save, pull_strategy=pull_strat)
                if ok:
                    msg = f"[{svc}] Git {subaction}: {git_res}"
                else:
                    self.send_json({"success": False, "message": f"[{svc}] Error {subaction}: {git_res}"}, status=400)
                    return
            elif act == "checkout-branch":
                svc = payload.get("service")
                branch = payload.get("branch")
                port = payload.get("port")
                ok, git_msg = checkout_service_branch(svc, branch)
                if ok:
                    msg = f"[{svc}] {git_msg}"
                    if port and is_port_open(int(port)):
                        get_terminal_backend().run_action(
                            "restart-single", (svc, str(port)),
                            wait=True, check=True, base_dir=BASE_DIR)
                        msg += " Consola refrescada en Tilix."
                else:
                    self.send_json({"success": False, "message": f"[{svc}] {git_msg}"}, status=400)
                    return

            elif act in ("create-branch", "rename-branch"):
                svc = payload.get("service")
                port = payload.get("port")
                if act == "create-branch":
                    ok, git_msg = create_service_branch(
                        svc, payload.get("branch", ""), payload.get("from_branch"))
                else:
                    ok, git_msg = rename_service_branch(
                        svc, payload.get("old") or payload.get("branch", ""), payload.get("new", ""))
                if ok:
                    msg = f"[{svc}] {git_msg}"
                    if payload.get("restart") and port and is_port_open(int(port)):
                        get_terminal_backend().run_action(
                            "restart-single", (svc, str(port)),
                            wait=True, check=True, base_dir=BASE_DIR)
                        msg += " Consola refrescada en Tilix."
                else:
                    self.send_json({"success": False, "message": f"[{svc}] {git_msg}"}, status=400)
                    return

            # `open_viewer`: además de crear las sesiones, abre la ventana de
            # Tilix con un panel por consola (lo que hacía el lanzador legacy).
            if payload.get("open_viewer"):
                nombres = [r.get("service") for r in (report or {}).get("results", [])
                           if isinstance(r, dict) and r.get("service")]
                if not nombres:
                    # Acciones que no devuelven informe por servicio (entornos,
                    # "single"/"all"): se toman las sesiones gestionadas.
                    nombres = [sess.metadata.get("@sisper_service")
                               for sess in terminal.managed_sessions()
                               if sess.metadata.get("@sisper_service")]
                if nombres:
                    vok, vmsg = terminal.attach_viewers(nombres, title=act)
                    msg = f"{msg} {vmsg}" if vok else f"{msg} (visor: {vmsg})"

            self.send_json({"success": True, "message": msg})
        else:
            self.send_json({"success": False, "message": f"Endpoint '{path}' no encontrado."}, status=404)

    #: Rutas que mutan por método HTTP pero no cambian el estado que sondean
    #: las cachés (telemetría entrante y sesión de administrador).  Invalidar
    #: en cada latido haría que /api/status volviera a arrancar en frío de
    #: forma constante.
    _CACHE_NEUTRAL_PREFIXES = ("/api/telemetry/", "/api/auth/")

    def _send_text(self, texto: str, content_type: str = "text/plain; charset=utf-8",
                   status: int = 200) -> None:
        cuerpo = texto.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def send_json(self, data: dict, status: int = 200, extra_headers=None):
        # Toda respuesta a un método mutador descarta los sondeos cacheados,
        # de modo que el siguiente GET lea el estado ya cambiado en vez de la
        # ventana anterior.
        if getattr(self, "command", "GET") in ("POST", "PUT", "PATCH", "DELETE"):
            if not self.path.startswith(self._CACHE_NEUTRAL_PREFIXES):
                invalidate_all()

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._send_cors_headers()
        for name, value in (extra_headers or ()):
            self.send_header(name, value)
        self._send_security_headers()
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        try:
            self.wfile.write(json.dumps(data).encode("utf-8"))
        except (BrokenPipeError, ConnectionResetError):
            # El cliente (pestaña, ventana Electron, sonda de auditoría) cerró
            # la conexión antes de leer la respuesta.  Es normal al navegar o
            # cerrar la vista, y no debe ensuciar el journal con una traza.
            pass

    def log_message(self, format, *args):
        pass


