"""Characterization tests: DevConsole read-only HTTP API (roadmap item 0A-C.10).

Two layers are frozen:

* **Isolated handler tests** — call ``do_GET`` on a handler instance wired to
  in-memory buffers, with every service-layer dependency patched.  These pin the
  JSON schema, status codes and CORS headers per endpoint.
* **One real-socket test** — a ``ThreadingHTTPServer`` bound to ``127.0.0.1`` on
  an ephemeral port, to prove HTTP framing and routing still work end to end.

Only ``GET`` is exercised.  No destructive endpoint is touched, no service is
started or stopped, and every dependency is mocked.
"""

from __future__ import annotations

import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from unittest import mock

from tests.devconsole.support import (
    DevConsoleTestCase,
    capture_output,
    json_body,
    json_documents,
    make_handler,
    make_workspace,
    raw_body,
    response_headers,
)

import devconsole.config as dcfg
from devconsole.api import handlers
from devconsole.api.handlers import DevConsoleHandler
from devconsole.services.terminal import tilix_backend


def fake_git_info(branch="develop", dirty=0, ahead=0, behind=0):
    return {
        "branch": branch, "dirty": dirty, "ahead": ahead, "behind": behind,
        "has_upstream": True, "unpushed_commits": [], "unpulled_commits": [],
        "dirty_files": [],
    }


