from __future__ import annotations

import unittest
from pathlib import Path

from devconsole import v11_catalog_aliases as aliases
from devconsole import v11_yaml_catalog as catalog


class V11CatalogAliasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        aliases.install()

    def test_contratos_service_specific_fields_are_normalized(self):
        values = {
            "PGHOST": "pg.test.local",
            "PGPORT": "5432",
            "CTTO_DB": "contratos_test",
            "CTTO_USER": "contratos_reader",
            "CTTO_PASSWORD": "contratos-secret",
        }

        fields = catalog._database_fields(values, "contratos")

        self.assertEqual("pg.test.local", fields["host"])
        self.assertEqual(5432, fields["port"])
        self.assertEqual("contratos_test", fields["contratos_db"])
        self.assertEqual("contratos_reader", fields["contratos_user"])
        self.assertEqual("contratos-secret", fields["contratos_pass"])

    def test_destinaciones_service_specific_fields_are_normalized(self):
        values = {
            "POSTGRESQL_HOST": "pg.main.local",
            "POSTGRESQL_PORT": "5433",
            "DESTINACIONES_DATABASE": "dest_main",
            "DESTINACIONES_USERNAME": "dest_reader",
            "DESTINACIONES_PASSWORD": "dest-secret",
        }

        fields = catalog._database_fields(values, "destinaciones")

        self.assertEqual("pg.main.local", fields["host"])
        self.assertEqual(5433, fields["port"])
        self.assertEqual("dest_main", fields["destinaciones_db"])
        self.assertEqual("dest_reader", fields["destinaciones_user"])
        self.assertEqual("dest-secret", fields["destinaciones_pass"])

    def test_libpq_and_common_db_aliases_are_supported(self):
        values = {
            "PGHOST": "pg.local",
            "PGPORT": "5432",
            "PGDATABASE": "db_name",
            "PGUSER": "db_user",
            "PGPASSWORD": "db-pass",
        }

        fields = catalog._database_fields(values, "contratos")

        self.assertEqual("db_name", fields["contratos_db"])
        self.assertEqual("db_user", fields["contratos_user"])
        self.assertEqual("db-pass", fields["contratos_pass"])

    def test_logical_database_aliases_recognize_ctto_and_destino(self):
        self.assertEqual(
            "contratos",
            catalog._logical_database(Path("config/test/ms_sisper_ctto.yaml"), ""),
        )
        self.assertEqual(
            "destinaciones",
            catalog._logical_database(Path("config/prod/ms_sisper_destino.yaml"), ""),
        )

    def test_keycloak_common_aliases_are_normalized(self):
        entry = catalog._keycloak_entry(
            {
                "KC_HOST": "keycloak.test.local",
                "KC_REALM": "SISPER",
                "KC_CLIENT_ID": "ms-sisper",
            }
        )

        self.assertEqual("https://keycloak.test.local", entry["url"])
        self.assertEqual("SISPER", entry["realm"])
        self.assertEqual("ms-sisper", entry["client_id"])


if __name__ == "__main__":
    unittest.main()
