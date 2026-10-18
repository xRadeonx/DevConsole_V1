"""Characterization tests: Tilix session handling (roadmap items 0A-C.5/6/7/8).

These tests freeze the Tilix session contract *before* the Phase 2
``TerminalBackend`` refactor replaces it.  Everything runs against temporary
fixtures; no window is ever opened and no session file is written to the real
``/tmp``.
"""

from __future__ import annotations

import json
from unittest import mock

from tests.devconsole.support import (
    DevConsoleTestCase,
    capture_output,
    build_balanced_session,
    make_workspace,
    normalize_uuids,
    paned_node,
    redirect_tmp_paths,
    session_node,
    terminal_node,
    write_session,
)

from devconsole.services import tilix_service
import devconsole.config as dcfg

PROFILE_AUTO = "c8e01000-0000-0000-0000-000000000001"


def patch_base_dir(testcase, root):
    """Patch BASE_DIR in both places tilix_service reads it from.

    ``scan_tilix_sessions`` uses the module-level ``BASE_DIR`` imported into
    ``tilix_service``; ``build_tilix_session_tree`` re-imports
    ``devconsole.config`` as ``dev_config`` inside the function body.  Both
    bindings must be patched for a hermetic test.
    """
    for target, owner in (("BASE_DIR", tilix_service), ("BASE_DIR", dcfg)):
        p = mock.patch.object(owner, target, root)
        p.start()
        testcase.addCleanup(p.stop)


class CountTerminalsTest(DevConsoleTestCase):
    """``count_terminals_in_node()`` recursion."""

    def test_non_dict_is_zero(self):
        self.assertEqual(0, tilix_service.count_terminals_in_node(None))
        self.assertEqual(0, tilix_service.count_terminals_in_node("x"))
        self.assertEqual(0, tilix_service.count_terminals_in_node([]))

    def test_single_terminal(self):
        self.assertEqual(1, tilix_service.count_terminals_in_node(terminal_node("/a")))

    def test_paned_with_two_terminals(self):
        node = paned_node(terminal_node("/a"), terminal_node("/b"))
        self.assertEqual(2, tilix_service.count_terminals_in_node(node))

    def test_nested_tree_counts_every_leaf(self):
        tree = build_balanced_session([f"/d{i}" for i in range(7)])
        self.assertEqual(7, tilix_service.count_terminals_in_node(tree))

    def test_paned_node_itself_is_not_counted(self):
        node = paned_node(terminal_node("/a"), paned_node(terminal_node("/b"), terminal_node("/c")))
        self.assertEqual(3, tilix_service.count_terminals_in_node(node))

    def test_session_wrapper_is_traversed(self):
        tree = session_node(paned_node(terminal_node("/a"), terminal_node("/b")))
        self.assertEqual(2, tilix_service.count_terminals_in_node(tree))


