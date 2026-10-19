from __future__ import annotations

import unittest
from unittest import mock

from devconsole import v11_telemetry_compat as telemetry_compat


class V11TelemetryCompatTests(unittest.TestCase):
    def test_adds_safe_label_to_real_recovered_targets(self):
        mapping = {
            "test": {
                "url": "https://test.invalid",
                "realm": "SISPER",
                "client_id": "backend",
                "client_secret": "secret",
            },
            "main": {
                "url": "https://main.invalid",
                "realm": "SISPER",
                "client_id": "backend",
                "client_secret": "secret",
            },
        }

        changed = telemetry_compat._apply_to_map(mapping)

        self.assertTrue(changed)
        self.assertEqual("TEST", mapping["test"]["name"])
        self.assertEqual("MAIN", mapping["main"]["name"])

    def test_preserves_explicit_legacy_name(self):
        mapping = {
            "test": {
                "url": "https://test.invalid",
                "name": "Ambiente de Pruebas",
            }
        }

        changed = telemetry_compat._apply_to_map(mapping)

        self.assertFalse(changed)
        self.assertEqual("Ambiente de Pruebas", mapping["test"]["name"])

    def test_does_not_fabricate_environment_from_label_only(self):
        mapping = {"test": {}, "main": {"realm": "SISPER"}}

        changed = telemetry_compat._apply_to_map(mapping)

        self.assertFalse(changed)
        self.assertNotIn("name", mapping["test"])
        self.assertNotIn("name", mapping["main"])

    def test_apply_environment_labels_updates_config_without_exposing_values(self):
        import devconsole.config as config

        mapping = {
            "test": {
                "url": "https://test.invalid",
                "realm": "SISPER",
                "client_id": "backend",
                "client_secret": "do-not-render",
            }
        }
        with mock.patch.object(config, "KEYCLOAK_ENV_CONFIGS", mapping):
            changed = telemetry_compat.apply_environment_labels()

        self.assertTrue(changed)
        self.assertEqual("TEST", mapping["test"]["name"])


if __name__ == "__main__":
    unittest.main()
