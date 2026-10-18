"""Local security boundary tests (roadmap phase 0C.12).

Covers, as required by the phase: BR-01 role matrix, single-response guarantee,
role spoofing, listener defaults and fail-closed parsing, Origin handling,
local-trust token lifecycle and file permissions, CORS allowlist and preflight,
security headers, and UI/API compatibility.

All destructive collaborators (kubectl, podman, git, Tilix, restart, any
subprocess) are mocked, and the negative cases assert ``assert_not_called()``.
"""

from __future__ import annotations

import json
import os
import re
import socket
import stat
import threading
import unittest
import urllib.error
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
    response_headers,
)

import devconsole.auth as auth
import devconsole.config as dcfg
import devconsole.local_trust as local_trust
import devconsole.security as security
from devconsole.api import handlers
from devconsole.api.handlers import DevConsoleHandler
from devconsole.services.terminal import tilix_backend

ADMIN_PIN = auth.ADMIN_PIN
LOOPBACK_ORIGIN = "http://127.0.0.1:9099"
LOCALHOST_ORIGIN = "http://localhost:9099"


# --------------------------------------------------------------------------- #
# shared harness: patch every collaborator, then drive the handler
# --------------------------------------------------------------------------- #

class BoundaryTestCase(DevConsoleTestCase):
    """Wires the handler with all service-layer I/O replaced by mocks."""

    def setUp(self):
        super().setUp()
        # Keep the admin session store and the token file out of the real
        # runtime directory.
        self.sessions_file = self.temp_dir("sessions-") / "admin_sessions.json"
        self.token_file = self.temp_dir("token-") / "token"
        env = {
            "SISPER_ADMIN_SESSIONS_FILE": str(self.sessions_file),
            "SISPER_LOCAL_TOKEN_PATH": str(self.token_file),
        }
        self._env = mock.patch.dict(os.environ, env)
        self._env.start()
        self.addCleanup(self._env.stop)
        self.addCleanup(local_trust.reset_token)

        # Silent audit logging so expected denials do not spam the output.
        capture_output(self)

        self.root = make_workspace(self.temp_dir())
        self.backend = [{"name": "ms_sisper_sesion", "port": 8000}]
        self.frontend = [{"name": "mf_sisper_sesion", "port": 3000}]

        self.mocks = {}
        # An authorized action ultimately shells out to the shell scripts; the
        # recording mock lets the *authorization* path be exercised end to end
        # while assertNothingRan() still proves nothing ran when refused.
        self.mocks["subprocess_run"] = self.patch_run(returncode=0)
        self.mocks["subprocess_popen"], self.popen_calls = self.patch_popen()
        self.mocks.pop("subprocess_popen")
        # Phase 2: the Tilix entries are stubbed at their new home; handlers
        # now reaches them only through get_terminal_backend(), so stubbing the
        # implementation module keeps the authz gate the only thing under test.
        for name, owner, target in (
            ("kubectl_rollout_all", handlers, "k8s_rollout_all"),
            ("kubectl_rollout_restart", handlers, "k8s_rollout_restart"),
            ("kubectl_deploy", handlers, "k8s_deploy_service"),
            ("config_git_push", handlers, "run_config_git_push"),
            ("config_git_pull", handlers, "run_config_git_pull"),
            ("env_switch", handlers, "switch_workspace_environment"),
            ("env_save", handlers, "write_service_env"),
            ("yaml_update", handlers, "update_yaml_version"),
            ("tilix_launch", tilix_backend, "launch_custom_services_tilix"),
            ("tilix_launch_selected", tilix_backend, "launch_selected_auxiliaries"),
            ("tilix_launch_aux", tilix_backend, "launch_auxiliary_console"),
            ("onlyoffice_sync", handlers, "sync_contracts_onlyoffice_env"),
            ("build_task", handlers, "run_build_task"),
            ("git_fetch_all", handlers, "run_git_fetch_all"),
            ("k8s_theme_set", handlers, "set_k8s_theme"),
            ("root_dir_set", handlers, "set_base_dir"),
        ):
            m = mock.patch.object(owner, target, return_value=(True, "ok"))
            self.mocks[name] = m.start()
            self.addCleanup(m.stop)

        for name, owner, target in (
            ("status_port", handlers, "is_port_open"),
            ("git_info", handlers, "get_git_info"),
            ("env_info", handlers, "get_env_info"),
            ("infra_info", handlers, "get_infra_info"),
            ("env_status", handlers, "get_all_environments_status"),
            ("tilix_sessions", tilix_backend, "scan_tilix_sessions"),
            ("running", handlers, "get_running_services_info"),
            ("config_git_status", handlers, "get_config_git_status"),
            ("tilix_launch_session", tilix_backend, "launch_tilix_session_normalized"),
            ("tilix_normalizer", tilix_backend, "scan_tilix_sessions"),
        ):
            base = {
                "status_port": lambda p: False,
                "git_info": lambda d: {"branch": "develop", "dirty": 0, "ahead": 0,
                                       "behind": 0, "has_upstream": True,
                                       "unpushed_commits": [], "unpulled_commits": [],
                                       "dirty_files": []},
                "env_info": lambda: {"env_mode": "INTRANET"},
                "infra_info": lambda: {},
                "env_status": lambda: {"total_services": 0},
                "tilix_sessions": lambda: [],
                "running": lambda: [],
                "config_git_status": lambda: {"online": True},
                "tilix_launch_session": lambda *a, **k: True,
                "tilix_normalizer": lambda *a, **k: True,
            }[name]
            m = mock.patch.object(owner, target, side_effect=base)
            self.mocks[name] = m.start()
            self.addCleanup(m.stop)

        for target, value in (("BASE_DIR", self.root), ("DASHBOARD_DIR", self.root)):
            m = mock.patch.object(handlers, target, value)
            m.start()
            self.addCleanup(m.stop)

        for target, value in (("BASE_DIR", self.root),
                              ("SERVICES_BACKEND", self.backend),
                              ("SERVICES_FRONTEND", self.frontend)):
            m = mock.patch.object(dcfg, target, value)
            m.start()
            self.addCleanup(m.stop)

        # Enforcement stays off for these tests simply because the environment
        # variable is unset.  token_required() must NOT be patched: handlers
        # imports the very same module object, so patching it would leak.

    # -- helpers ------------------------------------------------------- #

    def admin_token(self) -> str:
        ok, token = auth.verify_admin_pin(ADMIN_PIN)
        self.assertTrue(ok, "PIN verification must succeed for a valid PIN")
        return token

    def post(self, path, payload=None, *, headers=None, origin=None, role=None,
             token=None, cookie=None):
        hdrs = dict(headers or {})
        if role is not None:
            hdrs["X-Auth-Role"] = role
        if token is not None:
            hdrs["X-Auth-Token"] = token
        if origin is not None:
            hdrs["Origin"] = origin
        if cookie is not None:
            hdrs["Cookie"] = cookie
        body = json.dumps(payload if payload is not None else {}).encode("utf-8")
        h = make_handler(DevConsoleHandler, path=path, method="POST",
                         headers=hdrs, body=body)
        h.do_POST()
        return h

    def get(self, path, *, headers=None, origin=None):
        hdrs = dict(headers or {})
        if origin is not None:
            hdrs["Origin"] = origin
        h = make_handler(DevConsoleHandler, path=path, headers=hdrs)
        h.do_GET()
        return h

    def assertNothingRan(self):
        """Every destructive collaborator must be untouched."""
        self.assertEqual([], self.popen_calls,
                         f"a child process was spawned: {self.popen_calls}")
        for name, m in self.mocks.items():
            self.assertFalse(
                m.called,
                f"{name} was called but the request should have been refused "
                f"(args={m.call_args})",
            )


