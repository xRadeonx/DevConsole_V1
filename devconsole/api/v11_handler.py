"""V1.1 compatibility handler.

This class wraps the large V1 handler instead of replacing it.  Existing routes
still execute the exact legacy code, while V1.1 adds a stricter outer
authorization boundary and additive endpoints.  This keeps rollback trivial:
server.py can switch back to the legacy handler in one line.
"""
from __future__ import annotations

import io
import json
import urllib.parse
from pathlib import Path

import devconsole.config as dcfg
from devconsole import auth, auth_v11, local_trust
from devconsole.api.handlers import DevConsoleHandler as LegacyHandler
from devconsole.api.handlers import _version_estaticos
from devconsole.security import (
    ADMIN_ACTIONS,
    ADMIN_PATHS,
    INFRA_EXEMPT_CONTAINERS,
    is_loopback_host,
    is_origin_allowed,
)
from devconsole.services.build_jobs import get_build_coordinator
from devconsole.services.k8s_guard import current_context, diff_manifest, preflight, rollout_undo
from devconsole.services.manifest_service import (
    ManifestDependencyMissing,
    apply_image_tag_update,
    preview_image_tag_update,
)
from devconsole.services.project_detector import detect_workspace
from devconsole.services.terminal.capabilities import terminal_capabilities
from devconsole.startup import configuration_diagnostics

_ROLE_RANK = {"viewer": 1, "dev": 2, "admin": 3}

# These V1 GET routes expose user/session/IP/audit or raw environment material.
_ADMIN_GETS = {
    "/api/analytics/connections",
    "/api/activity/feed",
    "/api/activity/detail",
    "/api/telemetry/live",
    "/api/telemetry/mirror_view",
}
_DEV_GETS = {
    "/api/env/get",
    "/api/deployments/inspect",
}

# Frontend telemetry ingestion must continue working without a developer login;
# reads of that telemetry are admin-only above.
_PUBLIC_POSTS = {
    "/api/auth/verify_pin",
    "/api/auth/logout",
    "/api/telemetry/heartbeat",
    "/api/telemetry/mirror_stream",
}

_EXTRA_ADMIN_POSTS = {
    "/api/telemetry/mirror_control",
    "/api/k8s/theme",
    "/api/v1.1/k8s/update_image",
    "/api/v1.1/k8s/rollback",
}


def _manifest_for(service: str, env_key: str) -> tuple[Path | None, str, str]:
    from devconsole.services.k8s_service import k8s_dir_for

    env_cfg = dcfg.ENVIRONMENTS.get(env_key, {})
    namespace = str(env_cfg.get("namespace", env_key or "develop"))
    all_services = list(dcfg.SERVICES_BACKEND) + list(dcfg.SERVICES_FRONTEND)
    meta = next((item for item in all_services if item.get("name") == service), None)
    if not meta or not meta.get("k8s_file"):
        return None, namespace, "Servicio sin manifiesto K8s mapeado."
    root = Path(dcfg.BASE_DIR) / k8s_dir_for(env_key)
    path = (root / str(meta["k8s_file"])).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return None, namespace, "Ruta de manifiesto fuera de la carpeta K8s."
    if not path.is_file():
        return None, namespace, f"Manifiesto no encontrado: {path.name}"
    return path, namespace, ""


