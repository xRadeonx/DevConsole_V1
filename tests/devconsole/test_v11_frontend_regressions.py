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

    def test_webawesome_readiness_is_global_and_uses_existing_components(self):
        source = self._read("static/js/v11/features/webawesome-ui.js")
        self.assertIn('document.querySelector(".topbar-right")', source)
        self.assertIn("READINESS", source)
        self.assertIn("M✓ A✓", source)
        self.assertIn('document.createElement("wa-badge")', source)
        self.assertIn('document.createElement("wa-tooltip")', source)
        self.assertIn('document.createElement("wa-spinner")', source)

    def test_workspace_table_is_not_replaced_by_gridjs(self):
        source = self._read("static/js/v11/features/grid-enhancements.js")
        self.assertIn("restoreWorkspaceLegacyTable", source)
        self.assertNotIn("enhanceTable(workspace", source)
        self.assertIn('document.getElementById("activityTable")', source)

    def test_gridjs_exposes_activity_search_sort_pagination_value(self):
        source = self._read("static/js/v11/features/grid-enhancements.js")
        self.assertIn("ensureGridValueHeader", source)
        self.assertIn("⌕ búsqueda", source)
        self.assertIn("↕ orden", source)
        self.assertIn("◫ paginación", source)

    def test_codemirror_env_editor_has_visible_validation_and_actions(self):
        source = self._read("static/js/v11/features/code-editors.js")
        self.assertIn("CodeMirror 6 · ENV", source)
        self.assertIn("analyseEnv", source)
        self.assertIn("duplicada", source)
        self.assertIn("KEY=valor", source)
        self.assertIn('data-action="find"', source)
        self.assertIn('data-action="validate"', source)
        self.assertIn('data-action="copy"', source)
        self.assertIn("lib.openSearch?.(editor)", source)
        self.assertIn("sensitive", source)

    def test_codemirror_bundle_source_has_real_dotenv_language_and_native_search(self):
        source = self._read("tools/vendor-ui/codemirror-entry.js")
        self.assertIn("StreamLanguage", source)
        self.assertIn("openSearchPanel", source)
        self.assertIn("const dotenv", source)
        self.assertIn('language === "env"', source)
        self.assertIn("variableName.definition", source)
        self.assertIn("export function openSearch", source)

    def test_terminal_addons_are_discoverable_without_replacing_xterm(self):
        source = self._read("static/js/v11/features/terminal-addons.js")
        self.assertIn("makeTerminalToolbar", source)
        self.assertIn("xterm+", source)
        self.assertIn("⌕ Buscar", source)
        self.assertIn("↔ Ajustar", source)
        self.assertIn("WebLinksAddon", source)
        self.assertIn("WebglCtor", source)

    def test_splitjs_gutter_is_discoverable_and_resettable(self):
        source = self._read("static/js/v11/features/split-layouts.js")
        self.assertIn("decorateGutter", source)
        self.assertIn("doble clic", source)
        self.assertIn("setSizes", source)
        self.assertIn("DEFAULT_MAP_SIZES", source)

    def test_library_value_styles_are_isolated_and_booted_by_v11(self):
        app = self._read("static/js/v11/app.js")
        css = self._read("static/css/v11-library-value.css")
        self.assertIn("v11-library-value.css", app)
        self.assertIn("ensureLibraryValueStyles", app)
        self.assertIn(".dc-v11-editor-toolbar", css)
        self.assertIn(".dc-v11-wa-global-health", css)
        self.assertIn(".dc-v11-terminal-toolbar", css)
        self.assertIn(".dc-v11-grid-valuebar", css)
        self.assertIn(".dc-v11-split-grip", css)

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