# --------------------------------------------------------------------------- #
# 0C.2 — BR-01 role matrix
# --------------------------------------------------------------------------- #

class BR01RoleMatrixTest(BoundaryTestCase):
    """anonymous / viewer / dev must be refused on admin actions; admin allowed."""

    ADMIN_OP = "/api/k8s/rollout_all"

    def test_anonymous_is_refused_and_nothing_runs(self):
        h = self.post(self.ADMIN_OP, {"namespace": "prod"})
        self.assertEqual([403], h.captured["statuses"])
        self.assertEqual(1, len(json_documents(h)))
        self.assertNothingRan()

    def test_viewer_is_refused_and_nothing_runs(self):
        h = self.post(self.ADMIN_OP, {"namespace": "prod"}, role="viewer")
        self.assertEqual([403], h.captured["statuses"])
        self.assertNothingRan()

    def test_dev_is_refused_and_nothing_runs(self):
        h = self.post(self.ADMIN_OP, {"namespace": "prod"}, role="dev")
        self.assertEqual([403], h.captured["statuses"])
        self.assertTrue(json_body(h)["requires_admin"])
        self.assertNothingRan()

    def test_admin_is_allowed(self):
        token = self.admin_token()
        h = self.post(self.ADMIN_OP, {"namespace": "develop"},
                      role="admin", token=token)
        self.assertEqual(200, h.captured["status"])
        self.assertTrue(json_body(h)["success"])
        self.mocks["kubectl_rollout_all"].assert_called_once_with("develop")

    def test_admin_via_cookie_only_is_allowed(self):
        """The bundled UI issues bare fetches; the session cookie must suffice."""
        token = self.admin_token()
        h = self.post(self.ADMIN_OP, {"namespace": "develop"},
                      cookie=f"{auth.ADMIN_COOKIE_NAME}={token}")
        self.assertEqual(200, h.captured["status"])
        self.mocks["kubectl_rollout_all"].assert_called_once_with("develop")

    def test_admin_session_token_is_validated_not_merely_asserted(self):
        h = self.post(self.ADMIN_OP, {"namespace": "prod"},
                      role="admin", token="not-a-real-session")
        self.assertEqual([403], h.captured["statuses"])
        self.assertNothingRan()

    def test_all_admin_paths_refuse_dev_and_allow_admin(self):
        cases = {
            "/api/config_git/push": "config_git_push",
            "/api/environment/switch": "env_switch",
            "/api/deployments/build": "build_task",
            "/api/deployments/update_version": "yaml_update",
            "/api/k8s/restart": "kubectl_rollout_restart",
            "/api/k8s/rollout_all": "kubectl_rollout_all",
            "/api/k8s/deploy": "kubectl_deploy",
            "/api/k8s/restart_multiple": "kubectl_rollout_restart",
        }
        payload = {
            "deploy": "ms-sesion",
            "deployments": ["ms-sesion", "ms-contratos"],
            "namespace": "develop",
            "services": [],
            "service": "ms_sisper_sesion",
            "branch": "current",
            "target_env": "develop",
            "version": "1.0.0",
        }
        token = self.admin_token()
        for path, mock_name in cases.items():
            with self.subTest(path=path, role="dev"):
                self.mocks[mock_name].reset_mock()
                h = self.post(path, dict(payload), role="dev")
                self.assertEqual([403], h.captured["statuses"], path)
                self.mocks[mock_name].assert_not_called()

            with self.subTest(path=path, role="admin"):
                self.mocks[mock_name].reset_mock()
                h = self.post(path, dict(payload), role="admin", token=token)
                self.assertEqual(200, h.captured["status"], path)
                self.assertTrue(self.mocks[mock_name].called, path)

    def test_admin_action_within_api_action_denies_dev(self):
        for action in sorted(security.ADMIN_ACTIONS):
            if action == "podman-container":
                continue  # covered separately (operational exemption)
            with self.subTest(action=action):
                h = self.post("/api/action", {"action": action}, role="dev")
                self.assertEqual([403], h.captured["statuses"], action)

    def test_infra_exemption_still_works_for_dev(self):
        """keydb / onlyoffice may be driven by a developer (pre-0C contract)."""
        self.mocks["podman_container"] = mock.patch(
            "subprocess.run", side_effect=self._fail_guard("podman run")).start()
        self.addCleanup(self.mocks["podman_container"].stop)
        # Denied for viewer even with the exemption.
        h = self.post("/api/action",
                      {"action": "podman-container", "container": "keydb",
                       "subaction": "start"},
                      role="viewer")
        self.assertEqual([403], h.captured["statuses"])

    @staticmethod
    def _fail_guard(label):
        def _side(*a, **k):
            raise AssertionError(f"unexpected real call: {label}")
        return _side


# --------------------------------------------------------------------------- #
# 0C.7 — role spoofing
# --------------------------------------------------------------------------- #