class GetEndpointTestCase(DevConsoleTestCase):
    """Common wiring: patch every I/O-touching dependency of ``do_GET``."""

    def setUp(self):
        super().setUp()
        self.root = make_workspace(self.temp_dir())
        self.backend = [{"name": "ms_sisper_sesion", "port": 8000, "group": "Backend 1",
                         "k8s_file": "backend/ms_sesion.yaml", "k8s_deploy": "ms-sesion"}]
        self.frontend = [{"name": "mf_sisper_sesion", "port": 3000,
                          "k8s_file": "frontend/mf_sesion.yaml", "k8s_deploy": "mf-sesion"}]

        patches = [
            mock.patch.object(handlers, "is_port_open", return_value=False),
            mock.patch.object(handlers, "get_git_info", side_effect=lambda d: fake_git_info()),
            mock.patch.object(handlers, "get_env_info",
                              return_value={"env_mode": "INTRANET",
                                            "bitacora_status": "ORIGINAL",
                                            "database_host": "172.30.23.71",
                                            "keycloak_url": ""}),
            mock.patch.object(handlers, "get_infra_info",
                              return_value={"keydb": {"port_open": True}}),
            mock.patch.object(handlers, "get_all_environments_status",
                              return_value={"total_services": 2, "aligned_counts": {},
                                            "dirty_counts": {}, "services": []}),
            mock.patch.object(tilix_backend, "scan_tilix_sessions", return_value=[]),
            mock.patch.object(handlers, "get_running_services_info", return_value=[]),
            mock.patch.object(handlers, "get_config_git_status",
                              return_value={"online": True, "branch": "main", "dirty": 0,
                                            "dirty_count": 0, "dirty_files": [], "files": [],
                                            "ahead": 0, "behind": 0}),
            mock.patch.object(handlers, "inspect_directory",
                              return_value={"valid": True, "path": str(self.root),
                                            "folder_name": "Develop", "has_backend_dir": True,
                                            "has_frontend_dir": True, "has_config_json": True,
                                            "backend_services": ["ms_sisper_sesion"],
                                            "frontend_services": ["mf_sisper_sesion"],
                                            "backend_count": 1, "frontend_count": 1,
                                            "subdirs": [], "parent_dir": "/home/proteo/Documentos"}),
            mock.patch.object(handlers, "BASE_DIR", self.root),
            mock.patch.object(handlers, "DASHBOARD_DIR", self.root),
            mock.patch.object(dcfg, "BASE_DIR", self.root),
            mock.patch.object(dcfg, "SERVICES_BACKEND", self.backend),
            mock.patch.object(dcfg, "SERVICES_FRONTEND", self.frontend),
            mock.patch.object(dcfg, "SLICES", {
                "contratos": {"title": "Flujo Contratos", "description": "d",
                              "services": [["ms_sisper_sesion", 8000]]}}),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def get(self, path, headers=None):
        h = make_handler(DevConsoleHandler, path=path, headers=headers or {})
        h.do_GET()
        return h


class ApiStatusTest(GetEndpointTestCase):
    """/api/status — the dashboard's main polling endpoint."""

    def test_returns_200_json(self):
        h = self.get("/api/status")
        self.assertEqual(200, h.captured["status"])
        self.assertEqual("application/json; charset=utf-8",
                         response_headers(h)["content-type"])

    def test_payload_contract(self):
        data = json_body(self.get("/api/status"))
        for key in ("base_dir", "folder_name", "backend", "frontend", "env",
                    "infra", "env_summary", "slices", "env_watcher"):
            self.assertIn(key, data, f"/api/status lost key {key!r}")

    def test_services_are_enriched_with_online_and_git_fields(self):
        data = json_body(self.get("/api/status"))
        entry = data["backend"][0]
        self.assertEqual("ms_sisper_sesion", entry["name"])
        self.assertEqual(8000, entry["port"])
        self.assertIn("online", entry)
        self.assertIn("branch", entry)
        self.assertIn("dirty", entry)

    def test_online_reflects_the_port_probe(self):
        with mock.patch.object(handlers, "is_port_open", side_effect=lambda p: p == 8000):
            data = json_body(self.get("/api/status"))
        self.assertTrue(data["backend"][0]["online"])
        self.assertFalse(data["frontend"][0]["online"])

    def test_env_watcher_block_is_reported(self):
        data = json_body(self.get("/api/status"))
        self.assertTrue(data["env_watcher"]["enabled"])
        self.assertIsInstance(data["env_watcher"]["recent_events"], list)

    def test_slices_are_flattened_to_service_names(self):
        data = json_body(self.get("/api/status"))
        self.assertIn("contratos", data["slices"])
        self.assertEqual(["ms_sisper_sesion"],
                         data["slices"]["contratos"]["services_names"])

    def test_base_dir_is_reported(self):
        data = json_body(self.get("/api/status"))
        self.assertEqual(str(self.root), data["base_dir"])

    def test_same_origin_response_carries_no_wildcard_cors(self):
        """Hardened in 0C.6: a same-origin request gets no CORS grant at all.

        Pre-0C every response carried ``Access-Control-Allow-Origin: *`` plus
        ``Access-Control-Allow-Private-Network: true``, which allowed any web
        page the developer visited to *read* this API cross-origin.
        """
        h = self.get("/api/status")
        hdrs = response_headers(h)
        self.assertNotIn("access-control-allow-origin", hdrs)
        self.assertNotIn("access-control-allow-private-network", hdrs)

    def test_allowed_origin_is_echoed_back(self):
        h = self.get("/api/status", headers={"Origin": "http://127.0.0.1:9099"})
        hdrs = response_headers(h)
        self.assertEqual("http://127.0.0.1:9099", hdrs["access-control-allow-origin"])
        self.assertIn("GET", hdrs["access-control-allow-methods"])
        self.assertEqual("Origin", hdrs["vary"])

    def test_hostile_origin_is_refused_outright(self):
        """Origin validation is defence *and* enforcement: a hostile page is
        refused outright, not merely denied the CORS grant."""
        h = self.get("/api/status", headers={"Origin": "https://evil.example"})
        self.assertEqual(403, h.captured["status"])
        self.assertNotIn("access-control-allow-origin", response_headers(h))

    def test_wildcard_is_never_emitted(self):
        for origin in (None, "http://127.0.0.1:9099", "https://evil.example", "null"):
            with self.subTest(origin=origin):
                hdrs = response_headers(self.get(
                    "/api/status", headers={"Origin": origin} if origin else {}))
                self.assertNotEqual("*", hdrs.get("access-control-allow-origin"))

    def test_no_cache_headers(self):
        hdrs = response_headers(self.get("/api/status"))
        self.assertIn("no-store", hdrs["cache-control"])


class ApiRootDirInfoTest(GetEndpointTestCase):
    """/api/root_dir/info."""

    def test_returns_200_with_inspection_payload(self):
        h = self.get("/api/root_dir/info")
        data = json_body(h)
        self.assertEqual(200, h.captured["status"])
        self.assertIn("valid", data)
        self.assertIn("backend_count", data)

    def test_adds_dashboard_dir_and_default_flag(self):
        data = json_body(self.get("/api/root_dir/info"))
        self.assertIn("dashboard_dir", data)
        self.assertIn("is_default", data)
        self.assertTrue(data["is_default"], "BASE_DIR == DASHBOARD_DIR must yield is_default")


class ApiTilixSessionsTest(GetEndpointTestCase):
    """/api/tilix/sessions."""

    def test_returns_200_and_empty_list(self):
        h = self.get("/api/tilix/sessions")
        data = json_body(h)
        self.assertEqual(200, h.captured["status"])
        self.assertEqual([], data["sessions"])

    def test_payload_contract(self):
        data = json_body(self.get("/api/tilix/sessions"))
        self.assertEqual({"base_dir", "sessions"}, set(data.keys()))

    def test_sessions_are_passed_through(self):
        sample = [{"name": "s.json", "rel_path": "s.json", "abs_path": "/x/s.json",
                   "terminals": 3, "is_default": True}]
        with mock.patch.object(tilix_backend, "scan_tilix_sessions", return_value=sample):
            data = json_body(self.get("/api/tilix/sessions"))
        self.assertEqual(3, data["sessions"][0]["terminals"])


class ApiEnvironmentStatusTest(GetEndpointTestCase):
    """/api/environment/status."""

    def test_returns_200_and_passes_payload_through(self):
        payload = {"total_services": 31, "aligned_counts": {"develop": 5},
                   "dirty_counts": {}, "services": []}
        with mock.patch.object(handlers, "get_all_environments_status", return_value=payload):
            h = self.get("/api/environment/status")
        self.assertEqual(200, h.captured["status"])
        self.assertEqual(31, json_body(h)["total_services"])


class ApiServicesRunningTest(GetEndpointTestCase):
    """/api/services/running."""

    def test_returns_200_with_empty_running_set(self):
        h = self.get("/api/services/running")
        data = json_body(h)
        self.assertEqual(200, h.captured["status"])
        self.assertEqual([], data["running"])
        self.assertEqual(0, data["count"])

    def test_count_matches_the_running_list(self):
        running = [{"name": "ms_sisper_sesion", "port": 8000},
                   {"name": "mf_sisper_sesion", "port": 3000}]
        with mock.patch.object(handlers, "get_running_services_info", return_value=running):
            data = json_body(self.get("/api/services/running"))
        self.assertEqual(2, data["count"])
        self.assertEqual(running, data["running"])


class ApiConfigGitStatusTest(GetEndpointTestCase):
    """/api/config_git/status."""

    def test_returns_200_and_payload_contract(self):
        h = self.get("/api/config_git/status")
        data = json_body(h)
        self.assertEqual(200, h.captured["status"])
        for key in ("online", "branch", "dirty", "dirty_count", "dirty_files",
                    "files", "ahead", "behind"):
            self.assertIn(key, data, f"/api/config_git/status lost key {key!r}")

    def test_offline_state_is_reported(self):
        with mock.patch.object(handlers, "get_config_git_status",
                               return_value={"online": False, "error": "no repo"}):
            data = json_body(self.get("/api/config_git/status"))
        self.assertFalse(data["online"])
        self.assertIn("error", data)


class ApiAuthValidateSessionTest(GetEndpointTestCase):
    """/api/auth/validate_session — role/token gate used by the UI on load."""

    def test_anonymous_request_is_not_valid(self):
        data = json_body(self.get("/api/auth/validate_session"))
        self.assertFalse(data["valid"])
        self.assertEqual("dev", data["role"])

    def test_developer_role_is_not_valid(self):
        data = json_body(self.get("/api/auth/validate_session",
                                  headers={"X-Auth-Role": "dev"}))
        self.assertFalse(data["valid"])

    def test_admin_with_invalid_token_is_not_valid(self):
        data = json_body(self.get("/api/auth/validate_session",
                                  headers={"X-Auth-Role": "admin",
                                           "X-Auth-Token": "bogus"}))
        self.assertFalse(data["valid"])

    def test_admin_with_valid_token_is_valid(self):
        with mock.patch.object(handlers, "is_valid_admin_token", return_value=True):
            data = json_body(self.get("/api/auth/validate_session",
                                      headers={"X-Auth-Role": "admin",
                                               "X-Auth-Token": "good"}))
        self.assertTrue(data["valid"])
        self.assertEqual("admin", data["role"])

    def test_contract_keys(self):
        data = json_body(self.get("/api/auth/validate_session"))
        self.assertIn("valid", data)
        self.assertIn("role", data)


class ApiUnknownRouteTest(GetEndpointTestCase):
    """Unknown GET routes must 404, not raise."""

    def test_unknown_path_returns_404(self):
        h = self.get("/api/definitely-not-a-route")
        self.assertEqual(404, h.captured["status"])

    def test_root_returns_404_when_index_html_is_absent(self):
        # handlers.STATIC_DIR is patched to a temp dir with no index.html.
        with mock.patch.object(handlers, "STATIC_DIR", self.temp_dir()):
            h = self.get("/")
        self.assertEqual(404, h.captured["status"])

    def test_root_serves_index_html_when_present(self):
        static = self.temp_dir()
        (static / "index.html").write_text("<html>ok</html>", encoding="utf-8")
        with mock.patch.object(handlers, "STATIC_DIR", static):
            h = self.get("/")
        self.assertEqual(200, h.captured["status"])
        self.assertIn(b"<html>ok</html>", raw_body(h))

    def test_static_path_traversal_is_blocked(self):
        static = self.temp_dir()
        (static / "ok.txt").write_text("fine", encoding="utf-8")
        with mock.patch.object(handlers, "STATIC_DIR", static):
            h = self.get("/static/../../../../etc/passwd")
        self.assertEqual(404, h.captured["status"])


class EphemeralServerWireTest(GetEndpointTestCase):
    """Real HTTP round-trip on 127.0.0.1 with an ephemeral port.

    Proves routing/framing work over a socket.  All service dependencies remain
    mocked, so no real I/O reaches the workspace.
    """

    def test_get_endpoints_answer_over_a_real_socket(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), DevConsoleHandler)
        port = server.server_address[1]
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        self.addCleanup(server.shutdown)
        self.addCleanup(server.server_close)

        try:
            for path, expect_key in (
                ("/api/services/running", "running"),
                ("/api/auth/validate_session", "valid"),
                ("/api/tilix/sessions", "sessions"),
            ):
                with self.subTest(path=path):
                    with urllib.request.urlopen(
                            f"http://127.0.0.1:{port}{path}", timeout=5) as resp:
                        self.assertEqual(200, resp.status)
                        self.assertIn("application/json", resp.headers["Content-Type"])
                        # Wired over a real socket with no Origin header, i.e.
                        # a same-origin / non-browser client: no CORS grant is
                        # emitted (hardened in 0C.6).
                        self.assertIsNone(resp.headers["Access-Control-Allow-Origin"])
                        # Security headers are present on the wire.
                        self.assertEqual("nosniff", resp.headers["X-Content-Type-Options"])
                        self.assertEqual("no-referrer", resp.headers["Referrer-Policy"])
                        self.assertEqual("SAMEORIGIN", resp.headers["X-Frame-Options"])
                        payload = json.loads(resp.read().decode("utf-8"))
                        self.assertIn(expect_key, payload)
        finally:
            server.shutdown()

    def test_unknown_route_returns_404_over_a_real_socket(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), DevConsoleHandler)
        port = server.server_address[1]
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        self.addCleanup(server.server_close)

        try:
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/nope", timeout=5)
            self.assertEqual(404, ctx.exception.code)
            ctx.exception.close()
        finally:
            server.shutdown()


