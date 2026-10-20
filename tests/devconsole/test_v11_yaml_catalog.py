from __future__ import annotations

import base64
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from devconsole import v11_k8s_secrets as k8s_secrets
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

    def test_absolute_parent_named_develop_does_not_contaminate_test_or_main(self):
        workspace = self.root / "Develop" / "PROTEO"
        config = workspace / "config"
        test_file = config / "test" / "ms_sisper_bitacora.yaml"
        main_file = config / "prod" / "ms_sisper_bitacora.yaml"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        main_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text(
            """
metadata:
  name: ms-sisper-bitacora
stringData:
  DATABASE_HOST: pg.test.local
  DATABASE_PASSWORD: test-secret
""",
            encoding="utf-8",
        )
        main_file.write_text(
            """
metadata:
  name: ms-sisper-bitacora
stringData:
  DATABASE_HOST: pg.main.local
  DATABASE_PASSWORD: main-secret
""",
            encoding="utf-8",
        )

        with mock.patch.object(yaml_catalog, "_config_roots", return_value=[config]):
            scanned = yaml_catalog.scan_workspace_yaml(workspace)

        self.assertNotIn("develop", scanned["databases"])
        self.assertEqual("test-secret", scanned["databases"]["test"]["bitacora_pass"])
        self.assertEqual("main-secret", scanned["databases"]["main"]["bitacora_pass"])
        self.assertEqual(1, scanned["classified_files"]["test"])
        self.assertEqual(1, scanned["classified_files"]["main"])

    def test_embedded_namespace_environment_names_are_normalized(self):
        self.assertEqual("test", yaml_catalog._normalise_env("sisper-test"))
        self.assertEqual("main", yaml_catalog._normalise_env("proteo-production"))
        self.assertEqual("develop", yaml_catalog._normalise_env("dgpa-development"))
        self.assertIsNone(yaml_catalog._normalise_env("sisper"))

        path = self._write(
            "generic/keycloak.yaml",
            """
metadata:
  namespace: sisper-test
  name: keycloak-config
stringData:
  KEYCLOAK_HOST: keycloak.test.local
  KEYCLOAK_CLIENT_SECRET: namespace-secret
""",
        )
        with mock.patch.object(yaml_catalog, "_config_roots", return_value=[self.config]):
            self.assertEqual("test", yaml_catalog._detect_environment(path, path.read_text(), self.root))

    def test_kubernetes_secret_data_is_base64_decoded_before_becoming_credential(self):
        encoded = base64.b64encode(b"test-db-password").decode("ascii")
        self._write(
            "test/ms_sisper_contratos-secret.yaml",
            f"""
apiVersion: v1
kind: Secret
metadata:
  name: ms-sisper-contratos-secret
data:
  DATABASE_PASSWORD: {encoded}
""",
        )

        with mock.patch.object(yaml_catalog, "_config_roots", return_value=[self.config]):
            result = k8s_secrets._augment_scan(
                {"keycloak": {}, "databases": {}, "secret_candidates": []},
                self.root,
            )

        self.assertEqual("test-db-password", result["databases"]["test"]["contratos_pass"])
        candidate = next(
            item
            for item in result["secret_candidates"]
            if item["clave"] == "databases.test.contratos_pass"
        )
        self.assertEqual("test-db-password", candidate["valor"])
        self.assertEqual("k8s-secret-data-b64", candidate["fuente"])
        self.assertNotEqual(encoded, candidate["valor"])

    def test_secretkeyref_resolves_generic_base64_key_for_main(self):
        encoded = base64.b64encode(b"main-contratos-password").decode("ascii")
        self._write(
            "prod/contratos-db-secret.yaml",
            f"""
apiVersion: v1
kind: Secret
metadata:
  name: contratos-db
data:
  password: {encoded}
""",
        )
        self._write(
            "prod/ms_sisper_contratos.yaml",
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
            - name: DATABASE_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: contratos-db
                  key: password
""",
        )

        with mock.patch.object(yaml_catalog, "_config_roots", return_value=[self.config]):
            result = k8s_secrets._augment_scan(
                {"keycloak": {}, "databases": {}, "secret_candidates": []},
                self.root,
            )

        self.assertEqual(
            "main-contratos-password",
            result["databases"]["main"]["contratos_pass"],
        )
        candidate = next(
            item
            for item in result["secret_candidates"]
            if item["clave"] == "databases.main.contratos_pass"
        )
        self.assertEqual("k8s-secretKeyRef", candidate["fuente"])
        self.assertIn("contratos-db-secret.yaml", candidate["origen"])
        self.assertIn("ms_sisper_contratos.yaml", candidate["origen"])

    def test_kubernetes_secret_stringdata_stays_plain_text(self):
        self._write(
            "test/ms_sisper_bitacora-secret.yaml",
            """
apiVersion: v1
kind: Secret
metadata:
  name: ms-sisper-bitacora-secret
stringData:
  DATABASE_PASSWORD: already-plain
""",
        )

        with mock.patch.object(yaml_catalog, "_config_roots", return_value=[self.config]):
            result = k8s_secrets._augment_scan(
                {"keycloak": {}, "databases": {}, "secret_candidates": []},
                self.root,
            )

        self.assertEqual("already-plain", result["databases"]["test"]["bitacora_pass"])
        candidate = next(
            item
            for item in result["secret_candidates"]
            if item["clave"] == "databases.test.bitacora_pass"
        )
        self.assertEqual("k8s-secret-stringData", candidate["fuente"])

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
            "classified_files": {"develop": 0, "test": 1, "main": 0, "unknown": 0},
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

    def test_secret_merge_keeps_one_value_per_environment_key(self):
        original = [
            {
                "clave": "keycloak.develop.client_secret",
                "valor": "env-secret",
                "pista": "en…et",
                "origen": "ms_sisper_sesion/.env",
            }
        ]
        yaml = [
            {
                "clave": "keycloak.develop.client_secret",
                "valor": "yaml-secret",
                "pista": "ya…et",
                "origen": "config/develop/deployment.yaml",
            },
            {
                "clave": "databases.test.bitacora_pass",
                "valor": "db-secret",
                "pista": "db…et",
                "origen": "config/test/bitacora.yaml",
            },
        ]
        required = {"keycloak.develop.client_secret", "databases.test.bitacora_pass"}

        merged = yaml_catalog._merge_secret_candidates(original, yaml, required)

        self.assertEqual(2, len(merged))
        self.assertEqual("env-secret", merged[0]["valor"])
        self.assertEqual("db-secret", merged[1]["valor"])


if __name__ == "__main__":
    unittest.main()
