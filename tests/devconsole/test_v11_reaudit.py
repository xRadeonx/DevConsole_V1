from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from devconsole import pins
from devconsole.api.v11_verified_handler import DevConsoleVerifiedV11Handler
from devconsole.services.container_engine import ContainerEngine
from devconsole.services.environment_transaction import RepoState, _rollback


class VerifiedFacadeRegressionTest(unittest.TestCase):
    def handler(self):
        handler = object.__new__(DevConsoleVerifiedV11Handler)
        handler.send_json = mock.Mock()
        return handler

    def test_environment_switch_reports_aborted_transaction_as_failure(self):
        handler = self.handler()
        aborted = {
            "transaction": "aborted",
            "message": "preflight failed",
            "results": [],
        }
        with mock.patch(
            "devconsole.api.v11_verified_handler.switch_workspace_environment_transactional",
            return_value=aborted,
        ):
            handler._switch_environment({"target_env": "test"})
        payload = handler.send_json.call_args.args[0]
        self.assertFalse(payload["success"])
        self.assertEqual("aborted", payload["data"]["transaction"])
        self.assertEqual(409, handler.send_json.call_args.kwargs["status"])

    def test_launch_message_remains_v1_compatible_and_viewer_is_additive(self):
        handler = self.handler()
        backend = mock.Mock()
        backend.launch_services.return_value = (True, "fake services", 1)
        backend.attach_viewers.return_value = (False, "viewer unavailable")
        with mock.patch(
            "devconsole.api.v11_verified_handler.get_terminal_backend",
            return_value=backend,
        ), mock.patch(
            "devconsole.api.v11_verified_handler.get_running_services_info",
            return_value=[],
        ):
            handler._launch_selected({"services": ["api"], "force": True})
        payload = handler.send_json.call_args.args[0]
        self.assertTrue(payload["success"])
        self.assertEqual("fake services", payload["message"])
        self.assertEqual(1, payload["count"])
        self.assertTrue(payload["viewer"]["requested"])
        self.assertTrue(payload["viewer"]["attempted"])
        self.assertFalse(payload["viewer"]["success"])
        self.assertEqual("viewer unavailable", payload["viewer"]["message"])


class ProductCredentialRegressionTest(unittest.TestCase):
    def test_historical_builtin_admin_pin_is_not_a_verifier_fallback(self):
        with tempfile.TemporaryDirectory() as td, mock.patch.dict(
            os.environ,
            {
                "SISPER_SECRETS_FILE": str(Path(td) / "missing-secrets.json"),
                "SISPER_ADMIN_PIN": "",
                "SISPER_DEV_PIN": "",
                "CREDENTIALS_DIRECTORY": "",
            },
            clear=False,
        ):
            pins._FALLOS.clear()
            self.assertFalse(pins.verify("admin", "sisper2026"))
            self.assertEqual("sin configurar", pins.estado()["admin"])


class EnvironmentRollbackRefTest(unittest.TestCase):
    @staticmethod
    def git(repo: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def make_repo(self, root: Path) -> Path:
        repo = root / "repo"
        repo.mkdir()
        self.git(repo, "init", "-b", "main")
        self.git(repo, "config", "user.email", "ci@example.invalid")
        self.git(repo, "config", "user.name", "CI")
        (repo / "file.txt").write_text("main\n", encoding="utf-8")
        self.git(repo, "add", "file.txt")
        self.git(repo, "commit", "-m", "main")
        return repo

    def test_rollback_restores_existing_target_branch_ref(self):
        with tempfile.TemporaryDirectory() as td:
            repo = self.make_repo(Path(td))
            main_commit = self.git(repo, "rev-parse", "HEAD")
            self.git(repo, "checkout", "-b", "test")
            (repo / "file.txt").write_text("test-before\n", encoding="utf-8")
            self.git(repo, "commit", "-am", "test before")
            target_before = self.git(repo, "rev-parse", "HEAD")
            self.git(repo, "checkout", "main")

            state = RepoState(
                "api", repo, "main", main_commit, "test", True, False, target_before
            )

            self.git(repo, "checkout", "test")
            (repo / "file.txt").write_text("test-after\n", encoding="utf-8")
            self.git(repo, "commit", "-am", "test after")
            self.assertNotEqual(target_before, self.git(repo, "rev-parse", "test"))

            ok, message = _rollback(state)
            self.assertTrue(ok, message)
            self.assertEqual("main", self.git(repo, "branch", "--show-current"))
            self.assertEqual(main_commit, self.git(repo, "rev-parse", "HEAD"))
            self.assertEqual(target_before, self.git(repo, "rev-parse", "test"))

    def test_rollback_deletes_target_branch_created_by_transaction(self):
        with tempfile.TemporaryDirectory() as td:
            repo = self.make_repo(Path(td))
            main_commit = self.git(repo, "rev-parse", "HEAD")
            state = RepoState(
                "api", repo, "main", main_commit, "temporary-target", False, True, None
            )
            self.git(repo, "checkout", "-b", "temporary-target")
            self.assertEqual("temporary-target", self.git(repo, "branch", "--show-current"))

            ok, message = _rollback(state)
            self.assertTrue(ok, message)
            self.assertEqual("main", self.git(repo, "branch", "--show-current"))
            result = subprocess.run(
                ["git", "-C", str(repo), "show-ref", "--verify", "--quiet", "refs/heads/temporary-target"],
                capture_output=True,
            )
            self.assertNotEqual(0, result.returncode)


class ContainerCancellationRegressionTest(unittest.TestCase):
    def test_cancel_does_not_wait_for_stdout_newline(self):
        with tempfile.TemporaryDirectory() as td:
            engine = ContainerEngine(sys.executable)
            cancelled = threading.Event()
            cancelled.set()
            result = engine._stream(
                ["-c", "import time; time.sleep(30)"],
                cwd=Path(td),
                cancel_event=cancelled,
            )
            self.assertTrue(result.cancelled)
            self.assertFalse(result.ok)


if __name__ == "__main__":
    unittest.main()