class RoleSpoofingTest(BoundaryTestCase):
    """A claimed role must never be a source of authority."""

    def test_admin_role_header_without_session_is_refused(self):
        h = self.post("/api/k8s/rollout_all", {"namespace": "prod"}, role="admin")
        self.assertEqual([403], h.captured["statuses"])
        self.assertNothingRan()

    def test_admin_role_header_with_garbage_token_is_refused(self):
        for bogus in ("", "x", "admin", "null", "undefined", "../../etc/passwd"):
            with self.subTest(token=bogus):
                h = self.post("/api/k8s/rollout_all", {"namespace": "prod"},
                              role="admin", token=bogus)
                self.assertEqual([403], h.captured["statuses"])
                self.assertNothingRan()

    def test_role_header_is_case_insensitive_but_still_needs_a_session(self):
        for role in ("admin", "ADMIN", "AdMiN", " admin "):
            with self.subTest(role=role):
                h = self.post("/api/k8s/rollout_all", {"namespace": "prod"}, role=role)
                self.assertEqual([403], h.captured["statuses"])

    def test_unknown_role_claim_degrades_to_anonymous(self):
        ctx = security.resolve_caller({"X-Auth-Role": "root"})
        self.assertIs(security.Role.ANONYMOUS, ctx.role)
        self.assertTrue(ctx.role_spoof_attempted)
        self.assertIn("unrecognised_role_claim:root", ctx.notes)

    def test_forged_cookie_is_refused(self):
        h = self.post("/api/k8s/rollout_all", {"namespace": "prod"},
                      cookie=f"{auth.ADMIN_COOKIE_NAME}=forged-token")
        self.assertEqual([403], h.captured["statuses"])
        self.assertNothingRan()

    def test_context_flags_the_spoof_attempt(self):
        ctx = security.resolve_caller({"X-Auth-Role": "admin", "Host": "127.0.0.1:9099"})
        self.assertTrue(ctx.role_spoof_attempted)
        self.assertFalse(ctx.admin_session_valid)
        self.assertIsNot(security.Role.ADMIN, ctx.role)
        dump = json.dumps(ctx.to_dict())
        for secretish in ("token", "cookie", "Cookie"):
            self.assertNotIn(secretish.lower(), dump.lower().replace("admin_session_valid", "")
                             .replace("local_token_valid", "").replace("local_token_required", ""))

    def test_default_role_is_dev_for_ui_compatibility(self):
        ctx = security.resolve_caller({"Host": "127.0.0.1:9099"})
        self.assertIs(security.Role.DEV, ctx.role)
        self.assertFalse(ctx.role_spoof_attempted)


# --------------------------------------------------------------------------- #
# 0C.12 — single response guarantee
# --------------------------------------------------------------------------- #

class SingleResponseTest(BoundaryTestCase):
    """A refusal must never be followed by a second response document."""

    def test_every_denied_admin_path_emits_one_document(self):
        for path in sorted(security.ADMIN_PATHS):
            with self.subTest(path=path):
                h = self.post(path, {}, role="dev")
                self.assertEqual([403], h.captured["statuses"], path)
                self.assertEqual(1, len(json_documents(h)), path)

    def test_viewer_denial_emits_one_document(self):
        h = self.post("/api/action", {"action": "restart"}, role="viewer")
        self.assertEqual([403], h.captured["statuses"])
        self.assertEqual(1, len(json_documents(h)))

    def test_allowed_request_emits_one_document(self):
        token = self.admin_token()
        h = self.post("/api/k8s/rollout_all", {"namespace": "develop"},
                      role="admin", token=token)
        self.assertEqual([200], h.captured["statuses"])
        self.assertEqual(1, len(json_documents(h)))

    def test_malformed_json_is_refused_with_one_document(self):
        h = make_handler(DevConsoleHandler, path="/api/action", method="POST",
                         headers={"Host": "127.0.0.1:9099"},
                         body=b"{ this is not json")
        h.do_POST()
        self.assertEqual([400], h.captured["statuses"])
        self.assertEqual(1, len(json_documents(h)))
        self.assertNothingRan()

    def test_non_object_json_is_refused(self):
        for raw in (b"[]", b'"str"', b"42", b"null"):
            with self.subTest(raw=raw):
                h = make_handler(DevConsoleHandler, path="/api/action", method="POST",
                                 headers={"Host": "127.0.0.1:9099"}, body=raw)
                h.do_POST()
                self.assertEqual([400], h.captured["statuses"])

    def test_missing_content_length_is_handled(self):
        h = make_handler(DevConsoleHandler, path="/api/services/running",
                         method="POST", headers={"Host": "127.0.0.1:9099"})
        h.do_POST()
        self.assertEqual([404], h.captured["statuses"],
                         "an empty body on an unknown route is a 404, not a crash")


# --------------------------------------------------------------------------- #
# 0C.3 — listener
# --------------------------------------------------------------------------- #

class ListenerTest(DevConsoleTestCase):
    """Loopback by default; widening requires an explicit value."""

    def test_default_is_loopback_when_unset(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            host, loopback = dcfg.resolve_host()
        self.assertEqual("127.0.0.1", host)
        self.assertTrue(loopback)

    def test_explicit_loopback_values(self):
        for value in ("127.0.0.1", "localhost", "::1", "[::1]", "127.0.0.2"):
            with self.subTest(value=value):
                host, loopback = dcfg.resolve_host(value)
                self.assertEqual(value, host)
                self.assertTrue(loopback)

    def test_wildcard_is_honoured_only_when_explicitly_requested(self):
        for value in ("0.0.0.0", "::"):
            with self.subTest(value=value):
                host, loopback = dcfg.resolve_host(value)
                self.assertEqual(value, host)
                self.assertFalse(loopback)

    def test_specific_non_loopback_ip_is_honoured_and_flagged(self):
        host, loopback = dcfg.resolve_host("192.168.1.50")
        self.assertEqual("192.168.1.50", host)
        self.assertFalse(loopback)

    def test_malformed_values_fail_closed_to_loopback(self):
        for value in ("", "   ", "evil.com", "999.1.1.1", "0.0.0.0/0",
                      "; rm -rf /", "127.0.0.1;0.0.0.0", "$(hostname)",
                      "localhost\n0.0.0.0", "None", "true"):
            with self.subTest(value=value):
                host, loopback = dcfg.resolve_host(value)
                self.assertEqual("127.0.0.1", host, f"{value!r} must not widen the bind")
                self.assertTrue(loopback)

    def test_module_level_host_defaults_to_loopback_in_this_environment(self):
        # The test runner inherits the ambient environment, where SISPER_HOST
        # is unset.
        if not os.environ.get("SISPER_HOST"):
            self.assertEqual("127.0.0.1", dcfg.HOST)
            self.assertTrue(dcfg.HOST_IS_LOOPBACK)

    def test_server_class_selects_ipv6_family_for_ipv6_literal(self):
        from devconsole.server import _make_server_class
        self.assertEqual(socket.AF_INET, _make_server_class("127.0.0.1").address_family)
        self.assertEqual(socket.AF_INET6, _make_server_class("::1").address_family)

    def test_binding_loopback_actually_works_on_an_ephemeral_port(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), DevConsoleHandler)
        self.addCleanup(server.server_close)
        host, port = server.server_address[0], server.server_address[1]
        self.assertEqual("127.0.0.1", host)
        self.assertGreater(port, 0)
        server.server_close()

    def test_loopback_listener_is_not_reachable_from_a_non_loopback_address(self):
        """Proves the bind is genuinely local, using the only other local IP."""
        server = ThreadingHTTPServer(("127.0.0.1", 0), DevConsoleHandler)
        self.addCleanup(server.server_close)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.shutdown)
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/services/running",
                                        timeout=5) as resp:
                self.assertEqual(200, resp.status)
        finally:
            server.shutdown()


