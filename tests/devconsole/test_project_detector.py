from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from devconsole.services.project_detector import detect_project, detect_workspace


class ProjectDetectorTests(unittest.TestCase):
    def temp_project(self, name: str = "project") -> Path:
        td = tempfile.TemporaryDirectory(prefix="devconsole-detector-")
        self.addCleanup(td.cleanup)
        root = Path(td.name) / name
        root.mkdir(parents=True)
        return root

    def test_detects_django_drf_pipenv_and_celery(self):
        root = self.temp_project("ms_contratos")
        (root / "manage.py").write_text("# django\n", encoding="utf-8")
        (root / "Pipfile").write_text(
            '[packages]\ndjango="*"\ndjangorestframework="*"\ncelery="*"\n',
            encoding="utf-8",
        )
        (root / "config").mkdir()
        (root / "config" / "celery.py").write_text("# celery\n", encoding="utf-8")
        (root / "Dockerfile").write_text("FROM python:3.11\n", encoding="utf-8")

        profile = detect_project(root)

        self.assertEqual("backend", profile.kind)
        self.assertIn("Django", profile.frameworks)
        self.assertIn("Django REST Framework", profile.frameworks)
        self.assertIn("Celery", profile.frameworks)
        self.assertEqual("pipenv", profile.package_manager)
        self.assertTrue(profile.capabilities["run"])
        self.assertTrue(profile.capabilities["migrate"])
        self.assertTrue(profile.capabilities["worker"])
        self.assertTrue(profile.capabilities["container"])
        self.assertIn("pipenv run python manage.py runserver", profile.commands["run"])

    def test_detects_react_vite_and_npm_scripts(self):
        root = self.temp_project("mf_documentos")
        package = {
            "scripts": {"dev": "vite", "test": "vitest", "build": "vite build"},
            "dependencies": {"react": "^18.0.0"},
            "devDependencies": {"vite": "^5.0.0"},
        }
        (root / "package.json").write_text(json.dumps(package), encoding="utf-8")
        (root / "package-lock.json").write_text("{}", encoding="utf-8")
        (root / "vite.config.js").write_text("export default {}\n", encoding="utf-8")

        profile = detect_project(root)

        self.assertEqual("frontend", profile.kind)
        self.assertIn("React", profile.frameworks)
        self.assertIn("Vite", profile.frameworks)
        self.assertEqual("npm", profile.package_manager)
        self.assertEqual("npm run dev", profile.commands["run"])
        self.assertTrue(profile.capabilities["build"])

    def test_unknown_directory_is_not_promoted_by_name_alone(self):
        root = self.temp_project("random-folder")
        profile = detect_project(root)
        self.assertEqual("unknown", profile.kind)
        self.assertEqual(0, profile.confidence)

    def test_workspace_discovers_backend_and_frontend_children(self):
        td = tempfile.TemporaryDirectory(prefix="devconsole-workspace-")
        self.addCleanup(td.cleanup)
        workspace = Path(td.name)
        backend = workspace / "backend" / "ms_demo"
        frontend = workspace / "frontend" / "mf_demo"
        backend.mkdir(parents=True)
        frontend.mkdir(parents=True)
        (backend / "manage.py").write_text("# django\n", encoding="utf-8")
        (frontend / "package.json").write_text(
            json.dumps({"scripts": {"start": "react-scripts start"}, "dependencies": {"react": "18"}}),
            encoding="utf-8",
        )

        profiles = detect_workspace(workspace)
        names = {profile.name for profile in profiles}

        self.assertIn("ms_demo", names)
        self.assertIn("mf_demo", names)


if __name__ == "__main__":
    unittest.main()
