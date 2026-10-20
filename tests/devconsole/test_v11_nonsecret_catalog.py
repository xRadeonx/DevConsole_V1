from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from devconsole import v11_db_name_recovery as db_name_recovery
from devconsole import v11_k8s_configmaps as configmaps
from devconsole import v11_local_env_catalog as local_catalog
from devconsole import v11_yaml_catalog as yaml_catalog


class V11LocalEnvCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="devconsole-local-catalog-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "backend").mkdir()

    def _service(self, name: str, content: str) -> None:
        service = self.root / "backend" / name
        service.mkdir(parents=True)
        (service / ".env").write_text(content, encoding="utf-8")

    def test_recovers_develop_keycloak_and_database_metadata_without_secrets(self):
        self._service(
            "ms_sisper_sesion",
            """
KEYCLOAK_HOST=keycloak.dev.local
KEYCLOAK_REALM=SISPER
KEYCLOAK_CLIENT_ID=ms-sisper
KEYCLOAK_CLIENT_SECRET=must-not-be-promoted
""",
        )
        self._service(
            "ms_sisper_contratos",
            """
DATABASE_HOST=pg.dev.local
DATABASE_PORT=5432
DATABASE_NAME=contratos_dev
DATABASE_USER=contratos_reader
DATABASE_PASSWORD=must-not-be-promoted
""",
        )

        scanned = local_catalog.scan_local_develop(self.root)

        self.assertEqual("https://keycloak.dev.local", scanned["keycloak"]["url"])
        self.assertEqual("SISPER", scanned["keycloak"]["realm"])
        self.assertEqual("ms-sisper", scanned["keycloak"]["client_id"])
        self.assertNotIn("client_secret", scanned["keycloak"])
        self.assertEqual("pg.dev.local", scanned["database"]["host"])
        self.assertEqual(5432, scanned["database"]["port"])
        self.assertEqual("contratos_dev", scanned["database"]["contratos_db"])
        self.assertEqual("contratos_reader", scanned["database"]["contratos_user"])
        self.assertNotIn("contratos_pass", scanned["database"])


