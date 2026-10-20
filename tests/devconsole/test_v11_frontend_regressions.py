from __future__ import annotations

import unittest
from pathlib import Path


class V11FrontendRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[2]

    def _read(self, relative: str) -> str:
        return (self.root / relative).read_text(encoding="utf-8")

    def test_webawesome_does_not_load_global_stylesheet(self):
        source = self._read("static/js/v11/features/webawesome-ui.js")
        self.assertNotIn("webawesome.css", source)
        self.assertNotIn("ensureStyle(", source)
        self.assertIn("webawesome.bundle.js", source)

    def test_workspace_table_is_not_replaced_by_gridjs(self):
        source = self._read("static/js/v11/features/grid-enhancements.js")
        self.assertIn("restoreWorkspaceLegacyTable", source)
        self.assertNotIn("enhanceTable(workspace", source)
        self.assertIn('document.getElementById("activityTable")', source)

    def test_secret_guidance_names_each_environment_and_yaml_discovery(self):
        source = self._read("static/js/v11/features/secret-guidance.js")
        for env in ("develop", "test", "main"):
            self.assertIn(env, source)
        self.assertIn("Buscar en .env + config YAML", source)
        self.assertIn("Mapa Operativo", source)
        self.assertIn("Actividad", source)
        self.assertIn("OnlyOffice · JWT Secret", source)

    def test_app_boots_guided_secrets_without_replacing_legacy_tabs(self):
        source = self._read("static/js/v11/app.js")
        self.assertIn('from "./features/secret-guidance.js"', source)
        self.assertIn("bootSecretGuidance();", source)
        self.assertIn("bootGridEnhancements();", source)
        self.assertIn("bootTerminalAddons();", source)


if __name__ == "__main__":
    unittest.main()
