"""Characterization tests: service discovery and configuration loading.

Covers roadmap item 0A-C.1.  Two kinds of assertion are used deliberately:

* **Fixture tests** drive ``discover_services()`` against a synthetic workspace
  so the *rules* (what is included, how a port is derived) are pinned.
* **Golden test** snapshots the result of discovery against the real workspace
  at a known commit, so any later refactor that changes the discovered set is
  caught immediately.
"""

from __future__ import annotations

import json
from unittest import mock

from tests.devconsole.support import (
    DevConsoleTestCase,
    capture_output,
    fixture_path,
    load_fixture,
    make_backend_service,
    make_frontend_service,
    make_workspace,
)

import devconsole.config as dcfg


class DiscoverServicesRulesTest(DevConsoleTestCase):
    """``discover_services()`` inclusion rules and port derivation."""

    def setUp(self):
        super().setUp()
        self.root = make_workspace(self.temp_dir())
        self._patch = mock.patch.object(dcfg, "BASE_DIR", self.root)
        self._patch.start()
        self.addCleanup(self._patch.stop)

    def test_backend_requires_ms_prefix_or_manage_py(self):
        make_backend_service(self.root, "ms_alpha", port=8000)
        make_backend_service(self.root, "beta_with_manage", port=8001, with_manage_py=True)
        # Neither ms_ prefix nor manage.py -> must be ignored.
        (self.root / "backend" / "notes").mkdir()
        (self.root / "backend" / "notes" / "readme.txt").write_text("x", encoding="utf-8")

        backend, _ = dcfg.discover_services()
        names = [s["name"] for s in backend]
        self.assertIn("ms_alpha", names)
        self.assertIn("beta_with_manage", names)
        self.assertNotIn("notes", names)

    def test_backend_excluded_directories(self):
        for excluded in ("config", "__pycache__", "venv", ".venv", "keydb",
                         "ms_sisper_migrate", "qa_integracion", ".hidden"):
            d = self.root / "backend" / excluded
            d.mkdir(parents=True, exist_ok=True)
            (d / "manage.py").write_text("# fake\n", encoding="utf-8")

        backend, _ = dcfg.discover_services()
        self.assertEqual([], [s["name"] for s in backend])

    def test_frontend_requires_package_json_or_git_or_mf_prefix(self):
        make_frontend_service(self.root, "mf_alpha", port=3000, with_package_json=True)
        make_frontend_service(self.root, "web_bravo", port=3001, with_package_json=True)
        make_frontend_service(self.root, "mf_charlie", port=3002, with_package_json=False, with_git=True)
        # mf_ prefix alone is enough.
        make_frontend_service(self.root, "mf_delta", port=3003, with_package_json=False)
        # None of the markers -> ignored.
        (self.root / "frontend" / "plain").mkdir()

        _, frontend = dcfg.discover_services()
        names = [s["name"] for s in frontend]
        # discover_services() sorts by directory name.
        self.assertEqual(["mf_alpha", "mf_charlie", "mf_delta", "web_bravo"], names)
        self.assertNotIn("plain", names)

    def test_frontend_excluded_directories(self):
        for excluded in ("__pycache__", "node_modules", "dist", ".hidden"):
            d = self.root / "frontend" / excluded
            d.mkdir(parents=True, exist_ok=True)
            (d / "package.json").write_text("{}", encoding="utf-8")

        _, frontend = dcfg.discover_services()
        self.assertEqual([], [s["name"] for s in frontend])

    def test_port_from_env_file_takes_precedence(self):
        make_backend_service(self.root, "ms_sisper_sesion", port=9199)
        backend, _ = dcfg.discover_services()
        svc = next(s for s in backend if s["name"] == "ms_sisper_sesion")
        self.assertEqual(9199, svc["port"])

    def test_port_from_daphne_port_env_key(self):
        d = make_backend_service(self.root, "ms_zeta", with_manage_py=True)
        (d / ".env").write_text("DAPHNE_PORT=9299\n", encoding="utf-8")
        backend, _ = dcfg.discover_services()
        svc = next(s for s in backend if s["name"] == "ms_zeta")
        self.assertEqual(9299, svc["port"])

    def test_port_falls_back_to_known_ports_table(self):
        make_backend_service(self.root, "ms_sisper_contratos", with_manage_py=True)
        backend, _ = dcfg.discover_services()
        svc = next(s for s in backend if s["name"] == "ms_sisper_contratos")
        self.assertEqual(dcfg.KNOWN_PORTS["ms_sisper_contratos"], svc["port"])

    def test_port_fallback_formula_for_unknown_service(self):
        make_backend_service(self.root, "ms_totally_unknown_one", with_manage_py=True)
        backend, _ = dcfg.discover_services()
        svc = next(s for s in backend if s["name"] == "ms_totally_unknown_one")
        # Documented fallback: 8000 + index + 20 for the first discovered service.
        self.assertEqual(8020, svc["port"])

    def test_frontend_port_fallback_formula_for_unknown_service(self):
        make_frontend_service(self.root, "mf_unknown_front", with_package_json=True)
        _, frontend = dcfg.discover_services()
        svc = next(s for s in frontend if s["name"] == "mf_unknown_front")
        self.assertEqual(3012, svc["port"])

    def test_has_consumer_and_has_worker_detection(self):
        make_backend_service(self.root, "ms_cons", with_manage_py=True, with_consumer=True)
        make_backend_service(self.root, "ms_work", with_manage_py=True, with_worker=True)
        make_backend_service(self.root, "ms_none", with_manage_py=True)
        backend, _ = dcfg.discover_services()
        by_name = {s["name"]: s for s in backend}
        self.assertTrue(by_name["ms_cons"]["has_consumer"])
        self.assertFalse(by_name["ms_cons"]["has_worker"])
        self.assertTrue(by_name["ms_work"]["has_worker"])
        self.assertFalse(by_name["ms_work"]["has_consumer"])
        self.assertFalse(by_name["ms_none"]["has_consumer"])
        self.assertFalse(by_name["ms_none"]["has_worker"])

    def test_k8s_metadata_defaults_are_derived_from_name(self):
        make_backend_service(self.root, "ms_sisper_brandnew", with_manage_py=True)
        backend, _ = dcfg.discover_services()
        svc = next(s for s in backend if s["name"] == "ms_sisper_brandnew")
        # clean_name = name.replace("_", "-"); k8s_deploy strips the "ms-sisper-" stem.
        self.assertEqual("ms-brandnew", svc["k8s_deploy"])
        self.assertEqual("backend/ms_sisper_brandnew.yaml", svc["k8s_file"])
        self.assertIn(svc["group"], ("Backend 1", "Backend 2"))

    def test_backend_result_is_sorted_by_directory_name(self):
        make_backend_service(self.root, "ms_zulu", with_manage_py=True)
        make_backend_service(self.root, "ms_alfa", with_manage_py=True)
        make_backend_service(self.root, "ms_mike", with_manage_py=True)
        backend, _ = dcfg.discover_services()
        self.assertEqual(["ms_alfa", "ms_mike", "ms_zulu"], [s["name"] for s in backend])

    def test_missing_backend_and_frontend_dirs_yield_empty_lists(self):
        empty = make_workspace(self.temp_dir())
        (empty / "backend").rmdir()
        (empty / "frontend").rmdir()
        with mock.patch.object(dcfg, "BASE_DIR", empty):
            backend, frontend = dcfg.discover_services()
        self.assertEqual([], backend)
        self.assertEqual([], frontend)

    def test_every_service_exposes_the_expected_contract_keys(self):
        make_backend_service(self.root, "ms_contract", with_manage_py=True)
        make_frontend_service(self.root, "mf_contract", with_package_json=True)
        backend, frontend = dcfg.discover_services()

        for entry in backend:
            for key in ("name", "port", "group", "k8s_file", "k8s_deploy",
                        "has_consumer", "has_worker"):
                self.assertIn(key, entry, f"backend entry missing {key!r}")
            self.assertIsInstance(entry["port"], int)

        for entry in frontend:
            for key in ("name", "port", "k8s_file", "k8s_deploy"):
                self.assertIn(key, entry, f"frontend entry missing {key!r}")
            self.assertIsInstance(entry["port"], int)