class ScanTilixSessionsTest(DevConsoleTestCase):
    """``scan_tilix_sessions()`` discovery, filtering and ordering (item 0A-C.5)."""

    def setUp(self):
        super().setUp()
        self.root = make_workspace(self.temp_dir())
        self._p = mock.patch.object(tilix_service, "BASE_DIR", self.root)
        self._p.start()
        self.addCleanup(self._p.stop)

    def test_valid_session_at_root_is_found(self):
        write_session(self.root / "my_session.json",
                      build_balanced_session(["/a", "/b"], name="S"))
        sessions = tilix_service.scan_tilix_sessions()
        self.assertEqual(1, len(sessions))
        self.assertEqual("my_session.json", sessions[0]["name"])
        self.assertEqual(2, sessions[0]["terminals"])
        self.assertFalse(sessions[0]["is_default"])
        self.assertEqual("my_session.json", sessions[0]["rel_path"])
        self.assertEqual(str(self.root / "my_session.json"), sessions[0]["abs_path"])

    def test_default_session_is_flagged(self):
        write_session(self.root / "sisper_all_single_session_auto.json",
                      build_balanced_session(["/a"], name="D"))
        sessions = tilix_service.scan_tilix_sessions()
        self.assertTrue(sessions[0]["is_default"])

    def test_excluded_filenames_are_ignored(self):
        for excluded in ("package.json", "package-lock.json", "tsconfig.json",
                         "skills-lock.json", "services.json"):
            write_session(self.root / excluded, build_balanced_session(["/a"]))
        self.assertEqual([], tilix_service.scan_tilix_sessions())

    def test_non_tilix_json_is_rejected(self):
        (self.root / "random.json").write_text(
            json.dumps({"foo": "bar"}), encoding="utf-8")
        self.assertEqual([], tilix_service.scan_tilix_sessions())

    def test_bare_terminal_node_at_root_is_accepted(self):
        # scan_tilix_sessions also accepts a root whose type is "Terminal".
        write_session(self.root / "bare.json", terminal_node("/a"))
        sessions = tilix_service.scan_tilix_sessions()
        self.assertEqual(1, len(sessions))
        self.assertEqual(1, sessions[0]["terminals"])

    def test_malformed_json_is_skipped_without_raising(self):
        (self.root / "broken.json").write_text("{not json", encoding="utf-8")
        write_session(self.root / "good.json", build_balanced_session(["/a"]))
        sessions = tilix_service.scan_tilix_sessions()
        self.assertEqual(["good.json"], [s["name"] for s in sessions])

    def test_backend_frontend_and_config_sessions_dirs_are_scanned(self):
        write_session(self.root / "backend" / "b.json", build_balanced_session(["/a"]))
        write_session(self.root / "frontend" / "f.json", build_balanced_session(["/a"]))
        write_session(self.root / "config" / "sessions" / "c.json",
                      build_balanced_session(["/a"]))
        names = sorted(s["name"] for s in tilix_service.scan_tilix_sessions())
        self.assertEqual(["b.json", "c.json", "f.json"], names)

    def test_rel_path_is_relative_to_base_dir(self):
        write_session(self.root / "backend" / "b.json", build_balanced_session(["/a"]))
        sessions = tilix_service.scan_tilix_sessions()
        self.assertEqual("backend/b.json", sessions[0]["rel_path"])

    def test_ordering_default_first_then_by_terminal_count_desc(self):
        write_session(self.root / "small.json", build_balanced_session(["/a"]))
        write_session(self.root / "big.json", build_balanced_session([f"/d{i}" for i in range(5)]))
        write_session(self.root / "sisper_all_single_session_auto.json",
                      build_balanced_session(["/a", "/b"]))
        sessions = tilix_service.scan_tilix_sessions()
        self.assertEqual(
            ["sisper_all_single_session_auto.json", "big.json", "small.json"],
            [s["name"] for s in sessions],
        )

    def test_result_contract_keys(self):
        write_session(self.root / "s.json", build_balanced_session(["/a"]))
        s = tilix_service.scan_tilix_sessions()[0]
        self.assertEqual(
            {"name", "rel_path", "abs_path", "terminals", "is_default"},
            set(s.keys()),
        )

    def test_dedup_does_not_double_report_same_file(self):
        # config/sessions is a distinct search dir; no duplication expected.
        write_session(self.root / "config" / "sessions" / "x.json",
                      build_balanced_session(["/a"]))
        self.assertEqual(1, len(tilix_service.scan_tilix_sessions()))

    def test_missing_search_dirs_are_tolerated(self):
        empty = self.temp_dir()
        with mock.patch.object(tilix_service, "BASE_DIR", empty):
            self.assertEqual([], tilix_service.scan_tilix_sessions())


