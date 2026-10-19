from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from devconsole import v11_yaml_catalog as yaml_catalog


class V11YamlCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="devconsole-yaml-catalog-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = self.root / "config"
        self.config.mkdir()

    def _write(self, relative: str, content: str) -> Path:
        path = self.config / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_scans_environment_specific_keycloak_and_database_values(self):
        self._write(
            "test/ms_sisper_contratos.yaml",
            """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ms-sisper-contratos
spec:
  template:
    spec:
      containers:
        - name: app
          env:
            - name: KEYCLOAK_HOST
              value: keycloak.test.local
            - name: KEYCLOAK_REALM
              value: SISPER
            - name: KEYCLOAK_CLIENT_ID
              value: ms-sisper
            - name: KEYCLOAK_CLIENT_SECRET_KEY
              value: test-kc-secret
            - name: DATABASE_HOST
              value: pg.test.local
            - name: DATABASE_PORT
              value: "5432"
            - name: DATABASE_NAME
              value: contratos_test
            - name: DATABASE_USER
              value: contratos_reader
            - name: DATABASE_PASSWORD
              value: contratos-secret
""",
        )

        with mock.patch.object(yaml_catalog, "_config_roots", return_value=[self.config]):
            scanned = yaml_catalog.scan_workspace_yaml(self.root)

        self.assertEqual("https://keycloak.test.local", scanned["keycloak"]["test"]["url"])
        self.assertEqual("SISPER", scanned["keycloak"]["test"]["realm"])
        self.assertEqual("ms-sisper", scanned["keycloak"]["test"]["client_id"])
        self.assertEqual("test-kc-secret", scanned["keycloak"]["test"]["client_secret"])
        db = scanned["databases"]["test"]
        self.assertEqual("pg.test.local", db["host"])
        self.assertEqual(5432, db["port"])
        self.assertEqual("contratos_test", db["contratos_db"])
        self.assertEqual("contratos_reader", db["contratos_user"])
        self.assertEqual("contratos-secret", db["contratos_pass"])

    def test_prod_path_is_normalized_to_main_and_not_mixed_with_develop(self):
        self._write(
            "develop/ms_sisper_bitacora.yaml",
            """
metadata:
  name: ms-sisper-bitacora
stringData:
  DATABASE_HOST: pg.dev.local
  DATABASE_NAME: bitacora_dev
  DATABASE_USER: dev_reader
  DATABASE_PASSWORD: dev-secret
""",
        )
        self._write(
            "prod/ms_sisper_bitacora.yaml",
            """
metadata:
  name: ms-sisper-bitacora
stringData:
  DATABASE_HOST: pg.main.local
  DATABASE_NAME: bitacora_main
  DATABASE_USER: main_reader
  DATABASE_PASSWORD: main-secret
""",
        )

        with mock.patch.object(yaml_catalog, "_config_roots", return_value=[self.config]):
            scanned = yaml_catalog.scan_workspace_yaml(self.root)

        self.assertEqual("pg.dev.local", scanned["databases"]["develop"]["host"])
        self.assertEqual("dev-secret", scanned["databases"]["develop"]["bitacora_pass"])
        self.assertEqual("pg.main.local", scanned["databases"]["main"]["host"])
        self.assertEqual("main-secret", scanned["databases"]["main"]["bitacora_pass"])

    def test_hydration_preserves_explicit_values_and_fills_missing_fields(self):
        fake_scan = {
            "keycloak": {
                "test": {
                    "url": "https://yaml.test.local",
                    "realm": "SISPER",
                    "client_id": "yaml-client",
                }
            },
            "databases": {
                "test": {
                    "host": "pg.test.local",
                    "port": 5432,
                    "contratos_db": "ctto",
                }
            },
            "secret_candidates": [],
            "files_scanned": 1,
        }
        kc = {"test": {"url": "https://explicit.test.local"}}
        db = {"test": {"host": "explicit-db.local"}}

        from devconsole import config

        with mock.patch.object(yaml_catalog, "scan_workspace_yaml", return_value=fake_scan), mock.patch.object(
            config, "KEYCLOAK_ENV_CONFIGS", kc
        ), mock.patch.object(config, "DATABASE_ENV_CONFIGS", db):
            changed = yaml_catalog.hydrate_environment_catalog(self.root)

        self.assertTrue(changed)
        self.assertEqual("https://explicit.test.local", kc["test"]["url"])
        self.assertEqual("SISPER", kc["test"]["realm"])
        self.assertEqual("yaml-client", kc["test"]["client_id"])
        self.assertEqual("explicit-db.local", db["test"]["host"])
        self.assertEqual(5432, db["test"]["port"])
        self.assertEqual("ctto", db["test"]["contratos_db"])

    def test_secret_merge_prefers_running_env_candidate_over_yaml_duplicate(self):
        original = [
            {
                "clave": "keycloak.test.client_secret",
                "valor": "env-secret",
                "pista": "en…et",
                "origen": "ms_sisper_sesion/.env",
            }
        ]
        yaml = [
            {
                "clave": "keycloak.test.client_secret",
                "valor": "yaml-secret",
                "pista": "ya…et",
                "origen": "config/test/deployment.yaml",
            },
            {
                "clave": "databases.test.bitacora_pass",
                "valor": "db-secret",
                "pista": "db…et",
                "origen": "config/test/bitacora.yaml",
            },
        ]
        required = {"keycloak.test.client_secret", "databases.test.bitacora_pass"}

        merged = yaml_catalog._merge_secret_candidates(original, yaml, required)

        self.assertEqual(2, len(merged))
        self.assertEqual("env-secret", merged[0]["valor"])
        self.assertEqual("db-secret", merged[1]["valor"])


if __name__ == "__main__":
    unittest.main()
