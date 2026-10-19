from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from devconsole.services import env_profile_service as eps


class EnvironmentProfileSafetyTest(unittest.TestCase):
    def _workspace(self, root: Path) -> tuple[Path, Path, Path]:
        backend = root / "backend" / "ms_sisper_sesion"
        frontend = root / "frontend" / "mf_sisper_sesion"
        views = backend / "core" / "ms_sesion" / "v1" / "views.py"
        backend.mkdir(parents=True)
        frontend.mkdir(parents=True)
        views.parent.mkdir(parents=True)
        (backend / ".env").write_text(
            "DATABASE_USER=old\n"
            "DATABASE_PASSWORD=real-secret\n"
            "DATABASE_HOST=10.0.0.2\n"
            "KEYCLOAK_SERVER_URL=https://old.example/\n",
            encoding="utf-8",
        )
        (frontend / ".env").write_text("MS_KEYCLOAK=\"https://old.example/\"\n", encoding="utf-8")
        views.write_text("prefix\n" + eps.BITACORA_ORIG + "\nsuffix\n", encoding="utf-8")
        return backend / ".env", frontend / ".env", views

    def test_local_switch_changes_env_only_and_preserves_secret(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            backend_env, frontend_env, views = self._workspace(root)
            original_source = views.read_text(encoding="utf-8")
            with mock.patch.object(eps.dcfg, "BASE_DIR", root):
                report = eps.apply_environment_profile("local", all_services=False)

            self.assertEqual("LOCAL", report["mode"])
            self.assertFalse(report["source_patch"])
            backend_text = backend_env.read_text(encoding="utf-8")
            self.assertIn("DATABASE_USER=postgres", backend_text)
            self.assertIn("DATABASE_PASSWORD=real-secret", backend_text)
            self.assertIn("DATABASE_HOST=127.0.0.1", backend_text)
            self.assertIn("localhost:8080", backend_text)
            self.assertIn("localhost:8080", frontend_env.read_text(encoding="utf-8"))
            self.assertEqual(original_source, views.read_text(encoding="utf-8"))

    def test_explicit_bitacora_action_preserves_legacy_capability(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _, _, views = self._workspace(root)
            with mock.patch.object(eps.dcfg, "BASE_DIR", root):
                ok, _ = eps.set_bitacora_patch("local")
                self.assertTrue(ok)
                self.assertIn(eps.BITACORA_PATCH, views.read_text(encoding="utf-8"))
                ok, _ = eps.set_bitacora_patch("intranet")
                self.assertTrue(ok)
                self.assertIn(eps.BITACORA_ORIG, views.read_text(encoding="utf-8"))

    def test_status_json_semantics_remain_compatible(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._workspace(root)
            with mock.patch.object(eps.dcfg, "BASE_DIR", root):
                eps.apply_environment_profile("local", all_services=False)
                status = eps.environment_status()
            self.assertEqual("LOCAL", status["env_mode"])
            self.assertIn("database_host", status)
            self.assertIn("keycloak_url", status)
            self.assertIn("bitacora_status", status)


if __name__ == "__main__":
    unittest.main()