class NormalizeSessionDictTest(DevConsoleTestCase):
    """``normalize_session_dict()`` path rewriting (item 0A-C.6)."""

    def setUp(self):
        super().setUp()
        self.root = self.temp_dir()

    def test_backend_directory_is_rebased(self):
        node = {"directory": "/old/root/backend/ms_sisper_sesion"}
        tilix_service.normalize_session_dict(node, self.root)
        self.assertEqual(str(self.root / "backend" / "ms_sisper_sesion"), node["directory"])

    def test_frontend_directory_is_rebased(self):
        node = {"directory": "/old/root/frontend/mf_sisper_sesion"}
        tilix_service.normalize_session_dict(node, self.root)
        self.assertEqual(str(self.root / "frontend" / "mf_sisper_sesion"), node["directory"])

    def test_bare_backend_suffix_is_rebased(self):
        node = {"directory": "/somewhere/backend"}
        tilix_service.normalize_session_dict(node, self.root)
        self.assertEqual(str(self.root / "backend"), node["directory"])

    def test_bare_frontend_suffix_is_rebased(self):
        node = {"directory": "/somewhere/frontend"}
        tilix_service.normalize_session_dict(node, self.root)
        self.assertEqual(str(self.root / "frontend"), node["directory"])

    def test_arbitrary_directory_is_left_untouched(self):
        node = {"directory": "/etc/hosts"}
        tilix_service.normalize_session_dict(node, self.root)
        self.assertEqual("/etc/hosts", node["directory"])

    def test_non_string_directory_is_ignored(self):
        node = {"directory": 12345}
        tilix_service.normalize_session_dict(node, self.root)
        self.assertEqual(12345, node["directory"])

    def test_recursion_through_nested_panes(self):
        tree = build_balanced_session(
            ["/old/backend/ms_a", "/old/frontend/mf_b"], name="S")
        tilix_service.normalize_session_dict(tree, self.root)
        dirs = []

        def walk(n):
            if isinstance(n, dict):
                if "directory" in n:
                    dirs.append(n["directory"])
                for v in n.values():
                    walk(v)
            elif isinstance(n, list):
                for v in n:
                    walk(v)

        walk(tree)
        self.assertEqual(
            sorted([str(self.root / "backend" / "ms_a"),
                    str(self.root / "frontend" / "mf_b")]),
            sorted(dirs),
        )

    def test_recursion_through_lists(self):
        node = [{"directory": "/old/backend/ms_a"}, {"directory": "/old/frontend/mf_b"}]
        tilix_service.normalize_session_dict(node, self.root)
        self.assertEqual(str(self.root / "backend" / "ms_a"), node[0]["directory"])
        self.assertEqual(str(self.root / "frontend" / "mf_b"), node[1]["directory"])

    def test_original_path_is_mutated_in_place(self):
        node = {"directory": "/old/backend/x"}
        returned = tilix_service.normalize_session_dict(node, self.root)
        self.assertIsNone(returned)
        self.assertNotIn("/old/", node["directory"])


