from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from devconsole import v11_capabilities


class V11CapabilityEnrichmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="devconsole-capabilities-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "backend" / "ms_demo").mkdir(parents=True)
        (self.root / "frontend" / "mf_demo").mkdir(parents=True)
        (self.root / "backend" / "ms_demo" / "manage.py").write_text("# django\n", encoding="utf-8")
        (self.root / "backend" / "ms_demo" / "Pipfile").write_text('[packages]\ndjango="*"\n', encoding="utf-8")
        (self.root / "frontend" / "mf_demo" / "package.json").write_text(
            json.dumps({"dependencies": {"react": "18"}, "scripts": {"start": "react-scripts start"}}),
            encoding="utf-8",
        )

    def fake_config(self):
        root = self.root

        def repo_dir(name: str):
            for kind in ("backend", "frontend"):
                candidate = root / kind / name
                if candidate.is_dir():
                    return candidate
            return None

        return SimpleNamespace(BASE_DIR=root, get_service_repo_dir=repo_dir)

    def test_enrichment_adds_metadata_without_removing_legacy_fields(self):
        cfg = self.fake_config()
        service = {"name": "ms_demo", "port": 8020, "group": "Backend 1"}
        original = dict(service)

        result = v11_capabilities.enrich_service(cfg, service, "backend")

        for key, value in original.items():
            self.assertEqual(value, result[key])
        self.assertIn("detected", result)
        self.assertIn("Django", result["detected"]["frameworks"])
        self.assertTrue(result["detected"]["capabilities"]["run"])

    def test_enrichment_works_for_frontend(self):
        cfg = self.fake_config()
        service = {"name": "mf_demo", "port": 3012}
        result = v11_capabilities.enrich_service(cfg, service, "frontend")
        self.assertIn("React", result["detected"]["frameworks"])
        self.assertTrue(result["detected"]["capabilities"]["frontend"])

    def test_missing_path_fails_closed_and_keeps_service(self):
        cfg = self.fake_config()
        service = {"name": "missing", "port": 9999}
        result = v11_capabilities.enrich_service(cfg, service, "backend")
        self.assertEqual(9999, result["port"])
        self.assertEqual(0, result["detected"]["confidence"])
        self.assertIn("service-path-unavailable", result["detected"]["signals"])


if __name__ == "__main__":
    unittest.main()
