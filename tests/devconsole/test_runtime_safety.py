"""Safety invariants for the runtime layer (roadmap phase 0B, rules 1-6/16-21).

These tests are the enforcement mechanism for the phase's hard constraints:

* the runtime package must contain **no destructive primitive** at all;
* the legacy kill surface must be **byte-identical** to the frozen baseline;
* the shadow hook must be provably inert in the default ``legacy`` mode.

Note on the scan in :class:`NoDestructivePrimitivesTest`: the check runs over
AST-unparsed code with docstrings removed, because the package *documents* the
prohibition (its ``__init__`` docstring names the forbidden commands).  Scanning
raw text would produce false positives on the documentation itself.
"""

from __future__ import annotations

import ast
import os
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from tests.devconsole.support import DevConsoleTestCase

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = REPO_ROOT / "devconsole" / "services" / "runtime"

#: Files that must not change at all: the complete legacy kill surface plus the
#: Tilix launch/run scripts and the Tilix session/launch implementation.
FROZEN_LEGACY_FILES = (
    # The 18 destructive call sites live here; no phase may touch them silently.
    "start_tilix.sh",
    "tilix_runner.sh",
    "switch_env.sh",
    # The Tilix session/launch contract.  Phase 2 moved this implementation
    # verbatim out of devconsole/services/tilix_service.py (now a compatibility
    # shim), so the freeze follows the code it protects instead of the import
    # path it used to live at.  Entries missing from HEAD are skipped, which is
    # how this path stays verifiable before its first commit.
    "devconsole/services/terminal/tilix_backend.py",
)

#: ``install_devconsole.sh`` is an installer (systemd unit + .desktop entry), not
#: part of the kill surface -- it contains no destructive primitive.  Phase 0C.5
#: legitimately edits it to declare ``SISPER_HOST`` for future installations, so
#: it is covered by an invariant on its *content* rather than on its bytes.
INSTALLER_SCRIPT = "install_devconsole.sh"

#: Every legacy script that must never gain a destructive primitive.
LEGACY_SCRIPTS_NEVER_DESTRUCTIVE = (
    "install_devconsole.sh",
)

#: The runtime package from phase 0B.  Phase 0C is a security-boundary change
#: and must not alter process-identity semantics.
#:
#: Phase 3F-ID note: ``process_ownership.py`` was removed from this list because
#: that phase changes identity *grading* on purpose — Fedora ships ``node-22``
#: and webpack-dev-server rewrites its own process title, so no frontend could
#: ever exceed MEDIUM.  The guarantee is not dropped, it is **strengthened**:
#: ``tests/devconsole/test_frontend_identity.py`` pins the exact grade of a case
#: matrix on both the pre- and post-change logic and fails if any negative case
#: is weakened.  The other five files stay frozen: 3F-ID touched only this one.
FROZEN_RUNTIME_FILES = (
    "devconsole/services/runtime/process_identity.py",
    "devconsole/services/runtime/process_inspector.py",
    "devconsole/services/runtime/process_resolver.py",
    "devconsole/services/runtime/shadow.py",
    "devconsole/services/runtime/audit.py",
)

#: Tokens indicating a destructive capability, checked against *code* only.
FORBIDDEN_CODE_TOKENS = (
    "pkill",
    "killall",
    "os.kill",
    "os.killpg",
    "SIGKILL",
    "SIGTERM",
    "SIGHUP",
    "fuser -k",
)


def _python_sources(directory: Path) -> list[Path]:
    return sorted(p for p in directory.rglob("*.py") if "__pycache__" not in p.parts)