class BuildTilixSessionTreeTest(DevConsoleTestCase):
    """Golden-shape tests for ``build_tilix_session_tree()`` (item 0A-C.7)."""

    def setUp(self):
        super().setUp()
        self.root = make_workspace(self.temp_dir())
        patch_base_dir(self, self.root)

    def _tree(self, dirs, name="T", commands=None):
        return tilix_service.build_tilix_session_tree(dirs, name, commands)

    def test_empty_directory_list_returns_empty_dict(self):
        self.assertEqual({}, self._tree([]))

    def test_single_directory_produces_a_terminal_session(self):
        tree = self._tree(["/one"])
        self.assertEqual("Session", tree["type"])
        self.assertEqual("SISPER - T", tree["name"])
        self.assertEqual("1.0", tree["version"])
        self.assertEqual(1, tilix_service.count_terminals_in_node(tree))
        child = tree["child"]
        self.assertEqual("Terminal", child["type"])
        self.assertEqual("/one", child["directory"])
        self.assertEqual(PROFILE_AUTO, child["profile"])
        self.assertFalse(child["readOnly"])
        self.assertFalse(child["synchronizedInput"])

    def test_single_directory_default_command_uses_tilix_runner(self):
        tree = self._tree(["/one"])
        cmd = tree["child"]["overrideCommand"]
        self.assertIn("bash -c", cmd)
        self.assertIn('cd "/one"', cmd)
        self.assertIn(str(self.root / "tilix_runner.sh"), cmd)

    def test_explicit_command_overrides_the_default_runner(self):
        tree = self._tree(["/one"], commands={"/one": "/tmp/custom.sh"})
        self.assertEqual("/tmp/custom.sh", tree["child"]["overrideCommand"])

    def test_command_lookup_is_by_exact_directory_string(self):
        tree = self._tree(["/one", "/two"], commands={"/two": "/tmp/two.sh"})
        dirs_to_cmds = {}

        def walk(n):
            if isinstance(n, dict):
                if n.get("type") == "Terminal":
                    dirs_to_cmds[n["directory"]] = n["overrideCommand"]
                for v in n.values():
                    walk(v)

        walk(tree)
        self.assertEqual("/tmp/two.sh", dirs_to_cmds["/two"])
        self.assertIn("tilix_runner.sh", dirs_to_cmds["/one"])

    def test_two_directories_produce_one_paned_with_two_terminals(self):
        tree = self._tree(["/a", "/b"])
        self.assertEqual(2, tilix_service.count_terminals_in_node(tree))
        child = tree["child"]
        self.assertEqual("Paned", child["type"])
        self.assertEqual(0, child["orientation"])
        self.assertEqual(50, child["position"])
        self.assertEqual(0.5, child["ratio"])

    def test_three_directories_split_one_then_two(self):
        # build_node() uses mid = len(items) // 2, so 3 dirs split as 1 | 2:
        # child1 is the single Terminal, child2 is the Paned holding the rest.
        tree = self._tree(["/a", "/b", "/c"])
        self.assertEqual(3, tilix_service.count_terminals_in_node(tree))
        root_paned = tree["child"]
        self.assertEqual("Paned", root_paned["type"])
        self.assertEqual("Terminal", root_paned["child1"]["type"])
        self.assertEqual("/a", root_paned["child1"]["directory"])
        self.assertEqual("Paned", root_paned["child2"]["type"])
        self.assertEqual("Terminal", root_paned["child2"]["child1"]["type"])
        self.assertEqual("Terminal", root_paned["child2"]["child2"]["type"])

    def test_orientation_alternates_with_depth(self):
        tree = self._tree(["/a", "/b", "/c", "/d"])
        root_paned = tree["child"]
        self.assertEqual(0, root_paned["orientation"])
        self.assertEqual(1, root_paned["child1"]["orientation"])
        self.assertEqual(1, root_paned["child2"]["orientation"])

    def test_larger_even_tree_has_exact_terminal_count(self):
        for n in (1, 2, 3, 4, 5, 8, 16, 25):
            with self.subTest(n=n):
                tree = self._tree([f"/d{i}" for i in range(n)])
                self.assertEqual(n, tilix_service.count_terminals_in_node(tree))

    def test_every_directory_appears_exactly_once(self):
        dirs = [f"/svc/{i}" for i in range(9)]
        tree = self._tree(dirs)
        seen = []

        def walk(n):
            if isinstance(n, dict):
                if n.get("type") == "Terminal":
                    seen.append(n["directory"])
                for v in n.values():
                    walk(v)

        walk(tree)
        self.assertEqual(dirs, seen)

    def test_session_geometry_and_flags(self):
        tree = self._tree(["/a"])
        self.assertEqual(1920, tree["width"])
        self.assertEqual(1080, tree["height"])
        self.assertFalse(tree["synchronizedInput"])
        self.assertIn("uuid", tree)

    def test_tree_is_json_serializable(self):
        tree = self._tree(["/a", "/b", "/c"])
        payload = json.dumps(tree)
        self.assertIn("Terminal", payload)

    def test_normalized_shape_is_stable(self):
        """Golden shape: uuid placeholders removed, structure must not drift."""
        tree = normalize_uuids(self._tree(["/a", "/b"]))
        expected_child = {
            "child1": {
                "directory": "/a", "height": 420, "profile": PROFILE_AUTO,
                "readOnly": False, "synchronizedInput": False, "type": "Terminal",
                "uuid": "<uuid>", "width": 640,
                "overrideCommand": mock.ANY,
            },
            "child2": {
                "directory": "/b", "height": 420, "profile": PROFILE_AUTO,
                "readOnly": False, "synchronizedInput": False, "type": "Terminal",
                "uuid": "<uuid>", "width": 640,
                "overrideCommand": mock.ANY,
            },
            "orientation": 0, "position": 50, "ratio": 0.5, "type": "Paned",
        }
        self.assertEqual(expected_child, tree["child"])

    def test_each_terminal_gets_a_unique_uuid(self):
        tree = self._tree([f"/d{i}" for i in range(5)])
        uuids = []

        def walk(n):
            if isinstance(n, dict):
                if n.get("type") == "Terminal":
                    uuids.append(n["uuid"])
                for v in n.values():
                    walk(v)

        walk(tree)
        self.assertEqual(5, len(set(uuids)))


