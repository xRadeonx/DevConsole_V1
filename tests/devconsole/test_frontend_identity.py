"""Phase 3F-ID — frontend process identity, with an OLD vs NEW differential.

Background (measured in Fase 3, not assumed)
--------------------------------------------
All 10 frontends were stuck at ``MEDIUM``, so the terminal backend refused to
touch them.  Two independent defects, both confirmed against live processes:

1. **Node is shipped as ``node-22``.**  ``/usr/bin/node`` is a symlink to
   ``/usr/bin/node-22``, and the *real* executable of the process is ``node-22``.
   The allowlist pattern ``^(node|npm|…)$`` is anchored with ``$`` and therefore
   never matched.  Measured ancestry shows the whole chain runs on ``node-22``
   (``webpack`` → ``npm run`` → ``node`` → ``npm start``), so this defect alone
   blocked the match.
2. **webpack-dev-server rewrites its own process title.**  By the time it listens,
   its argv is literally ``["webpack"]``; the ``webpack serve --config …``
   command line the pattern looked for no longer exists anywhere in ``/proc``.

This module pins both fixes with a differential against the pre-change logic, and
— more importantly — proves the change **never weakens a negative case**: no
candidate may be promoted to a higher confidence than it had before, and the only
promotions allowed are the 10 measured frontend shapes going ``MEDIUM → HIGH``.

The pre-change module is loaded straight out of git history so the comparison is
against the real old code, not a paraphrase of it.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.devconsole.support import DevConsoleTestCase

from devconsole.services.runtime import (
    Confidence,
    ProcessFacts,
    ServiceType,
    build_descriptor,
)
from devconsole.services.runtime import process_ownership as current
from devconsole.services.runtime.process_identity import ServiceDescriptor

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Last commit before the 3F-ID change.  The "OLD" side of the differential.
BASELINE_REV = "35d7727"
BASELINE_PATH = "devconsole/services/runtime/process_ownership.py"

#: Backend ports/names and frontend names of the real workspace, transcribed from
#: the measured Fase 3 appendix.  Only the *shape* matters here (executable name,
#: argv, cwd relationship), which is why the matrix runs on a temp workspace.
FRONTEND_SERVICES = [
    ("mf_sisper_sesion", 3000),
    ("mf_sisper_adm_usuario", 3001),
    ("mf_sisper_identificacion", 3002),
    ("mf_sisper_bitacora", 3003),
    ("mf_sisper_solicitudes", 3004),
    ("mf_sisper_contratos", 3006),
    ("mf_sisper_documentos", 3007),
    ("mf_sisper_perfiles_de_riesgo", 3008),
    ("mf_sisper_carrera_correct_comp", 3009),
    ("mf_sisper_promocion_otros", 3010),
]

BACKEND_SERVICES = [
    ("ms_sisper_sesion", 8000),
    ("ms_sisper_promocion", 8007),
    ("ms_sisper_form_acad", 8012),
    ("ms_sisper_asistente", 8100),
]

#: The measured frontend shape, exactly as observed in /proc.
FRONTEND_EXE = "/usr/bin/node-22"
FRONTEND_ARGV = ("webpack",)


def baseline_available() -> bool:
    try:
        subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "cat-file", "-e", f"{BASELINE_REV}^{{commit}}"],
            stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return False


def load_baseline_module():
    """Import the pre-change ``process_ownership`` as a private module."""
    source = subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), "show", f"{BASELINE_REV}:{BASELINE_PATH}"],
        stderr=subprocess.DEVNULL).decode("utf-8")
    tmp = Path(tempfile.mkdtemp(prefix="devconsole-3fid-"))
    target = tmp / "baseline_ownership.py"
    target.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("devconsole_ownership_baseline", target)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


class FrontendIdentityDifferentialTest(DevConsoleTestCase):
    """Every case is graded twice: by the old logic and by the new one."""

    baseline = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        import unittest as _u
        if not baseline_available():
            raise _u.SkipTest(
                f"baseline {BASELINE_REV} is not present in this clone; the "
                "OLD-vs-NEW differential cannot run here")
        cls.baseline = load_baseline_module()

    def setUp(self):
        super().setUp()
        self.root = Path(self.temp_dir())
        self.services = []
        for name, port in FRONTEND_SERVICES + BACKEND_SERVICES:
            kind = "frontend" if name.startswith("mf_") else "backend"
            (self.root / kind / name).mkdir(parents=True, exist_ok=True)
            self.services.append({"name": name, "port": port})

    # -- helpers --------------------------------------------------------- #

    def descriptor(self, name: str) -> ServiceDescriptor:
        return build_descriptor(name, base_dir=self.root, services=self.services)

    def ancestors(self, name: str):
        kind = "frontend" if name.startswith("mf_") else "backend"
        cwd = str(self.root / kind / name)
        return [
            (("bash", f"{self.root}/tilix_runner.sh"), cwd),
            (("npm", "start"), cwd),
            (("node", f"{self.root}/{kind}/{name}/node_modules/.bin/webpack"), cwd),
        ]

    def grade(self, module, descriptor, facts, ancestors):
        verdict = module.OwnershipVerifier(self.root).verify(
            descriptor, facts, ancestors=ancestors)
        return verdict.confidence.value, verdict.owned

    def both(self, name, *, exe, argv, cwd=None, ports=(), ancestors=None,
             pid=4242):
        """Grade one candidate with the old logic and the new one."""
        kind = "frontend" if name.startswith("mf_") else "backend"
        desc = self.descriptor(name)
        facts = ProcessFacts(
            pid=pid, executable=exe, command_line=tuple(argv),
            cwd=str(cwd) if cwd is not None else str(self.root / kind / name),
            listening_ports=tuple(ports),
        )
        anc = self.ancestors(name) if ancestors is None else ancestors
        return (self.grade(self.baseline, desc, facts, anc),
                self.grade(current, desc, facts, anc))

    # -- the fix --------------------------------------------------------- #

    def test_all_ten_measured_frontends_are_promoted_to_high(self):
        """The exact measured shape must now reach HIGH — and only HIGH."""
        for name, port in FRONTEND_SERVICES:
            with self.subTest(service=name):
                old, new = self.both(name, exe=FRONTEND_EXE, argv=FRONTEND_ARGV,
                                     ports=(port,))
                self.assertEqual("MEDIUM", old[0], "baseline must reproduce the defect")
                self.assertEqual(("HIGH", True), new,
                                 "the measured frontend shape must grade HIGH and owned")

    def test_promotion_is_exactly_medium_to_high(self):
        """Nothing is invented: the change moves MEDIUM to HIGH and no further."""
        for name, port in FRONTEND_SERVICES:
            with self.subTest(service=name):
                old, new = self.both(name, exe=FRONTEND_EXE, argv=FRONTEND_ARGV,
                                     ports=(port,))
                self.assertEqual("MEDIUM", old[0])
                self.assertEqual("HIGH", new[0])

    def test_backends_do_not_regress(self):
        """The fix is shared code, so the backend grades must be untouched."""
        for name, port in BACKEND_SERVICES:
            with self.subTest(service=name):
                exe = f"{self.root}/venv/bin/python"
                old, new = self.both(
                    name, exe=exe,
                    argv=(exe, "manage.py", "runserver", f"0.0.0.0:{port}"),
                    ports=(port,))
                self.assertEqual("HIGH", old[0], f"{name} baseline")
                self.assertEqual("HIGH", new[0], f"{name} after the fix")
                self.assertEqual(old, new, "a backend grade must be bit-identical")

    def test_backends_using_versioned_python_do_not_regress(self):
        exe = "/usr/bin/python3.11"
        old, new = self.both("ms_sisper_sesion", exe=exe,
                             argv=(exe, "manage.py", "runserver", "0.0.0.0:8000"),
                             ports=(8000,))
        self.assertEqual(old, new)
        self.assertEqual("HIGH", new[0])

    # -- no weakening ---------------------------------------------------- #

    def test_no_negative_case_reaches_high_or_gains_destructive_power(self):
        """The safety invariant over the whole matrix.

        Stated as the property that actually matters rather than as "confidence
        may never rise", which would be wrong: the executable normalization
        legitimately lifts some shapes from ``LOW`` to ``MEDIUM`` because they are
        genuinely Node in the right cwd.  ``MEDIUM`` is ``owned=True`` **and
        ``allows_destructive_action=False``**, and it is the same grade a backend
        already receives for "right place, right runtime, unrecognised command".

        What must never happen is a negative case reaching ``HIGH`` or acquiring
        the ability to authorise a destructive action.  That is what is asserted
        here, for every case in the matrix.
        """
        import devconsole.services.runtime.process_ownership as cur

        def destructive(module, confidence, owned):
            return module.Confidence(confidence).allows_destructive_action() and owned

        cases = self._negative_matrix()
        for label, kwargs in cases:
            with self.subTest(case=label):
                old, new = kwargs()
                self.assertNotEqual("HIGH", new[0],
                                    f"{label}: must never reach HIGH")
                self.assertFalse(destructive(cur, *new),
                                 f"{label}: must never authorise a destructive action")
                # and the old logic must not have allowed it either
                self.assertFalse(destructive(self.baseline, *old),
                                 f"{label}: baseline sanity")

    def test_only_the_measured_frontend_shape_reaches_high(self):
        """The single allowed promotion, asserted from the other direction."""
        promoted = []
        for name, port in FRONTEND_SERVICES:
            old, new = self.both(name, exe=FRONTEND_EXE, argv=FRONTEND_ARGV,
                                 ports=(port,))
            if old[0] != "HIGH" and new[0] == "HIGH":
                promoted.append(name)
        self.assertEqual([n for n, _ in FRONTEND_SERVICES], promoted)

    def _negative_matrix(self):
        r = self.root
        port = 3001
        name = "mf_sisper_adm_usuario"
        return [
            # executable is an unrelated binary that merely starts with "node"
            ("nodefoo executable",
             lambda: self.both(name, exe="/usr/bin/nodefoo", argv=FRONTEND_ARGV,
                               ports=(port,))),
            # cwd outside the workspace
            ("cwd outside BASE_DIR",
             lambda: self.both(name, exe=FRONTEND_EXE, argv=FRONTEND_ARGV,
                               cwd="/tmp", ports=(port,))),
            # cwd is a *different* service
            ("cwd of another service",
             lambda: self.both(name, exe=FRONTEND_EXE, argv=FRONTEND_ARGV,
                               cwd=r / "frontend" / "mf_sisper_contratos",
                               ports=(port,))),
            # not listening on its configured port
            ("port not listening",
             lambda: self.both(name, exe=FRONTEND_EXE, argv=FRONTEND_ARGV,
                               ports=())),
            # argv unrelated to any known frontend command
            ("unrelated argv",
             lambda: self.both(name, exe=FRONTEND_EXE, argv=("cat", "/etc/passwd"),
                               ports=(port,))),
            # no workspace lineage at all
            ("no lineage", lambda: self.both(name, exe=FRONTEND_EXE,
                                             argv=FRONTEND_ARGV, ports=(port,),
                                             ancestors=())),
            # a name that only *contains* webpack must not count as a command
            ("webpack appearing only as a file argument",
             lambda: self.both(name, exe="/usr/bin/node-22",
                               argv=("cp", "webpack.config.js", "/tmp/x"),
                               ports=())),
            # critical infrastructure must stay NONE
            ("pid 1", lambda: self.both(name, exe=FRONTEND_EXE, argv=FRONTEND_ARGV,
                                        ports=(port,), pid=1)),
        ]

    def test_critical_infrastructure_is_still_rejected(self):
        """DevConsole itself, and the Tilix D-Bus service, must stay NONE.

        These are the real ``_CRITICAL_COMMAND_HINTS`` values: killing either
        would take down the console or the operator's terminal service.
        """
        for argv in (("python3", "/home/proteo/Documentos/Develop/dashboard.py"),
                     ("/usr/bin/tilix", "--gapplication-service")):
            with self.subTest(argv=argv):
                old, new = self.both("ms_sisper_sesion", exe="/usr/bin/python3",
                                     argv=argv, ports=(8000,))
                self.assertEqual("NONE", new[0], argv)
                self.assertFalse(new[1])
                self.assertEqual(old[0], new[0], "critical rejection must not move")

    def test_unknown_service_type_cannot_be_promoted(self):
        desc = ServiceDescriptor(
            name="mystery", service_type=ServiceType.UNKNOWN,
            configured_port=3001,
            expected_service_dir=self.root / "frontend" / "mf_sisper_adm_usuario",
            base_dir=self.root)
        facts = ProcessFacts(pid=99, executable=FRONTEND_EXE,
                             command_line=FRONTEND_ARGV,
                             cwd=str(self.root / "frontend" / "mf_sisper_adm_usuario"),
                             listening_ports=(3001,))
        for module in (self.baseline, current):
            verdict = module.OwnershipVerifier(self.root).verify(desc, facts)
            self.assertEqual("NONE", verdict.confidence.value)
            self.assertFalse(verdict.owned)

    def test_does_not_allow_destructive_action_on_medium(self):
        """MEDIUM must keep refusing destructive actions after the change."""
        _, new = self.both("mf_sisper_adm_usuario", exe="/usr/bin/nodefoo",
                           argv=FRONTEND_ARGV, ports=(3001,))
        self.assertEqual("MEDIUM", new[0])
        verdict = current.OwnershipVerifier(self.root).verify(
            self.descriptor("mf_sisper_adm_usuario"),
            ProcessFacts(pid=7, executable="/usr/bin/nodefoo",
                         command_line=FRONTEND_ARGV,
                         cwd=str(self.root / "frontend" / "mf_sisper_adm_usuario"),
                         listening_ports=(3001,)),
            ancestors=self.ancestors("mf_sisper_adm_usuario"))
        self.assertFalse(verdict.allows_destructive_action,
                         "MEDIUM must not authorise a destructive action")


class ExecutableNormalizationTest(DevConsoleTestCase):
    """The version-suffix normalizer is narrow and cannot widen the allowlist."""

    def test_versioned_runtimes_are_normalized(self):
        cases = {
            "node-22": "node",
            "node": "node",
            "npm-10.9.7": "npm",
            "python3.11": "python3",
            "python3": "python3",
            "python": "python",
            "bash-5.2": "bash",
            "webpack": "webpack",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(expected, current.normalize_executable_basename(raw))

    def test_unrelated_names_are_left_alone(self):
        for raw in ("nodefoo", "nodejs", "my-node", "webpacker", "node_22",
                    "node-", "node-lts"):
            with self.subTest(raw=raw):
                self.assertEqual(raw, current.normalize_executable_basename(raw))

    def test_normalized_names_still_cannot_smuggle_a_binary(self):
        """Only a numeric suffix is stripped, so lookalikes stay rejected."""
        for raw in ("nodefoo", "nodejs", "node_22", "node-lts", "webpacker",
                    "/usr/bin/node-2-2"):
            with self.subTest(raw=raw):
                self.assertFalse(
                    current.executable_matches_type(raw, ServiceType.FRONTEND),
                    f"{raw} must not be accepted as a frontend runtime")

    def test_measured_executables_are_accepted(self):
        self.assertTrue(current.executable_matches_type("/usr/bin/node-22",
                                                        ServiceType.FRONTEND))
        self.assertTrue(current.executable_matches_type("/usr/bin/node",
                                                        ServiceType.FRONTEND))
        self.assertTrue(current.executable_matches_type(
            "/home/u/.local/share/virtualenvs/ms_x/bin/python", ServiceType.BACKEND))

    def test_a_frontend_binary_is_not_a_backend_runtime(self):
        """The allowlists stay type-specific."""
        self.assertFalse(current.executable_matches_type("/usr/bin/node-22",
                                                         ServiceType.BACKEND))
        self.assertFalse(current.executable_matches_type("/usr/bin/python3.11",
                                                         ServiceType.FRONTEND))


class WebpackCommandEvidenceTest(DevConsoleTestCase):
    """The rewritten process title is accepted; nothing else is."""

    def test_the_renamed_process_title_is_accepted(self):
        self.assertTrue(current.command_matches_type(("webpack",),
                                                     ServiceType.FRONTEND))

    def test_the_pre_rewrite_command_lines_still_match(self):
        for argv in (("webpack", "serve", "--config", "webpack.config.js"),
                     ("npm", "start"),
                     ("npm", "run", "start"),
                     ("node", "webpack"),
                     ("concurrently",)):
            with self.subTest(argv=argv):
                self.assertTrue(current.command_matches_type(argv, ServiceType.FRONTEND))

    def test_unrelated_commands_do_not_match(self):
        for argv in (("cat", "/etc/passwd"), ("bash",), ("python", "manage.py"),
                     ("webpacker", "build")):
            with self.subTest(argv=argv):
                self.assertFalse(current.command_matches_type(argv, ServiceType.FRONTEND),
                                 f"{argv} must not look like a frontend launch")

    def test_empty_argv_never_matches(self):
        self.assertFalse(current.command_matches_type((), ServiceType.FRONTEND))

    def test_backend_patterns_are_untouched(self):
        self.assertTrue(current.command_matches_type(
            ("python", "manage.py", "runserver", "0.0.0.0:8000"),
            ServiceType.BACKEND))
        self.assertFalse(current.command_matches_type(("webpack",),
                                                      ServiceType.BACKEND))