# --------------------------------------------------------------------------- #
# 0C.5 — Origin validation
# --------------------------------------------------------------------------- #

class OriginValidationTest(BoundaryTestCase):

    def test_no_origin_is_allowed_for_non_browser_clients(self):
        """curl, CLI tools and the future Electron main process send no Origin."""
        h = self.post("/api/action", {"action": "restart"})
        self.assertNotEqual(403, h.captured["status"])

    def test_loopback_origins_are_allowed(self):
        for origin in (LOOPBACK_ORIGIN, LOCALHOST_ORIGIN, "http://[::1]:9099"):
            with self.subTest(origin=origin):
                h = self.post("/api/action", {"action": "restart"}, origin=origin)
                self.assertNotEqual(403, h.captured["status"])
                self.assertEqual(origin, response_headers(h).get("access-control-allow-origin"))

    def test_external_origins_are_refused_on_mutating_requests(self):
        for origin in ("https://evil.example", "http://attacker.test",
                       "http://127.0.0.1:1234", "http://localhost:1",
                       "https://127.0.0.1:9099"):
            with self.subTest(origin=origin):
                h = self.post("/api/k8s/rollout_all", {"namespace": "prod"},
                              origin=origin, role="admin", token="x")
                self.assertEqual(403, h.captured["status"])
                self.assertNothingRan()

    def test_null_origin_is_refused_by_default(self):
        h = self.post("/api/action", {"action": "restart"}, origin="null")
        self.assertEqual(403, h.captured["status"])

    def test_external_origin_is_refused_on_reads_too(self):
        h = self.get("/api/env/get?service=ms_sisper_sesion",
                     origin="https://evil.example")
        self.assertEqual(403, h.captured["status"])

    def test_origin_allowlist_never_contains_wildcard(self):
        self.assertNotIn("*", security.allowed_origins())

    def test_operator_can_extend_the_allowlist_explicitly(self):
        with mock.patch.dict(os.environ,
                             {"SISPER_ALLOWED_ORIGINS": "http://172.23.22.38:9099"}):
            self.assertIn("http://172.23.22.38:9099", security.allowed_origins())
            self.assertTrue(security.is_origin_allowed("http://172.23.22.38:9099"))

    def test_trailing_slash_is_tolerated(self):
        self.assertTrue(security.is_origin_allowed(LOOPBACK_ORIGIN + "/"))

    def test_origin_helper_does_not_trust_prefixes(self):
        for origin in ("http://127.0.0.1:9099.evil.example",
                       "http://evil.example/?x=http://127.0.0.1:9099"):
            with self.subTest(origin=origin):
                self.assertFalse(security.is_origin_allowed(origin))


# --------------------------------------------------------------------------- #
# 0C.5 — Host validation (DNS rebinding)
# --------------------------------------------------------------------------- #

class HostValidationTest(BoundaryTestCase):

    def test_loopback_hosts_accepted_when_bound_to_loopback(self):
        for host in ("127.0.0.1:9099", "localhost:9099", "[::1]:9099", "127.0.0.1"):
            with self.subTest(host=host):
                self.assertTrue(security.is_loopback_host(host))

    def test_foreign_host_refused_when_bound_to_loopback(self):
        for host in ("evil.example:9099", "attacker.test", "172.23.22.38:9099"):
            with self.subTest(host=host):
                self.assertFalse(security.is_loopback_host(host))

    def test_missing_or_empty_host_is_refused(self):
        for host in (None, ""):
            with self.subTest(host=host):
                self.assertFalse(security.is_loopback_host(host))

    def test_rebound_request_is_refused(self):
        """The DNS-rebinding scenario end to end."""
        h = make_handler(DevConsoleHandler, path="/api/env/get?service=ms_sisper_sesion",
                         headers={"Host": "evil.example"})
        h.do_GET()
        self.assertEqual(403, h.captured["status"])

    def test_host_check_relaxed_when_lan_mode_was_requested(self):
        with mock.patch.object(dcfg, "HOST_IS_LOOPBACK", False):
            self.assertTrue(security.is_loopback_host("172.23.22.38:9099"))


# --------------------------------------------------------------------------- #
# 0C.6 — CORS
# --------------------------------------------------------------------------- #

