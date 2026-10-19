from __future__ import annotations

import json
import os
import ssl
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from devconsole import auth, auth_v11
from devconsole.config_models import validate_panel_config, validate_service_catalog
from devconsole.services.build_jobs import BuildJobStore
from devconsole.services.environment_transaction import switch_workspace_environment_transactional
from devconsole.services.git_safety import checkout_service_branch_safe
from devconsole.services.git_worktree import temporary_worktree
from devconsole.services.k8s_guard import KubectlResult, preflight
from devconsole.services.manifest_service import preview_image_tag_update
from devconsole.services.project_detector import detect_project, detect_workspace
from devconsole.services.runtime.process_inspector import ProcessInspector
from devconsole.services.runtime.psutil_inspector import create_process_inspector
from devconsole.services.telemetry_tls_adapter import HardenedContext, install_telemetry_tls_policy
from devconsole.services.terminal.capabilities import terminal_capabilities


class TypedConfigurationTest(unittest.TestCase):
    def test_valid_legacy_shape_is_accepted_without_rewriting(self):
        panel = {"project_name": "Demo", "registry": "registry.local", "unknown_v1_key": {"keep": True}}
        report = validate_panel_config(panel)
        self.assertTrue(report.valid, report.errors)
        self.assertEqual("Demo", panel["project_name"])
        self.assertIn("unknown_v1_key", panel)

    def test_duplicate_service_and_port_are_reported(self):
        report = validate_service_catalog([
            {"name": "api", "port": 8000},
            {"name": "api", "port": 8001},
            {"name": "other", "port": 8000},
        ])
        self.assertFalse(report.valid)
        joined = " ".join(report.errors)
        self.assertIn("duplicado", joined)
        self.assertIn("8000", joined)


