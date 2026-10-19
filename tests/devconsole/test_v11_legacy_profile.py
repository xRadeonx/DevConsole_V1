from __future__ import annotations

import base64
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from devconsole import v11_legacy_profile as legacy


class LegacyProfileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "devconsole").mkdir(parents=True)
        (self.root / "static" / "js").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_reads_develop_test_main_without_executing_legacy_module(self):
        encoded = base64.b64encode(b"main-secret-only-in-memory").decode("ascii")
        (self.root / "devconsole" / "config.py").write_text(
            f'''\nimport base64\nSIDE_EFFECT = __import__("pathlib").Path("SHOULD_NOT_EXIST").write_text("bad")\nKEYCLOAK_ENV_CONFIGS = {{\n  "develop": {{"url": "https://dev.invalid", "name": "DEV", "client_secret": "dev-secret"}},\n  "test": {{"url": "https://test.invalid", "name": "TEST", "client_secret": "test-secret"}},\n  "main": {{"url": "https://main.invalid", "name": "MAIN", "client_secret": "main-secret"}},\n}}\nDATABASE_ENV_CONFIGS = {{\n  "develop": {{"host": "10.0.0.1", "port": 5432, "bitacora_pass": "dev-db"}},\n  "test": {{"host": "10.0.0.2", "port": 5433, "bitacora_pass": "test-db"}},\n  "main": {{"host": "10.0.0.3", "port": 5432, "bitacora_pass": base64.b64decode("{encoded}").decode("utf-8")}},\n}}\n''',
            encoding="utf-8",
        )

        data = legacy._read_legacy_python_catalog(self.root)

        self.assertEqual({"develop", "test", "main"}, set(data["KEYCLOAK_ENV_CONFIGS"]))
        self.assertEqual("https://test.invalid", data["KEYCLOAK_ENV_CONFIGS"]["test"]["url"])
        self.assertEqual("main-secret-only-in-memory", data["DATABASE_ENV_CONFIGS"]["main"]["bitacora_pass"])
        self.assertFalse((self.root / "SHOULD_NOT_EXIST").exists())

    def test_reads_legacy_infra_matrix_and_normalizes_prod_to_main(self):
        (self.root / "static" / "js" / "dashboard.js").write_text(
            '''\nconst INFRA_ENDPOINTS = {\n  local: [\n    { id: "postgres", name: "Postgres Local", type: "DB", target: "127.0.0.1:5432", localKey: "postgres_local", testUrl: null, note: "Local", cmd: "nc local" }\n  ],\n  develop: [\n    { id: "postgres", name: "Postgres Dev", type: "DB", target: "10.0.0.1:5432", testUrl: null, note: "Dev", cmd: "nc dev" }\n  ],\n  test: [\n    { id: "postgres", name: "Postgres Test", type: "DB", target: "10.0.0.2:5433", testUrl: null, note: "Test", cmd: "nc test" }\n  ],\n  prod: [\n    { id: "postgres", name: "Postgres Prod", type: "DB", target: "10.0.0.3:5432", k8sPod: "postgres", testUrl: null, note: "Prod", cmd: "nc prod" }\n  ]\n};\n''',
            encoding="utf-8",
        )

        targets = legacy._read_legacy_infra_targets(self.root)

        self.assertEqual(["develop", "local", "main", "test"], sorted(targets))
        self.assertEqual("10.0.0.2:5433", targets["test"][0]["target"])
        self.assertEqual("10.0.0.3:5432", targets["main"][0]["target"])
        self.assertEqual("postgres", targets["main"][0]["k8sPod"])

    def test_hydration_fills_missing_environments_but_preserves_explicit_v11_values(self):
        (self.root / "devconsole" / "config.py").write_text(
            '''\nKEYCLOAK_ENV_CONFIGS = {\n  "develop": {"url": "https://legacy-dev.invalid", "name": "DEV"},\n  "test": {"url": "https://legacy-test.invalid", "name": "TEST"},\n  "main": {"url": "https://legacy-main.invalid", "name": "MAIN"},\n}\nDATABASE_ENV_CONFIGS = {\n  "test": {"host": "10.0.0.2", "port": 5433},\n  "main": {"host": "10.0.0.3", "port": 5432},\n}\n''',
            encoding="utf-8",
        )
        import devconsole.config as config

        with mock.patch.object(config, "BASE_DIR", self.root), mock.patch.object(
            config,
            "KEYCLOAK_ENV_CONFIGS",
            {"develop": {"url": "https://explicit-dev.invalid"}},
        ), mock.patch.object(config, "DATABASE_ENV_CONFIGS", {}):
            changed = legacy.hydrate_environment_catalog(self.root)
            self.assertTrue(changed)
            self.assertEqual("https://explicit-dev.invalid", config.KEYCLOAK_ENV_CONFIGS["develop"]["url"])
            self.assertEqual("https://legacy-test.invalid", config.KEYCLOAK_ENV_CONFIGS["test"]["url"])
            self.assertEqual("https://legacy-main.invalid", config.KEYCLOAK_ENV_CONFIGS["main"]["url"])
            self.assertEqual(5433, config.DATABASE_ENV_CONFIGS["test"]["port"])
            self.assertEqual("10.0.0.3", config.DATABASE_ENV_CONFIGS["main"]["host"])

    def test_auto_discovery_finds_legacy_checkout_next_to_workspace(self):
        parent = self.root / "host"
        workspace = parent / "microservices"
        dashboard = parent / "DevConsole_V1"
        old = parent / "devconsole"
        workspace.mkdir(parents=True)
        dashboard.mkdir(parents=True)
        (old / "devconsole").mkdir(parents=True)
        (old / "devconsole" / "config.py").write_text(
            '''\nKEYCLOAK_ENV_CONFIGS = {\n "develop": {"url": "https://dev.invalid"},\n "test": {"url": "https://test.invalid"},\n "main": {"url": "https://main.invalid"}\n}\nDATABASE_ENV_CONFIGS = {\n "develop": {"host": "10.0.0.1"},\n "test": {"host": "10.0.0.2"},\n "main": {"host": "10.0.0.3"}\n}\n''',
            encoding="utf-8",
        )

        with mock.patch.object(legacy, "_workspace_root", return_value=workspace), mock.patch.object(
            legacy, "_DASHBOARD_ROOT", dashboard
        ), mock.patch.dict("os.environ", {legacy._LEGACY_DIR_ENV: ""}, clear=False):
            catalog = legacy._read_legacy_python_catalog()

        self.assertEqual(
            {"develop", "test", "main"},
            set(catalog["KEYCLOAK_ENV_CONFIGS"]),
        )
        self.assertEqual("10.0.0.2", catalog["DATABASE_ENV_CONFIGS"]["test"]["host"])

    def test_auto_discovery_finds_legacy_infra_next_to_workspace(self):
        parent = self.root / "host2"
        workspace = parent / "microservices"
        dashboard = parent / "DevConsole_V1"
        old = parent / "devconsole"
        workspace.mkdir(parents=True)
        dashboard.mkdir(parents=True)
        (old / "static" / "js").mkdir(parents=True)
        (old / "static" / "js" / "dashboard.js").write_text(
            '''\nconst INFRA_ENDPOINTS = {\n develop: [{ id: "db", name: "DEV", type: "DB", target: "dev:5432", testUrl: null, note: "", cmd: "" }],\n test: [{ id: "db", name: "TEST", type: "DB", target: "test:5433", testUrl: null, note: "", cmd: "" }],\n main: [{ id: "db", name: "MAIN", type: "DB", target: "main:5432", testUrl: null, note: "", cmd: "" }]\n};\n''',
            encoding="utf-8",
        )

        with mock.patch.object(legacy, "_workspace_root", return_value=workspace), mock.patch.object(
            legacy, "_DASHBOARD_ROOT", dashboard
        ), mock.patch.dict("os.environ", {legacy._LEGACY_DIR_ENV: ""}, clear=False):
            targets = legacy._read_legacy_infra_targets()

        self.assertEqual(["develop", "main", "test"], sorted(targets))
        self.assertEqual("test:5433", targets["test"][0]["target"])

    def test_explicit_root_does_not_search_unrelated_siblings(self):
        empty = self.root / "empty"
        sibling = self.root / "devconsole"
        empty.mkdir()
        (sibling / "devconsole").mkdir(parents=True, exist_ok=True)
        (sibling / "devconsole" / "config.py").write_text(
            'KEYCLOAK_ENV_CONFIGS = {"test": {"url": "https://wrong.invalid"}}\n',
            encoding="utf-8",
        )

        self.assertEqual({}, legacy._read_legacy_python_catalog(empty))


if __name__ == "__main__":
    unittest.main()