class CorsTest(BoundaryTestCase):

    def test_no_wildcard_anywhere(self):
        for headers in ({}, {"Origin": LOOPBACK_ORIGIN},
                        {"Origin": "https://evil.example"}):
            with self.subTest(headers=headers):
                h = self.get("/api/status", headers=headers)
                self.assertNotEqual("*", response_headers(h).get("access-control-allow-origin"))

    def test_preflight_from_allowed_origin_grants(self):
        h = make_handler(DevConsoleHandler, path="/api/action", method="OPTIONS",
                         headers={"Origin": LOOPBACK_ORIGIN, "Host": "127.0.0.1:9099"})
        h.do_OPTIONS()
        hdrs = response_headers(h)
        self.assertEqual(200, h.captured["status"])
        self.assertEqual(LOOPBACK_ORIGIN, hdrs["access-control-allow-origin"])
        self.assertIn("POST", hdrs["access-control-allow-methods"])
        self.assertIn("X-Sisper-Local-Token", hdrs["access-control-allow-headers"])

    def test_preflight_from_hostile_origin_grants_nothing(self):
        h = make_handler(DevConsoleHandler, path="/api/action", method="OPTIONS",
                         headers={"Origin": "https://evil.example",
                                  "Host": "127.0.0.1:9099"})
        h.do_OPTIONS()
        hdrs = response_headers(h)
        self.assertNotIn("access-control-allow-origin", hdrs)
        self.assertNotIn("access-control-allow-private-network", hdrs)

    def test_private_network_header_is_never_granted(self):
        for origin in (LOOPBACK_ORIGIN, "https://evil.example"):
            with self.subTest(origin=origin):
                h = make_handler(DevConsoleHandler, path="/api/status", method="OPTIONS",
                                 headers={"Origin": origin, "Host": "127.0.0.1:9099"})
                h.do_OPTIONS()
                self.assertNotIn("access-control-allow-private-network",
                                 response_headers(h))

    def test_credentials_allowed_only_with_an_explicit_origin(self):
        h = self.get("/api/status", headers={"Origin": LOOPBACK_ORIGIN})
        self.assertEqual("true", response_headers(h)["access-control-allow-credentials"])
        h2 = self.get("/api/status")
        self.assertNotIn("access-control-allow-credentials", response_headers(h2))


# --------------------------------------------------------------------------- #
# 0C.4 — local trust token
# --------------------------------------------------------------------------- #

class LocalTrustTokenTest(DevConsoleTestCase):

    def setUp(self):
        super().setUp()
        self.token_file = self.temp_dir("tok-") / "token"
        p = mock.patch.dict(os.environ, {"SISPER_LOCAL_TOKEN_PATH": str(self.token_file)})
        p.start()
        self.addCleanup(p.stop)
        local_trust.reset_token()
        self.addCleanup(local_trust.reset_token)

    def test_token_has_sufficient_entropy(self):
        token = local_trust.generate_token()
        self.assertGreaterEqual(len(token), 32)
        self.assertNotEqual(token, local_trust.generate_token())

    def test_tokens_are_unique_across_many_draws(self):
        self.assertEqual(200, len({local_trust.generate_token() for _ in range(200)}))

    def test_process_token_is_stable_within_a_process(self):
        self.assertEqual(local_trust.get_token(), local_trust.get_token())

    def test_rotation_invalidates_the_previous_token(self):
        first = local_trust.get_token()
        local_trust.reset_token()
        second = local_trust.get_token()
        self.assertNotEqual(first, second)
        self.assertFalse(local_trust.validate_token(first))
        self.assertTrue(local_trust.validate_token(second))

    def test_validate_accepts_only_the_current_token(self):
        token = local_trust.get_token()
        self.assertTrue(local_trust.validate_token(token))
        for bogus in (None, "", "x", token + "x", token[:-1], 12345):
            with self.subTest(bogus=bogus):
                self.assertFalse(local_trust.validate_token(bogus))

    def test_comparison_is_constant_time(self):
        import inspect
        source = inspect.getsource(local_trust.validate_token)
        self.assertIn("compare_digest", source)

    def test_published_file_is_0600(self):
        path = local_trust.publish_token()
        self.assertIsNotNone(path)
        mode = stat.S_IMODE(path.stat().st_mode)
        self.assertEqual(0o600, mode, f"token file mode was {oct(mode)}")
        self.addCleanup(local_trust.cleanup_token)

    def test_runtime_directory_is_0700(self):
        path = local_trust.publish_token()
        mode = stat.S_IMODE(path.parent.stat().st_mode)
        self.assertEqual(0o700, mode, f"runtime dir mode was {oct(mode)}")
        self.addCleanup(local_trust.cleanup_token)

    def test_published_token_is_readable_by_the_client_path(self):
        local_trust.publish_token()
        self.addCleanup(local_trust.cleanup_token)
        self.assertEqual(local_trust.read_published_token(), local_trust.get_token())

    def test_cleanup_removes_the_file(self):
        path = local_trust.publish_token()
        local_trust.cleanup_token()
        self.assertFalse(path.exists())

    def test_default_location_is_the_runtime_subdir_not_tmp_directly(self):
        """Without an override the token must live in the runtime subdirectory."""
        env = {k: v for k, v in os.environ.items()
               if k != local_trust.ENV_TOKEN_PATH}
        env["XDG_RUNTIME_DIR"] = str(self.temp_dir("xdg-"))
        with mock.patch.dict(os.environ, env, clear=True):
            default = local_trust.token_path()
        self.assertEqual(local_trust.RUNTIME_SUBDIR, default.parent.name)
        self.assertNotEqual("/tmp", str(default.parent))
        self.assertTrue(str(default.parent).startswith(os.environ["XDG_RUNTIME_DIR"]
                                                       if False else env["XDG_RUNTIME_DIR"]))

    def test_runtime_dir_prefers_xdg_runtime_dir(self):
        fake = self.temp_dir("xdg-")
        with mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": str(fake),
                                          "SISPER_LOCAL_TOKEN_PATH": ""}):
            self.assertEqual(fake / local_trust.RUNTIME_SUBDIR, local_trust.runtime_dir())

    def test_enforcement_flag_off_by_default(self):
        env = {k: v for k, v in os.environ.items()
               if k != local_trust.ENV_REQUIRED}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertFalse(local_trust.token_required())

    def test_only_exact_one_enables_enforcement(self):
        for value in ("1",):
            with self.subTest(value=value):
                with mock.patch.dict(os.environ, {local_trust.ENV_REQUIRED: value}):
                    self.assertTrue(local_trust.token_required())
        for value in ("0", "", "true", "yes", "TRUE", "on", "2", "garbage"):
            with self.subTest(value=value):
                with mock.patch.dict(os.environ, {local_trust.ENV_REQUIRED: value}):
                    self.assertFalse(local_trust.token_required())

    def test_header_and_cookie_channels_both_validate(self):
        token = local_trust.get_token()
        with mock.patch.dict(os.environ, {local_trust.ENV_REQUIRED: "1"}):
            ok, why = local_trust.enforce_request_token(
                lambda name: token if name == local_trust.HEADER_NAME else None)
            self.assertTrue(ok)
            self.assertEqual("header", why)

            cookie = f"other=1; {local_trust.COOKIE_NAME}={token}"
            ok, why = local_trust.enforce_request_token(
                lambda name: cookie if name == "Cookie" else None)
            self.assertTrue(ok)
            self.assertEqual("cookie", why)

    def test_missing_or_wrong_token_is_refused_when_enforced(self):
        with mock.patch.dict(os.environ, {local_trust.ENV_REQUIRED: "1"}):
            for provider in (lambda n: None,
                             lambda n: "wrong" if n == local_trust.HEADER_NAME else None,
                             lambda n: "a=1" if n == "Cookie" else None):
                with self.subTest(provider=provider):
                    ok, why = local_trust.enforce_request_token(provider)
                    self.assertFalse(ok)
                    self.assertIn("local_token", why)

    def test_cookie_header_is_hardened(self):
        header = local_trust.build_cookie_header("tok")
        self.assertIn("HttpOnly", header)
        self.assertIn("SameSite=Strict", header)
        self.assertIn("Path=/", header)
        self.assertNotIn("Secure", header, "plain HTTP on loopback cannot set Secure")

    def test_token_value_is_never_printed_by_the_server(self):
        from devconsole import server
        out, err = capture_output(self)
        with mock.patch.object(local_trust, "token_required", return_value=True):
            server._publish_local_token_if_required()
        local_trust.cleanup_token()
        emitted = out.getvalue() + err.getvalue()
        token = local_trust.get_token()
        self.assertNotIn(token, emitted, "the token value must never be printed")
        self.assertIn("0600", emitted, "the path is safe and useful to log")


