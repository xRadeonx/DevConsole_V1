"""Characterization tests: ``git_service`` (roadmap item 0A-C.2).

``git_service.get_git_info()`` is the single most-called function in DevConsole
(every ``/api/status`` request fans out one call per service).  Its contract is
frozen here so later refactors cannot silently change branch/dirty/ahead/behind
semantics.

Every subprocess call is mocked.  ``DevConsoleTestCase`` fails the test if any
real child process is spawned.
"""

from __future__ import annotations

import subprocess
from unittest import mock

from tests.devconsole.support import DevConsoleTestCase

from devconsole.services import git_service


def git_dispatcher(*, branch="develop", porcelain="", upstream="origin/develop",
                   ahead="0", behind="0", unpushed="", unpulled="",
                   fail_branch=False, fail_status=False, fail_revlist=False,
                   fail_log=False):
    """Return a fake ``check_output`` implementing the git calls get_git_info makes."""
    calls: list[list[str]] = []

    def _fake(cmd, *args, **kwargs):
        calls.append(list(cmd))
        joined = " ".join(cmd)

        def out(text):
            return text.encode()

        if "branch --show-current" in joined:
            if fail_branch:
                raise subprocess.CalledProcessError(1, cmd)
            return out(branch)
        if "status --porcelain" in joined:
            if fail_status:
                raise subprocess.CalledProcessError(1, cmd)
            return out(porcelain)
        if "rev-parse --abbrev-ref" in joined:
            if upstream is None:
                raise subprocess.CalledProcessError(128, cmd)
            return out(upstream)
        if "rev-list --count" in joined and "..HEAD" in joined and not joined.startswith("git -C"):
            return out(ahead)
        if "rev-list --count" in joined:
            # Distinguish ahead (upstream..HEAD) from behind (HEAD..upstream).
            if "HEAD.." in joined:
                if fail_revlist:
                    raise subprocess.CalledProcessError(1, cmd)
                return out(behind)
            if fail_revlist:
                raise subprocess.CalledProcessError(1, cmd)
            return out(ahead)
        if "log" in joined and "..HEAD" in joined:
            if fail_log:
                raise subprocess.CalledProcessError(1, cmd)
            return out(unpushed)
        if "log" in joined and "HEAD.." in joined:
            if fail_log:
                raise subprocess.CalledProcessError(1, cmd)
            return out(unpulled)
        return out("")

    return _fake, calls


