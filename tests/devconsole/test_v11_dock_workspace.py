from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class V11DockWorkspaceTests(unittest.TestCase):
    def test_dockview_is_self_hosted_and_licensed(self):
        vendor = ROOT / "static" / "vendor" / "terminal-lab"
        self.assertTrue((vendor / "dockview.js").is_file())
        self.assertTrue((vendor / "dockview.css").is_file())
        self.assertTrue((vendor / "LICENSE-dockview.md").is_file())

    def test_production_module_is_lazy_and_preserves_legacy_wall(self):
        module = (ROOT / "static" / "js" / "v11" / "features" / "dock-workspace.js").read_text(
            encoding="utf-8"
        )
        app = (ROOT / "static" / "js" / "v11" / "app.js").read_text(encoding="utf-8")
        legacy_index = (ROOT / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn('/static/vendor/terminal-lab/dockview.js', module)
        self.assertIn("function loadDockview()", module)
        self.assertIn("btnV11DockWorkspace", module)
        self.assertIn("/api/services/mosaic", module)
        self.assertIn("bootDockWorkspace", app)
        # The existing console wall remains the default and recovery path.
        self.assertIn('id="consoleWallToolbar"', legacy_index)
        self.assertIn('id="consoleMosaicGrid"', legacy_index)

    def test_log_rendering_uses_text_content_not_html(self):
        module = (ROOT / "static" / "js" / "v11" / "features" / "dock-workspace.js").read_text(
            encoding="utf-8"
        )
        self.assertIn('this.pre.textContent = lines.join("\\n")', module)
        self.assertNotIn("this.pre.innerHTML", module)


if __name__ == "__main__":
    unittest.main()