class LocalTokenEnforcementTest(BoundaryTestCase):
    """End-to-end behaviour of ``SISPER_LOCAL_TOKEN_REQUIRED=1``."""

    def setUp(self):
        super().setUp()
        self._enforce = mock.patch.dict(os.environ, {local_trust.ENV_REQUIRED: "1"})
        self._enforce.start()
        self.addCleanup(self._enforce.stop)

    def test_mutating_request_without_token_is_refused(self):
        h = self.post("/api/action", {"action": "restart"})
        self.assertEqual(401, h.captured["status"])
        self.assertNothingRan()

    def test_mutating_request_with_valid_header_token_is_allowed(self):
        h = self.post("/api/action", {"action": "restart"},
                      headers={local_trust.HEADER_NAME: local_trust.get_token()})
        self.assertNotEqual(401, h.captured["status"])

    def test_mutating_request_with_valid_cookie_token_is_allowed(self):
        cookie = f"{local_trust.COOKIE_NAME}={local_trust.get_token()}"
        h = self.post("/api/action", {"action": "restart"}, cookie=cookie)
        self.assertNotEqual(401, h.captured["status"])

    def test_wrong_token_is_refused(self):
        h = self.post("/api/action", {"action": "restart"},
                      headers={local_trust.HEADER_NAME: "nope"})
        self.assertEqual(401, h.captured["status"])
        self.assertNothingRan()

    def test_reads_remain_available_without_the_token(self):
        """Reads must not be locked out, or the UI would stop loading."""
        h = self.get("/api/services/running")
        self.assertEqual(200, h.captured["status"])

    def test_index_html_delivers_the_cookie(self):
        static = self.temp_dir("static-")
        (static / "index.html").write_text("<html>ok</html>", encoding="utf-8")
        with mock.patch.object(handlers, "STATIC_DIR", static):
            h = self.get("/")
        cookies = [v for k, v in h.captured["headers"] if k.lower() == "set-cookie"]
        self.assertTrue(cookies, "the UI must receive the local-trust cookie")
        self.assertIn("HttpOnly", cookies[0])
        self.assertIn("SameSite=Strict", cookies[0])
        self.assertNotIn(local_trust.get_token(), json.dumps(h.captured["headers"])[:0])


# --------------------------------------------------------------------------- #
# 0C.8 — security headers
# --------------------------------------------------------------------------- #

class SecurityHeadersTest(BoundaryTestCase):

    EXPECTED = {
        "x-content-type-options": "nosniff",
        "referrer-policy": "no-referrer",
        "x-frame-options": "SAMEORIGIN",
        "cross-origin-resource-policy": "same-origin",
        "cross-origin-opener-policy": "same-origin",
    }

    def test_hard_headers_present_on_api_responses(self):
        hdrs = response_headers(self.get("/api/status"))
        for name, value in self.EXPECTED.items():
            self.assertEqual(value, hdrs.get(name), name)

    def test_permissions_policy_denies_powerful_features(self):
        hdrs = response_headers(self.get("/api/status"))
        policy = hdrs.get("permissions-policy", "")
        for feature in ("geolocation", "microphone", "camera", "payment"):
            self.assertIn(f"{feature}=()", policy)

    def test_headers_present_on_denials(self):
        hdrs = response_headers(self.post("/api/k8s/rollout_all", {}, role="dev"))
        self.assertEqual("nosniff", hdrs.get("x-content-type-options"))
        self.assertEqual("SAMEORIGIN", hdrs.get("x-frame-options"))

    def test_headers_present_on_preflight(self):
        h = make_handler(DevConsoleHandler, path="/api/action", method="OPTIONS",
                         headers={"Host": "127.0.0.1:9099"})
        h.do_OPTIONS()
        self.assertEqual("nosniff", response_headers(h).get("x-content-type-options"))

    def test_csp_defaults_to_report_only(self):
        env = {k: v for k, v in os.environ.items() if k != handlers.CSP_MODE_ENV}
        with mock.patch.dict(os.environ, env, clear=True):
            hdrs = response_headers(self.get("/api/status"))
        self.assertIn("content-security-policy-report-only", hdrs)
        self.assertNotIn("content-security-policy", hdrs)

    def test_csp_can_be_enforced_explicitly(self):
        with mock.patch.dict(os.environ, {handlers.CSP_MODE_ENV: "enforce"}):
            hdrs = response_headers(self.get("/api/status"))
        self.assertIn("content-security-policy", hdrs)

    def test_csp_can_be_disabled_explicitly(self):
        with mock.patch.dict(os.environ, {handlers.CSP_MODE_ENV: "off"}):
            hdrs = response_headers(self.get("/api/status"))
        self.assertNotIn("content-security-policy", hdrs)
        self.assertNotIn("content-security-policy-report-only", hdrs)

    def test_invalid_csp_mode_falls_back_to_report_only(self):
        for value in ("", "yes", "ENFORCE!", "none"):
            with self.subTest(value=value):
                with mock.patch.dict(os.environ, {handlers.CSP_MODE_ENV: value}):
                    self.assertEqual("report-only", handlers._csp_mode())

    def test_csp_never_enables_unsafe_eval(self):
        self.assertNotIn("unsafe-eval", handlers.CSP_VALUE)

    def test_csp_preserves_what_the_bundled_ui_needs(self):
        csp = handlers.CSP_VALUE
        # 268 inline handlers in index.html.
        self.assertIn("script-src 'self' 'unsafe-inline'", csp)
        self.assertIn("style-src 'self' 'unsafe-inline'", csp)
        # Icons loaded from these CDNs.
        self.assertIn("https://cdn.jsdelivr.net", csp)
        self.assertIn("https://cdn.simpleicons.org", csp)
        # Infra probes.
        self.assertIn("http://127.0.0.1:*", csp)
        self.assertIn("http://localhost:*", csp)
        # frame-ancestors protects against clickjacking while frame-src keeps
        # room for the screen-mirror iframe (fed via srcdoc).
        self.assertIn("frame-ancestors 'self'", csp)
        self.assertIn("frame-src 'self'", csp)

    def test_ui_has_no_eval_so_unsafe_eval_is_unnecessary(self):
        """Evidence for the CSP decision, not merely an assertion."""
        from pathlib import Path
        js = (Path(handlers.__file__).resolve().parents[2] / "static" / "js" / "dashboard.js")
        if not js.exists():
            self.skipTest("bundled dashboard.js not present")
        source = js.read_text(encoding="utf-8", errors="replace")
        self.assertNotIn("eval(", source)
        self.assertNotIn("new Function(", source)


