from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest import mock

from devconsole import v11_runtime_compat as compat


class RuntimeCompatTest(unittest.TestCase):
    def test_infra_snapshot_is_safe_without_panel_catalog(self):
        fake = SimpleNamespace(
            INFRA_CONTAINERS={},
            is_port_open=lambda *args, **kwargs: False,
            _probe_host=lambda: "",
            sync_contracts_onlyoffice_env=lambda auto_fix=False: {
                "success": False,
                "synced": False,
                "updated": False,
                "message": "not configured",
            },
        )
        with mock.patch.object(compat, "_container_state", return_value="not_found"), mock.patch.object(
            compat, "_image_exists", return_value=False
        ):
            data = compat._fallback_infra_snapshot(fake)

        self.assertFalse(data["configured"])
        self.assertEqual(["keydb", "onlyoffice-local"], data["configuration_missing"])
        self.assertIn("keydb", data)
        self.assertIn("onlyoffice", data)
        self.assertIn("postgres_local", data)
        self.assertFalse(data["keydb"]["configured"])
        self.assertFalse(data["onlyoffice"]["configured"])

    def test_telemetry_has_safe_develop_fallback_on_fresh_checkout(self):
        import devconsole.config as config
        from devconsole.services import telemetry_service

        config.KEYCLOAK_ENV_CONFIGS.pop("develop", None)
        config.DATABASE_ENV_CONFIGS.pop("develop", None)
        telemetry_service.KEYCLOAK_ENV_CONFIGS.pop("develop", None)
        telemetry_service.DATABASE_ENV_CONFIGS.pop("develop", None)

        compat._install_telemetry_defaults()

        self.assertIn("develop", config.KEYCLOAK_ENV_CONFIGS)
        self.assertIn("develop", config.DATABASE_ENV_CONFIGS)
        self.assertIn("develop", telemetry_service.KEYCLOAK_ENV_CONFIGS)
        self.assertIn("develop", telemetry_service.DATABASE_ENV_CONFIGS)

    def test_tilix_inherits_optional_tmux_capabilities_safely(self):
        from devconsole.services.terminal.base import TerminalBackend
        from devconsole.services.terminal.tilix_backend import TilixBackend

        compat._install_terminal_optional_capabilities()
        self.assertTrue(hasattr(TerminalBackend, "managed_sessions"))
        self.assertTrue(hasattr(TerminalBackend, "attach_viewers"))

        backend = TilixBackend()
        self.assertEqual([], backend.managed_sessions())
        ok, message = backend.attach_viewers([], title="test")
        self.assertFalse(ok)
        self.assertTrue(message)


if __name__ == "__main__":
    unittest.main()
