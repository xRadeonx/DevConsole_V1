"""Characterization tests: ``env_service`` (roadmap item 0A-C.9).

The important contract frozen here is the **restart side effect**: saving a
service ``.env`` from the UI does not restart anything directly — it shells out
to ``start_tilix.sh restart-single <svc> <port>``, which is what touches the
``/tmp/sisper_restart_<svc>`` sentinel and frees the TCP port.  Later phases
(0B process identity, Phase 2 TerminalBackend) must preserve that contract.

``subprocess`` is fully mocked: no ``.env`` outside a temporary directory is
written, and no restart is ever attempted.
"""

from __future__ import annotations

import json
import threading
import time
from unittest import mock

from tests.devconsole.support import DevConsoleTestCase, capture_output, make_workspace

from devconsole.services import env_service


class ServiceEnvMapTest(DevConsoleTestCase):
    """``get_service_env_map()`` path derivation."""

    def setUp(self):
        super().setUp()
        self.root = make_workspace(self.temp_dir())
        self._patches = [
            mock.patch.object(env_service, "BASE_DIR", self.root),
            mock.patch.object(env_service, "SERVICES_BACKEND",
                              [{"name": "ms_a", "port": 8000},
                               {"name": "ms_b", "port": 8001}]),
            mock.patch.object(env_service, "SERVICES_FRONTEND",
                              [{"name": "mf_a", "port": 3000}]),
        ]
        for p in self._patches:
            p.start()
            self.addCleanup(p.stop)

    def test_backend_and_frontend_entries_are_mapped(self):
        m = env_service.get_service_env_map()
        self.assertEqual({"ms_a", "ms_b", "mf_a"}, set(m.keys()))
        self.assertEqual(
            self.root / "backend" / "ms_a" / ".env", m["ms_a"]["path"])
        self.assertEqual(
            self.root / "frontend" / "mf_a" / ".env", m["mf_a"]["path"])

    def test_type_and_port_are_recorded(self):
        m = env_service.get_service_env_map()
        self.assertEqual("backend", m["ms_a"]["type"])
        self.assertEqual("frontend", m["mf_a"]["type"])
        self.assertEqual(8001, m["ms_b"]["port"])
        self.assertEqual(3000, m["mf_a"]["port"])


class ReadServiceEnvTest(DevConsoleTestCase):
    """``read_service_env()`` never writes."""

    def setUp(self):
        super().setUp()
        self.root = make_workspace(self.temp_dir())
        for p in (
            mock.patch.object(env_service, "BASE_DIR", self.root),
            mock.patch.object(env_service, "SERVICES_BACKEND",
                              [{"name": "ms_a", "port": 8000}]),
            mock.patch.object(env_service, "SERVICES_FRONTEND", []),
        ):
            p.start()
            self.addCleanup(p.stop)

    def test_unregistered_service_is_rejected(self):
        result = env_service.read_service_env("ms_unknown")
        self.assertFalse(result["success"])
        self.assertIn("no registrado", result["error"])

    def test_missing_env_reports_exists_false(self):
        result = env_service.read_service_env("ms_a")
        self.assertTrue(result["success"])
        self.assertFalse(result["exists"])
        self.assertEqual("", result["content"])

    def test_existing_env_content_is_returned(self):
        env = self.root / "backend" / "ms_a" / ".env"
        env.parent.mkdir(parents=True, exist_ok=True)
        env.write_text("DATABASE_HOST=127.0.0.1\n", encoding="utf-8")
        result = env_service.read_service_env("ms_a")
        self.assertTrue(result["exists"])
        self.assertIn("DATABASE_HOST=127.0.0.1", result["content"])
        self.assertEqual("backend/ms_a/.env", result["path"])

    def test_contract_keys(self):
        result = env_service.read_service_env("ms_a")
        self.assertEqual(
            {"success", "service", "port", "type", "path", "content", "exists"},
            set(result.keys()),
        )