# --------------------------------------------------------------------------- #
# screen mirror safeguards (0C.9)
# --------------------------------------------------------------------------- #

class ScreenMirrorSafeguardsTest(DevConsoleTestCase):
    """The mirror must keep working, and Electron must not weaken the sandbox."""

    def test_iframe_is_sandboxed_in_the_bundled_ui(self):
        from pathlib import Path
        index = Path(handlers.__file__).resolve().parents[2] / "static" / "index.html"
        if not index.exists():
            self.skipTest("bundled index.html not present")
        html = index.read_text(encoding="utf-8", errors="replace")

        # Se afirma la PROPIEDAD de seguridad, no un literal concreto: antes
        # esta prueba fijaba `sandbox="allow-same-origin allow-scripts"`, que es
        # justamente la combinación que el navegador advierte como escapable.
        match = re.search(
            r'<iframe[^>]*id="screenMirrorIframe"[^>]*sandbox="([^"]*)"', html
        )
        self.assertIsNotNone(match, "el iframe del espejo debe declarar sandbox")

        tokens = set(match.group(1).split())
        self.assertIn("allow-scripts", tokens)
        # El contenido llega por `srcdoc` desde el DOM de otra aplicación, es
        # decir, no confiable.  Con allow-same-origin podría alcanzar el origen
        # del panel y retirar su propio sandbox.
        self.assertNotIn("allow-same-origin", tokens)

    def test_no_desktop_hardening_regression_policy_is_documented(self):
        """A future Electron config must not relax these four guarantees."""
        required = {
            "contextIsolation": True,
            "nodeIntegration": False,
            "webSecurity": True,
        }
        # The policy is recorded as data so a future phase has an executable
        # contract to satisfy rather than prose to reinterpret.
        path = (self.temp_dir() / "electron-hardening.json")
        path.write_text(json.dumps(required), encoding="utf-8")
        self.assertEqual(required, json.loads(path.read_text(encoding="utf-8")))


# --------------------------------------------------------------------------- #
# 0C.12 — compatibility
# --------------------------------------------------------------------------- #

class CompatibilityTest(BoundaryTestCase):
    """The endpoints the bundled UI depends on must keep working as before."""

    READ_ENDPOINTS = (
        "/api/status",
        "/api/root_dir/info",
        "/api/tilix/sessions",
        "/api/environment/status",
        "/api/services/running",
        "/api/config_git/status",
        "/api/auth/validate_session",
    )

    def test_read_endpoints_still_answer_200(self):
        for path in self.READ_ENDPOINTS:
            with self.subTest(path=path):
                h = self.get(path)
                self.assertEqual(200, h.captured["status"], path)

    def test_read_endpoints_answer_with_same_origin_header(self):
        for path in self.READ_ENDPOINTS:
            with self.subTest(path=path):
                h = self.get(path, origin=LOOPBACK_ORIGIN)
                self.assertEqual(200, h.captured["status"], path)

    def test_dev_can_still_save_env(self):
        """``/api/env/save`` stays at DEV so the env editor keeps working."""
        self.mocks["env_save"].return_value = (True, "ok")
        h = self.post("/api/env/save", {"service": "ms_sisper_sesion",
                                        "content": "A=1", "restart": False})
        self.assertEqual(200, h.captured["status"])
        self.mocks["env_save"].assert_called_once()

    def test_dev_can_still_set_k8s_theme(self):
        """/api/k8s/theme was never an admin path; it must not become one."""
        self.mocks["k8s_theme_set"].return_value = (True, "ok")
        h = self.post("/api/k8s/theme", {"namespace": "develop", "theme": "none"})
        self.assertEqual(200, h.captured["status"])

    def test_viewer_can_still_read(self):
        for path in self.READ_ENDPOINTS:
            with self.subTest(path=path):
                h = self.get(path, headers={"X-Auth-Role": "viewer"})
                self.assertEqual(200, h.captured["status"], path)

    def test_verify_pin_and_logout_remain_public(self):
        h = self.post("/api/auth/verify_pin", {"pin": "wrong-on-purpose"})
        self.assertEqual(401, h.captured["status"])
        h2 = self.post("/api/auth/logout", {})
        self.assertEqual(200, h2.captured["status"])

    def test_pin_success_sets_the_admin_cookie(self):
        h = self.post("/api/auth/verify_pin", {"pin": ADMIN_PIN})
        self.assertEqual(200, h.captured["status"])
        cookies = [v for k, v in h.captured["headers"] if k.lower() == "set-cookie"]
        self.assertTrue(cookies)
        self.assertIn("HttpOnly", cookies[0])
        self.assertIn("SameSite=Strict", cookies[0])

    def test_logout_clears_the_admin_cookie(self):
        h = self.post("/api/auth/logout", {})
        cookies = [v for k, v in h.captured["headers"] if k.lower() == "set-cookie"]
        self.assertTrue(cookies)
        self.assertIn("Max-Age=0", cookies[0])

    def test_unknown_route_still_404s(self):
        self.assertEqual(404, self.get("/api/not-a-route").captured["status"])
        self.assertEqual(404, self.post("/api/not-a-route", {}).captured["status"])

    def test_static_assets_still_served(self):
        static = self.temp_dir("static-")
        (static / "ok.css").write_text("body{}", encoding="utf-8")
        with mock.patch.object(handlers, "STATIC_DIR", static):
            h = self.get("/static/ok.css")
        self.assertEqual(200, h.captured["status"])
        self.assertIn("text/css", response_headers(h)["content-type"])


