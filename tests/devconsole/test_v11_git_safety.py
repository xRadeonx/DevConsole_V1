from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from devconsole import v11_git_safety


class V11GitSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="devconsole-git-safety-")
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "ms_demo"
        (self.repo / ".git").mkdir(parents=True)

    def fake_service(self):
        return SimpleNamespace(get_service_repo_dir=lambda _name: self.repo)

    def test_checkout_delegates_unchanged_without_lock(self):
        original = mock.Mock(return_value=(True, "legacy-ok"))
        result = v11_git_safety.checkout_guarded(
            self.fake_service(), original, "ms_demo", "develop"
        )
        self.assertEqual((True, "legacy-ok"), result)
        original.assert_called_once_with("ms_demo", "develop")

    def test_checkout_is_blocked_while_index_lock_exists(self):
        lock = self.repo / ".git" / "index.lock"
        lock.write_text("", encoding="utf-8")
        original = mock.Mock(return_value=(True, "must-not-run"))

        ok, message = v11_git_safety.checkout_guarded(
            self.fake_service(), original, "ms_demo", "feature/demo"
        )

        self.assertFalse(ok)
        self.assertIn("index.lock", message)
        self.assertIn("no eliminará", message)
        self.assertTrue(lock.exists())
        original.assert_not_called()

    def test_old_lock_is_still_not_deleted_automatically(self):
        lock = self.repo / ".git" / "index.lock"
        lock.write_text("", encoding="utf-8")
        old = time.time() - 24 * 3600
        os.utime(lock, (old, old))
        original = mock.Mock()

        ok, _message = v11_git_safety.checkout_guarded(
            self.fake_service(), original, "ms_demo", "main"
        )

        self.assertFalse(ok)
        self.assertTrue(lock.exists(), "age alone never proves that a Git lock is safe to delete")
        original.assert_not_called()

    def test_lock_status_is_read_only(self):
        lock = self.repo / ".git" / "index.lock"
        lock.write_text("sentinel", encoding="utf-8")
        before = lock.read_bytes()
        status = v11_git_safety.lock_status(self.repo)
        self.assertTrue(status["locked"])
        self.assertEqual(before, lock.read_bytes())


if __name__ == "__main__":
    unittest.main()