class GetGitInfoTest(DevConsoleTestCase):
    """``get_git_info()`` contract."""

    def _git_dir(self, *, exists=True):
        root = self.temp_dir()
        d = root / "ms_sisper_demo"
        d.mkdir(parents=True, exist_ok=True)
        if exists:
            (d / ".git").mkdir()
        return d

    def _run(self, directory, **kw):
        fake, calls = git_dispatcher(**kw)
        with mock.patch.object(subprocess, "check_output", side_effect=fake):
            return git_service.get_git_info(directory), calls

    def test_missing_directory_returns_default_without_spawning_git(self):
        missing = self.temp_dir() / "nope"
        info = git_service.get_git_info(missing)
        self.assertEqual("N/A", info["branch"])
        self.assertEqual(0, info["dirty"])
        self.assertFalse(info["has_upstream"])
        self.assertEqual([], info["dirty_files"])

    def test_directory_without_dot_git_returns_default(self):
        d = self._git_dir(exists=False)
        info = git_service.get_git_info(d)
        self.assertEqual("N/A", info["branch"])
        self.assertFalse(info["has_upstream"])

    def test_clean_repo_on_branch(self):
        d = self._git_dir()
        info, calls = self._run(d, branch="develop", porcelain="", ahead="0", behind="0")
        self.assertEqual("develop", info["branch"])
        self.assertEqual(0, info["dirty"])
        self.assertEqual(0, info["ahead"])
        self.assertEqual(0, info["behind"])
        self.assertTrue(info["has_upstream"])
        self.assertEqual([], info["unpushed_commits"])
        self.assertEqual([], info["unpulled_commits"])
        self.assertEqual([], info["dirty_files"])
        self.assertTrue(any("branch" in " ".join(c) for c in calls))

    def test_dirty_repo_counts_lines_and_lists_files(self):
        d = self._git_dir()
        porcelain = " M backend/x.py\n?? scratch.txt\n"
        info, _ = self._run(d, porcelain=porcelain)
        self.assertEqual(2, info["dirty"])
        self.assertEqual(["M backend/x.py", "?? scratch.txt"], info["dirty_files"])

    def test_dirty_files_is_capped_at_ten(self):
        d = self._git_dir()
        porcelain = "".join(f" M f{i:02d}.py\n" for i in range(15))
        info, _ = self._run(d, porcelain=porcelain)
        self.assertEqual(15, info["dirty"])
        self.assertEqual(10, len(info["dirty_files"]))

    def test_ahead_commits_are_collected(self):
        d = self._git_dir()
        info, _ = self._run(
            d, ahead="2", unpushed="abc123 first\ndef456 second\n",
        )
        self.assertEqual(2, info["ahead"])
        self.assertEqual(["abc123 first", "def456 second"], info["unpushed_commits"])

    def test_behind_commits_are_collected(self):
        d = self._git_dir()
        info, _ = self._run(
            d, behind="3", unpulled="aaa one\nbbb two\nccc three\n",
        )
        self.assertEqual(3, info["behind"])
        self.assertEqual(3, len(info["unpulled_commits"]))

    def test_no_upstream_falls_back_to_origin_branch_and_flags_false(self):
        d = self._git_dir()
        info, calls = self._run(d, upstream=None, branch="feature-x")
        self.assertFalse(info["has_upstream"])
        # Fallback ref must be origin/<branch>.
        self.assertTrue(any("origin/feature-x" in " ".join(c) for c in calls))

    def test_empty_branch_output_becomes_head(self):
        d = self._git_dir()
        info, _ = self._run(d, branch="")
        self.assertEqual("HEAD", info["branch"])

    def test_failed_branch_command_yields_na(self):
        d = self._git_dir()
        info, _ = self._run(d, fail_branch=True)
        self.assertEqual("N/A", info["branch"])

    def test_failed_status_command_yields_zero_dirty(self):
        d = self._git_dir()
        info, _ = self._run(d, fail_status=True)
        # A failing status must degrade to "clean", not raise.
        self.assertEqual(0, info["dirty"])
        self.assertEqual([], info["dirty_files"])

    def test_failed_revlist_yields_zero_ahead_and_behind(self):
        d = self._git_dir()
        info, _ = self._run(d, fail_revlist=True)
        self.assertEqual(0, info["ahead"])
        self.assertEqual(0, info["behind"])

    def test_failed_log_yields_empty_commit_lists(self):
        d = self._git_dir()
        info, _ = self._run(d, fail_log=True)
        self.assertEqual([], info["unpushed_commits"])
        self.assertEqual([], info["unpulled_commits"])

    def test_result_always_exposes_the_same_keys(self):
        d = self._git_dir()
        info, _ = self._run(d)
        expected = {
            "branch", "dirty", "ahead", "behind", "has_upstream",
            "unpushed_commits", "unpulled_commits", "dirty_files",
        }
        self.assertEqual(expected, set(info.keys()))


class ServiceBranchesTest(DevConsoleTestCase):
    """``get_service_branches()`` normalizes ``origin/`` prefixes."""

    def test_missing_repo_reports_sin_git(self):
        with mock.patch.object(git_service, "get_service_repo_dir",
                               return_value=self.temp_dir() / "nope"):
            info = git_service.get_service_branches("ms_x")
        self.assertEqual("sin git", info["current"])
        self.assertEqual([], info["branches"])

    def test_origin_prefixes_stripped_and_current_first(self):
        repo = self.temp_dir() / "ms_x"
        (repo / ".git").mkdir(parents=True)

        def fake(cmd, *a, **kw):
            joined = " ".join(cmd)
            if "branch --show-current" in joined:
                return b"develop"
            if "branch -a" in joined:
                return b"origin/develop\norigin/main\norigin/test\norigin/HEAD\n"
            return b""

        with mock.patch.object(git_service, "get_service_repo_dir", return_value=repo), \
             mock.patch.object(subprocess, "check_output", side_effect=fake):
            info = git_service.get_service_branches("ms_x")

        self.assertEqual("develop", info["current"])
        self.assertEqual("develop", info["branches"][0])
        self.assertNotIn("origin/develop", info["branches"])
        self.assertIn("main", info["branches"])
        self.assertIn("test", info["branches"])
        self.assertNotIn("HEAD", info["branches"])


