from __future__ import annotations

import unittest
from unittest import mock

from devconsole import config
from devconsole import v11_infra_catalog as infra


class InfraCatalogTest(unittest.TestCase):
    def test_merge_rows_preserves_explicit_and_adds_missing_components(self):
        explicit = [{"id": "postgres", "target": "explicit-db:5432"}]
        fallback = [
            {"id": "postgres", "target": "legacy-db:5432"},
            {"id": "keycloak", "target": "legacy-keycloak"},
        ]
        merged = infra._merge_rows(explicit, fallback)
        self.assertEqual("explicit-db:5432", merged[0]["target"])
        self.assertEqual(["postgres", "keycloak"], [row["id"] for row in merged])

    def test_synthesis_uses_non_secret_environment_targets(self):
        kc = {
            "develop": {"url": "https://dev.invalid", "client_secret": "secret-not-returned"},
            "test": {"url": "https://test.invalid", "client_secret": "another-secret"},
            "main": {},
        }
        db = {
            "develop": {"host": "10.0.0.1", "port": 5432, "bitacora_pass": "hidden"},
            "test": {"host": "10.0.0.2", "port": 5433, "bitacora_pass": "hidden-too"},
            "main": {},
        }
        with mock.patch.object(config, "KEYCLOAK_ENV_CONFIGS", kc), mock.patch.object(
            config, "DATABASE_ENV_CONFIGS", db
        ):
            targets = infra._synthesized_targets()

        self.assertEqual({"develop", "test"}, set(targets))
        rendered = repr(targets)
        self.assertNotIn("secret-not-returned", rendered)
        self.assertNotIn("another-secret", rendered)
        self.assertNotIn("hidden-too", rendered)
        self.assertEqual("10.0.0.2:5433", targets["test"][0]["target"])

    def test_partial_current_catalog_does_not_block_other_environments(self):
        current = {"develop": [{"id": "custom", "target": "explicit-dev"}]}
        legacy = {
            "test": [{"id": "postgres", "target": "legacy-test"}],
            "main": [{"id": "postgres", "target": "legacy-main"}],
        }
        with mock.patch(
            "devconsole.v11_legacy_profile._read_legacy_infra_targets", return_value=legacy
        ), mock.patch(
            "devconsole.v11_legacy_profile.hydrate_environment_catalog", return_value=False
        ), mock.patch.object(infra, "_synthesized_targets", return_value={}):
            composed = infra.compose_targets(current)

        self.assertEqual("explicit-dev", composed["develop"][0]["target"])
        self.assertEqual("legacy-test", composed["test"][0]["target"])
        self.assertEqual("legacy-main", composed["main"][0]["target"])


if __name__ == "__main__":
    unittest.main()