class PostGuardsTest(GetEndpointTestCase):
    """Characterization of POST authorization guards.

    Only *denial* paths are exercised and every service function is mocked, so
    no protected action can actually take effect.  What is asserted is the
    **observed** behaviour, including one pre-existing defect:

    ``KNOWN_PREEXISTING`` (CRITICAL, see docs/desktop-migration/phase-0a-baseline.md#br-01):
    the admin guard at ``handlers.py:535-541`` calls ``send_json(..., status=403)``
    **without a ``return``**.  Consequently, for a caller that is not viewer
    (including an anonymous caller, because ``is_admin_request`` defaults the
    role to ``"dev"``), the 403 is emitted *and then the protected handler body
    still runs*, emitting a second response.  As a real HTTP client only reads
    the first status line, such a request looks rejected while the action is
    executed server-side.

    These tests pin that behaviour so Phase 0C can prove the fix without
    guessing what "before" looked like.
    """

    def setUp(self):
        super().setUp()
        # Expected denials are logged by the security audit; keep the suite
        # output clean while still exercising the real code path.
        capture_output(self)

    def post(self, path, payload, headers=None):
        body = json.dumps(payload).encode("utf-8")
        h = make_handler(DevConsoleHandler, path=path, method="POST",
                         headers=headers or {}, body=body)
        h.do_POST()
        return h

    # -- viewer guard: correctly implemented, must return early ------------- #

    def test_viewer_role_is_denied_on_generic_action(self):
        h = self.post("/api/action", {"action": "restart"},
                      headers={"X-Auth-Role": "viewer"})
        self.assertEqual(403, h.captured["status"])
        self.assertEqual([403], h.captured["statuses"],
                         "viewer guard must emit exactly one response")
        self.assertIn("solo lectura", json_body(h)["message"])

    def test_viewer_is_denied_for_every_protected_path(self):
        for path in ("/api/config_git/push", "/api/environment/switch",
                     "/api/deployments/build", "/api/k8s/restart",
                     "/api/k8s/rollout_all", "/api/k8s/deploy"):
            with self.subTest(path=path):
                h = self.post(path, {}, headers={"X-Auth-Role": "viewer"})
                self.assertEqual([403], h.captured["statuses"], path)

    # -- admin guard: BR-01 fixed in 0C ------------------------------------- #

    def test_admin_guard_denial_does_not_reach_the_action(self):
        """BR-01 (fixed): the 403 must stop execution before the handler body."""
        called = []
        with mock.patch.object(handlers, "k8s_rollout_restart",
                               side_effect=lambda d, ns: (called.append((d, ns)), (True, "ok"))[1]):
            h = self.post("/api/k8s/restart", {"deploy": "ms-sesion",
                                               "namespace": "develop"},
                          headers={"X-Auth-Role": "dev"})

        self.assertEqual([403], h.captured["statuses"])
        self.assertEqual([], called, "the protected action must never be reached")

    def test_anonymous_caller_is_refused_and_action_not_reached(self):
        """No credentials at all: refused, and nothing runs."""
        called = []
        with mock.patch.object(handlers, "k8s_rollout_all",
                               side_effect=lambda ns: (called.append(ns), (True, "ok"))[1]):
            h = self.post("/api/k8s/rollout_all", {"namespace": "prod"})

        self.assertEqual([403], h.captured["statuses"])
        self.assertEqual([], called, "an anonymous caller must not reach the rollout")

    def test_denial_produces_exactly_one_json_document(self):
        """A refusal emits one status line and one JSON body -- never two."""
        with mock.patch.object(handlers, "k8s_rollout_all", return_value=(True, "ok")):
            h = self.post("/api/k8s/rollout_all", {"namespace": "develop"},
                          headers={"X-Auth-Role": "dev"})

        docs = json_documents(h)
        self.assertEqual(1, len(docs), f"expected exactly 1 JSON document, got {docs!r}")
        self.assertTrue(docs[0]["requires_admin"])
        self.assertFalse(docs[0]["success"])
        self.assertEqual([403], h.captured["statuses"])

    def test_every_admin_path_emits_exactly_one_403_for_a_dev_caller(self):
        """The whole admin surface, not just one route."""
        for path in ("/api/config_git/push", "/api/environment/switch",
                     "/api/deployments/build", "/api/k8s/restart",
                     "/api/k8s/rollout_all", "/api/k8s/deploy",
                     "/api/k8s/restart_multiple", "/api/deployments/update_version"):
            with self.subTest(path=path):
                called = []
                side = lambda tag: (lambda *a, **k: called.append(tag))
                with mock.patch.object(handlers, "run_config_git_push", side_effect=side("push")), \
                     mock.patch.object(handlers, "switch_workspace_environment", side_effect=side("switch")), \
                     mock.patch.object(handlers, "k8s_rollout_all", side_effect=side("rollout_all")), \
                     mock.patch.object(handlers, "k8s_rollout_restart", side_effect=side("restart")), \
                     mock.patch.object(handlers, "k8s_deploy_service", side_effect=side("deploy")), \
                     mock.patch.object(handlers, "update_yaml_version", side_effect=side("yaml")):
                    h = self.post(path, {"services": []},
                                  headers={"X-Auth-Role": "dev"})
                self.assertEqual([403], h.captured["statuses"], path)
                self.assertEqual(1, len(json_documents(h)), path)
                self.assertEqual([], called, f"{path}: action must not run")

    # -- other guards ------------------------------------------------------- #

    def test_unknown_post_route_returns_404(self):
        h = self.post("/api/not-a-real-endpoint", {})
        self.assertEqual(404, h.captured["status"])

    def test_verify_pin_with_wrong_pin_is_401(self):
        h = self.post("/api/auth/verify_pin", {"pin": "definitely-wrong"})
        self.assertEqual(401, h.captured["status"])
        self.assertFalse(json_body(h)["success"])

    def test_root_dir_set_without_path_is_400(self):
        h = self.post("/api/root_dir/set", {})
        self.assertEqual(400, h.captured["status"])
        self.assertIn("Falta parámetro", json_body(h)["message"])