class WriteServiceEnvTest(DevConsoleTestCase):
    """``write_service_env()`` write + restart contract (item 0A-C.9)."""

    def setUp(self):
        super().setUp()
        self.root = make_workspace(self.temp_dir())
        for p in (
            mock.patch.object(env_service, "BASE_DIR", self.root),
            mock.patch.object(env_service, "SERVICES_BACKEND",
                              [{"name": "ms_sisper_sesion", "port": 8000}]),
            mock.patch.object(env_service, "SERVICES_FRONTEND",
                              [{"name": "mf_sisper_sesion", "port": 3000}]),
        ):
            p.start()
            self.addCleanup(p.stop)
        env_service.ENV_WATCHER_EVENTS.clear()

    def _env_file(self, svc, kind="backend"):
        return self.root / kind / svc / ".env"

    def test_content_is_written_verbatim(self):
        ok, msg = env_service.write_service_env(
            "ms_sisper_sesion", "A=1\nB=2\n", restart=False)
        self.assertTrue(ok)
        self.assertIn("guardado con éxito", msg)
        self.assertEqual("A=1\nB=2\n",
                         self._env_file("ms_sisper_sesion").read_text(encoding="utf-8"))

    def test_missing_parent_directory_is_created(self):
        ok, _ = env_service.write_service_env("ms_sisper_sesion", "X=1\n", restart=False)
        self.assertTrue(ok)
        self.assertTrue(self._env_file("ms_sisper_sesion").parent.is_dir())

    def test_unregistered_service_is_rejected_and_writes_nothing(self):
        ok, msg = env_service.write_service_env("ms_nope", "X=1\n", restart=False)
        self.assertFalse(ok)
        self.assertIn("no registrado", msg)
        self.assertFalse((self.root / "backend" / "ms_nope").exists())

    def test_restart_true_invokes_start_tilix_restart_single(self):
        m = self.patch_run(returncode=0)
        ok, msg = env_service.write_service_env(
            "ms_sisper_sesion", "X=1\n", restart=True)
        self.assertTrue(ok)
        self.assertIn("reiniciado automáticamente", msg)

        self.assertEqual(1, m.call_count, "expected exactly one restart invocation")
        args, kwargs = m.call_args
        cmd = args[0]
        self.assertEqual(str(self.root / "start_tilix.sh"), cmd[0])
        self.assertEqual("restart-single", cmd[1])
        self.assertEqual("ms_sisper_sesion", cmd[2])
        self.assertEqual("8000", cmd[3], "port must be passed as a string")
        self.assertFalse(kwargs.get("check", True),
                         "restart must not raise on failure (check=False)")
        self.assertEqual(5, kwargs.get("timeout"))

    def test_restart_false_never_invokes_a_subprocess(self):
        m = self.patch_run()
        ok, msg = env_service.write_service_env(
            "ms_sisper_sesion", "X=1\n", restart=False)
        self.assertTrue(ok)
        self.assertNotIn("reiniciado", msg)
        self.assertEqual(0, m.call_count)

    def test_restart_uses_the_frontend_port_for_frontends(self):
        m = self.patch_run()
        env_service.write_service_env("mf_sisper_sesion", "X=1\n", restart=True)
        self.assertEqual("3000", m.call_args[0][0][3])

    def test_restart_failure_is_reported_but_write_survives(self):
        with mock.patch("subprocess.run", side_effect=OSError("no such binary")):
            ok, msg = env_service.write_service_env(
                "ms_sisper_sesion", "X=1\n", restart=True)
        self.assertTrue(ok, "a failed restart must not fail the save")
        self.assertIn("Aviso reinicio", msg)
        self.assertEqual("X=1\n",
                         self._env_file("ms_sisper_sesion").read_text(encoding="utf-8"))

    def test_mtime_is_recorded_to_suppress_self_triggered_watcher_events(self):
        env_service.write_service_env("ms_sisper_sesion", "X=1\n", restart=False)
        key = str(self._env_file("ms_sisper_sesion"))
        self.assertIn(key, env_service.ENV_WATCHER_LAST_MTIME)

    def test_no_restart_is_attempted_without_the_restart_flag(self):
        """Regression guard: the default must be documented as restart=True."""
        import inspect
        sig = inspect.signature(env_service.write_service_env)
        self.assertTrue(sig.parameters["restart"].default,
                        "write_service_env() defaults to restarting the service")


class GetEnvInfoTest(DevConsoleTestCase):
    """``get_env_info()`` shells out to ``switch_env.sh status-json``."""

    def setUp(self):
        super().setUp()
        self.root = make_workspace(self.temp_dir())
        for p in (mock.patch.object(env_service, "BASE_DIR", self.root),):
            p.start()
            self.addCleanup(p.stop)

    def test_valid_json_is_parsed(self):
        payload = {"env_mode": "LOCAL", "bitacora_status": "PARCHE LOCAL (try/except)",
                   "database_host": "127.0.0.1", "keycloak_url": "http://localhost:8080/"}
        script = self.root / "switch_env.sh"
        script.write_text("#!/bin/sh\n", encoding="utf-8")
        self.patch_check_output(output=json.dumps(payload))

        info = env_service.get_env_info()
        self.assertEqual("LOCAL", info["env_mode"])
        self.assertEqual("127.0.0.1", info["database_host"])

    def test_command_failure_falls_back_to_desconocido(self):
        # The script exists, so the call is attempted; its failure is caught and
        # reported as DESCONOCIDO (with the exception text as bitacora_status).
        script = self.root / "switch_env.sh"
        script.write_text("#!/bin/sh\n", encoding="utf-8")
        self.patch_check_output(output="", returncode=1)

        info = env_service.get_env_info()
        self.assertEqual("DESCONOCIDO", info["env_mode"])
        self.assertIn("bitacora_status", info)

    def test_missing_script_falls_back_to_intranet_defaults(self):
        # No script on disk -> the final hardcoded default is returned.
        info = env_service.get_env_info()
        self.assertEqual("INTRANET", info["env_mode"])
        self.assertEqual("ORIGINAL", info["bitacora_status"])

    def test_missing_script_falls_back_without_raising(self):
        info = env_service.get_env_info()
        self.assertIn("env_mode", info)

    def test_contract_keys(self):
        self.patch_check_output(output=json.dumps({
            "env_mode": "INTRANET", "bitacora_status": "X",
            "database_host": "h", "keycloak_url": "u"}))
        info = env_service.get_env_info()
        self.assertEqual(
            {"env_mode", "bitacora_status", "database_host", "keycloak_url"},
            set(info.keys()),
        )