class LaunchCustomServicesTilixTest(DevConsoleTestCase):
    """``launch_custom_services_tilix()`` selection and command (item 0A-C.8).

    ``subprocess.Popen`` is mocked and every command that *would* run is
    recorded.  No Tilix window is opened.
    """

    def setUp(self):
        super().setUp()
        self.root = make_workspace(self.temp_dir())
        self.tmp_out = self.temp_dir("devconsole-sessions-")
        patch_base_dir(self, self.root)
        for name in ("ms_sisper_sesion", "ms_sisper_contratos"):
            (self.root / "backend" / name).mkdir(parents=True)
        for name in ("mf_sisper_sesion",):
            (self.root / "frontend" / name).mkdir(parents=True)

    def _launch(self, names, env="develop"):
        _, recorded = self.patch_popen()
        real_path, captured = redirect_tmp_paths(self, tilix_service, self.tmp_out)
        ok, msg, count = tilix_service.launch_custom_services_tilix(
            names, target_env=env, base_dir=self.root)
        return ok, msg, count, recorded, captured

    def test_selected_backend_and_frontend_directories_are_resolved(self):
        ok, msg, count, _, _ = self._launch(
            ["ms_sisper_sesion", "mf_sisper_sesion"])
        self.assertTrue(ok)
        self.assertEqual(2, count)
        self.assertIn("2 servicio", msg)

    def test_unknown_service_names_are_dropped(self):
        ok, msg, count, _, _ = self._launch(["ms_sisper_sesion", "ms_does_not_exist"])
        self.assertTrue(ok)
        self.assertEqual(1, count)

    def test_no_valid_directories_returns_failure(self):
        capture_output(self)
        ok, msg, count, _, _ = self._launch(["ms_nope", "mf_nope"])
        self.assertFalse(ok)
        self.assertEqual(0, count)
        self.assertIn("No se encontraron directorios", msg)

    def test_tilix_is_invoked_with_a_session_file(self):
        _, _, _, recorded, _ = self._launch(["ms_sisper_sesion"])
        self.assertEqual(1, len(recorded))
        args, kwargs = recorded[0]
        cmd = args[0]
        self.assertEqual("tilix", cmd[0])
        self.assertTrue(cmd[1].startswith("--session="))
        self.assertIn("SISPER_ENV", kwargs["env"])
        self.assertEqual("develop", kwargs["env"]["SISPER_ENV"])

    def test_target_env_propagates_into_the_environment(self):
        for env in ("develop", "test", "main"):
            with self.subTest(env=env):
                _, _, _, recorded, _ = self._launch(["ms_sisper_sesion"], env=env)
                self.assertEqual(env, recorded[0][1]["env"]["SISPER_ENV"])

    def test_generated_session_file_is_written_with_expected_panels(self):
        _, _, _, _, captured = self._launch(
            ["ms_sisper_sesion", "mf_sisper_sesion"])
        self.assertEqual(1, len(captured))
        data = json.loads(captured[0].read_text(encoding="utf-8"))
        self.assertEqual(2, tilix_service.count_terminals_in_node(data))
        self.assertIn("2 Servicios", data["name"])

    def test_single_service_title_includes_the_service_name(self):
        _, _, _, _, captured = self._launch(["ms_sisper_sesion"])
        data = json.loads(captured[0].read_text(encoding="utf-8"))
        self.assertIn("ms_sisper_sesion", data["name"])
        self.assertIn("DEVELOP", data["name"])

    def test_default_service_list_comes_from_config_when_none_given(self):
        # Passing None must fall back to SERVICES_BACKEND + SERVICES_FRONTEND.
        backend = [{"name": "ms_sisper_sesion", "port": 8000}]
        frontend = [{"name": "mf_sisper_sesion", "port": 3000}]
        with mock.patch.object(dcfg, "SERVICES_BACKEND", backend), \
             mock.patch.object(dcfg, "SERVICES_FRONTEND", frontend):
            _, _, _, recorded, captured = self._launch(None)
        data = json.loads(captured[0].read_text(encoding="utf-8"))
        self.assertEqual(2, tilix_service.count_terminals_in_node(data))

    def test_cwd_is_the_first_resolved_service_directory(self):
        _, _, _, recorded, _ = self._launch(["ms_sisper_sesion"])
        self.assertEqual(
            str((self.root / "backend" / "ms_sisper_sesion").resolve()),
            recorded[0][1]["cwd"],
        )

    def test_launch_tilix_session_normalized_writes_and_launches(self):
        session = write_session(self.root / "sess.json",
                                build_balanced_session(["/old/backend/ms_sisper_sesion"]))
        _, recorded = self.patch_popen()
        _, captured = redirect_tmp_paths(self, tilix_service, self.tmp_out)
        ok = tilix_service.launch_tilix_session_normalized(session, "test")
        self.assertTrue(ok)
        self.assertEqual(1, len(recorded))
        self.assertEqual("tilix", recorded[0][0][0][0])
        data = json.loads(captured[0].read_text(encoding="utf-8"))
        dirs = []

        def walk(n):
            if isinstance(n, dict):
                if "directory" in n:
                    dirs.append(n["directory"])
                for v in n.values():
                    walk(v)

        walk(data)
        self.assertTrue(all(str(self.root) in d for d in dirs), dirs)

    def test_missing_session_file_returns_failure(self):
        capture_output(self)
        _, recorded = self.patch_popen()
        ok = tilix_service.launch_tilix_session_normalized(
            self.root / "nope.json", "develop")
        self.assertFalse(ok)
        self.assertEqual([], recorded)

    def test_auxiliary_console_script_is_generated_not_executed(self):
        _, recorded = self.patch_popen()
        _, captured = redirect_tmp_paths(self, tilix_service, self.tmp_out)
        ok, msg = tilix_service.launch_auxiliary_console(
            "ms_sisper_sesion", "consumer", "develop", base_dir=self.root)
        self.assertTrue(ok)
        self.assertIn("Consumidor RabbitMQ", msg)
        # A generated helper script must exist in the redirected tmp dir.
        scripts = [p for p in captured if p.suffix == ".sh"]
        self.assertTrue(scripts, [str(p) for p in captured])
        body = scripts[0].read_text(encoding="utf-8")
        self.assertIn("start_consumer", body)
        self.assertIn('SISPER_ENV="develop"', body)
        self.assertEqual(1, len(recorded))

    def test_each_auxiliary_type_maps_to_its_own_command(self):
        cases = {
            "consumer": "start_consumer",
            "worker": "celery -A config worker",
            "beat": "celery -A config beat",
            "shell": "pipenv shell",
        }
        for aux_type, needle in cases.items():
            with self.subTest(aux_type=aux_type):
                self.patch_popen()
                _, captured = redirect_tmp_paths(self, tilix_service,
                                                 self.temp_dir("aux-"))
                ok, _ = tilix_service.launch_auxiliary_console(
                    "ms_sisper_sesion", aux_type, "develop", base_dir=self.root)
                self.assertTrue(ok)
                scripts = [p for p in captured if p.suffix == ".sh"]
                self.assertIn(needle, scripts[0].read_text(encoding="utf-8"))

    def test_unknown_auxiliary_type_is_rejected(self):
        ok, msg = tilix_service.launch_auxiliary_console(
            "ms_sisper_sesion", "bogus", "develop", base_dir=self.root)
        self.assertFalse(ok)
        self.assertIn("no reconocido", msg)
