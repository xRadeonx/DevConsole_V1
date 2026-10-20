from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
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
        sibling = {
            "local": [{"id": "mongo", "target": "127.0.0.1:27017"}],
            "test": [{"id": "postgres", "target": "panel-test"}],
            "main": [{"id": "postgres", "target": "panel-main"}],
        }
        with mock.patch.object(infra, "_read_sibling_panel_targets", return_value=sibling), mock.patch(
            "devconsole.v11_legacy_profile._read_legacy_infra_targets", return_value={}
        ), mock.patch(
            "devconsole.v11_legacy_profile.hydrate_environment_catalog", return_value=False
        ), mock.patch.object(infra, "_synthesized_targets", return_value={}):
            composed = infra.compose_targets(current)

        self.assertEqual(["local", "develop", "test", "main"], list(composed))
        self.assertEqual("explicit-dev", composed["develop"][0]["target"])
        self.assertEqual("panel-test", composed["test"][0]["target"])
        self.assertEqual("panel-main", composed["main"][0]["target"])

    def test_panel_reader_recovers_full_matrix_and_normalises_prod(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            panel = root / "config" / "panel.json"
            panel.parent.mkdir(parents=True)
            panel.write_text(
                json.dumps(
                    {
                        "infra_targets": {
                            "local": [
                                {"id": "postgres", "target": "127.0.0.1:5432"},
                                {"id": "mongo", "target": "127.0.0.1:27017"},
                                {"id": "keycloak", "target": "http://localhost:8080"},
                                {"id": "keydb", "target": "127.0.0.1:6379"},
                                {"id": "rabbitmq", "target": "127.0.0.1:5672"},
                                {"id": "alfresco", "target": "http://alfresco.local"},
                                {"id": "onlyoffice", "target": "http://127.0.0.1:8082"},
                                {"id": "firmador", "target": "http://firmador.local"},
                            ],
                            "develop": [{"id": "postgres", "target": "dev-db:5432"}],
                            "test": [{"id": "postgres", "target": "test-db:5433"}],
                            "prod": [{"id": "postgres", "target": "prod-db:5432"}],
                        }
                    }
                ),
                encoding="utf-8",
            )

            targets = infra._read_panel_targets_at(root)

        self.assertEqual(["local", "develop", "test", "main"], list(targets))
        self.assertEqual(8, len(targets["local"]))
        self.assertEqual("prod-db:5432", targets["main"][0]["target"])

    def test_panel_reader_never_promotes_secret_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            panel = root / "config" / "panel.json"
            panel.parent.mkdir(parents=True)
            panel.write_text(
                json.dumps(
                    {
                        "infra_targets": {
                            "develop": [
                                {"id": "bad", "target": "__SECRET__infra.endpoint__"},
                                {
                                    "id": "safe",
                                    "target": "db.invalid:5432",
                                    "testUrl": "__SECRET__infra.test_url__",
                                    "cmd": "curl __SECRET__infra.token__",
                                },
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )

            targets = infra._read_panel_targets_at(root)

        self.assertEqual(["safe"], [row["id"] for row in targets["develop"]])
        self.assertIsNone(targets["develop"][0]["testUrl"])
        self.assertEqual("", targets["develop"][0]["cmd"])

    def test_richest_sibling_panel_wins_instead_of_first_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            thin = base / "thin"
            rich = base / "rich"
            for root, count in ((thin, 1), (rich, 4)):
                panel = root / "config" / "panel.json"
                panel.parent.mkdir(parents=True)
                panel.write_text(
                    json.dumps(
                        {
                            "infra_targets": {
                                "develop": [
                                    {"id": f"svc-{index}", "target": f"host-{index}:80"}
                                    for index in range(count)
                                ]
                            }
                        }
                    ),
                    encoding="utf-8",
                )

            with mock.patch(
                "devconsole.v11_legacy_profile._candidate_roots", return_value=[thin, rich]
            ):
                targets = infra._read_sibling_panel_targets()

        self.assertEqual(4, len(targets["develop"]))


if __name__ == "__main__":
    unittest.main()
