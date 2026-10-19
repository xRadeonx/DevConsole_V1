from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from devconsole import v11_multienv


class V11MultiEnvironmentTests(unittest.TestCase):
    def test_missing_test_never_calls_develop_fallback(self):
        original = mock.Mock(return_value={"env": "develop", "marker": "WRONG"})
        wrapped = v11_multienv._wrap_env_function(
            original,
            capability="de Mapa Operativo",
            validator=lambda env: env == "develop",
        )

        result = wrapped(env_key="test", force_refresh=True)

        original.assert_not_called()
        self.assertFalse(result["success"])
        self.assertEqual("test", result["requested_env"])
        self.assertTrue(result["configuration_missing"])
        self.assertEqual([], result["zones"])

    def test_main_is_forwarded_as_main_when_configured(self):
        original = mock.Mock(return_value={"env": "main", "items": [1]})
        wrapped = v11_multienv._wrap_env_function(
            original,
            capability="de Actividad",
            validator=lambda env: env == "main",
        )

        result = wrapped(env_key="main", limit=50)

        original.assert_called_once_with(env_key="main", limit=50)
        self.assertEqual("main", result["effective_env"])
        self.assertEqual([1], result["items"])

    def test_prod_alias_is_normalised_to_main(self):
        original = mock.Mock(return_value={})
        wrapped = v11_multienv._wrap_env_function(
            original,
            capability="de Actividad",
            validator=lambda env: env == "main",
        )

        wrapped("prod", 25)

        original.assert_called_once_with("main", 25)

    def test_environment_status_contains_no_connection_values(self):
        import devconsole.config as config

        keycloak = {
            "develop": {"url": "https://dev.invalid", "client_secret": "secret-dev"},
            "test": {"url": "https://test.invalid", "client_secret": "secret-test"},
            "main": {"url": "https://main.invalid", "client_secret": "secret-main"},
        }
        databases = {
            "develop": {"host": "10.0.0.1", "bitacora_db": "db", "bitacora_pass": "pw1"},
            "test": {"host": "10.0.0.2", "bitacora_db": "db", "bitacora_pass": "pw2"},
            "main": {"host": "10.0.0.3", "bitacora_db": "db", "bitacora_pass": "pw3"},
        }

        with mock.patch.object(config, "KEYCLOAK_ENV_CONFIGS", keycloak), mock.patch.object(
            config, "DATABASE_ENV_CONFIGS", databases
        ), mock.patch("devconsole.v11_multienv._refresh_local_catalog"):
            status = v11_multienv.environment_status()

        self.assertEqual(["develop", "test", "main"], status["available"])
        rendered = repr(status)
        self.assertNotIn("secret-", rendered)
        self.assertNotIn("10.0.0.", rendered)
        self.assertNotIn("pw1", rendered)

    def test_map_candidates_use_workspace_then_bundled_fallback(self):
        import devconsole.config as config

        class Handlers:
            DASHBOARD_DIR = Path("/opt/devconsole")

        with mock.patch.object(config, "BASE_DIR", Path("/srv/sisper")):
            candidates = v11_multienv._map_candidates(Handlers)

        self.assertEqual(Path("/srv/sisper/config/chile_naval_map.svg"), candidates[0])
        self.assertEqual(
            Path("/opt/devconsole/static/assets/chile_naval_map_v11.svg"), candidates[1]
        )

    def test_bundled_map_exists_in_repository(self):
        repo_root = Path(__file__).resolve().parents[2]
        svg = repo_root / "static" / "assets" / "chile_naval_map_v11.svg"
        self.assertTrue(svg.is_file())
        text = svg.read_text(encoding="utf-8")
        for zone in range(1, 6):
            self.assertIn(f"zone-path-{zone}", text)
            self.assertIn(f"svg-conn-label-{zone}", text)


if __name__ == "__main__":
    unittest.main()
