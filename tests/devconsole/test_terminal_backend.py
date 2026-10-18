"""Phase 2 parity suite: ``TilixBackend`` against the frozen pre-refactor behaviour.

Two independent kinds of evidence, because "funciona parecido" is not accepted:

1. **Differential, OLD vs NEW.**  The pre-refactor implementation is loaded
   straight out of git history — the last commit where the code still lived in
   ``devconsole/services/tilix_service.py`` — into a private module.  Both that
   module and the new backend are then driven with *the same inputs* while
   ``subprocess`` is mocked, and their results, recorded ``argv``/``cwd``/``env``
   and every file they generate are compared.  This is a real equivalence check
   against the old code, not a restatement of the new one.

   If the baseline revision is unavailable (shallow clone, source archive) the
   differential tests skip loudly rather than passing vacuously.

2. **Frozen expectations.**  The 0A golden fixtures and golden shapes are
   re-checked *through the backend*, so parity is also pinned by values that
   predate the refactor by several phases and were never regenerated for it.

The suite also covers the new surface the refactor introduces: the
``run_action`` invocation contract, the ``SISPER_TERMINAL_BACKEND`` factory, the
absence of a second hardcoded implementation behind the endpoints, and the
structural rule that no consumer names Tilix any more.
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

from tests.devconsole.support import (
    DevConsoleTestCase,
    build_balanced_session,
    capture_output,
    load_fixture,
    make_handler,
    make_workspace,
    normalize_uuids,
    redirect_tmp_paths,
    terminal_node,
    write_session,
)

import devconsole.config as dcfg
from devconsole.api import handlers
from devconsole.api.handlers import DevConsoleHandler
from devconsole.services.terminal import (
    DEFAULT_BACKEND,
    ENV_VAR,
    KNOWN_ACTIONS,
    TerminalBackend,
    TilixBackend,
    UnsupportedTerminalBackend,
    get_terminal_backend,
    reset_terminal_backend,
    resolve_backend_name,
)
from devconsole.services.terminal import registry as terminal_registry
from devconsole.services.terminal import tilix_backend

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Last commit in which ``tilix_service.py`` still held the implementation.
#: Pinned deliberately: it is the "OLD" side of every differential comparison.
BASELINE_REV = "f514ffb"
BASELINE_PATH = "devconsole/services/tilix_service.py"


# --------------------------------------------------------------------------- #
# Baseline loading
# --------------------------------------------------------------------------- #

def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), *args], stderr=subprocess.DEVNULL).decode("utf-8")


def baseline_available() -> bool:
    """True when the pinned pre-refactor revision is present in this clone."""
    try:
        subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "cat-file", "-e", f"{BASELINE_REV}^{{commit}}"],
            stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return False


def load_baseline_module():
    """Import the pre-refactor ``tilix_service`` as a private, isolated module."""
    source = _git("show", f"{BASELINE_REV}:{BASELINE_PATH}")
    tmpdir = Path(tempfile.mkdtemp(prefix="devconsole-baseline-"))
    target = tmpdir / "baseline_tilix_service.py"
    target.write_text(source, encoding="utf-8")

    spec = importlib.util.spec_from_file_location("devconsole_parity_baseline", target)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


# --------------------------------------------------------------------------- #
# Recording harness
# --------------------------------------------------------------------------- #

class SubprocessRecorder:
    """Records every ``Popen``/``run`` call and returns inert handles.

    The point is to capture the *exact* invocation — program, argv, ``cwd`` and
    the full ``env`` — so the two implementations can be compared on what they
    would actually execute, without executing anything.
    """

    def __init__(self):
        self.calls: list[tuple[str, list, dict]] = []

    def popen(self, cmd, *args, **kwargs):
        self.calls.append(("Popen", list(cmd), dict(kwargs)))
        return mock.MagicMock(name="Popen-result")

    def run(self, cmd, *args, **kwargs):
        self.calls.append(("run", list(cmd), dict(kwargs)))
        return mock.MagicMock(name="run-result", returncode=0)


class ParityMixin:
    """Runs one side of a differential comparison in an isolated sandbox."""

    def parity_side(self, module, thunk, root: Path, tmpdir: Path) -> dict:
        """Execute ``thunk`` against ``module`` and fingerprint the outcome.

        Everything that could differ is captured: the return value, every
        recorded child-process invocation, and the bytes of every file the
        operation wrote under ``/tmp``.

        Both sides share one ``tmpdir`` on purpose — generated session JSON
        embeds the absolute path of the companion script, so using different
        directories would produce a spurious difference.
        """
        recorder = SubprocessRecorder()
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(module, "BASE_DIR", root))
            stack.enter_context(mock.patch.object(dcfg, "BASE_DIR", root))
            stack.enter_context(mock.patch.object(module.subprocess, "Popen", recorder.popen))
            stack.enter_context(mock.patch.object(module.subprocess, "run", recorder.run))
            _, captured = redirect_tmp_paths(self, module, tmpdir)
            result = thunk()

        files = {}
        for path in captured:
            files[path.name] = path.read_bytes() if path.exists() else None

        return {"result": result, "calls": recorder.calls, "files": files}

    # -- helpers ------------------------------------------------------------ #

    @staticmethod
    def canonical_json(raw: bytes) -> str:
        """Normalise a generated JSON file so UUIDs do not defeat comparison."""
        parsed = json.loads(raw.decode("utf-8"))
        return json.dumps(normalize_uuids(parsed), indent=2, ensure_ascii=False)


class BaselineTestCase(ParityMixin, DevConsoleTestCase):
    """Base class that skips differential tests when the baseline is absent.

    The baseline source is read once in :meth:`setUpClass`, which runs *before*
    the guarded base class installs its "no real subprocess" hooks — reading git
    history is a legitimate read-only child process, and the guard exists to
    forbid destructive ones.
    """

    baseline = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        import unittest as _unittest
        if not baseline_available():
            raise _unittest.SkipTest(
                f"parity baseline {BASELINE_REV} is not present in this clone; "
                "the OLD-vs-NEW differential cannot run here")
        cls.baseline = load_baseline_module()

    def setUp(self):
        super().setUp()
        self.old = type(self).baseline
        self.new = tilix_backend
        self.backend = TilixBackend()
        self.root = make_workspace(self.temp_dir())
        self.tmpdir = self.temp_dir("parity-tmp-")


# --------------------------------------------------------------------------- #
# 1. Discovery
# --------------------------------------------------------------------------- #

class ScanSessionsParityTest(BaselineTestCase):
    """``scan_sessions()`` is equivalent to the pre-refactor scan."""

    def _compare(self):
        old = self.parity_side(self.old, self.old.scan_tilix_sessions,
                               self.root, self.tmpdir)
        new = self.parity_side(self.new, self.backend.scan_sessions,
                               self.root, self.tmpdir)
        self.assertEqual(old, new)
        return new["result"]

    def test_empty_workspace_is_equivalent(self):
        self.assertEqual([], self._compare())

    def test_discovered_sessions_are_equivalent(self):
        write_session(self.root / "a.json", build_balanced_session(["/a", "/b"], name="A"))
        write_session(self.root / "backend" / "b.json", build_balanced_session(["/c"]))
        write_session(self.root / "frontend" / "c.json", terminal_node("/d"))
        write_session(self.root / "config" / "sessions" / "d.json",
                      build_balanced_session(["/e", "/f", "/g"]))
        self.assertEqual(4, len(self._compare()))

    def test_default_session_ordering_is_equivalent(self):
        write_session(self.root / "sisper_all_single_session_auto.json",
                      build_balanced_session(["/a"]))
        write_session(self.root / "other.json", build_balanced_session(["/a", "/b"]))
        sessions = self._compare()
        self.assertTrue(sessions[0]["is_default"])

    def test_filtered_and_malformed_files_are_equivalent(self):
        for excluded in ("package.json", "package-lock.json", "tsconfig.json",
                         "skills-lock.json", "services.json"):
            (self.root / excluded).write_text("{}", encoding="utf-8")
        (self.root / "broken.json").write_text("{not json", encoding="utf-8")
        (self.root / "unrelated.json").write_text('{"foo": "bar"}', encoding="utf-8")
        write_session(self.root / "good.json", build_balanced_session(["/a"]))
        self.assertEqual(["good.json"], [s["name"] for s in self._compare()])

    def test_golden_discovery_fixture_still_drives_a_service_launch(self):
        """The 0A golden service list is what the backend resolves directories for.

        Scope note: 0A froze a *discovery* golden plus session *shapes* (in
        ``test_tilix_service.py``), not a session golden file.  The shapes are
        re-checked above; this uses the discovery golden for what it actually
        pins — the 21 + 10 service names a full launch has to resolve.
        """
        golden = load_fixture("golden_discovery.json")
        self.assertEqual(21, golden["backend_count"])
        self.assertEqual(10, golden["frontend_count"])
        names = [s["name"] for s in golden["backend"]] + [s["name"] for s in golden["frontend"]]
        self.assertEqual(31, len(names))

        for name in names:
            (self.root / "backend" / name).mkdir(parents=True, exist_ok=True)

        new = self.parity_side(
            self.new,
            lambda: self.backend.launch_services(names, "develop", self.root),
            self.root, self.tmpdir)
        ok, msg, count = new["result"]
        self.assertTrue(ok)
        self.assertEqual(31, count)
        self.assertIn("31 servicio(s)", msg)

    def test_session_scan_result_keys_are_unchanged(self):
        write_session(self.root / "s.json", build_balanced_session(["/a", "/b"]))
        sessions = self.parity_side(
            self.new, self.backend.scan_sessions, self.root, self.tmpdir)["result"]
        self.assertEqual({"name", "rel_path", "abs_path", "terminals", "is_default"},
                         set(sessions[0].keys()))
        self.assertEqual(2, sessions[0]["terminals"])


# --------------------------------------------------------------------------- #
# 2. Layout generation
# --------------------------------------------------------------------------- #

class SessionTreeParityTest(BaselineTestCase):
    """The generated Tilix layout is byte-equivalent modulo UUIDs."""

    def _compare(self, dirs, name="T", commands=None):
        def run(module):
            return module.build_tilix_session_tree(dirs, name, commands)

        old = self.parity_side(self.old, lambda: run(self.old), self.root, self.tmpdir)
        new = self.parity_side(self.new, lambda: run(self.new), self.root, self.tmpdir)
        self.assertEqual(normalize_uuids(old["result"]), normalize_uuids(new["result"]))
        return new["result"]

    def test_single_directory_is_equivalent(self):
        self.assertEqual("Terminal", self._compare(["/a"])["child"]["type"])

    def test_empty_list_is_equivalent(self):
        self.assertEqual({}, self._compare([]))

    def test_two_and_three_directories_are_equivalent(self):
        self.assertEqual("Paned", self._compare(["/a", "/b"])["child"]["type"])
        tree = self._compare(["/a", "/b", "/c"])
        self.assertEqual(1, len([tree["child"]["child1"]]))
        self.assertEqual("Paned", tree["child"]["child2"]["type"])

    def test_alternating_orientation_is_equivalent(self):
        tree = self._compare(["/a", "/b", "/c", "/d"])
        self.assertEqual(0, tree["child"]["orientation"])
        self.assertEqual(1, tree["child"]["child1"]["orientation"])

    def test_commands_override_is_equivalent(self):
        tree = self._compare(["/a"], commands={"/a": "bash -c 'echo hi'"})
        self.assertEqual("bash -c 'echo hi'", tree["child"]["overrideCommand"])

    def test_default_command_uses_the_runner_and_is_equivalent(self):
        tree = self._compare(["/a"])
        self.assertIn("tilix_runner.sh", tree["child"]["overrideCommand"])

    def test_session_wrapper_fields_are_equivalent(self):
        tree = self._compare(["/a"], name="X")
        self.assertEqual("SISPER - X", tree["name"])
        self.assertEqual({"height": 1080, "width": 1920, "version": "1.0"},
                         {k: tree[k] for k in ("height", "width", "version")})
        self.assertFalse(tree["synchronizedInput"])


# --------------------------------------------------------------------------- #
# 3. Normalisation of imported sessions
# --------------------------------------------------------------------------- #

class NormalizeSessionParityTest(BaselineTestCase):
    """Imported session paths are rebased identically."""

    def _compare(self, node):
        def run(module):
            copy = json.loads(json.dumps(node))
            module.normalize_session_dict(copy, self.root)
            return copy

        old = self.parity_side(self.old, lambda: run(self.old), self.root, self.tmpdir)
        new = self.parity_side(self.new, lambda: run(self.new), self.root, self.tmpdir)
        self.assertEqual(old["result"], new["result"])
        return new["result"]

    def test_backend_and_frontend_rebasing_is_equivalent(self):
        out = self._compare({"directory": "/old/place/backend/svc"})
        self.assertEqual(str(self.root / "backend" / "svc"), out["directory"])
        out = self._compare({"directory": "/old/place/frontend/web"})
        self.assertEqual(str(self.root / "frontend" / "web"), out["directory"])

    def test_bare_suffix_rebasing_is_equivalent(self):
        self.assertEqual(str(self.root / "backend"),
                         self._compare({"directory": "/old/backend"})["directory"])
        self.assertEqual(str(self.root / "frontend"),
                         self._compare({"directory": "/old/frontend"})["directory"])

    def test_unrelated_and_nested_directories_are_equivalent(self):
        self.assertEqual("/somewhere/else",
                         self._compare({"directory": "/somewhere/else"})["directory"])
        nested = self._compare({"child1": {"directory": "/x/backend/a"},
                                "child2": {"directory": "/x/frontend/b"}})
        self.assertEqual(str(self.root / "backend" / "a"), nested["child1"]["directory"])


# --------------------------------------------------------------------------- #
# 4. Launching
# --------------------------------------------------------------------------- #

class LaunchServicesParityTest(BaselineTestCase):
    """Selected-service launch: result, command and generated session file."""

    def setUp(self):
        super().setUp()
        for name in ("ms_sisper_sesion", "ms_sisper_contratos"):
            (self.root / "backend" / name).mkdir(parents=True, exist_ok=True)
        (self.root / "frontend" / "mf_sisper_sesion").mkdir(parents=True, exist_ok=True)

    def _compare(self, names, env="develop"):
        old = self.parity_side(
            self.old,
            lambda: self.old.launch_custom_services_tilix(names, env, self.root),
            self.root, self.tmpdir)
        new = self.parity_side(
            self.new,
            lambda: self.backend.launch_services(names, env, self.root),
            self.root, self.tmpdir)
        return old, new

    def _assert_same(self, names, env="develop"):
        old, new = self._compare(names, env)
        self.assertEqual(old["result"], new["result"])
        self.assertEqual(old["calls"], new["calls"])
        self.assertEqual(sorted(old["files"]), sorted(new["files"]))
        for name in old["files"]:
            self.assertEqual(self.canonical_json(old["files"][name]),
                             self.canonical_json(new["files"][name]))
        return new

    def test_backend_and_frontend_selection_is_equivalent(self):
        new = self._assert_same(["ms_sisper_sesion", "mf_sisper_sesion"])
        ok, msg, count = new["result"]
        self.assertTrue(ok)
        self.assertEqual(2, count)

    def test_unknown_names_are_dropped_equivalently(self):
        new = self._assert_same(["ms_sisper_sesion", "ms_nope"])
        self.assertEqual(1, new["result"][2])

    def test_no_valid_directories_is_equivalent(self):
        old, new = self._compare(["ms_nope"])
        self.assertEqual(old["result"], new["result"])
        self.assertEqual((False, old["result"][1], 0), new["result"])
        self.assertEqual([], new["calls"])
        self.assertEqual({}, new["files"])

    def test_empty_selection_is_equivalent(self):
        self._assert_same([])

    def test_environment_is_passed_through_equivalently(self):
        new = self._assert_same(["ms_sisper_sesion"], env="test")
        _, argv, kwargs = new["calls"][0]
        self.assertEqual(["tilix", f"--session={self.tmpdir}/tilix_dynamic_"
                                   f"{os.environ.get('USER', 'user')}_selected.json"], argv)
        self.assertEqual("test", kwargs["env"]["SISPER_ENV"])

    def test_cwd_and_env_are_equivalent(self):
        old, new = self._compare(["ms_sisper_sesion", "mf_sisper_sesion"])
        self.assertEqual(old["calls"][0][2]["cwd"], new["calls"][0][2]["cwd"])
        self.assertEqual(old["calls"][0][2]["env"], new["calls"][0][2]["env"])
        self.assertEqual(str((self.root / "backend" / "ms_sisper_sesion").resolve()),
                         new["calls"][0][2]["cwd"])

    def test_single_service_title_is_equivalent(self):
        new = self._assert_same(["ms_sisper_sesion"])
        payload = json.loads(new["files"]["tilix_dynamic_"
                                        f"{os.environ.get('USER', 'user')}_selected.json"])
        self.assertEqual("SISPER - ms_sisper_sesion (DEVELOP)", payload["name"])

    def test_generated_session_file_is_valid_and_formatted_identically(self):
        new = self._assert_same(["ms_sisper_sesion", "mf_sisper_sesion"])
        raw = [v for k, v in new["files"].items() if k.endswith("_selected.json")][0]
        parsed = json.loads(raw.decode("utf-8"))
        # Written with indent=2, exactly as before.
        self.assertEqual(json.dumps(normalize_uuids(parsed), indent=2, ensure_ascii=False),
                         self.canonical_json(raw))
        self.assertEqual("Session", parsed["type"])
        self.assertEqual("Paned", parsed["child"]["type"])

    def test_default_service_list_from_config_is_equivalent(self):
        backend_cfg = [{"name": "ms_sisper_sesion", "port": 8000}]
        front_cfg = [{"name": "mf_sisper_sesion", "port": 3000}]
        with mock.patch.object(dcfg, "SERVICES_BACKEND", backend_cfg), \
             mock.patch.object(dcfg, "SERVICES_FRONTEND", front_cfg):
            self._assert_same(None)

    def test_error_path_is_equivalent(self):
        old = self.parity_side(
            self.old,
            lambda: self.old.launch_custom_services_tilix(
                ["ms_sisper_sesion"], "develop", self.root / "does-not-exist"),
            self.root, self.tmpdir)
        new = self.parity_side(
            self.new,
            lambda: self.backend.launch_services(
                ["ms_sisper_sesion"], "develop", self.root / "does-not-exist"),
            self.root, self.tmpdir)
        self.assertEqual(old["result"], new["result"])
        self.assertFalse(new["result"][0])


class LaunchSessionParityTest(BaselineTestCase):
    """Normalised session launch (``/api/tilix/launch``)."""

    def setUp(self):
        super().setUp()
        self.session = self.root / "imported.json"
        write_session(self.session, build_balanced_session(
            ["/old/backend/svc", "/old/frontend/web"], name="Imported"))

    def _compare(self, env="develop"):
        old = self.parity_side(
            self.old,
            lambda: self.old.launch_tilix_session_normalized(self.session, env),
            self.root, self.tmpdir)
        new = self.parity_side(
            self.new,
            lambda: self.backend.launch_session(self.session, env),
            self.root, self.tmpdir)
        return old, new

    def test_launch_is_equivalent(self):
        old, new = self._compare()
        self.assertEqual(old["result"], new["result"])
        self.assertTrue(new["result"])
        self.assertEqual(old["calls"], new["calls"])

    def test_written_normalised_file_is_equivalent(self):
        old, new = self._compare()
        name = f"tilix_norm_{os.environ.get('USER', 'user')}_imported.json"
        self.assertEqual(self.canonical_json(old["files"][name]),
                         self.canonical_json(new["files"][name]))
        payload = json.loads(new["files"][name].decode("utf-8"))
        dirs = [payload["child"]["child1"]["directory"],
                payload["child"]["child2"]["directory"]]
        self.assertEqual([str(self.root / "backend" / "svc"),
                          str(self.root / "frontend" / "web")], dirs)

    def test_cwd_env_and_argv_are_equivalent(self):
        old, new = self._compare(env="main")
        self.assertEqual(old["calls"][0], new["calls"][0])
        kind, argv, kwargs = new["calls"][0]
        self.assertEqual("Popen", kind)
        self.assertEqual(["tilix", f"--session={self.tmpdir}/tilix_norm_"
                                   f"{os.environ.get('USER', 'user')}_imported.json"], argv)
        self.assertEqual(str(self.root), kwargs["cwd"])
        self.assertEqual("main", kwargs["env"]["SISPER_ENV"])

    def test_missing_session_file_is_equivalent(self):
        capture_output(self)
        missing = self.root / "nope.json"
        old = self.parity_side(
            self.old,
            lambda: self.old.launch_tilix_session_normalized(missing, "develop"),
            self.root, self.tmpdir)
        new = self.parity_side(
            self.new,
            lambda: self.backend.launch_session(missing, "develop"),
            self.root, self.tmpdir)
        self.assertEqual(old["result"], new["result"])
        self.assertFalse(new["result"])
        self.assertEqual([], new["calls"])


class AuxiliaryParityTest(BaselineTestCase):
    """Auxiliary consoles: generated shell script, session file and command."""

    def setUp(self):
        super().setUp()
        (self.root / "backend" / "ms_sisper_sesion").mkdir(parents=True, exist_ok=True)

    def _compare_single(self, aux_type, svc="ms_sisper_sesion"):
        old = self.parity_side(
            self.old,
            lambda: self.old.launch_auxiliary_console(svc, aux_type, "develop", self.root),
            self.root, self.tmpdir)
        new = self.parity_side(
            self.new,
            lambda: self.backend.launch_auxiliary(svc, aux_type, "develop", self.root),
            self.root, self.tmpdir)
        return old, new

    def _assert_single_equivalent(self, aux_type):
        old, new = self._compare_single(aux_type)
        self.assertEqual(old["result"], new["result"])
        self.assertEqual(old["calls"], new["calls"])
        self.assertEqual(sorted(old["files"]), sorted(new["files"]))
        for name in old["files"]:
            if name.endswith(".json"):
                self.assertEqual(self.canonical_json(old["files"][name]),
                                 self.canonical_json(new["files"][name]))
            else:
                # Script bytes must match exactly, including permissions.
                self.assertEqual(old["files"][name], new["files"][name])
        return new

    def test_consumer_is_equivalent(self):
        self._assert_single_equivalent("consumer")

    def test_worker_is_equivalent(self):
        self._assert_single_equivalent("worker")

    def test_beat_is_equivalent(self):
        self._assert_single_equivalent("beat")

    def test_shell_is_equivalent(self):
        self._assert_single_equivalent("shell")

    def test_generated_script_content_is_equivalent(self):
        new = self._assert_single_equivalent("consumer")
        name = f"sisper_aux_{os.environ.get('USER', 'user')}_ms_sisper_sesion_consumer.sh"
        script = new["files"][name].decode("utf-8")
        self.assertIn("#!/usr/bin/env bash", script)
        self.assertIn('cd "', script)
        self.assertIn('export SISPER_ENV="develop"', script)
        self.assertIn("start_consumer", script)

    def test_unknown_auxiliary_type_is_equivalent(self):
        old, new = self._compare_single("nonsense")
        self.assertEqual(old["result"], new["result"])
        self.assertFalse(new["result"][0])
        self.assertEqual({}, new["files"])

    def test_missing_service_directory_is_equivalent(self):
        old, new = self._compare_single("consumer", svc="ms_absent")
        self.assertEqual(old["result"], new["result"])
        self.assertFalse(new["result"][0])

    def test_selected_auxiliaries_are_equivalent(self):
        (self.root / "backend" / "ms_sisper_contratos").mkdir(parents=True, exist_ok=True)
        names = ["ms_sisper_sesion", "ms_sisper_contratos"]
        old = self.parity_side(
            self.old,
            lambda: self.old.launch_selected_auxiliaries(names, "worker", "develop", self.root),
            self.root, self.tmpdir)
        new = self.parity_side(
            self.new,
            lambda: self.backend.launch_selected_auxiliaries(names, "worker", "develop", self.root),
            self.root, self.tmpdir)
        self.assertEqual(old["result"], new["result"])
        self.assertEqual(old["calls"], new["calls"])
        self.assertEqual(sorted(old["files"]), sorted(new["files"]))
        for name in old["files"]:
            if name.endswith(".json"):
                self.assertEqual(self.canonical_json(old["files"][name]),
                                 self.canonical_json(new["files"][name]))
            else:
                self.assertEqual(old["files"][name], new["files"][name])

    def test_empty_selected_auxiliaries_is_equivalent(self):
        old = self.parity_side(
            self.old,
            lambda: self.old.launch_selected_auxiliaries([], "consumer", "develop", self.root),
            self.root, self.tmpdir)
        new = self.parity_side(
            self.new,
            lambda: self.backend.launch_selected_auxiliaries([], "consumer", "develop", self.root),
            self.root, self.tmpdir)
        self.assertEqual(old["result"], new["result"])
        self.assertEqual((False, "No se seleccionaron servicios.", 0), new["result"])


# --------------------------------------------------------------------------- #
# 5. run_action invocation contract
# --------------------------------------------------------------------------- #

class RunActionContractTest(DevConsoleTestCase):
    """``run_action`` reproduces the exact child-process call of each old site.

    The old consumer code called ``subprocess.Popen`` / ``subprocess.run``
    directly, with a different mode per call site for the *same* action
    (``restart-single`` is ``check=True`` in handlers and
    ``check=False``+``timeout=5`` in env_service).  These cases pin every mode
    that was in use.
    """

    def setUp(self):
        super().setUp()
        self.backend = TilixBackend()
        self.recorder = SubprocessRecorder()
        self._stack = contextlib.ExitStack()
        self._stack.enter_context(
            mock.patch.object(tilix_backend.subprocess, "Popen", self.recorder.popen))
        self._stack.enter_context(
            mock.patch.object(tilix_backend.subprocess, "run", self.recorder.run))
        self.addCleanup(self._stack.close)
        self.base = Path("/tmp/parity-launcher")

    def _call(self, *args, **kwargs):
        self.recorder.calls.clear()
        self.backend.run_action(*args, base_dir=self.base, **kwargs)
        self.assertEqual(1, len(self.recorder.calls))
        return self.recorder.calls[0]

    def test_fire_and_forget_passes_no_extra_kwargs(self):
        kind, argv, kwargs = self._call("tabs", wait=False)
        self.assertEqual("Popen", kind)
        self.assertEqual([f"{self.base}/start_tilix.sh", "tabs"], argv)
        self.assertEqual({}, kwargs, "the old call site passed no cwd/env at all")

    def test_stop_close_matches_old_site(self):
        kind, argv, kwargs = self._call("stop-close", wait=False)
        self.assertEqual(("Popen", [f"{self.base}/start_tilix.sh", "stop-close"], {}),
                         (kind, argv, kwargs))

    def test_blocking_restart_matches_old_site(self):
        kind, argv, kwargs = self._call("restart", wait=True, check=True)
        self.assertEqual("run", kind)
        self.assertEqual([f"{self.base}/start_tilix.sh", "restart"], argv)
        self.assertEqual({"check": True}, kwargs, "timeout must stay absent when unset")

    def test_restart_single_with_check_matches_handler_site(self):
        kind, argv, kwargs = self._call("restart-single", ("ms_x", "8000"),
                                        wait=True, check=True)
        self.assertEqual([f"{self.base}/start_tilix.sh", "restart-single", "ms_x", "8000"], argv)
        self.assertEqual({"check": True}, kwargs)

    def test_restart_single_with_timeout_matches_env_service_site(self):
        kind, argv, kwargs = self._call("restart-single", ("ms_x", "8000"),
                                        wait=True, check=False, timeout=5)
        self.assertEqual([f"{self.base}/start_tilix.sh", "restart-single", "ms_x", "8000"], argv)
        self.assertEqual({"check": False, "timeout": 5}, kwargs)

    def test_start_with_extra_args_matches_slice_site(self):
        kind, argv, kwargs = self._call("start", ("ms_x", "8000"), wait=False)
        self.assertEqual([f"{self.base}/start_tilix.sh", "start", "ms_x", "8000"], argv)
        self.assertEqual({}, kwargs)

    def test_base_dir_defaults_to_module_base_dir(self):
        self.recorder.calls.clear()
        self.backend.run_action("restart", wait=True, check=True)
        self.assertEqual(
            [str(dcfg.BASE_DIR / "start_tilix.sh"), "restart"],
            self.recorder.calls[0][1])

    def test_check_failure_propagates_unchanged(self):
        """``check=True`` must still raise, exactly as the old call did."""
        with mock.patch.object(tilix_backend.subprocess, "run",
                               side_effect=subprocess.CalledProcessError(1, ["x"])):
            with self.assertRaises(subprocess.CalledProcessError):
                self.backend.run_action("restart", wait=True, check=True, base_dir=self.base)

    def test_known_actions_cover_every_action_used_in_the_codebase(self):
        """Every action passed to run_action is in the documented vocabulary."""
        import re
        source = (REPO_ROOT / "devconsole" / "api" / "handlers.py").read_text(encoding="utf-8")
        source += (REPO_ROOT / "devconsole" / "services" / "env_service.py").read_text(
            encoding="utf-8")
        used = set(re.findall(r'run_action\(\s*"([^"]+)"', source))
        self.assertTrue(used, "expected run_action call sites in the consumers")
        self.assertTrue(used <= KNOWN_ACTIONS, f"undocumented actions: {used - KNOWN_ACTIONS}")


# --------------------------------------------------------------------------- #
# 6. Interface conformance
# --------------------------------------------------------------------------- #

class TerminalBackendContractTest(DevConsoleTestCase):
    """The abstraction is a real seam and leaks no Tilix concept."""

    def test_tilix_backend_implements_the_contract(self):
        self.assertTrue(issubclass(TilixBackend, TerminalBackend))
        self.assertEqual("tilix", TilixBackend.name)
        self.assertNotEqual("unknown", TilixBackend.name)

    def test_contract_cannot_be_instantiated_directly(self):
        with self.assertRaises(TypeError):
            TerminalBackend()

    def test_no_abstract_method_is_left_unimplemented(self):
        self.assertEqual(set(), set(TerminalBackend.__abstractmethods__)
                         - set(dir(TilixBackend)))
        self.assertIsInstance(TilixBackend(), TerminalBackend)

    def test_abstract_surface_is_exactly_the_six_operations(self):
        """Fase 3 must only have to implement these to add a backend."""
        self.assertEqual(
            {"scan_sessions", "launch_session", "launch_services",
             "launch_auxiliary", "launch_selected_auxiliaries", "run_action"},
            set(TerminalBackend.__abstractmethods__))

    def test_contract_signatures_mention_no_tilix_specific_concept(self):
        import inspect
        forbidden = ("tilix", "session_file", "overrideCommand", "Paned",
                     "profile", "uuid", "norm_file", "aux_sess")
        for name in TerminalBackend.__abstractmethods__:
            rendered = f"{name}{inspect.signature(getattr(TerminalBackend, name))}"
            for token in forbidden:
                self.assertNotIn(token.lower(), rendered.lower(),
                                 f"{name} leaks {token!r} into the backend contract")

    def test_tilix_internals_stay_inside_the_tilix_module(self):
        """JSON/Paned/uuid/overrideCommand are Tilix's business, not the API's."""
        self.assertTrue(hasattr(tilix_backend, "build_tilix_session_tree"))
        self.assertFalse(hasattr(TerminalBackend, "build_tilix_session_tree"))
        for name in ("normalize_session_dict", "count_terminals_in_node",
                     "_prepare_tilix_env"):
            self.assertFalse(hasattr(TerminalBackend, name),
                             f"{name} must not be part of the backend contract")

    def test_tmux_backend_exists_and_is_registered(self):
        """Phase 3 ships the tmux backend; Phase 2's exclusion no longer holds.

        Phase 2 asserted the opposite on purpose — that no tmux implementation
        existed yet.  Phase 3 implements it, so the assertion is inverted rather
        than deleted, and the *policy* it protected (only implemented backends
        are selectable) is still tested below.
        """
        terminal_dir = REPO_ROOT / "devconsole" / "services" / "terminal"
        self.assertTrue((terminal_dir / "tmux_backend.py").exists())
        self.assertIn("tmux", terminal_registry.IMPLEMENTED)
        self.assertIn("tilix", terminal_registry.IMPLEMENTED)
        self.assertEqual({"tilix", "tmux"}, set(terminal_registry.IMPLEMENTED))

    def test_default_backend_did_not_change_in_phase_3(self):
        """A missing env var must still land on tilix, for safe rollback."""
        self.assertEqual("tilix", DEFAULT_BACKEND)
        self.assertEqual("tilix", terminal_registry.DEFAULT_BACKEND)

    def test_no_new_external_dependency_was_added(self):
        source = (REPO_ROOT / "devconsole" / "services" / "terminal" / "base.py"
                  ).read_text(encoding="utf-8")
        self.assertNotIn("import pty", source)
        self.assertNotIn("import pexpect", source)
        self.assertNotIn("libtmux", source)
        self.assertIn("from abc import ABC, abstractmethod", source)


class ConsumersDoNotKnowTilixTest(DevConsoleTestCase):
    """The real payoff: no consumer names Tilix or its launcher any more."""

    CONSUMERS = (
        "devconsole/api/handlers.py",
        "devconsole/services/env_service.py",
    )

    def _code(self, rel: str) -> str:
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        return "\n".join(line for line in text.splitlines()
                         if not line.lstrip().startswith("#"))

    def test_consumers_do_not_import_the_legacy_module(self):
        for rel in self.CONSUMERS:
            with self.subTest(consumer=rel):
                self.assertNotIn("tilix_service", self._code(rel))

    def test_consumers_do_not_resolve_the_launcher_script(self):
        for rel in self.CONSUMERS:
            with self.subTest(consumer=rel):
                self.assertNotIn("start_tilix.sh", self._code(rel))

    def test_consumers_reach_the_backend_through_the_factory(self):
        for rel in self.CONSUMERS:
            with self.subTest(consumer=rel):
                code = self._code(rel)
                self.assertIn("get_terminal_backend", code)
                self.assertNotIn("TilixBackend", code,
                                 "consumers must not bind a concrete backend")

    def test_legacy_import_path_still_works(self):
        """The compatibility shim keeps every historical import usable."""
        import devconsole.services.tilix_service as legacy
        self.assertIs(legacy, tilix_backend)
        for name in ("scan_tilix_sessions", "build_tilix_session_tree",
                     "normalize_session_dict", "count_terminals_in_node",
                     "launch_tilix_session_normalized", "launch_custom_services_tilix",
                     "launch_auxiliary_console", "launch_selected_auxiliaries"):
            self.assertTrue(hasattr(legacy, name), f"shim lost {name}")

    def test_legacy_and_backend_share_one_namespace(self):
        """Patching the legacy path must affect the code that actually runs."""
        write_session(self.root_session() / "s.json", build_balanced_session(["/a"]))
        with mock.patch.object(tilix_backend, "BASE_DIR", self.root_session()):
            self.assertEqual(1, len(TilixBackend().scan_sessions()))
        with mock.patch.object(tilix_backend, "scan_tilix_sessions", return_value=["x"]):
            self.assertEqual(["x"], TilixBackend().scan_sessions())

    def root_session(self) -> Path:
        if not hasattr(self, "_root"):
            self._root = make_workspace(self.temp_dir())
        return self._root


# --------------------------------------------------------------------------- #
# 7. Factory / backend selection
# --------------------------------------------------------------------------- #

class BackendFactoryTest(DevConsoleTestCase):
    """``SISPER_TERMINAL_BACKEND`` selection rules."""

    def setUp(self):
        super().setUp()
        self.addCleanup(reset_terminal_backend)
        reset_terminal_backend()

    def _with_env(self, value):
        if value is None:
            os.environ.pop(ENV_VAR, None)
        else:
            os.environ[ENV_VAR] = value

    def test_default_backend_is_tilix(self):
        self.assertEqual("tilix", DEFAULT_BACKEND)
        self.assertEqual("tilix", resolve_backend_name(None))
        self._with_env(None)
        self.assertEqual("tilix", get_terminal_backend().name)

    def test_explicit_tilix_resolves_to_tilix(self):
        self._with_env("tilix")
        self.assertEqual("tilix", get_terminal_backend().name)
        self.assertIsInstance(get_terminal_backend(), TilixBackend)

    def test_matching_is_case_and_whitespace_insensitive(self):
        for value in ("TILIX", "Tilix", "  tilix  ", "\ttilix\n", " TILIX "):
            with self.subTest(value=value):
                reset_terminal_backend()
                self._with_env(value)
                self.assertEqual("tilix", get_terminal_backend().name)

    def test_empty_values_fall_back_to_the_default(self):
        for value in ("", "   ", "\t"):
            with self.subTest(value=repr(value)):
                reset_terminal_backend()
                self._with_env(value)
                self.assertEqual("tilix", resolve_backend_name())

    def test_tmux_now_selects_the_tmux_backend(self):
        """Phase 3: ``tmux`` graduated from reserved to implemented."""
        from devconsole.services.terminal import TmuxBackend
        for value in ("tmux", "TMUX", " tmux "):
            with self.subTest(value=value):
                reset_terminal_backend()
                self._with_env(value)
                self.assertEqual("tmux", resolve_backend_name())
                self.assertIsInstance(get_terminal_backend(), TmuxBackend)

    def test_a_reserved_name_is_still_rejected(self):
        """The two-tier policy survives even though its only member graduated.

        Tested by reserving a synthetic name, so the mechanism stays covered
        without inventing a real backend.
        """
        with mock.patch.object(terminal_registry, "RESERVED_UNIMPLEMENTED",
                               frozenset({"futuretmux"})):
            reset_terminal_backend()
            with self.assertRaises(UnsupportedTerminalBackend) as ctx:
                resolve_backend_name("futuretmux")
            message = str(ctx.exception)
            self.assertIn(ENV_VAR, message)
            self.assertIn("tilix", message)
            self.assertIn("nothing was started", message)

    def test_reserved_set_is_empty_now_that_tmux_is_implemented(self):
        self.assertEqual(frozenset(), terminal_registry.RESERVED_UNIMPLEMENTED)

    def test_unknown_value_warns_once_and_falls_back_to_tilix(self):
        out, err = capture_output(self)
        self._with_env("tliix")
        self.assertEqual("tilix", resolve_backend_name())
        self.assertEqual("tilix", get_terminal_backend().name)
        first = err.getvalue()
        self.assertIn("unknown backend", first)
        self.assertIn("'tliix'", first)
        self.assertIn("falling back to 'tilix'", first)
        # A second call must not repeat the warning (per-request safety).
        self.assertEqual("tilix", get_terminal_backend().name)
        self.assertEqual(first, err.getvalue())
        self.assertEqual("", out.getvalue())

    def test_unknown_value_never_yields_a_different_backend(self):
        capture_output(self)
        self._with_env("anything-else")
        self.assertIsInstance(get_terminal_backend(), TilixBackend)
        self.assertEqual("tilix", get_terminal_backend().name)

    def test_instance_is_cached_while_the_name_is_stable(self):
        self._with_env("tilix")
        self.assertIs(get_terminal_backend(), get_terminal_backend())

    def test_instance_is_rebuilt_when_configuration_changes(self):
        self._with_env("tilix")
        first = get_terminal_backend()
        self._with_env("tilix")          # same name -> cached
        self.assertIs(first, get_terminal_backend())
        reset_terminal_backend()
        self.assertIsNot(first, get_terminal_backend())

    def test_explicit_name_overrides_the_environment(self):
        self._with_env("tilix")
        self.assertEqual("tilix", get_terminal_backend("tilix").name)

    def test_unknown_terminal_env_is_not_read_at_import_time(self):
        """Selection is lazy: importing the package must not read the env."""
        source = (REPO_ROOT / "devconsole" / "services" / "terminal" / "registry.py"
                  ).read_text(encoding="utf-8")
        self.assertIn('os.environ.get(ENV_VAR, "")', source)
        self.assertNotIn("os.environ[ENV_VAR]", source)


# --------------------------------------------------------------------------- #
# 8. Public API delegation
# --------------------------------------------------------------------------- #

class FakeBackend(TerminalBackend):
    """Records every call routed through the abstraction."""

    name = "fake"

    def __init__(self):
        self.calls = []
        self.available = False

    def scan_sessions(self):
        self.calls.append(("scan_sessions",))
        return [{"name": "fake.json", "rel_path": "fake.json",
                 "abs_path": "/x/fake.json", "terminals": 7, "is_default": False}]

    def launch_session(self, session_path, environment="develop"):
        self.calls.append(("launch_session", str(session_path), environment))
        return self.available

    def launch_services(self, services=None, environment="develop", base_dir=None):
        self.calls.append(("launch_services", services, environment))
        return True, "fake services", 3

    def launch_auxiliary(self, service, aux_type="consumer", environment="develop",
                         base_dir=None):
        self.calls.append(("launch_auxiliary", service, aux_type, environment))
        return True, "fake auxiliary"

    def launch_selected_auxiliaries(self, services, aux_type="consumer",
                                    environment="develop", base_dir=None):
        self.calls.append(("launch_selected_auxiliaries", services, aux_type))
        return True, "fake selected", 2

    def run_action(self, action, args=(), *, wait, check=False, timeout=None,
                   base_dir=None):
        self.calls.append(("run_action", action, tuple(args), wait, check, timeout))
        return mock.MagicMock(returncode=0)


class EndpointsDelegateToBackendTest(DevConsoleTestCase):
    """The endpoints must go *through* the backend, not around it.

    Replacing the backend with a fake and observing the response proves there is
    no second hardcoded implementation sitting behind the public API, and that
    handlers is wired to the abstraction rather than to Tilix.
    """

    def setUp(self):
        super().setUp()
        self.fake = FakeBackend()
        self.root = make_workspace(self.temp_dir())
        self._stack = contextlib.ExitStack()
        self.addCleanup(self._stack.close)
        for target, value in (
                ("get_terminal_backend", lambda *a, **k: self.fake),
                ("BASE_DIR", self.root),
                ("DASHBOARD_DIR", self.root),
                ("is_port_open", lambda p: False),
                ("get_running_services_info", lambda: []),
                ("scan_tilix_sessions", lambda: [])):
            module = handlers
            if hasattr(module, target):
                self._stack.enter_context(
                    mock.patch.object(module, target,
                                      value if callable(value) else value))
        self._stack.enter_context(mock.patch.object(dcfg, "BASE_DIR", self.root))

    # -- helpers ------------------------------------------------------------ #

    def get(self, path):
        h = make_handler(DevConsoleHandler, path=path, method="GET")
        h.do_GET()
        return h

    def post(self, path, payload):
        body = json.dumps(payload).encode("utf-8")
        h = make_handler(DevConsoleHandler, path=path, method="POST", body=body)
        h.do_POST()
        return h

    @staticmethod
    def body(handler):
        return json.loads(handler.wfile.getvalue().decode("utf-8"))

    # -- read path ---------------------------------------------------------- #

    def test_sessions_endpoint_uses_the_backend(self):
        h = self.get("/api/tilix/sessions")
        self.assertEqual(200, h.captured["status"])
        self.assertEqual(7, self.body(h)["sessions"][0]["terminals"])
        self.assertIn(("scan_sessions",), self.fake.calls)

    def test_sessions_endpoint_does_not_call_the_implementation_directly(self):
        with mock.patch.object(tilix_backend, "scan_tilix_sessions") as direct:
            self.get("/api/tilix/sessions")
        self.assertFalse(direct.called,
                         "handlers must reach the scan only through the backend")

    # -- launch paths ------------------------------------------------------- #

    def test_launch_selected_endpoint_uses_the_backend(self):
        h = self.post("/api/tilix/launch_selected",
                      {"services": ["ms_sisper_sesion"], "env": "test"})
        self.assertEqual(200, h.captured["status"])
        self.assertEqual({"success": True, "message": "fake services", "count": 3},
                         self.body(h))
        self.assertIn(("launch_services", ["ms_sisper_sesion"], "test"), self.fake.calls)

    def test_launch_auxiliary_endpoint_uses_the_backend(self):
        h = self.post("/api/tilix/launch_auxiliary",
                      {"service": "ms_sisper_sesion", "aux_type": "worker"})
        self.assertEqual(200, h.captured["status"])
        self.assertEqual("fake auxiliary", self.body(h)["message"])
        self.assertIn(("launch_auxiliary", "ms_sisper_sesion", "worker", "develop"),
                      self.fake.calls)

    def test_launch_selected_auxiliary_endpoint_uses_the_backend(self):
        h = self.post("/api/tilix/launch_selected_auxiliary",
                      {"services": ["a", "b"], "aux_type": "beat"})
        self.assertEqual(200, h.captured["status"])
        self.assertEqual(2, self.body(h)["count"])
        self.assertIn(("launch_selected_auxiliaries", ["a", "b"], "beat"), self.fake.calls)

    def test_launch_session_endpoint_uses_the_backend(self):
        session = self.root / "s.json"
        write_session(session, build_balanced_session(["/a"]))
        self.fake.available = True
        h = self.post("/api/tilix/launch", {"session_path": str(session), "env": "main"})
        self.assertEqual(200, h.captured["status"])
        self.assertIn(("launch_session", str(session), "main"), self.fake.calls)

    def test_missing_session_is_still_rejected_before_the_backend(self):
        h = self.post("/api/tilix/launch", {"session_path": str(self.root / "no.json")})
        self.assertEqual(400, h.captured["status"])
        self.assertEqual([], self.fake.calls, "validation must precede the backend")

    def test_action_endpoint_routes_restart_through_run_action(self):
        h = self.post("/api/action", {"action": "restart"})
        self.assertEqual(200, h.captured["status"])
        self.assertIn(("run_action", "restart", (), True, True, None), self.fake.calls)

    def test_action_endpoint_routes_restart_single_through_run_action(self):
        self.post("/api/action", {"action": "restart-single",
                                  "service": "ms_x", "port": 8000})
        self.assertIn(("run_action", "restart-single", ("ms_x", "8000"), True, True, None),
                      self.fake.calls)

    def test_action_endpoint_routes_stop_through_run_action(self):
        self.post("/api/action", {"action": "stop"})
        self.assertIn(("run_action", "stop", (), False, False, None), self.fake.calls)

    def test_action_endpoint_does_not_touch_subprocess_for_console_actions(self):
        """Console actions must not spawn anything from the consumer layer."""
        with mock.patch.object(handlers.subprocess, "Popen") as popen, \
             mock.patch.object(handlers.subprocess, "run") as run:
            self.post("/api/action", {"action": "restart"})
            self.post("/api/action", {"action": "tabs"})
        self.assertFalse(popen.called, "console launches must go through the backend")
        self.assertFalse(run.called)


# --------------------------------------------------------------------------- #
# 9. Public API surface unchanged
# --------------------------------------------------------------------------- #

class PublicApiUnchangedTest(DevConsoleTestCase):
    """No endpoint was renamed, re-schematised or re-statused by the refactor."""

    def setUp(self):
        super().setUp()
        self.root = make_workspace(self.temp_dir())
        self._stack = contextlib.ExitStack()
        self.addCleanup(self._stack.close)
        self.fake = FakeBackend()
        for target, value in (
                ("get_terminal_backend", lambda *a, **k: self.fake),
                ("BASE_DIR", self.root),
                ("is_port_open", lambda p: False),
                ("get_running_services_info", lambda: [])):
            self._stack.enter_context(mock.patch.object(handlers, target, value))
        self._stack.enter_context(mock.patch.object(dcfg, "BASE_DIR", self.root))

    def _get(self, path):
        h = make_handler(DevConsoleHandler, path=path, method="GET")
        h.do_GET()
        return h

    def test_tilix_endpoints_keep_their_names(self):
        for path in ("/api/tilix/sessions",):
            with self.subTest(path=path):
                self.assertEqual(200, self._get(path).captured["status"])

    def test_no_terminal_endpoint_was_introduced(self):
        source = (REPO_ROOT / "devconsole" / "api" / "handlers.py").read_text(encoding="utf-8")
        self.assertNotIn("/api/terminal", source,
                         "public URLs must not be renamed in Phase 2")

    def test_sessions_payload_keys_are_unchanged(self):
        h = self._get("/api/tilix/sessions")
        self.assertEqual({"base_dir", "sessions"}, set(json.loads(
            h.wfile.getvalue().decode("utf-8")).keys()))

    def test_launch_selected_payload_keys_are_unchanged(self):
        body = json.dumps({"services": ["a"]}).encode("utf-8")
        h = make_handler(DevConsoleHandler, path="/api/tilix/launch_selected",
                         method="POST", body=body)
        h.do_POST()
        payload = json.loads(h.wfile.getvalue().decode("utf-8"))
        self.assertEqual({"success", "message", "count"}, set(payload.keys()))

    def test_status_codes_for_failures_are_unchanged(self):
        self.fake.launch_services = lambda *a, **k: (False, "boom", 0)
        body = json.dumps({"services": ["a"]}).encode("utf-8")
        h = make_handler(DevConsoleHandler, path="/api/tilix/launch_selected",
                         method="POST", body=body)
        h.do_POST()
        self.assertEqual(400, h.captured["status"])