def code_without_docstrings(path: Path) -> str:
    """Return the module's code with docstrings and comments stripped.

    Implemented by parsing and re-unparsing the AST: ``ast.unparse`` drops
    comments, and docstring expression statements are removed beforehand.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstring_owners = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    for node in ast.walk(tree):
        if isinstance(node, docstring_owners) and node.body:
            first = node.body[0]
            if (isinstance(first, ast.Expr)
                    and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                node.body = node.body[1:] or [ast.Pass()]
    return ast.unparse(tree)


class NoDestructivePrimitivesTest(DevConsoleTestCase):
    """The runtime package must be incapable of terminating a process."""

    def test_runtime_package_exists(self):
        self.assertTrue(RUNTIME_DIR.is_dir())
        self.assertGreaterEqual(len(_python_sources(RUNTIME_DIR)), 6)

    def test_no_destructive_tokens_in_runtime_code(self):
        offenders: list[str] = []
        for path in _python_sources(RUNTIME_DIR):
            code = code_without_docstrings(path)
            for token in FORBIDDEN_CODE_TOKENS:
                if token in code:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")
        self.assertEqual([], offenders,
                         "the runtime package must contain no destructive primitive")

    def test_docstrings_are_not_scanned_but_do_document_the_prohibition(self):
        """Sanity check on the scanner itself, plus the advisory docstring."""
        raw = (RUNTIME_DIR / "__init__.py").read_text(encoding="utf-8")
        self.assertIn("pkill", raw, "the package should document what it must not do")
        self.assertNotIn("pkill", code_without_docstrings(RUNTIME_DIR / "__init__.py"))

    def test_no_signal_module_import(self):
        for path in _python_sources(RUNTIME_DIR):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertNotEqual("signal", alias.name,
                                            f"{path.name} must not import signal")
                elif isinstance(node, ast.ImportFrom):
                    self.assertNotEqual("signal", node.module,
                                        f"{path.name} must not import signal")

    def test_no_popen_and_no_shell_true(self):
        for path in _python_sources(RUNTIME_DIR):
            code = code_without_docstrings(path)
            self.assertNotIn("shell=True", code, path.name)
            self.assertNotIn("Popen", code, path.name)

    def test_no_subprocess_call_receives_a_legacy_script(self):
        """The runtime may *name* start_tilix.sh (as a lineage hint) but must
        never hand it to a subprocess."""
        offenders: list[str] = []
        for path in _python_sources(RUNTIME_DIR):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                target = None
                if isinstance(func, ast.Attribute):
                    target = func.attr
                elif isinstance(func, ast.Name):
                    target = func.id
                if target not in ("run", "Popen", "call", "check_call", "check_output", "system"):
                    continue
                rendered = ast.unparse(node)
                for script in ("start_tilix.sh", "tilix_runner.sh", "switch_env.sh"):
                    if script in rendered:
                        offenders.append(f"{path.name}: {script} in {rendered[:80]}")
        self.assertEqual([], offenders)

    def test_legacy_script_names_are_only_used_as_detection_hints(self):
        """They must appear solely inside the module-level hint constants."""
        path = RUNTIME_DIR / "process_ownership.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        hint_values: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id.startswith("_")
                    and ("HINTS" in t.id or "PATTERNS" in t.id)
                    for t in node.targets):
                for sub in ast.walk(node.value):
                    if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                        hint_values.add(sub.value)
        self.assertIn("start_tilix.sh", hint_values)
        self.assertIn("tilix_runner.sh", hint_values)

    def test_fuser_fallback_asserts_against_kill_flag(self):
        source = (RUNTIME_DIR / "process_inspector.py").read_text(encoding="utf-8")
        self.assertIn('if "-k" in cmd:', source)
        self.assertIn('cmd = ["fuser", f"{int(port)}/tcp"]', source)

    def test_only_subprocess_use_is_the_query_fallback(self):
        """Only the inspector may use subprocess, and only for the fuser query."""
        inspector_code = code_without_docstrings(RUNTIME_DIR / "process_inspector.py")
        self.assertEqual(1, inspector_code.count("subprocess.run"),
                         "expected exactly one read-only subprocess call")

        others = ("shadow.py", "process_ownership.py", "process_resolver.py",
                  "process_identity.py", "audit.py", "__init__.py", "__main__.py")
        for name in others:
            code = code_without_docstrings(RUNTIME_DIR / name)
            self.assertNotIn("subprocess", code,
                             f"{name} must not use subprocess at all")


class LegacySurfaceFrozenTest(unittest.TestCase):
    """The legacy **kill surface** must stay untouched.

    Scope note: during phase 0B this class asserted that *no* production file
    other than ``env_service.py`` changed.  Phase 0C legitimately rewrites
    ``handlers.py``, ``config.py``, ``server.py``, ``auth.py`` and
    ``build_service.py`` to build the local security boundary, so the invariant
    is re-scoped to what actually must not drift: the shell scripts that
    terminate processes, the per-pane supervisor, and the ``runtime`` package.

    Phase 2 note: ``devconsole/services/tilix_service.py`` was legitimately
    rewritten as a compatibility shim when its implementation moved to
    ``devconsole/services/terminal/tilix_backend.py``.  The freeze was moved to
    the new path rather than dropped, so the original guarantee — the Tilix
    launch contract may not change silently — still holds.  Behavioural parity
    across that move is covered separately by
    ``tests/devconsole/test_terminal_backend.py``.

    Uses plain :class:`unittest.TestCase` rather than the guarded base class:
    ``git show`` is read-only, and the guard exists to forbid *destructive*
    child processes.  No repository state is written.
    """

    @staticmethod
    def _git_show(rel_path: str) -> bytes | None:
        """Return ``HEAD:rel_path`` bytes, or ``None`` if absent from HEAD."""
        try:
            return subprocess.check_output(
                ["git", "-C", str(REPO_ROOT), "show", f"HEAD:{rel_path}"],
                stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            return None

    def test_frozen_files_are_byte_identical_to_head(self):
        changed = []
        for rel in FROZEN_LEGACY_FILES:
            baseline = self._git_show(rel)
            if baseline is None:
                # Not in HEAD yet: nothing to compare against.  The freeze
                # starts applying from the commit that introduces it.
                continue
            if (REPO_ROOT / rel).read_bytes() != baseline:
                changed.append(rel)
        self.assertEqual(
            [], changed,
            "no phase may silently modify the legacy kill surface, the Tilix "
            "launch scripts or the Tilix launch implementation")

    def test_non_kill_legacy_scripts_have_no_destructive_primitive(self):
        """A script outside the frozen kill surface must not gain one either."""
        import re as _re

        patterns = (r"\bpkill\b", r"\bkillall\b", r"fuser\s+-k", r"os\.kill")
        for rel in LEGACY_SCRIPTS_NEVER_DESTRUCTIVE:
            with self.subTest(script=rel):
                text = (REPO_ROOT / rel).read_text(encoding="utf-8")
                # Comments are stripped so documentation about the prohibition
                # is not mistaken for the prohibition being violated.
                code = "\n".join(l for l in text.splitlines()
                                  if not l.lstrip().startswith("#"))
                for pattern in patterns:
                    self.assertIsNone(
                        _re.search(pattern, code),
                        f"{rel} must not contain {pattern!r}")

    def test_installer_declares_the_loopback_bind(self):
        """Future installations must inherit the hardened listener."""
        text = (REPO_ROOT / INSTALLER_SCRIPT).read_text(encoding="utf-8")
        self.assertIn("Environment=SISPER_HOST=127.0.0.1", text)
        self.assertNotIn("Environment=SISPER_HOST=0.0.0.0", text)

    def test_runtime_package_unchanged_by_later_phases(self):
        """Process-identity semantics must not drift in a security phase."""
        changed = [rel for rel in FROZEN_RUNTIME_FILES
                   if (REPO_ROOT / rel).read_bytes() != self._git_show(rel)]
        self.assertEqual([], changed,
                         "the runtime package must be byte-identical to its 0B state")

    def test_legacy_restart_command_unchanged(self):
        """The restart invocation must stay identical to the baseline.

        Phase 2 note: the call is now worded as a terminal-backend action
        instead of a direct ``subprocess.run([tilix_script, ...])``.  The
        command is unchanged — same launcher, same argv, same ``check`` and
        ``timeout`` — and is still asserted argument by argument, through the
        real ``subprocess.run`` mock, by
        ``test_env_service.test_restart_true_invokes_start_tilix_restart_single``.
        This tripwire keeps the count pinned at two and forbids the consumer
        from resolving the launcher script itself again.
        """
        text = (REPO_ROOT / "devconsole/services/env_service.py").read_text(encoding="utf-8")
        self.assertEqual(
            2, text.count('"restart-single", (svc_name, str(port)),'),
            "expected exactly the two pre-existing restart call sites")
        self.assertIn("wait=True, check=False, timeout=5, base_dir=BASE_DIR", text,
                      "the restart must keep the baseline check/timeout semantics")
        self.assertNotIn("tilix_script", text,
                         "env_service must no longer resolve start_tilix.sh itself")
        self.assertNotIn("subprocess.run([tilix_script", text)

    def test_handlers_have_no_unreturned_denial(self):
        """BR-01 tripwire, now permanent.

        Every ``send_json`` that reports a denial must be followed by a
        ``return`` before the next statement of the same block.  This is the
        structural form of the bug that let a 403 fall through into the
        protected handler.
        """
        import ast

        source = (REPO_ROOT / "devconsole/api/handlers.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        offenders = []
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if not isinstance(body, list):
                continue
            for index, stmt in enumerate(body[:-1]):
                if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Call):
                    continue
                call = stmt.value
                name = getattr(call.func, "attr", getattr(call.func, "id", ""))
                if name != "send_json":
                    continue
                status = None
                for kw in call.keywords:
                    if kw.arg == "status" and isinstance(kw.value, ast.Constant):
                        status = kw.value.value
                if isinstance(status, int) and status >= 400:
                    nxt = body[index + 1]
                    if not isinstance(nxt, ast.Return):
                        offenders.append(f"line {stmt.lineno}: status={status} "
                                         f"followed by {type(nxt).__name__}")
        self.assertEqual([], offenders,
                         "a denial response must be followed by return (BR-01)")


class ShadowHookInertTest(DevConsoleTestCase):
    """In the default ``legacy`` mode the hook must be a provable no-op."""

    def setUp(self):
        super().setUp()
        from devconsole.services import env_service
        self.env_service = env_service

    def test_hook_returns_immediately_in_legacy_mode(self):
        with mock.patch.dict(os.environ, {"SISPER_PROCESS_MODE": "legacy"}):
            with mock.patch("devconsole.services.runtime.ShadowComparator.compare",
                            side_effect=AssertionError("must not run")) as spy:
                self.env_service._observe_restart_safety("ms_x", 8000)
        self.assertEqual(0, spy.call_count)

    def test_hook_returns_immediately_when_env_unset(self):
        env = {k: v for k, v in os.environ.items() if k != "SISPER_PROCESS_MODE"}
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch("devconsole.services.runtime.ShadowComparator.compare",
                            side_effect=AssertionError("must not run")) as spy:
                self.env_service._observe_restart_safety("ms_x", 8000)
        self.assertEqual(0, spy.call_count)

    def test_hook_swallows_every_exception(self):
        with mock.patch.dict(os.environ, {"SISPER_PROCESS_MODE": "shadow"}):
            with mock.patch("devconsole.services.runtime.ShadowComparator.compare",
                            side_effect=RuntimeError("boom")):
                self.env_service._observe_restart_safety("ms_x", 8000)  # must not raise

    def test_hook_runs_when_shadow_enabled(self):
        with mock.patch.dict(os.environ, {"SISPER_PROCESS_MODE": "shadow"}):
            with mock.patch("devconsole.services.runtime.ShadowComparator.compare",
                            return_value=mock.MagicMock(
                                operation="restart",
                                shadow={"pid": None, "confidence": "NONE", "owned": False},
                                match=True, reason="no_target")) as spy:
                self.env_service._observe_restart_safety("ms_x", 8000)
        self.assertEqual(1, spy.call_count)

    def test_write_service_env_still_calls_legacy_restart_unchanged(self):
        """The baseline contract survives with the hook present (legacy mode)."""
        root = self.temp_dir()
        (root / "backend" / "ms_sisper_sesion").mkdir(parents=True)
        with mock.patch.object(self.env_service, "BASE_DIR", root), \
             mock.patch.object(self.env_service, "SERVICES_BACKEND",
                               [{"name": "ms_sisper_sesion", "port": 8000}]), \
             mock.patch.object(self.env_service, "SERVICES_FRONTEND", []), \
             mock.patch.dict(os.environ, {"SISPER_PROCESS_MODE": "legacy"}):
            run = self.patch_run(returncode=0)
            ok, msg = self.env_service.write_service_env(
                "ms_sisper_sesion", "X=1\n", restart=True)

        self.assertTrue(ok)
        self.assertIn("reiniciado automáticamente", msg)
        self.assertEqual(1, run.call_count)
        cmd = run.call_args[0][0]
        self.assertEqual(str(root / "start_tilix.sh"), cmd[0])
        self.assertEqual("restart-single", cmd[1])
        self.assertEqual("ms_sisper_sesion", cmd[2])
        self.assertEqual("8000", cmd[3])
        self.assertFalse(run.call_args[1].get("check", True))
        self.assertEqual(5, run.call_args[1].get("timeout"))

    def test_shadow_mode_does_not_alter_the_restart_command(self):
        """Even with shadow on, the command sent to start_tilix.sh is identical."""
        root = self.temp_dir()
        (root / "backend" / "ms_sisper_sesion").mkdir(parents=True)
        with mock.patch.object(self.env_service, "BASE_DIR", root), \
             mock.patch.object(self.env_service, "SERVICES_BACKEND",
                               [{"name": "ms_sisper_sesion", "port": 8000}]), \
             mock.patch.object(self.env_service, "SERVICES_FRONTEND", []), \
             mock.patch.dict(os.environ, {"SISPER_PROCESS_MODE": "shadow"}):
            run = self.patch_run(returncode=0)
            ok, _ = self.env_service.write_service_env(
                "ms_sisper_sesion", "X=1\n", restart=True)

        self.assertTrue(ok)
        self.assertEqual(1, run.call_count)
        self.assertEqual(str(root / "start_tilix.sh"), run.call_args[0][0][0])
        self.assertEqual("restart-single", run.call_args[0][0][1])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
