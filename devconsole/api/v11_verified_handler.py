"""Second-pass verified V1.1 HTTP facade.

This layer is intentionally very small.  It fixes compatibility/correctness
issues found during the independent V1.1 re-audit without modifying the frozen
legacy handler used by ``SISPER_V11_HANDLER=0``.
"""
from __future__ import annotations

import urllib.parse

from devconsole.api.handlers import get_running_services_info
from devconsole.api.v11_handler import DevConsoleV11Handler, required_role_for
from devconsole.services.environment_transaction import switch_workspace_environment_transactional
from devconsole.services.terminal.registry import get_terminal_backend


class DevConsoleVerifiedV11Handler(DevConsoleV11Handler):
    """V1.1 facade with strict transaction reporting and V1 response parity."""

    def _verified_payload(self, path: str):
        body, payload = self._read_body()
        if payload is None:
            self.send_json({"success": False, "message": "JSON inválido."}, status=400)
            return None
        trusted, message = self._trusted_request()
        if not trusted:
            self.send_json({"success": False, "message": message}, status=403)
            return None
        minimum = required_role_for(path, payload)
        if minimum != "viewer" and not self._require_role(minimum):
            return None
        return payload

    def _switch_environment(self, payload: dict) -> None:
        result = switch_workspace_environment_transactional(
            str(payload.get("target_env") or "develop"),
            bool(payload.get("force_pull", False)),
        )
        committed = result.get("transaction") == "committed"
        response = {"success": committed, "data": result}
        if not committed:
            response["message"] = result.get("message") or "Cambio de entorno no confirmado."
        self.send_json(response, status=200 if committed else 409)

    def _launch_selected(self, payload: dict) -> None:
        raw_services = payload.get("services", [])
        if raw_services is None:
            raw_services = []
        if not isinstance(raw_services, list):
            self.send_json({"success": False, "message": "'services' debe ser una lista."}, status=400)
            return
        selected = [str(name) for name in raw_services if str(name).strip()]
        target_env = str(payload.get("env") or "develop")
        force = bool(payload.get("force", False))

        if not force:
            running = get_running_services_info()
            running_map = {r["name"]: r for r in running if "name" in r}
            conflicts = [running_map[name] for name in selected if name in running_map] if selected else running
            if conflicts:
                self.send_json({
                    "success": False,
                    "already_running": True,
                    "active_count": len(conflicts),
                    "active_services": conflicts,
                    "message": f"Ya hay {len(conflicts)} de los servicios seleccionados activos en ejecución.",
                }, status=409)
                return

        backend = get_terminal_backend()
        ok, launch_message, count = backend.launch_services(selected, target_env)

        # Viewer information is additive metadata.  The historical ``message``
        # remains exactly the launch provider's message so V1 clients/tests do
        # not change behaviour simply because V1.1 can also attach a viewer.
        viewer = {
            "requested": bool(payload.get("open_viewer", True) and selected),
            "attempted": False,
            "success": None,
            "message": "",
        }
        if ok and viewer["requested"]:
            viewer["attempted"] = True
            viewer_ok, viewer_message = backend.attach_viewers(selected, title="seleccionados")
            viewer["success"] = bool(viewer_ok)
            viewer["message"] = viewer_message or ""

        self.send_json({
            "success": ok,
            "message": launch_message,
            "count": count,
            "viewer": viewer,
        }, status=200 if ok else 400)

    def _do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/environment/switch":
            payload = self._verified_payload(path)
            if payload is not None:
                self._switch_environment(payload)
            return
        if path in {"/api/tilix/launch_selected", "/api/tilix/launch_selected_services"}:
            payload = self._verified_payload(path)
            if payload is not None:
                self._launch_selected(payload)
            return
        super()._do_POST()


DevConsoleHandler = DevConsoleVerifiedV11Handler