class ProjectDetectorTest(unittest.TestCase):
    def test_detects_django_celery_and_build_capabilities(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ms_demo"
            root.mkdir()
            (root / "manage.py").write_text("# django\n", encoding="utf-8")
            (root / "Pipfile").write_text('django = "*"\ndjangorestframework = "*"\ncelery = "*"\n', encoding="utf-8")
            (root / "Dockerfile").write_text("FROM python:3.11\n", encoding="utf-8")
            profile = detect_project(root)
            self.assertIsNotNone(profile)
            assert profile is not None
            self.assertEqual("backend", profile.kind)
            self.assertIn("django", profile.frameworks)
            self.assertIn("drf", profile.frameworks)
            self.assertIn("celery", profile.frameworks)
            self.assertIn("migrate", profile.capabilities)
            self.assertIn("worker", profile.capabilities)
            self.assertIn("build", profile.capabilities)
            self.assertEqual("pipenv", profile.package_manager)

    def test_workspace_detects_react_without_sisper_name_prefix(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            app = root / "frontend" / "customer-portal"
            app.mkdir(parents=True)
            (app / "package.json").write_text(json.dumps({"dependencies": {"react": "^19.0.0"}}), encoding="utf-8")
            (app / "package-lock.json").write_text("{}", encoding="utf-8")
            profiles = detect_workspace(root)
            self.assertEqual(1, len(profiles))
            self.assertEqual("customer-portal", profiles[0].name)
            self.assertIn("react", profiles[0].frameworks)
            self.assertEqual("npm", profiles[0].package_manager)


class ManifestRoundTripTest(unittest.TestCase):
    def test_image_update_keeps_comments_and_unrelated_fields(self):
        source = """# deployment comment\napiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: demo\nspec:\n  template:\n    spec:\n      containers:\n        - name: api\n          image: registry.local/demo:1.0.0 # keep image comment\n          env:\n            - name: MODE\n              value: \"develop\"\n        - name: proxy\n          image: nginx:1.27\n"""
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "deployment.yaml"
            path.write_text(source, encoding="utf-8")
            change = preview_image_tag_update(path, "1.1.0")
            self.assertTrue(change.changed)
            self.assertIn("registry.local/demo:1.1.0", change.after)
            self.assertIn("nginx:1.27", change.after)
            self.assertIn("# deployment comment", change.after)
            self.assertIn("# keep image comment", change.after)
            self.assertIn('value: "develop"', change.after)
            self.assertEqual(source, path.read_text(encoding="utf-8"), "preview must be read-only")


class ProcessInspectorFactoryTest(unittest.TestCase):
    def test_synthetic_proc_root_always_uses_legacy_inspector(self):
        with tempfile.TemporaryDirectory() as td:
            inspector = create_process_inspector(proc_root=td)
            self.assertIs(type(inspector), ProcessInspector)

    def test_procfs_mode_forces_legacy_backend(self):
        with mock.patch.dict(os.environ, {"SISPER_PROCESS_INSPECTOR": "procfs"}):
            inspector = create_process_inspector()
            self.assertIs(type(inspector), ProcessInspector)


class CredentialSecurityTest(unittest.TestCase):
    def test_developer_pin_creates_real_session_credential(self):
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.dict(os.environ, {"SISPER_DEV_SESSIONS_FILE": str(Path(td) / "dev.json")}), \
             mock.patch("devconsole.auth_v11.pins.verify", return_value=True):
            ok, token = auth_v11.verify_dev_pin("product-key")
            self.assertTrue(ok)
            self.assertTrue(token)
            self.assertTrue(auth_v11.is_valid_dev_token(token))
            self.assertEqual("dev", auth_v11.effective_role({"X-Dev-Auth-Token": token}))
            self.assertTrue(auth_v11.invalidate_dev_token(token))
            self.assertFalse(auth_v11.is_valid_dev_token(token))

    def test_implicit_historical_admin_pin_cannot_authorize(self):
        with mock.patch("devconsole.pins.estado", return_value={"admin": "PIN heredado por defecto (¡configúralo!)", "dev": "sin configurar"}), \
             mock.patch("devconsole.pins.verify", return_value=True):
            ok, token = auth.verify_pin("sisper2026", "admin")
        self.assertFalse(ok)
        self.assertEqual("", token)

    def test_configured_product_hash_remains_supported(self):
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.dict(os.environ, {"SISPER_ADMIN_SESSIONS_FILE": str(Path(td) / "admin.json")}), \
             mock.patch("devconsole.pins.estado", return_value={"admin": "scrypt en product-store", "dev": "scrypt en product-store"}), \
             mock.patch("devconsole.pins.verify", return_value=True):
            ok, token = auth.verify_pin("approved-product-key", "admin")
        self.assertTrue(ok)
        self.assertTrue(token)


class TLSSecurityTest(unittest.TestCase):
    def test_legacy_telemetry_cannot_downgrade_verified_context(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SISPER_ALLOW_INSECURE_KEYCLOAK_TLS", None)
            diagnostic = install_telemetry_tls_policy()
            from devconsole.services import telemetry_service
            context = telemetry_service.ssl.create_default_context()
            self.assertIsInstance(context, HardenedContext)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            self.assertTrue(context.check_hostname)
            self.assertEqual(ssl.CERT_REQUIRED, context.verify_mode)
            self.assertTrue(diagnostic["verify"])

    def test_insecure_tls_requires_explicit_opt_in(self):
        from devconsole.services.tls_policy import keycloak_tls_policy
        with mock.patch.dict(os.environ, {"SISPER_ALLOW_INSECURE_KEYCLOAK_TLS": "1"}):
            self.assertTrue(keycloak_tls_policy().insecure)


class WorktreeSafetyTest(unittest.TestCase):
    def _git(self, root: Path, *args: str) -> None:
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)

    def test_temporary_worktree_does_not_touch_dirty_active_workspace(self):
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": str(Path(td) / "runtime")}):
            repo = Path(td) / "repo"
            repo.mkdir()
            self._git(repo, "init")
            self._git(repo, "config", "user.email", "ci@example.invalid")
            self._git(repo, "config", "user.name", "CI")
            tracked = repo / "tracked.txt"
            tracked.write_text("committed\n", encoding="utf-8")
            self._git(repo, "add", "tracked.txt")
            self._git(repo, "commit", "-m", "initial")
            tracked.write_text("dirty local change\n", encoding="utf-8")
            with temporary_worktree(repo, "HEAD") as worktree:
                self.assertEqual("committed\n", (worktree / "tracked.txt").read_text(encoding="utf-8"))
                (worktree / "generated.txt").write_text("build artifact", encoding="utf-8")
            self.assertEqual("dirty local change\n", tracked.read_text(encoding="utf-8"))
            self.assertFalse((repo / "generated.txt").exists())


class GitSafetyTest(unittest.TestCase):
    def test_index_lock_is_reported_and_never_deleted(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()
            subprocess.run(["git", "-C", str(repo), "init"], check=True, capture_output=True)
            lock = repo / ".git" / "index.lock"
            lock.write_text("owned-by-git", encoding="utf-8")
            with mock.patch("devconsole.services.git_safety.get_service_repo_dir", return_value=repo):
                ok, message = checkout_service_branch_safe("api", "main")
            self.assertFalse(ok)
            self.assertTrue(lock.exists())
            self.assertIn("no elimina", message)


class EnvironmentTransactionTest(unittest.TestCase):
    def test_failed_second_checkout_rolls_back_first(self):
        fake_success = subprocess.CompletedProcess(["git"], 0, "", "")
        fake_failure = subprocess.CompletedProcess(["git"], 1, "", "boom")
        state_a = mock.Mock(name="state-a")
        state_b = mock.Mock(name="state-b")
        with mock.patch("devconsole.services.environment_transaction._repo_state", side_effect=[
            (state_a, {"name": "a", "status": "ready", "message": "ok"}),
            (state_b, {"name": "b", "status": "ready", "message": "ok"}),
        ]), mock.patch("devconsole.services.environment_transaction._checkout", side_effect=[fake_success, fake_failure]), \
             mock.patch("devconsole.services.environment_transaction._rollback", return_value=(True, "Restaurado")) as rollback, \
             mock.patch("devconsole.services.environment_transaction.dcfg.get_service_repo_dir", side_effect=lambda name: Path("/") / name):
            result = switch_workspace_environment_transactional("test", services=[{"name": "a"}, {"name": "b"}])
        self.assertEqual("rolled_back", result["transaction"])
        rollback.assert_called_once_with(state_a)


class BuildPersistenceTest(unittest.TestCase):
    def test_running_job_recovers_as_interrupted(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "jobs.json"
            path.write_text(json.dumps([{
                "id": "abc", "service": "api", "image": "api:1", "ref": "HEAD", "push": False,
                "status": "running", "created_at": 1.0, "started_at": 2.0,
                "finished_at": None, "returncode": None, "message": "", "logs": []
            }]), encoding="utf-8")
            store = BuildJobStore(path)
            job = store.get("abc")
            self.assertIsNotNone(job)
            assert job is not None
            self.assertEqual("interrupted", job.status)
            self.assertIsNotNone(job.finished_at)


class KubernetesGuardTest(unittest.TestCase):
    def test_preflight_detects_context_mismatch(self):
        def fake_run(args, timeout=30):
            if args[:2] == ["config", "current-context"]:
                return KubectlResult(True, tuple(args), stdout="cluster-a")
            return KubectlResult(True, tuple(args), stdout="namespace/develop")
        with mock.patch("devconsole.services.k8s_guard._run", side_effect=fake_run):
            result = preflight("develop", "cluster-b")
        self.assertFalse(result["ok"])
        self.assertIn("cluster-a", " ".join(result["errors"]))


class TerminalCapabilitiesTest(unittest.TestCase):
    def test_reports_self_hosted_xterm_and_addons(self):
        with tempfile.TemporaryDirectory() as td:
            static = Path(td)
            (static / "js").mkdir()
            (static / "vendor" / "terminal-lab").mkdir(parents=True)
            (static / "js" / "xterm.js").write_text("", encoding="utf-8")
            (static / "vendor" / "terminal-lab" / "addon-fit.js").write_text("", encoding="utf-8")
            (static / "vendor" / "terminal-lab" / "addon-search.js").write_text("", encoding="utf-8")
            caps = terminal_capabilities(static)
            self.assertTrue(caps["xterm"])
            self.assertTrue(caps["addons"]["fit"])
            self.assertTrue(caps["addons"]["search"])
            self.assertEqual("tmux", caps["session_owner"])


class CompatibilityFacadeTest(unittest.TestCase):
    def test_v11_handler_is_a_legacy_handler_subclass(self):
        from devconsole.api.handlers import DevConsoleHandler as Legacy
        from devconsole.api.v11_handler import DevConsoleV11Handler
        self.assertTrue(issubclass(DevConsoleV11Handler, Legacy))

    def test_role_matrix_requires_real_privilege_for_sensitive_operations(self):
        from devconsole.api.v11_handler import required_role_for
        self.assertEqual("viewer", required_role_for("/api/telemetry/heartbeat", {}))
        self.assertEqual("dev", required_role_for("/api/env/save", {}))
        self.assertEqual("admin", required_role_for("/api/environment/switch", {}))
        self.assertEqual("admin", required_role_for("/api/secrets/guardar", {}))
        self.assertEqual("dev", required_role_for("/api/v1.1/build/start", {"push": False}))
        self.assertEqual("admin", required_role_for("/api/v1.1/build/start", {"push": True}))


if __name__ == "__main__":
    unittest.main()