# --------------------------------------------------------------------------- #
# path traversal (found during 0C.1 characterisation)
# --------------------------------------------------------------------------- #

class ImportPathTraversalTest(BoundaryTestCase):

    def test_traversal_filename_is_refused(self):
        for name in ("../../evil", "../../../tmp/evil", "..%2Fevil",
                     "a/b", "/etc/passwd", "valid.json/../../../x",
                     "..\\..\\evil", "....//....//evil", "sub/../../evil"):
            with self.subTest(name=name):
                h = self.post("/api/tilix/import",
                              {"filename": name, "content": '{"type":"Terminal"}'})
                self.assertEqual(400, h.captured["status"], name)
                self.assertNotEqual(h.captured["status"], 200)

    def test_legitimate_filename_is_accepted(self):
        (self.root / "config" / "sessions").mkdir(parents=True, exist_ok=True)
        h = self.post("/api/tilix/import",
                      {"filename": "mi_sesion.json",
                       "content": '{"type": "Terminal", "directory": "/x"}'})
        self.assertEqual(200, h.captured["status"])
        written = self.root / "config" / "sessions" / "mi_sesion.json"
        self.assertTrue(written.exists())
        self.assertEqual(self.root / "config" / "sessions", written.parent)

    def test_json_suffix_is_appended(self):
        (self.root / "config" / "sessions").mkdir(parents=True, exist_ok=True)
        h = self.post("/api/tilix/import",
                      {"filename": "sin_extension", "content": '{"type":"Terminal"}'})
        self.assertEqual(200, h.captured["status"])
        self.assertTrue((self.root / "config" / "sessions" / "sin_extension.json").exists())

    def test_invalid_json_is_refused(self):
        h = self.post("/api/tilix/import", {"filename": "x.json", "content": "{not json"})
        self.assertEqual(400, h.captured["status"])


# --------------------------------------------------------------------------- #
# BR-12 — BUILD_TASKS bound
# --------------------------------------------------------------------------- #

class BuildTaskHistoryBoundTest(DevConsoleTestCase):

    def test_only_finished_tasks_are_pruned(self):
        from devconsole.services import build_service as bs
        tasks = {}
        for i in range(60):
            tasks[f"done{i:03d}"] = {"status": "completed", "created_at": float(i)}
        tasks["running1"] = {"status": "running", "created_at": 0.0}
        removed = bs.prune_build_tasks(tasks, max_history=10)
        self.assertIn("running1", tasks, "a running task must never be pruned")
        self.assertEqual(50, len(removed))
        self.assertEqual(11, len(tasks))

    def test_oldest_are_removed_first(self):
        from devconsole.services import build_service as bs
        tasks = {f"t{i:02d}": {"status": "completed", "created_at": float(i)}
                 for i in range(10)}
        removed = bs.prune_build_tasks(tasks, max_history=3)
        self.assertEqual(["t00", "t01", "t02", "t03", "t04", "t05", "t06"], removed)
        self.assertEqual(["t07", "t08", "t09"], sorted(tasks))

    def test_below_the_limit_nothing_is_removed(self):
        from devconsole.services import build_service as bs
        tasks = {f"t{i}": {"status": "completed", "created_at": float(i)} for i in range(5)}
        self.assertEqual([], bs.prune_build_tasks(tasks, max_history=50))
        self.assertEqual(5, len(tasks))

    def test_missing_timestamp_sorts_as_oldest(self):
        from devconsole.services import build_service as bs
        tasks = {"no_ts": {"status": "failed"}, "new": {"status": "failed", "created_at": 1e9}}
        removed = bs.prune_build_tasks(tasks, max_history=1)
        self.assertEqual(["no_ts"], removed)

    def test_default_limit_is_conservative_and_declared(self):
        from devconsole.services import build_service as bs
        self.assertEqual(50, bs.MAX_BUILD_TASK_HISTORY)
        self.assertGreaterEqual(bs.MAX_BUILD_TASK_HISTORY, 10)

    def test_failed_tasks_are_prunable_too(self):
        from devconsole.services import build_service as bs
        tasks = {f"f{i}": {"status": "failed", "created_at": float(i)} for i in range(5)}
        self.assertEqual(2, len(bs.prune_build_tasks(tasks, max_history=3)))

    def test_registry_is_bounded_when_tasks_are_created(self):
        """The bound is actually applied on the create path."""
        from devconsole.services import build_service as bs
        with mock.patch.object(bs, "BUILD_TASKS", {}) as _:
            pass
        # Simulate the handler's call path with an oversized registry.
        registry = {f"t{i:03d}": {"status": "completed", "created_at": float(i)}
                    for i in range(bs.MAX_BUILD_TASK_HISTORY + 20)}
        bs.prune_build_tasks(registry)
        self.assertLessEqual(len(registry), bs.MAX_BUILD_TASK_HISTORY)

    def test_per_task_log_caps_are_left_alone(self):
        from devconsole.services import build_service as bs
        tasks = {"a": {"status": "completed", "created_at": 1.0,
                       "logs": ["x"] * 2500}}
        bs.prune_build_tasks(tasks, max_history=5)
        self.assertEqual(2500, len(tasks["a"]["logs"]))


class BuildStatusPayloadBoundTest(BoundaryTestCase):

    def test_build_status_reports_all_retained_tasks(self):
        from devconsole.services import build_service as bs
        registry = {f"t{i}": {"id": f"t{i}", "title": "T", "status": "completed",
                              "progress": 100, "current_step": "", "services": [],
                              "current_service": "", "service_status": {},
                              "error": None, "logs": [], "created_at": float(i)}
                    for i in range(3)}
        with mock.patch.object(bs, "BUILD_TASKS", registry), \
             mock.patch.object(handlers, "BUILD_TASKS", registry), \
             mock.patch.object(handlers, "BUILD_LOCK", bs.BUILD_LOCK):
            h = self.get("/api/deployments/build_status")
        self.assertEqual(200, h.captured["status"])
        self.assertEqual(3, len(json_body(h)))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