class V11K8sConfigMapCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="devconsole-configmap-catalog-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = self.root / "config"
        self.config.mkdir()

    def _write(self, relative: str, content: str) -> Path:
        path = self.config / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def _augment(self) -> dict:
        with mock.patch.object(yaml_catalog, "_config_roots", return_value=[self.config]):
            return configmaps._augment_scan(
                {
                    "keycloak": {},
                    "databases": {},
                    "secret_candidates": [],
                    "files_scanned": 0,
                    "classified_files": {"develop": 0, "test": 0, "main": 0, "unknown": 0},
                },
                self.root,
            )

    def test_direct_configmaps_fill_test_keycloak_and_main_database_metadata(self):
        self._write(
            "test/keycloak-config.yaml",
            """
apiVersion: v1
kind: ConfigMap
metadata:
  name: keycloak-client-config
data:
  KEYCLOAK_HOST: keycloak.test.local
  KEYCLOAK_REALM: SISPER
  KEYCLOAK_CLIENT_ID: ms-sisper
  KEYCLOAK_CLIENT_SECRET: must-not-be-promoted
""",
        )
        self._write(
            "prod/ms_sisper_contratos-config.yaml",
            """
apiVersion: v1
kind: ConfigMap
metadata:
  name: contratos-db-config
data:
  HOST: pg.main.local
  PORT: "5432"
  DB: contratos_main
  USER: contratos_reader
  PASSWORD: must-not-be-promoted
""",
        )

        result = self._augment()

        self.assertEqual("https://keycloak.test.local", result["keycloak"]["test"]["url"])
        self.assertEqual("SISPER", result["keycloak"]["test"]["realm"])
        self.assertEqual("ms-sisper", result["keycloak"]["test"]["client_id"])
        self.assertNotIn("client_secret", result["keycloak"]["test"])
        db = result["databases"]["main"]
        self.assertEqual("pg.main.local", db["host"])
        self.assertEqual(5432, db["port"])
        self.assertEqual("contratos_main", db["contratos_db"])
        self.assertEqual("contratos_reader", db["contratos_user"])
        self.assertNotIn("contratos_pass", db)

    def test_configmap_key_ref_resolves_generic_keys_for_test(self):
        self._write(
            "shared/keycloak.yaml",
            """
apiVersion: v1
kind: ConfigMap
metadata:
  name: shared-keycloak
data:
  host: keycloak.test.local
  realm: SISPER
  clientId: ms-sisper
""",
        )
        self._write(
            "test/ms_sisper_sesion.yaml",
            """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ms-sisper-sesion
spec:
  template:
    spec:
      containers:
        - name: app
          env:
            - name: KEYCLOAK_HOST
              valueFrom:
                configMapKeyRef:
                  name: shared-keycloak
                  key: host
            - name: KEYCLOAK_REALM
              valueFrom:
                configMapKeyRef:
                  name: shared-keycloak
                  key: realm
            - name: KEYCLOAK_CLIENT_ID
              valueFrom:
                configMapKeyRef:
                  name: shared-keycloak
                  key: clientId
""",
        )

        result = self._augment()

        self.assertEqual("https://keycloak.test.local", result["keycloak"]["test"]["url"])
        self.assertEqual("SISPER", result["keycloak"]["test"]["realm"])
        self.assertEqual("ms-sisper", result["keycloak"]["test"]["client_id"])

    def test_envfrom_configmap_ref_resolves_database_metadata_for_main(self):
        self._write(
            "prod/contratos-config.yaml",
            """
apiVersion: v1
kind: ConfigMap
metadata:
  name: contratos-config
data:
  DATABASE_HOST: pg.main.local
  DATABASE_PORT: "5432"
  DATABASE_NAME: contratos_main
  DATABASE_USER: contratos_reader
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
          envFrom:
            - configMapRef:
                name: contratos-config
""",
        )

        result = self._augment()
        db = result["databases"]["main"]

        self.assertEqual("pg.main.local", db["host"])
        self.assertEqual(5432, db["port"])
        self.assertEqual("contratos_main", db["contratos_db"])
        self.assertEqual("contratos_reader", db["contratos_user"])


class V11DatabaseNameRecoveryTests(unittest.TestCase):
    def test_postgresql_url_extracts_database_name_only(self):
        self.assertEqual(
            "contracts_test",
            db_name_recovery._database_from_url(
                "postgresql://app:secret@db.example.invalid:5432/contracts_test?sslmode=require"
            ),
        )
        self.assertEqual("", db_name_recovery._database_from_url("https://example.invalid/db"))

    def test_service_account_inference_is_deliberately_narrow(self):
        self.assertEqual(
            "db_ms_example_contratos",
            db_name_recovery._infer_from_service_user("contratos", "ms_example_contratos"),
        )
        self.assertEqual(
            "db_ms_example_destinaciones",
            db_name_recovery._infer_from_service_user("destinaciones", "ms_example_destinaciones"),
        )
        self.assertEqual("", db_name_recovery._infer_from_service_user("contratos", "reader"))
        self.assertEqual("", db_name_recovery._infer_from_service_user("contratos", "ms_example_otro"))

    def test_recovery_fills_only_missing_names_and_never_crosses_logical_service(self):
        target = {
            "host": "db.example.invalid",
            "port": 5432,
            "contratos_user": "ms_example_contratos",
            "contratos_pass": "secret-a",
            "destinaciones_user": "ms_example_destinaciones",
            "destinaciones_pass": "secret-b",
        }

        changed = db_name_recovery._merge_names(target, {})

        self.assertTrue(changed)
        self.assertEqual("db_ms_example_contratos", target["contratos_db"])
        self.assertEqual("db_ms_example_destinaciones", target["destinaciones_db"])

        explicit = {"contratos": "explicit_contracts"}
        target2 = {
            "contratos_user": "ms_example_contratos",
            "destinaciones_user": "reader",
        }
        db_name_recovery._merge_names(target2, explicit)
        self.assertEqual("explicit_contracts", target2["contratos_db"])
        self.assertNotIn("destinaciones_db", target2)


if __name__ == "__main__":
    unittest.main()
