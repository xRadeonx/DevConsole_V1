from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from devconsole.services import yaml_service


SAMPLE = """# deployment comment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ms-demo
spec:
  template:
    spec:
      containers:
        - name: app
          image: registry.local/ms-demo:1.2.3 # keep comment
        - name: proxy
          image: nginx:1.25
---
apiVersion: v1
kind: Service
metadata:
  name: ms-demo
spec: {}
"""


class YamlServiceTests(unittest.TestCase):
    def test_missing_dependency_fails_explicitly(self):
        with mock.patch.object(yaml_service, "YAML", None):
            with self.assertRaises(yaml_service.YamlDependencyUnavailable):
                yaml_service.load_documents("a: 1")

    @unittest.skipUnless(yaml_service.available(), "ruamel.yaml not installed")
    def test_summary_prefers_workload_document(self):
        summary = yaml_service.summarize_manifest(SAMPLE)
        self.assertEqual("Deployment", summary.kind)
        self.assertEqual("ms-demo", summary.name)
        self.assertEqual("registry.local/ms-demo:1.2.3", summary.image)
        self.assertEqual("1.2.3", summary.version)

    @unittest.skipUnless(yaml_service.available(), "ruamel.yaml not installed")
    def test_retag_preserves_comment_and_skips_nginx(self):
        updated, changes = yaml_service.update_image_tags(SAMPLE, "2.0.0")
        self.assertEqual(1, len(changes))
        self.assertIn("registry.local/ms-demo:2.0.0", updated)
        self.assertIn("nginx:1.25", updated)
        self.assertIn("# keep comment", updated)
        self.assertIn("# deployment comment", updated)

    @unittest.skipUnless(yaml_service.available(), "ruamel.yaml not installed")
    def test_digest_and_untagged_images_are_not_changed(self):
        text = """apiVersion: apps/v1
kind: Deployment
metadata: {name: demo}
spec:
  template:
    spec:
      containers:
        - {name: a, image: registry/demo@sha256:abcdef}
        - {name: b, image: registry/demo}
"""
        updated, changes = yaml_service.update_image_tags(text, "9.9.9")
        self.assertEqual((), changes)
        self.assertIn("sha256:abcdef", updated)
        self.assertIn("registry/demo", updated)

    @unittest.skipUnless(yaml_service.available(), "ruamel.yaml not installed")
    def test_validation_detects_required_kubernetes_keys(self):
        ok, errors = yaml_service.validate_manifest(SAMPLE)
        self.assertTrue(ok, errors)
        ok, errors = yaml_service.validate_manifest("kind: Deployment\nmetadata: {}\n")
        self.assertFalse(ok)
        self.assertTrue(any("apiVersion" in error for error in errors))
        self.assertTrue(any("metadata.name" in error for error in errors))

    @unittest.skipUnless(yaml_service.available(), "ruamel.yaml not installed")
    def test_file_write_is_explicit_and_atomic(self):
        with tempfile.TemporaryDirectory(prefix="devconsole-yaml-") as td:
            path = Path(td) / "deploy.yaml"
            path.write_text(SAMPLE, encoding="utf-8")
            preview, changes = yaml_service.update_image_tags_file(path, "3.0.0", write=False)
            self.assertIn("3.0.0", preview)
            self.assertIn("1.2.3", path.read_text(encoding="utf-8"))
            yaml_service.update_image_tags_file(path, "3.0.0", write=True)
            self.assertIn("3.0.0", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
