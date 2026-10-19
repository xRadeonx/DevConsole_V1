from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from devconsole import v11_env_safety


class V11EnvironmentSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="devconsole-env-safety-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo_a = self.root / "ms_a"
        self.repo_b = self.root / "ms_b"
        for repo in (self.repo_a, self.repo_b):
            repo.mkdir()
            subprocess.run(["git", "init", "-q", "-b", "develop", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "DevConsole Test"], check=True)
            (repo / "README.md").write_text("baseline\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "baseline"], check=True)
            subprocess.run(["git", "-C", str(repo), "branch", "test"], check=True)

    def env_service(self):
        mapping = {"ms_a": self.repo_a, "ms_b": self.repo_b}
        return SimpleNamespace(
            ENVIRONMENTS={"develop": {"branch": "develop"}, "test": {"branch": "test"}},
            SERVICES_BACKEND=[{"name": "ms_a"}, {"name": "ms_b"}],
            SERVICES_FRONTEND=[],
            get_service_repo_dir=lambda name: mapping[name],
        )

    def branch(self, repo: Path) -> str:
        return subprocess.check_output(
            ["git", "-C", str(repo), "branch", "--show-current"], text=True
        ).strip()

    def test_unknown_environment_aborts_without_delegating(self):
        original = mock.Mock()
        result = v11_env_safety.switch_guarded(self.env_service(), original, "unknown")
        self.assertTrue(result["aborted"])
        self.assertEqual("unknown_environment", result["reason"])
        original.assert_not_called()

    def test_dirty_repository_blocks_entire_workspace_before_any_checkout(self):
        (self.repo_b / "README.md").write_text("dirty\n", encoding="utf-8")
        original = mock.Mock()

        result = v11_env_safety.switch_guarded(self.env_service(), original, "test")

        self.assertTrue(result["aborted"])
        self.assertEqual("preflight_failed", result["reason"])
        original.assert_not_called()
        self.assertEqual("develop", self.branch(self.repo_a))
        self.assertEqual("develop", self.branch(self.repo_b))

    def test_index_lock_blocks_switch_and_is_never_deleted(self):
        lock = self.repo_a / ".git" / "index.lock"
        lock.write_text("", encoding="utf-8")
        original = mock.Mock()
        result = v11_env_safety.switch_guarded(self.env_service(), original, "test")
        self.assertTrue(result["aborted"])
        self.assertTrue(lock.exists())
        original.assert_not_called()

    def test_clean_workspace_delegates_to_legacy_switch(self):
        def legacy(_target, _pull):
            for repo in (self.repo_a, self.repo_b):
                subprocess.run(["git", "-C", str(repo), "checkout", "-q", "test"], check=True)
            return {
                "target_env": "test",
                "target_branch": "test",
                "results": [
                    {"name": "ms_a", "status": "success", "message": "ok"},
                    {"name": "ms_b", "status": "success", "message": "ok"},
                ],
            }

        result = v11_env_safety.switch_guarded(self.env_service(), legacy, "test")
        self.assertFalse(result["aborted"])
        self.assertEqual("committed", result["reason"])
        self.assertEqual("test", self.branch(self.repo_a))
        self.assertEqual("test", self.branch(self.repo_b))

    def test_partial_legacy_failure_restores_original_branches(self):
        def legacy(_target, _pull):
            subprocess.run(["git", "-C", str(self.repo_a), "checkout", "-q", "test"], check=True)
            return {
                "target_env": "test",
                "target_branch": "test",
                "results": [
                    {"name": "ms_a", "status": "success", "message": "ok"},
                    {"name": "ms_b", "status": "error", "message": "simulated"},
                ],
            }

        result = v11_env_safety.switch_guarded(self.env_service(), legacy, "test")
        self.assertTrue(result["aborted"])
        self.assertTrue(result["rollback_ok"])
        self.assertEqual("develop", self.branch(self.repo_a))
        self.assertEqual("develop", self.branch(self.repo_b))


if __name__ == "__main__":
    unittest.main()
