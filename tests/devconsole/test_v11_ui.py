from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from devconsole import v11_ui


class V11UiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="devconsole-v11-ui-")
        self.addCleanup(self.tmp.cleanup)
        self.static = Path(self.tmp.name)
        (self.static / "css").mkdir()
        (self.static / "js" / "v11").mkdir(parents=True)
        (self.static / "css" / "v11-foundation.css").write_text("/* foundation */", encoding="utf-8")
        (self.static / "css" / "v11-libraries.css").write_text("/* libraries */", encoding="utf-8")
        (self.static / "js" / "v11" / "app.js").write_text("// js", encoding="utf-8")

    def test_injection_is_additive_and_idempotent(self):
        legacy = '<html><head><link href="legacy.css"></head><body><script src="legacy.js"></script></body></html>'
        once = v11_ui.inject_assets(legacy, self.static)
        twice = v11_ui.inject_assets(once, self.static)
        self.assertIn("legacy.css", once)
        self.assertIn("legacy.js", once)
        self.assertIn("v11-foundation.css", once)
        self.assertIn("v11-libraries.css", once)
        self.assertIn("/static/js/v11/app.js", once)
        self.assertEqual(once, twice)
        self.assertEqual(2, once.count('data-devconsole-v11="ui-foundation"'))
        self.assertEqual(1, once.count('data-devconsole-v11="ui-libraries"'))

    def test_render_preserves_dashboard_version_marker(self):
        index = self.static / "index.html"
        index.write_text(
            '<html><head></head><body><script src="/static/js/dashboard.js"></script></body></html>',
            encoding="utf-8",
        )
        module = SimpleNamespace(
            STATIC_DIR=self.static,
            _version_estaticos=lambda: {"js/dashboard.js": "abc123"},
        )
        html, versions = v11_ui.render_index(module)
        self.assertEqual("abc123", versions["js/dashboard.js"])
        self.assertIn("window.__UI_VERSION=\"abc123\"", html)
        self.assertIn('src="/static/js/dashboard.js?v=abc123"', html)
        self.assertIn("/static/js/v11/app.js", html)
        self.assertIn("/static/css/v11-libraries.css", html)

    def test_missing_index_returns_none_without_side_effect(self):
        module = SimpleNamespace(STATIC_DIR=self.static, _version_estaticos=lambda: {})
        html, versions = v11_ui.render_index(module)
        self.assertIsNone(html)
        self.assertEqual({}, versions)

    def test_self_hosted_ui_bundles_are_committed_and_nonempty(self):
        repo_root = Path(__file__).resolve().parents[2]
        vendor = repo_root / "static" / "vendor" / "v11"
        required = {
            "split.min.js": 1024,
            "gridjs.umd.js": 10_000,
            "gridjs-mermaid.min.css": 1000,
            "codemirror.bundle.js": 100_000,
            "THIRD_PARTY_LICENSES.txt": 500,
            "VERSIONS.txt": 50,
        }
        for filename, min_size in required.items():
            path = vendor / filename
            self.assertTrue(path.is_file(), f"Falta bundle self-hosted: {filename}")
            self.assertGreater(path.stat().st_size, min_size, f"Bundle incompleto: {filename}")

        versions = (vendor / "VERSIONS.txt").read_text(encoding="utf-8")
        self.assertIn("split.js=1.6.5", versions)
        self.assertIn("gridjs=6.2.0", versions)
        self.assertIn("codemirror=6.0.2", versions)


if __name__ == "__main__":
    unittest.main()
