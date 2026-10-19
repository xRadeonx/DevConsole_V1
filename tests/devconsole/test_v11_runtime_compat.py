from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
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

    def test_telemetry_has_complete_develop_shape_on_fresh_checkout(self):
        import devconsole.config as config
        from devconsole.services import telemetry_service

        config.KEYCLOAK_ENV_CONFIGS.pop("develop", None)
        config.DATABASE_ENV_CONFIGS.pop("develop", None)
        telemetry_service.KEYCLOAK_ENV_CONFIGS.pop("develop", None)
        telemetry_service.DATABASE_ENV_CONFIGS.pop("develop", None)

        compat._install_telemetry_defaults()

        kc = telemetry_service.KEYCLOAK_ENV_CONFIGS["develop"]
        db = telemetry_service.DATABASE_ENV_CONFIGS["develop"]
        self.assertEqual("DESARROLLO", kc["name"])
        self.assertIn("url", kc)
        self.assertIn("realm", kc)
        self.assertIn("client_id", kc)
        self.assertIn("client_secret", kc)
        self.assertIn("host", db)
        self.assertIn("bitacora_db", db)
        self.assertIn("contratos_db", db)
        self.assertIn("destinaciones_db", db)

    def test_workspace_envs_rebuild_telemetry_and_infra_targets(self):
        import devconsole.config as config

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixtures = {
                "ms_sisper_sesion": """
                    KEYCLOAK_SERVER_URL=https://keycloak.example.test/
                    KEYCLOAK_REALM=SISPER
                    KEYCLOAK_CLIENT_ID=sisper-client
                    KEYCLOAK_CLIENT_SECRET_KEY=secret-value
                    RABBITMQ_HOST=broker.example.test
                    RABBITMQ_PORT=5672
                """,
                "ms_sisper_bitacora": """
                    DATABASE_HOST=db.example.test
                    DATABASE_PORT=5432
                    DATABASE_NAME=ms_sisper_bitacora
                    DATABASE_USER=bitacora
                    DATABASE_PASSWORD=bit-pass
                """,
                "ms_sisper_contratos": """
                    DATABASE_HOST=db.example.test
                    DATABASE_NAME=ms_sisper_contratos
                    DATABASE_USER=contratos
                    DATABASE_PASSWORD=ctto-pass
                    ONLYOFFICE_DOCUMENTSERVER_URL=https://office.example.test
                """,
                "ms_sisper_destinaciones": """
                    DATABASE_HOST=db.example.test
                    DATABASE_NAME=ms_sisper_destinaciones
                    DATABASE_USER=destinaciones
                    DATABASE_PASSWORD=dest-pass
                """,
            }
            for service, text in fixtures.items():
                folder = root / "backend" / service
                folder.mkdir(parents=True)
                (folder / ".env").write_text(text, encoding="utf-8")

            with mock.patch.object(config, "BASE_DIR", root):
                kc, db, _ = compat._discover_workspace_integrations()
                targets = compat._discover_infra_targets()

            self.assertEqual("https://keycloak.example.test", kc["url"])
            self.assertEqual("SISPER", kc["realm"])
            self.assertEqual("db.example.test", db["host"])
            self.assertEqual("ms_sisper_bitacora", db["bitacora_db"])
            self.assertEqual("ms_sisper_contratos", db["contratos_db"])
            self.assertEqual("ms_sisper_destinaciones", db["destinaciones_db"])
            self.assertEqual("local", next(iter(targets)))
            self.assertTrue(any(x["id"] == "postgres" for x in targets["develop"]))
            self.assertTrue(any(x["id"] == "keycloak" for x in targets["develop"]))
            self.assertTrue(any(x["id"] == "rabbitmq" for x in targets["develop"]))
            self.assertTrue(any(x["id"] == "onlyoffice" for x in targets["develop"]))

    def test_public_auth_endpoint_is_reachable_from_viewer(self):
        from devconsole import security

        compat._install_public_auth_policy()
        ctx = security.CallerContext(
            role=security.Role.VIEWER,
            role_header=None,
            admin_session_valid=False,
            local_token_valid=True,
            local_token_required=False,
            origin="http://127.0.0.1:9099",
            origin_allowed=True,
            host_header="127.0.0.1:9099",
            host_allowed=True,
            client_ip="127.0.0.1",
        )
        decision = security.authorize_post("/api/auth/verify_pin", ctx, {"role": "dev"})
        self.assertTrue(decision.allowed)

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

    def test_tmux_is_v11_default_but_explicit_backend_is_respected(self):
        self.assertEqual("tmux", compat._preferred_terminal_backend(""))
        self.assertEqual("tilix", compat._preferred_terminal_backend("tilix"))
        self.assertEqual("tmux", compat._preferred_terminal_backend("tmux"))


if __name__ == "__main__":
    unittest.main()
