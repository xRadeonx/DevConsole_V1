from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from devconsole import config_schema


class ConfigSchemaTests(unittest.TestCase):
    def test_unavailable_dependency_reports_instead_of_crashing(self):
        with mock.patch.object(config_schema, "BaseModel", None):
            report = config_schema.validate_dict({}, schema="panel")
            self.assertFalse(report.valid)
            self.assertIn("pydantic unavailable", report.errors)

    @unittest.skipUnless(config_schema.available(), "pydantic not installed")
    def test_services_catalog_accepts_project_specific_extra_fields(self):
        report = config_schema.validate_dict({
            "project_name": "SISPER",
            "custom_project_flag": True,
            "environments": {"develop": {"namespace": "develop", "extra": "ok"}},
            "services_backend": [{
                "name": "ms_demo",
                "port": 8020,
                "group": "Backend 1",
                "custom_metadata": {"owner": "team"},
            }],
        }, schema="services")
        self.assertTrue(report.valid, report.errors)
        self.assertTrue(report.normalized["custom_project_flag"])
        self.assertEqual("team", report.normalized["services_backend"][0]["custom_metadata"]["owner"])

    @unittest.skipUnless(config_schema.available(), "pydantic not installed")
    def test_invalid_service_port_is_rejected(self):
        report = config_schema.validate_dict({
            "services_backend": [{"name": "ms_demo", "port": 70000}],
        }, schema="services")
        self.assertFalse(report.valid)
        self.assertTrue(any("port" in error for error in report.errors))

    @unittest.skipUnless(config_schema.available(), "pydantic not installed")
    def test_blank_service_name_is_rejected(self):
        report = config_schema.validate_dict({
            "services_backend": [{"name": "   ", "port": 8000}],
        }, schema="services")
        self.assertFalse(report.valid)
        self.assertTrue(any("name" in error for error in report.errors))

    @unittest.skipUnless(config_schema.available(), "pydantic not installed")
    def test_panel_ports_are_validated(self):
        report = config_schema.validate_dict({
            "project_name": "SISPER",
            "ports": {"ms_ok": 8000, "ms_bad": 0},
        }, schema="panel")
        self.assertFalse(report.valid)
        self.assertTrue(any("ports" in error for error in report.errors))

    @unittest.skipUnless(config_schema.available(), "pydantic not installed")
    def test_missing_optional_files_do_not_break_installation_validation(self):
        with tempfile.TemporaryDirectory(prefix="devconsole-schema-") as td:
            root = Path(td)
            (root / "config").mkdir()
            reports = config_schema.validate_installation(root)
            self.assertTrue(reports["panel"].valid)
            self.assertTrue(reports["services"].valid)

    @unittest.skipUnless(config_schema.available(), "pydantic not installed")
    def test_validate_file_returns_normalized_content(self):
        with tempfile.TemporaryDirectory(prefix="devconsole-schema-") as td:
            path = Path(td) / "services.json"
            path.write_text(json.dumps({
                "services_frontend": [{"name": "mf_demo", "port": 3000}],
            }), encoding="utf-8")
            report = config_schema.validate_file(path, schema="services")
            self.assertTrue(report.valid, report.errors)
            self.assertEqual("mf_demo", report.normalized["services_frontend"][0]["name"])


if __name__ == "__main__":
    unittest.main()