class InspectDirectoryTest(DevConsoleTestCase):
    """``inspect_directory()`` is pure w.r.t. its path argument."""

    def test_nonexistent_path_is_reported_invalid(self):
        missing = self.temp_dir() / "does-not-exist"
        result = dcfg.inspect_directory(missing)
        self.assertFalse(result["valid"])
        self.assertIn("no existe", result["error"])
        self.assertEqual(str(missing), result["path"])

    def test_file_path_is_reported_invalid(self):
        f = self.temp_dir() / "a-file.txt"
        f.write_text("x", encoding="utf-8")
        result = dcfg.inspect_directory(f)
        self.assertFalse(result["valid"])
        self.assertIn("no es un directorio", result["error"])

    def test_valid_workspace_is_described(self):
        root = make_workspace(self.temp_dir())
        make_backend_service(root, "ms_one", port=8000)
        make_backend_service(root, "ms_two", port=8001)
        make_frontend_service(root, "mf_one", port=3000)
        result = dcfg.inspect_directory(root)

        self.assertTrue(result["valid"])
        self.assertTrue(result["has_backend_dir"])
        self.assertTrue(result["has_frontend_dir"])
        self.assertEqual(2, result["backend_count"])
        self.assertEqual(1, result["frontend_count"])
        self.assertEqual(["ms_one", "ms_two"], result["backend_services"])
        self.assertEqual(["mf_one"], result["frontend_services"])

    def test_subdirs_are_capped_at_forty(self):
        root = make_workspace(self.temp_dir())
        for i in range(45):
            (root / f"dir{i:02d}").mkdir()
        result = dcfg.inspect_directory(root)
        self.assertEqual(40, len(result["subdirs"]))

    def test_parent_dir_reported(self):
        root = make_workspace(self.temp_dir())
        result = dcfg.inspect_directory(root / "backend")
        self.assertEqual(str(root), result["parent_dir"])