class RunningServicesTest(DevConsoleTestCase):
    """``get_running_services_info()`` must be a pure port probe (item 0A-C.3)."""

    def test_returns_only_services_whose_port_is_open(self):
        backend = [{"name": "ms_a", "port": 8000}, {"name": "ms_b", "port": 8001}]
        frontend = [{"name": "mf_a", "port": 3000}]
        probed: list[int] = []

        def fake_is_port_open(port, host="127.0.0.1"):
            probed.append(port)
            return port in (8001, 3000)

        with mock.patch.object(git_service, "SERVICES_BACKEND", backend), \
             mock.patch.object(git_service, "SERVICES_FRONTEND", frontend), \
             mock.patch.object(git_service, "is_port_open", side_effect=fake_is_port_open):
            running = git_service.get_running_services_info()

        self.assertEqual(
            [{"name": "ms_b", "port": 8001}, {"name": "mf_a", "port": 3000}],
            running,
        )
        self.assertEqual([8000, 8001, 3000], probed)

    def test_returns_empty_when_nothing_listens(self):
        with mock.patch.object(git_service, "SERVICES_BACKEND", [{"name": "ms_a", "port": 8000}]), \
             mock.patch.object(git_service, "SERVICES_FRONTEND", []), \
             mock.patch.object(git_service, "is_port_open", return_value=False):
            self.assertEqual([], git_service.get_running_services_info())

    def test_never_invokes_a_subprocess(self):
        """The guard in DevConsoleTestCase would raise; this asserts intent explicitly."""
        with mock.patch.object(git_service, "SERVICES_BACKEND", [{"name": "ms_a", "port": 8000}]), \
             mock.patch.object(git_service, "SERVICES_FRONTEND", []), \
             mock.patch.object(git_service, "is_port_open", return_value=True):
            running = git_service.get_running_services_info()
        self.assertEqual(1, len(running))
        self.assertEqual({"name", "port"}, set(running[0].keys()))


class GetServiceDetailTest(DevConsoleTestCase):
    """``infra_service.get_service_detail()`` (item 0A-C.4).

    Only the *query* form of ``fuser`` is ever exercised.  ``fuser -k`` must
    never appear in the generated command.
    """

    def _detail(self, *, service="ms_sisper_sesion", port=8000, online=True,
                fuser_output="12345", git_info=None):
        from devconsole.services import infra_service

        repo = self.temp_dir() / service
        repo.mkdir(parents=True, exist_ok=True)
        fuser_calls: list[str] = []

        def fake_check_output(cmd, *a, **kw):
            fuser_calls.append(cmd if isinstance(cmd, str) else " ".join(cmd))
            return fuser_output.encode()

        with mock.patch.object(infra_service, "get_service_repo_dir", return_value=repo), \
             mock.patch.object(infra_service, "is_port_open", return_value=online), \
             mock.patch.object(infra_service, "get_git_info",
                               return_value=git_info or {"branch": "develop", "dirty": 0}), \
             mock.patch.object(subprocess, "check_output", side_effect=fake_check_output):
            result = infra_service.get_service_detail(service, port)
        return result, fuser_calls

    def test_online_service_reports_pid_from_fuser_query(self):
        result, calls = self._detail(fuser_output="12345 67890")
        self.assertTrue(result["online"])
        self.assertEqual("12345, 67890", result["pid"])
        self.assertTrue(any("fuser" in c for c in calls))

    def test_fuser_is_never_invoked_with_kill_flag(self):
        _, calls = self._detail()
        for c in calls:
            self.assertNotIn("-k", c, f"fuser must not be called with -k: {c!r}")

    def test_offline_service_reports_no_pid_detected(self):
        result, calls = self._detail(online=False)
        self.assertFalse(result["online"])
        self.assertEqual("No detectado", result["pid"])
        self.assertEqual([], calls, "no fuser call expected when the port is closed")

    def test_backend_grouping(self):
        result, _ = self._detail(service="ms_sisper_sesion")
        self.assertEqual("Backend (Django / Daphne)", result["group"])

    def test_frontend_grouping(self):
        result, _ = self._detail(service="mf_sisper_sesion", port=3000)
        self.assertEqual("Frontend (Webpack Dev Server)", result["group"])

    def test_payload_contract(self):
        result, _ = self._detail()
        self.assertEqual(
            {"name", "port", "group", "online", "pid", "git", "path"},
            set(result.keys()),
        )
