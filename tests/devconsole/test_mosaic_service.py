# tests/devconsole/test_mosaic_service.py
"""Tests for Phase 5A: Lightweight read-only service mosaic with bounded log previews."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

import devconsole.config as dcfg
from devconsole.services.runtime.process_identity import (
    Confidence,
    ProcessIdentity,
    ServiceDescriptor,
    ServiceType,
)
from devconsole.services.runtime.process_resolver import Resolution
from devconsole.services.terminal.mosaic_service import (
    DEFAULT_MAX_LINES,
    HARD_MAX_LINES,
    MAX_LINE_CHARS,
    MosaicItem,
    MosaicService,
    is_port_listening,
)
from devconsole.services.terminal.tmux_runtime import TmuxSession
from tests.devconsole.support import (
    DevConsoleTestCase,
    json_body,
    make_handler,
    make_workspace,
)


class TestMosaicService(unittest.TestCase):
    def setUp(self):
        self.mock_backend = mock.MagicMock()
        self.mock_resolver = mock.MagicMock()
        self.service = MosaicService(backend=self.mock_backend, resolver=self.mock_resolver)

    def test_item_serialization(self):
        item = MosaicItem(
            name="ms_sisper_test",
            service_type="backend",
            port=8000,
            status="RUNNING",
            runtime_host="tmux",
            pid=1234,
            uptime_seconds=3600,
            environment="develop",
            recent_lines=["Line 1", "Line 2"],
            recent_error=None,
            is_standby=False,
        )
        d = item.to_dict()
        self.assertEqual(d["name"], "ms_sisper_test")
        self.assertEqual(d["status"], "RUNNING")
        self.assertEqual(d["recent_lines"], ["Line 1", "Line 2"])
        self.assertFalse(d["is_standby"])

    @mock.patch("devconsole.services.terminal.mosaic_service.is_port_listening", return_value=True)
    def test_running_service_preview(self, mock_listen):
        svc_cfg = {"name": "ms_sisper_test", "port": 8000}
        self.mock_backend.session_name.return_value = "sisper_ms_sisper_test"
        self.mock_backend.runtime.find_session.return_value = TmuxSession(
            name="sisper_ms_sisper_test", windows=1, attached=0, pane_pid=1234, pane_dead=False, pane_cwd="/app"
        )
        descriptor = ServiceDescriptor(
            name="ms_sisper_test",
            service_type=ServiceType.BACKEND,
            configured_port=8000,
            expected_service_dir=Path("/app"),
            base_dir=Path("/app"),
        )
        ident = ProcessIdentity(
            service_name="ms_sisper_test",
            service_type=ServiceType.BACKEND,
            configured_port=8000,
            pid=1234,
            ppid=1,
            pgid=1234,
            executable="/bin/python",
            command_line=("python", "manage.py"),
            cwd="/app",
            listening_ports=(8000,),
            expected_service_dir="/app",
            base_dir="/app",
            confidence=Confidence.HIGH,
            owned_by_devconsole=True,
        )
        self.mock_resolver.resolve_service.return_value = Resolution(
            descriptor=descriptor,
            identity=ident,
            candidate_pids=(1234,),
            rejected=(),
        )

        mock_proc = mock.MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Booting worker\nReady on port 8000\n"
        self.mock_backend.runtime._run.return_value = mock_proc

        item = self.service.get_service_preview(svc_cfg)
        self.assertEqual(item.name, "ms_sisper_test")
        self.assertEqual(item.status, "RUNNING")
        self.assertEqual(item.runtime_host, "tmux")
        self.assertEqual(item.pid, 1234)
        self.assertEqual(item.recent_lines, ["Booting worker", "Ready on port 8000"])
        self.assertFalse(item.is_standby)
        self.assertIsNone(item.recent_error)

    @mock.patch("devconsole.services.terminal.mosaic_service.is_port_listening", return_value=False)
    def test_standby_service_preview(self, mock_listen):
        svc_cfg = {"name": "ms_sisper_standby", "port": 8005}
        self.mock_backend.session_name.return_value = "sisper_ms_sisper_standby"
        self.mock_backend.runtime.find_session.return_value = TmuxSession(
            name="sisper_ms_sisper_standby", windows=1, attached=0, pane_pid=5678, pane_dead=False, pane_cwd="/app"
        )
        descriptor = ServiceDescriptor(
            name="ms_sisper_standby",
            service_type=ServiceType.BACKEND,
            configured_port=8005,
            expected_service_dir=Path("/app"),
            base_dir=Path("/app"),
        )
        self.mock_resolver.resolve_service.return_value = Resolution(
            descriptor=descriptor,
            identity=None,
            candidate_pids=(),
            rejected=(),
        )

        mock_proc = mock.MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = (
            "Exception occurred connecting to DB\n"
            "[MODO STANDBY] Presione 'r' para reintentar la conexión...\n"
            "Opción [r=reintentar]: "
        )
        self.mock_backend.runtime._run.return_value = mock_proc

        item = self.service.get_service_preview(svc_cfg)
        self.assertEqual(item.status, "STANDBY")
        self.assertTrue(item.is_standby)
        self.assertIsNotNone(item.recent_error)

    @mock.patch("devconsole.services.terminal.mosaic_service.is_port_listening", return_value=False)
    def test_failed_service_preview(self, mock_listen):
        svc_cfg = {"name": "ms_sisper_broken", "port": 8010}
        self.mock_backend.session_name.return_value = "sisper_ms_sisper_broken"
        self.mock_backend.runtime.find_session.return_value = TmuxSession(
            name="sisper_ms_sisper_broken", windows=1, attached=0, pane_pid=9999, pane_dead=False, pane_cwd="/app"
        )
        descriptor = ServiceDescriptor(
            name="ms_sisper_broken",
            service_type=ServiceType.BACKEND,
            configured_port=8010,
            expected_service_dir=Path("/app"),
            base_dir=Path("/app"),
        )
        self.mock_resolver.resolve_service.return_value = Resolution(
            descriptor=descriptor,
            identity=None,
            candidate_pids=(),
            rejected=(),
        )

        mock_proc = mock.MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Traceback (most recent call last):\n  File 'manage.py', line 10\nSyntaxError: invalid syntax"
        self.mock_backend.runtime._run.return_value = mock_proc

        item = self.service.get_service_preview(svc_cfg)
        self.assertEqual(item.status, "FAILED")
        self.assertFalse(item.is_standby)
        self.assertIn("SyntaxError", item.recent_error or "")

    def test_line_and_char_limits(self):
        svc_cfg = {"name": "ms_sisper_long", "port": 8020}
        self.mock_backend.session_name.return_value = "sisper_ms_sisper_long"
        self.mock_backend.runtime.find_session.return_value = TmuxSession(
            name="sisper_ms_sisper_long", windows=1, attached=0, pane_pid=1111, pane_dead=False, pane_cwd="/app"
        )
        descriptor = ServiceDescriptor(
            name="ms_sisper_long",
            service_type=ServiceType.BACKEND,
            configured_port=8020,
            expected_service_dir=Path("/app"),
            base_dir=Path("/app"),
        )
        self.mock_resolver.resolve_service.return_value = Resolution(
            descriptor=descriptor,
            identity=None,
            candidate_pids=(),
            rejected=(),
        )

        mock_proc = mock.MagicMock()
        mock_proc.returncode = 0
        long_line = "A" * (MAX_LINE_CHARS + 50)
        mock_proc.stdout = "\n".join([f"line-{i}: {long_line}" for i in range(20)])
        self.mock_backend.runtime._run.return_value = mock_proc

        item = self.service.get_service_preview(svc_cfg, max_lines=4)
        self.assertEqual(len(item.recent_lines), 4)
        for line in item.recent_lines:
            self.assertLessEqual(len(line), MAX_LINE_CHARS)


class TestMosaicAPIEndpoint(DevConsoleTestCase):
    def setUp(self):
        super().setUp()
        self.root = make_workspace(self.temp_dir())
        self.backend = [{"name": "ms_sisper_sesion", "port": 8000}]
        self.frontend = [{"name": "mf_sisper_sesion", "port": 3000}]
        self.patch_run(returncode=0, stdout="")


    def get(self, path: str, headers: dict | None = None):
        from devconsole.api.handlers import DevConsoleHandler
        h = make_handler(DevConsoleHandler, path=path, headers=headers or {})
        h.do_GET()
        return h

    @mock.patch("devconsole.services.terminal.mosaic_service.is_port_listening", return_value=True)
    def test_get_mosaic_overview_endpoint(self, mock_listen):
        h = self.get("/api/services/mosaic")
        self.assertEqual(200, h.captured["status"])
        body = json_body(h)
        self.assertIn("services", body)
        self.assertIn("count", body)
        self.assertGreaterEqual(body["count"], 1)

    @mock.patch("devconsole.services.terminal.mosaic_service.is_port_listening", return_value=True)
    def test_get_single_service_mosaic_endpoint(self, mock_listen):
        h = self.get("/api/services/mosaic?service=ms_sisper_sesion")
        self.assertEqual(200, h.captured["status"])
        body = json_body(h)
        self.assertEqual(body["name"], "ms_sisper_sesion")
        self.assertIn("status", body)

    @mock.patch("devconsole.services.terminal.mosaic_service.is_port_listening", return_value=True)
    def test_get_batch_services_mosaic_endpoint(self, mock_listen):
        h = self.get("/api/services/mosaic?services=ms_sisper_sesion,mf_sisper_sesion")
        self.assertEqual(200, h.captured["status"])
        body = json_body(h)
        self.assertIn("services", body)
        self.assertEqual(body["count"], 2)
        names = [s["name"] for s in body["services"]]
        self.assertIn("ms_sisper_sesion", names)
        self.assertIn("mf_sisper_sesion", names)

    def test_get_nonexistent_service_mosaic_endpoint(self):
        h = self.get("/api/services/mosaic?service=ms_nonexistent_xyz")
        self.assertEqual(404, h.captured["status"])

    def post(self, path: str, payload: dict, headers: dict | None = None):
        import json
        from devconsole.api.handlers import DevConsoleHandler
        body = json.dumps(payload).encode("utf-8")
        hdrs = {
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
            "Origin": "http://127.0.0.1:9099",
            "Host": "127.0.0.1:9099",
            **(headers or {}),
        }
        h = make_handler(DevConsoleHandler, path=path, method="POST", headers=hdrs, body=body)
        h.do_POST()
        return h

    @mock.patch("devconsole.api.handlers.get_terminal_backend")
    def test_post_attach_viewer_endpoint(self, mock_get_backend):
        mock_backend = mock.MagicMock()
        mock_backend.attach_viewer.return_value = (True, "Visor Tilix abierto")
        mock_get_backend.return_value = mock_backend

        h = self.post("/api/tilix/attach_viewer", {"service": "ms_sisper_sesion"})
        self.assertEqual(200, h.captured["status"])
        body = json_body(h)
        self.assertTrue(body["success"])
        self.assertIn("Visor Tilix", body["message"])
        mock_backend.attach_viewer.assert_called_once_with("ms_sisper_sesion", title=None)

    def test_post_attach_viewer_endpoint_missing_param(self):
        h = self.post("/api/tilix/attach_viewer", {})
        self.assertEqual(400, h.captured["status"])