class NormalizeEnvKeyTest(DevConsoleTestCase):
    """``normalize_env_key()`` alias collapsing."""

    def test_aliases_collapse_to_canonical_keys(self):
        cases = {
            "dev": "develop", "develop": "develop", "desarrollo": "develop",
            "test": "test", "qa": "test", "testing": "test",
            "main": "main", "prod": "main", "produccion": "main",
        }
        for raw, expected in cases.items():
            self.assertEqual(expected, dcfg.normalize_env_key(raw), raw)

    def test_case_and_whitespace_insensitive(self):
        self.assertEqual("develop", dcfg.normalize_env_key("  DEVELOP  "))

    def test_empty_falls_back_to_develop(self):
        self.assertEqual("develop", dcfg.normalize_env_key(""))
        self.assertEqual("develop", dcfg.normalize_env_key(None))

    def test_unknown_key_is_returned_lowercased(self):
        self.assertEqual("staging", dcfg.normalize_env_key("STAGING"))


class LoadConfigMergeTest(DevConsoleTestCase):
    """``load_config()`` merges on-disk JSON over discovered services."""

    def setUp(self):
        super().setUp()
        self.root = make_workspace(self.temp_dir())
        self.config_file = self.root / "config" / "services.json"
        for target, value in (("BASE_DIR", self.root),
                              ("CONFIG_FILE", self.config_file)):
            p = mock.patch.object(dcfg, target, value)
            p.start()
            self.addCleanup(p.stop)

    def test_json_overrides_discovered_port(self):
        make_backend_service(self.root, "ms_override", port=8100)
        self.config_file.write_text(json.dumps({
            "services_backend": [{"name": "ms_override", "port": 9999}],
            "services_frontend": [],
        }), encoding="utf-8")

        cfg = dcfg.load_config()
        svc = next(s for s in cfg["services_backend"] if s["name"] == "ms_override")
        self.assertEqual(9999, svc["port"])

    def test_json_service_absent_from_disk_is_still_merged(self):
        self.config_file.write_text(json.dumps({
            "services_backend": [{"name": "ms_ghost", "port": 8888}],
            "services_frontend": [],
        }), encoding="utf-8")

        cfg = dcfg.load_config()
        names = [s["name"] for s in cfg["services_backend"]]
        self.assertIn("ms_ghost", names)

    def test_slices_and_environments_come_from_json_when_present(self):
        self.config_file.write_text(json.dumps({
            "services_backend": [], "services_frontend": [],
            "slices": {"custom": {"title": "T", "description": "D", "services": []}},
            "environments": {"develop": {"label": "DEV"}},
        }), encoding="utf-8")

        cfg = dcfg.load_config()
        self.assertIn("custom", cfg["slices"])
        self.assertEqual("DEV", cfg["environments"]["develop"]["label"])

    def test_malformed_json_falls_back_to_discovered_services(self):
        make_backend_service(self.root, "ms_survivor", port=8123)
        self.config_file.write_text("{ this is not json", encoding="utf-8")

        out, _ = capture_output(self)
        cfg = dcfg.load_config()
        names = [s["name"] for s in cfg["services_backend"]]
        self.assertIn("ms_survivor", names)
        # The failure is reported as a warning, not raised.
        self.assertIn("Error leyendo config/services.json", out.getvalue())