class EnvWatcherEventsCapTest(DevConsoleTestCase):
    """``ENV_WATCHER_EVENTS`` is a bounded list (max 30 entries)."""

    def test_list_starts_empty_and_is_module_level(self):
        self.assertIsInstance(env_service.ENV_WATCHER_EVENTS, list)

    def test_events_are_capped_by_the_watcher_loop(self):
        """Drive one real iteration of the watcher with sleeps neutralised.

        The loop is a ``while True`` daemon; the test patches ``time.sleep`` to a
        no-op, starts it in a daemon thread, bumps a tracked ``.env`` mtime, and
        stops the loop by flipping ``ENV_WATCHER_ENABLED``.  The restart command
        itself is mocked, so nothing is executed.
        """
        root = make_workspace(self.temp_dir())
        env_dir = root / "backend" / "ms_sisper_sesion"
        env_dir.mkdir(parents=True, exist_ok=True)
        env_file = env_dir / ".env"
        env_file.write_text("A=1\n", encoding="utf-8")

        capture_output(self)
        env_service.ENV_WATCHER_EVENTS.clear()
        original_enabled = env_service.ENV_WATCHER_ENABLED
        env_service.ENV_WATCHER_ENABLED = True
        self.addCleanup(setattr, env_service, "ENV_WATCHER_ENABLED", original_enabled)

        run_mock = self.patch_run(returncode=0)
        stop = threading.Event()
        started = threading.Event()

        def fake_sleep(_seconds):
            started.set()
            # Yield so the main thread can mutate the file and then stop us.
            stop.wait(0.001)

        with mock.patch.object(env_service, "BASE_DIR", root), \
             mock.patch.object(env_service, "SERVICES_BACKEND",
                               [{"name": "ms_sisper_sesion", "port": 8000}]), \
             mock.patch.object(env_service, "SERVICES_FRONTEND", []), \
             mock.patch.object(env_service.time, "sleep", side_effect=fake_sleep):
            t = threading.Thread(target=env_service.env_file_watcher_loop, daemon=True)
            t.start()
            self.assertTrue(started.wait(2.0), "watcher thread did not start")

            # Bump the mtime so the loop detects a change and records an event.
            future = time.time() + 10
            import os
            os.utime(env_file, (future, future))

            deadline = time.time() + 3.0
            while time.time() < deadline and not env_service.ENV_WATCHER_EVENTS:
                time.sleep(0.005)

            env_service.ENV_WATCHER_ENABLED = False
            stop.set()
            t.join(timeout=2.0)

        self.assertTrue(env_service.ENV_WATCHER_EVENTS,
                        "watcher did not register an .env modification event")
        event = env_service.ENV_WATCHER_EVENTS[0]
        self.assertEqual("ms_sisper_sesion", event["service"])
        self.assertEqual(8000, event["port"])
        self.assertIn("ms_sisper_sesion/.env", event["file"])
        self.assertEqual(
            {"service", "port", "file", "timestamp", "time_str"},
            set(event.keys()),
        )
        # The watcher must route the restart through start_tilix.sh restart-single.
        self.assertTrue(run_mock.called)
        cmd = run_mock.call_args[0][0]
        self.assertEqual("restart-single", cmd[1])
        self.assertEqual("8000", cmd[3])

    def test_event_list_is_capped_at_thirty(self):
        env_service.ENV_WATCHER_EVENTS.clear()
        self.addCleanup(env_service.ENV_WATCHER_EVENTS.clear)
        for i in range(45):
            env_service.ENV_WATCHER_EVENTS.append({"service": f"s{i}"})
            if len(env_service.ENV_WATCHER_EVENTS) > 30:
                env_service.ENV_WATCHER_EVENTS.pop(0)
        self.assertEqual(30, len(env_service.ENV_WATCHER_EVENTS))
