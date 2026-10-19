from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from devconsole import v11_yaml_promotion
from devconsole.services import yaml_service


VALID_MANIFEST = """# keep this comment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ms-demo
spec:
  template:
    spec:
      containers:
        - name: app
          image: registry.local/ms-demo:1.0.0 # image comment
        - name: proxy
          image: nginx:1.25
"""


class V11YamlPromotionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="devconsole-yaml-promote-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.k8s_dir = self.root / "config" / "develop"
        self.k8s_dir.mkdir(parents=True)
        self.manifest = self.k8s_dir / "ms-demo.yaml"
        self.manifest.write_text(VALID_MANIFEST, encoding="utf-8")
        self.module = SimpleNamespace(
            BASE_DIR=self.root,
            ENVIRONMENTS={"develop": {"k8s_dir": "config/develop"}},
            SERVICES_BACKEND=[{"name": "ms_demo", "k8s_file": "ms-demo.yaml"}],
            SERVICES_FRONTEND=[],
            k8s_dir_for=lambda _env: "config/develop",
        )

    def test_missing_optional_dependency_delegates_exactly_to_legacy(self):
        legacy = mock.Mock(return_value=(True, "legacy"))
        with mock.patch.object(yaml_service, "YAML", None):
            result = v11_yaml_promotion.update_structured(
                self.module, legacy, "ms_demo", "2.0.0", "develop"
            )
        self.assertEqual((True, "legacy"), result)
        legacy.assert_called_once_with("ms_demo", "2.0.0", "develop")

    def test_invalid_image_tag_is_rejected_before_mutation(self):
        legacy = mock.Mock()
        before = self.manifest.read_text(encoding="utf-8")
        ok, message = v11_yaml_promotion.update_structured(
            self.module, legacy, "ms_demo", "2.0.0\nmalicious: value", "develop"
        )
        self.assertFalse(ok)
        self.assertIn("inválida", message)
        self.assertEqual(before, self.manifest.read_text(encoding="utf-8"))
        legacy.assert_not_called()

    @unittest.skipUnless(yaml_service.available(), "ruamel.yaml not installed")
    def test_structured_update_preserves_comments_and_skips_nginx(self):
        legacy = mock.Mock()
        ok, message = v11_yaml_promotion.update_structured(
            self.module, legacy, "ms_demo", "2.4.1", "develop"
        )
        self.assertTrue(ok, message)
        updated = self.manifest.read_text(encoding="utf-8")
        self.assertIn("registry.local/ms-demo:2.4.1", updated)
        self.assertIn("nginx:1.25", updated)
        self.assertIn("# keep this comment", updated)
        self.assertIn("# image comment", updated)
        legacy.assert_not_called()

    @unittest.skipUnless(yaml_service.available(), "ruamel.yaml not installed")
    def test_unknown_service_does_not_touch_disk(self):
        before = self.manifest.read_text(encoding="utf-8")
        ok, _ = v11_yaml_promotion.update_structured(
            self.module, mock.Mock(), "missing", "2.0.0", "develop"
        )
        self.assertFalse(ok)
        self.assertEqual(before, self.manifest.read_text(encoding="utf-8"))

    @unittest.skipUnless(yaml_service.available(), "ruamel.yaml not installed")
    def test_parse_failure_does_not_fall_back_to_regex_mutation(self):
        self.manifest.write_text("apiVersion: [broken\nimage: repo/app:1.0\n", encoding="utf-8")
        legacy = mock.Mock()
        ok, message = v11_yaml_promotion.update_structured(
            self.module, legacy, "ms_demo", "2.0.0", "develop"
        )
        self.assertFalse(ok)
        self.assertIn("YAML inválido", message)
        legacy.assert_not_called()


if __name__ == "__main__":
    unittest.main()