class GoldenDiscoveryTest(DevConsoleTestCase):
    """Golden snapshot of discovery against the real workspace.

    This is a *deliberate* golden test: it pins the exact service set of the
    workspace at the commit recorded in the fixture.  Regenerate only when the
    workspace itself legitimately changes, with::

        python3 -m tests.devconsole.regenerate_golden
    """

    def test_discovery_matches_golden_snapshot(self):
        golden = load_fixture("golden_discovery.json")
        backend, frontend = dcfg.discover_services()

        def slim(entries):
            return [
                {
                    "name": e["name"],
                    "port": e["port"],
                    "group": e.get("group"),
                    "k8s_deploy": e.get("k8s_deploy"),
                    "k8s_file": e.get("k8s_file"),
                    "has_consumer": e.get("has_consumer"),
                    "has_worker": e.get("has_worker"),
                }
                for e in entries
            ]

        self.assertEqual(
            golden["backend"], slim(backend),
            "Backend discovery changed vs golden snapshot.\n"
            "If this is a legitimate workspace change, regenerate with "
            "python3 -m tests.devconsole.regenerate_golden",
        )
        self.assertEqual(
            golden["frontend"], slim(frontend),
            "Frontend discovery changed vs golden snapshot.\n"
            "If this is a legitimate workspace change, regenerate with "
            "python3 -m tests.devconsole.regenerate_golden",
        )

    def test_golden_records_the_commit_it_was_taken_at(self):
        golden = load_fixture("golden_discovery.json")
        self.assertIn("captured_at_commit", golden)
        self.assertIn("captured_at", golden)

    def test_golden_counts_are_internally_consistent(self):
        golden = load_fixture("golden_discovery.json")
        self.assertEqual(golden["backend_count"], len(golden["backend"]))
        self.assertEqual(golden["frontend_count"], len(golden["frontend"]))

    def test_golden_fixture_file_exists(self):
        self.assertTrue(fixture_path("golden_discovery.json").exists())
