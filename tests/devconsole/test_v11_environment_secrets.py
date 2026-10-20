from __future__ import annotations

import unittest
from unittest import mock

from devconsole import config, settings
from devconsole import v11_environment_secrets as env_secrets


class EnvironmentSecretsTest(unittest.TestCase):
    def test_standard_secret_slots_cover_all_three_environments(self):
        keys = set(env_secrets._secret_keys())
        for env in ("develop", "test", "main"):
            self.assertIn(f"keycloak.{env}.client_secret", keys)
            self.assertIn(f"databases.{env}.bitacora_pass", keys)
            self.assertIn(f"databases.{env}.contratos_pass", keys)
            self.assertIn(f"databases.{env}.destinaciones_pass", keys)

    def test_overlay_fills_only_existing_catalog_entries(self):
        kc = {
            "develop": {"url": "https://dev.invalid", "client_secret": "already"},
            "test": {"url": "https://test.invalid"},
            "main": {},
        }
        db = {
            "test": {
                "host": "10.0.0.2",
                "bitacora_db": "bitacora",
                "bitacora_user": "reader",
            },
            "main": {},
        }
        values = {
            "keycloak.test.client_secret": "test-kc-local",
            "databases.test.bitacora_pass": "test-db-local",
            "keycloak.main.client_secret": "main-kc-local",
        }

        with mock.patch.object(config, "KEYCLOAK_ENV_CONFIGS", kc), mock.patch.object(
            config, "DATABASE_ENV_CONFIGS", db
        ), mock.patch.object(settings, "secret", side_effect=lambda key, default="": values.get(key, default)):
            changed = env_secrets.apply_secret_overlay()

        self.assertTrue(changed)
        self.assertEqual("already", kc["develop"]["client_secret"])
        self.assertEqual("test-kc-local", kc["test"]["client_secret"])
        self.assertEqual("test-db-local", db["test"]["bitacora_pass"])
        # A secret never fabricates a target catalog by itself.
        self.assertNotIn("client_secret", kc["main"])


if __name__ == "__main__":
    unittest.main()