class DevConsoleV11Handler(LegacyHandler):
    """Strict/additive facade over the V1 HTTP handler."""

    def _effective_role(self) -> str:
        return auth_v11.effective_role(self.headers)

    def _trusted_request(self) -> tuple[bool, str]:
        try:
            host = self.headers.get("Host")
            origin = self.headers.get("Origin")
        except Exception:
            return False, "Cabeceras de seguridad no disponibles."
        if not is_loopback_host(host):
            return False, "Solicitud rechazada: Host no permitido."
        if not is_origin_allowed(origin):
            return False, "Solicitud rechazada: origen no autorizado."
        ok, _reason = local_trust.enforce_request_token(self.headers.get)
        if not ok:
            return False, "Solicitud rechazada: token de confianza local ausente o inválido."
        return True, ""

    def _require_role(self, minimum: str) -> bool:
        role = self._effective_role()
        if _ROLE_RANK.get(role, 0) >= _ROLE_RANK[minimum]:
            return True
        self.send_json(
            {
                "success": False,
                "message": (
                    "Acción denegada: inicia sesión como Desarrollador."
                    if minimum == "dev"
                    else "Acción protegida: requiere sesión de Administrador / DevOps."
                ),
                "required_role": minimum,
                "role": role,
            },
            status=403,
        )
        return False

    def _read_body(self) -> tuple[bytes, dict | None]:
        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
        except (TypeError, ValueError):
            length = 0
        body = self.rfile.read(length) if length else b""
        if not body:
            return body, {}
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            return body, None
        return body, payload if isinstance(payload, dict) else None

    def _serve_index_v11(self) -> None:
        index_file = dcfg.STATIC_DIR / "index.html"
        if not index_file.exists():
            self.send_response(404)
            self.end_headers()
            return
        html = index_file.read_text(encoding="utf-8")
        versions = _version_estaticos()
        for name, version in versions.items():
            html = html.replace(f'"/static/{name}"', f'"/static/{name}?v={version}"')
        module_tag = '<script type="module" src="/static/js/app-v11.js"></script>'
        if module_tag not in html:
            html = html.replace("</body>", f"  {module_tag}\n</body>")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        if local_trust.token_required():
            self.send_header("Set-Cookie", local_trust.build_cookie_header())
        self._send_security_headers()
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path in {"/", "/index.html"}:
            self._serve_index_v11()
            return

        if path.startswith("/api/"):
            trusted, message = self._trusted_request()
            if not trusted:
                self.send_json({"success": False, "message": message}, status=403)
                return

        if path in _ADMIN_GETS and not self._require_role("admin"):
            return
        if path in _DEV_GETS and not self._require_role("dev"):
            return

        params = urllib.parse.parse_qs(parsed.query)
        if path == "/api/v1.1/capabilities":
            self.send_json({
                "version": "1.1",
                "role": self._effective_role(),
                "terminal": terminal_capabilities(dcfg.STATIC_DIR),
                "dependencies": configuration_diagnostics(dcfg.DASHBOARD_DIR)["dependencies"],
            })
            return
        if path == "/api/v1.1/config/diagnostics":
            if not self._require_role("dev"):
                return
            self.send_json(configuration_diagnostics(dcfg.DASHBOARD_DIR))
            return
        if path == "/api/v1.1/projects":
            if not self._require_role("dev"):
                return
            profiles = [p.to_dict() for p in detect_workspace(dcfg.BASE_DIR)]
            self.send_json({"projects": profiles, "count": len(profiles)})
            return
        if path == "/api/v1.1/build/jobs":
            if not self._require_role("dev"):
                return
            self.send_json({"jobs": get_build_coordinator().store.list()})
            return
        if path == "/api/v1.1/k8s/preflight":
            if not self._require_role("admin"):
                return
            env_key = params.get("env", ["develop"])[0]
            cfg = dcfg.ENVIRONMENTS.get(env_key, {})
            namespace = str(cfg.get("namespace", env_key))
            expected = params.get("context", [None])[0]
            self.send_json(preflight(namespace, expected))
            return
        if path == "/api/v1.1/k8s/manifest_preview":
            if not self._require_role("admin"):
                return
            service = params.get("service", [""])[0]
            env_key = params.get("env", ["develop"])[0]
            version = params.get("version", [""])[0]
            manifest, namespace, error = _manifest_for(service, env_key)
            if error or manifest is None:
                self.send_json({"success": False, "message": error}, status=400)
                return
            try:
                change = preview_image_tag_update(manifest, version)
            except ManifestDependencyMissing as exc:
                self.send_json({"success": False, "message": str(exc)}, status=503)
                return
            kdiff = diff_manifest(manifest, namespace)
            self.send_json({
                "success": True,
                "changed": change.changed,
                "diff": change.diff,
                "images_before": list(change.images_before),
                "images_after": list(change.images_after),
                "kubectl_context": current_context(),
                "kubectl_diff": kdiff.stdout or kdiff.stderr,
                "kubectl_diff_returncode": kdiff.returncode,
            })
            return

        super()._do_GET()

    def _do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body, payload = self._read_body()
        if payload is None:
            self.send_json({"success": False, "message": "JSON inválido."}, status=400)
            return

        trusted, message = self._trusted_request()
        if not trusted:
            self.send_json({"success": False, "message": message}, status=403)
            return

        if path == "/api/auth/verify_pin":
            raw_pin = payload.get("pin")
            pin = raw_pin.strip() if isinstance(raw_pin, str) else ""
            role = str(payload.get("role") or "admin").lower()
            if role == "dev":
                ok, token = auth_v11.verify_dev_pin(pin)
                if not ok:
                    self.send_json({"success": False, "message": "PIN incorrecto. Verifica la clave de desarrollador."}, status=401)
                    return
                self.send_json(
                    {"success": True, "token": token, "role": "dev", "message": "Autenticación exitosa como Desarrollador."},
                    extra_headers=[("Set-Cookie", auth_v11.build_dev_cookie(token))],
                )
                return
            ok, token = auth.verify_pin(pin, "admin")
            if not ok:
                self.send_json({"success": False, "message": "PIN incorrecto. Verifica la clave de administrador."}, status=401)
                return
            self.send_json(
                {"success": True, "token": token, "role": "admin", "message": "Autenticación exitosa como Administrador."},
                extra_headers=[("Set-Cookie", auth.build_admin_cookie(token))],
            )
            return

        if path == "/api/auth/logout":
            admin_token = auth.admin_token_from(self.headers)
            dev_token = auth_v11.dev_token_from(self.headers)
            auth.invalidate_admin_token(admin_token)
            auth_v11.invalidate_dev_token(dev_token)
            self.send_json(
                {"success": True, "message": "Sesión cerrada correctamente."},
                extra_headers=[
                    ("Set-Cookie", auth.build_admin_cookie_clear()),
                    ("Set-Cookie", auth_v11.build_dev_cookie_clear()),
                ],
            )
            return

        required = "viewer"
        if path not in _PUBLIC_POSTS:
            required = "dev"
        if path in ADMIN_PATHS or path in _EXTRA_ADMIN_POSTS:
            required = "admin"
        if path == "/api/action":
            action = str(payload.get("action") or "")
            container = payload.get("container")
            if action in ADMIN_ACTIONS and not (
                action == "podman-container" and container in INFRA_EXEMPT_CONTAINERS
            ):
                required = "admin"
        if path == "/api/v1.1/build/start" and bool(payload.get("push")):
            required = "admin"
        if required != "viewer" and not self._require_role(required):
            return

        if path == "/api/v1.1/build/start":
            service = str(payload.get("service") or "").strip()
            tag = str(payload.get("tag") or "latest").strip()
            ref = str(payload.get("ref") or "HEAD").strip()
            image = str(payload.get("image") or service).strip()
            if not service or not image:
                self.send_json({"success": False, "message": "service e image son obligatorios."}, status=400)
                return
            repo = Path(dcfg.get_service_repo_dir(service)).resolve()
            if not repo.is_dir():
                self.send_json({"success": False, "message": f"Repositorio no encontrado para {service}."}, status=404)
                return
            job = get_build_coordinator().start(
                service=service,
                repo_dir=repo,
                image=image,
                tag=tag,
                ref=ref,
                push=bool(payload.get("push", False)),
                engine_name=payload.get("engine"),
                build_args=payload.get("build_args") if isinstance(payload.get("build_args"), dict) else None,
            )
            self.send_json({"success": True, "job": job.to_dict()}, status=202)
            return

        if path == "/api/v1.1/build/cancel":
            job_id = str(payload.get("job_id") or "")
            ok = get_build_coordinator().cancel(job_id)
            self.send_json({"success": ok, "job_id": job_id}, status=200 if ok else 404)
            return

        if path == "/api/v1.1/k8s/update_image":
            service = str(payload.get("service") or "")
            env_key = str(payload.get("env") or "develop")
            version = str(payload.get("version") or "")
            confirmed = bool(payload.get("confirmed", False))
            if not confirmed:
                self.send_json({"success": False, "message": "Se requiere confirmed=true después de revisar el preview."}, status=409)
                return
            manifest, namespace, error = _manifest_for(service, env_key)
            if error or manifest is None:
                self.send_json({"success": False, "message": error}, status=400)
                return
            guard = preflight(namespace, payload.get("expected_context"))
            if not guard.get("ok"):
                self.send_json({"success": False, "message": "Preflight K8s falló.", "preflight": guard}, status=409)
                return
            try:
                change = apply_image_tag_update(manifest, version)
            except ManifestDependencyMissing as exc:
                self.send_json({"success": False, "message": str(exc)}, status=503)
                return
            self.send_json({"success": change.changed, "diff": change.diff, "preflight": guard}, status=200 if change.changed else 409)
            return

        if path == "/api/v1.1/k8s/rollback":
            deployment = str(payload.get("deployment") or "")
            namespace = str(payload.get("namespace") or "develop")
            if not deployment:
                self.send_json({"success": False, "message": "deployment es obligatorio."}, status=400)
                return
            result = rollout_undo(deployment, namespace)
            self.send_json({"success": result.ok, "stdout": result.stdout, "stderr": result.stderr}, status=200 if result.ok else 400)
            return

        # Rewind the body for the V1 handler.  It performs its own legacy
        # authorization as a second layer, then executes the unchanged route.
        original = self.rfile
        try:
            self.rfile = io.BytesIO(body)
            super()._do_POST()
        finally:
            self.rfile = original


# Stable import name for server.py.
DevConsoleHandler = DevConsoleV11Handler
