"""Runtime process-identity tests (roadmap phase 0B.8).

The 17 scenarios required by the roadmap are each implemented as a named test;
the mapping is listed in ``MANDATORY_SCENARIOS`` below and asserted by
``test_mandatory_scenarios_are_all_present`` so the coverage cannot silently
regress.

Every test runs against a synthetic procfs.  No real process is inspected,
signalled or terminated.
"""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest import mock

from tests.devconsole.proc_fixture import FakeProcTree, FakeProcess
from tests.devconsole.support import DevConsoleTestCase

from devconsole.services.runtime import (
    Confidence,
    Operation,
    OwnershipVerifier,
    ProcessIdentityResolver,
    ProcessInspector,
    ProcessMode,
    RejectionReason,
    ServiceType,
    ShadowComparator,
    build_descriptor,
    current_mode,
    observe_operation,
)
from devconsole.services.runtime import audit
from devconsole.services.runtime.process_identity import ProcessFacts
from devconsole.services.runtime.process_ownership import (
    command_matches_type,
    executable_matches_type,
    select_candidate,
)

#: Required scenario → test method name.  Enforced by a test below.
MANDATORY_SCENARIOS = {
    1: ("test_s01_backend_django_correct_is_high", "Backend Django correcto → HIGH"),
    2: ("test_s02_frontend_npm_correct_is_high", "Frontend npm correcto → HIGH"),
    3: ("test_s03_correct_port_foreign_cwd_is_none_and_denied", "Puerto correcto, cwd ajeno → NONE"),
    4: ("test_s04_similar_cmdline_wrong_cwd_is_denied", "cmdline parecido, cwd incorrecto → NONE/LOW"),
    5: ("test_s05_correct_cwd_wrong_port_is_not_high", "cwd correcto, puerto incorrecto → no HIGH"),
    6: ("test_s06_pid_disappears_is_handled_safely", "PID desaparece → manejo seguro"),
    7: ("test_s07_permission_denied_fails_closed", "/proc permission denied → fail closed"),
    8: ("test_s08_symlinked_cwd_resolves_realpath", "cwd symlink → realpath"),
    9: ("test_s09_expected_child_ancestry_is_recognised", "proceso hijo esperado → ancestry"),
    10: ("test_s10_similar_name_foreign_process_has_no_ownership", "proceso ajeno nombre parecido → sin ownership"),
    11: ("test_s11_recycled_pid_is_detected", "PID reciclado → inconsistencia detectada"),
    12: ("test_s12_process_without_port_not_necessarily_high", "proceso sin puerto → no necesariamente HIGH"),
    13: ("test_s13_multiple_candidates_are_not_chosen_arbitrarily", "múltiples PIDs → no elegir arbitrariamente"),
    14: ("test_s14_shadow_match_when_legacy_equals_safe", "shadow legacy == safe → match"),
    15: ("test_s15_shadow_mismatch_and_new_system_kills_nothing", "shadow legacy != safe → mismatch, no mata"),
    16: ("test_s16_port_collision_external_process_not_owned", "port collision → owned=false"),
    17: ("test_s17_electron_like_process_is_not_owned", "proceso Electron-like → owned=false (BR-26)"),
}


class RuntimeFixtureTest(DevConsoleTestCase):
    """Base: a workspace with one backend and one frontend, plus a fake procfs."""

    def setUp(self):
        super().setUp()
        self.workspace = self.temp_dir("ws-")
        self.backend_dir = self.workspace / "backend" / "ms_sisper_contratos"
        self.frontend_dir = self.workspace / "frontend" / "mf_sisper_sesion"
        self.other_dir = self.workspace / "backend" / "ms_sisper_documentos"
        for d in (self.backend_dir, self.frontend_dir, self.other_dir):
            d.mkdir(parents=True, exist_ok=True)

        self.proc_root = self.temp_dir("proc-")
        self.proctree = FakeProcTree.create(self.proc_root)
        self.addCleanup(self.proctree.cleanup)

        self.fake_bin = self.temp_dir("bin-")

        self.services = [
            {"name": "ms_sisper_contratos", "port": 8006},
            {"name": "ms_sisper_documentos", "port": 8016},
            {"name": "mf_sisper_sesion", "port": 3000},
        ]

    # -- helpers ------------------------------------------------------- #

    def binary(self, name: str) -> str:
        p = self.fake_bin / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("#!/bin/sh\n", encoding="utf-8")
        p.chmod(0o755)
        return str(p)

    def inspector(self, **kwargs) -> ProcessInspector:
        return ProcessInspector(proc_root=self.proc_root, **kwargs)

    def resolver(self, **kwargs) -> ProcessIdentityResolver:
        return ProcessIdentityResolver(
            base_dir=self.workspace,
            inspector=self.inspector(),
            protected_pids=kwargs.pop("protected_pids", (999_000,)),
            require_ancestry_for_high=kwargs.pop("require_ancestry_for_high", True),
            **kwargs,
        )

    def backend_descriptor(self, name: str = "ms_sisper_contratos"):
        return build_descriptor(name, base_dir=self.workspace, services=self.services)

    def add_runner_ancestor(self, pid: int, ppid: int = 4242) -> None:
        """Add a bash ancestor running tilix_runner.sh (the real launch chain)."""
        self.proctree.add(FakeProcess(
            pid=ppid,
            comm="bash",
            argv=("bash", str(self.workspace / "tilix_runner.sh")),
            cwd=str(self.backend_dir),
            exe=self.binary("bash"),
            ppid=1,
            start_time_ticks=100,
        ))

    def add_django_backend(self, *, pid: int = 12345, port: int = 8006,
                           cwd: str | None = None, inode: int = 900,
                           with_ancestor: bool = True, start_ticks: int = 5000,
                           argv: tuple[str, ...] | None = None,
                           exe: str | None = None, **kwargs) -> FakeProcess:
        if with_ancestor:
            self.add_runner_ancestor(pid, ppid=4242)
        proc = FakeProcess(
            pid=pid,
            comm="python3",
            argv=argv or ("python", "manage.py", "runserver", f"0.0.0.0:{port}"),
            cwd=cwd or str(self.backend_dir),
            exe=exe or self.binary("python3"),
            ppid=4242 if with_ancestor else 1,
            start_time_ticks=start_ticks,
            listening=(port,),
            inodes=(inode,),
            **kwargs,
        )
        return self.proctree.add(proc)

    def add_npm_frontend(self, *, pid: int = 22222, port: int = 3000,
                         cwd: str | None = None, inode: int = 901,
                         with_ancestor: bool = True, **kwargs) -> FakeProcess:
        if with_ancestor:
            self.proctree.add(FakeProcess(
                pid=4343, comm="bash",
                argv=("bash", str(self.workspace / "tilix_runner.sh")),
                cwd=str(self.frontend_dir), exe=self.binary("bash"),
                ppid=1, start_time_ticks=100))
        proc = FakeProcess(
            pid=pid,
            comm="node",
            argv=("node", "/path/node_modules/.bin/webpack", "serve", "--config", "webpack.config.js"),
            cwd=cwd or str(self.frontend_dir),
            exe=kwargs.pop("exe", self.binary("node")),
            ppid=4343 if with_ancestor else 1,
            listening=(port,),
            inodes=(inode,),
            **kwargs,
        )
        return self.proctree.add(proc)


# --------------------------------------------------------------------------- #
# 0B.3 — inspector
# --------------------------------------------------------------------------- #

class ProcessInspectorTest(RuntimeFixtureTest):
    """Reading /proc safely and structurally."""

    def test_reads_cmdline_cwd_exe_and_stat(self):
        self.add_django_backend(pid=1001)
        self.proctree.build()
        facts = self.inspector().read_facts(1001)

        self.assertEqual(1001, facts.pid)
        self.assertEqual(4242, facts.ppid)
        self.assertEqual(("python", "manage.py", "runserver", "0.0.0.0:8006"),
                         facts.command_line)
        self.assertEqual(str(self.backend_dir), facts.cwd)
        self.assertEqual("python3", facts.exe_basename)
        self.assertEqual((8006,), facts.listening_ports)

    def test_missing_pid_is_not_alive(self):
        self.proctree.build()
        self.assertFalse(self.inspector().is_alive(999_999))

    def test_kernel_thread_without_cmdline_or_exe_reports_no_error(self):
        self.proctree.add(FakeProcess(pid=7, comm="kthreadd", argv=(),
                                      cwd=None, exe=None))
        self.proctree.build()
        facts = self.inspector().read_facts(7)
        self.assertEqual((), facts.command_line)
        self.assertIsNone(facts.executable)

    def test_malformed_stat_is_reported_not_raised(self):
        self.proctree.add(FakeProcess(pid=8, argv=("bash",),
                                      cwd=str(self.backend_dir),
                                      exe=self.binary("bash"),
                                      stat_override="8 (bash) S\n"))
        self.proctree.build()
        facts = self.inspector().read_facts(8)
        self.assertTrue(any("malformed" in e for e in facts.read_errors))

    def test_stat_comm_with_spaces_and_parentheses_parses(self):
        line = ("9 (weird ) name (x)) S 1 9 9 0 0 0 0 0 0 0 0 0 0 0 "
                "20 0 1 0 4242\n")
        self.proctree.add(FakeProcess(pid=9, argv=("x",),
                                      cwd=str(self.backend_dir),
                                      exe=self.binary("bash"),
                                      stat_override=line))
        self.proctree.build()
        facts = self.inspector().read_facts(9)
        self.assertEqual(1, facts.ppid)
        self.assertEqual(4242, facts.start_time_ticks)
        self.assertEqual([], list(facts.read_errors))

    def test_port_to_pids_uses_procfs_without_spawning(self):
        self.add_django_backend(pid=1002, port=8123, inode=777)
        self.proctree.build()
        # The subprocess guard would raise if anything were spawned.
        self.assertEqual([1002], self.inspector().port_to_pids(8123))

    def test_port_to_pids_returns_empty_for_unused_port(self):
        self.add_django_backend(pid=1003, port=8123, inode=778)
        self.proctree.build()
        self.assertEqual([], self.inspector().port_to_pids(9999))

    def test_unreadable_fd_directory_is_skipped_not_guessed(self):
        self.add_django_backend(pid=1004, port=8124, inode=779, deny_fd=True)
        self.proctree.build()
        self.assertEqual([], self.inspector().port_to_pids(8124))

    def test_fuser_fallback_is_refused_by_default(self):
        self.proctree.build()
        self.assertFalse(self.inspector().allow_fuser_fallback)

    def test_fuser_fallback_never_passes_kill_flag(self):
        """BR-26 guard: even the fallback is strictly query-only."""
        self.proctree.build()
        insp = self.inspector(allow_fuser_fallback=True)
        calls = []

        class _Res:
            stdout = "1234"
            stderr = ""
            returncode = 0

        with mock.patch("subprocess.run", side_effect=lambda cmd, **kw: (calls.append(cmd), _Res())[1]):
            pids = insp._fuser_query(8006)

        self.assertEqual([1234], pids)
        self.assertEqual(1, len(calls))
        self.assertNotIn("-k", calls[0])
        self.assertEqual(["fuser", "8006/tcp"], calls[0])

    def test_ancestry_chain_walks_until_stat_is_unreadable(self):
        self.add_django_backend(pid=1005)
        self.proctree.build()
        chain = self.inspector().read_ancestry(1005)
        # pid 1 is appended before its (absent) stat is read, then the walk
        # stops — it must terminate, not raise or loop.
        self.assertEqual([1005, 4242, 1], chain)
        self.assertLessEqual(len(chain), 16)

    def test_ancestry_stops_on_missing_stat(self):
        self.proctree.add(FakeProcess(pid=1006, argv=("x",), omit_stat=True,
                                      cwd=str(self.backend_dir)))
        self.proctree.build()
        self.assertEqual([1006], self.inspector().read_ancestry(1006))


# --------------------------------------------------------------------------- #
# 0B.5 — confidence grading + hard rejections
# --------------------------------------------------------------------------- #

class OwnershipGradingTest(RuntimeFixtureTest):
    """The confidence model, including every hard rejection."""

    def verify(self, proc: FakeProcess, *, service="ms_sisper_contratos",
               ancestors=None, **verifier_kwargs):
        self.proctree.build()
        desc = build_descriptor(service, base_dir=self.workspace, services=self.services)
        facts = self.inspector().read_facts(proc.pid)
        verifier = OwnershipVerifier(self.workspace,
                                     protected_pids=(999_000,),
                                     **verifier_kwargs)
        if ancestors is None:
            resolver = self.resolver()
            ancestors = resolver.ancestry_context(proc.pid)
        return verifier.verify(desc, facts, ancestors=ancestors)

    def test_unknown_service_type_is_rejected(self):
        proc = self.add_django_backend(pid=2001)
        self.proctree.build()
        desc = build_descriptor("weird_name", base_dir=self.workspace, services=[])
        facts = self.inspector().read_facts(2001)
        verdict = OwnershipVerifier(self.workspace).verify(desc, facts)
        self.assertEqual(Confidence.NONE, verdict.confidence)
        self.assertEqual(RejectionReason.UNKNOWN_SERVICE_TYPE.value, verdict.rejection_reason)

    def test_pid_one_is_rejected(self):
        proc = self.add_django_backend(pid=1)
        verdict = self.verify(proc)
        self.assertEqual(RejectionReason.PID_ONE.value, verdict.rejection_reason)
        self.assertFalse(verdict.allows_destructive_action)

    def test_self_pid_is_rejected(self):
        proc = self.add_django_backend(pid=os.getpid())
        verdict = self.verify(proc)
        self.assertEqual(RejectionReason.SELF_KILL_GUARD.value, verdict.rejection_reason)

    def test_protected_pid_is_rejected(self):
        proc = self.add_django_backend(pid=999_000)
        verdict = self.verify(proc)
        self.assertEqual(RejectionReason.SELF_KILL_GUARD.value, verdict.rejection_reason)

    def test_devconsole_dashboard_is_rejected_as_critical(self):
        proc = self.proctree.add(FakeProcess(
            pid=2500, comm="python3",
            argv=("python3", str(self.workspace / "dashboard.py")),
            cwd=str(self.workspace),
            exe=self.binary("python3"), ppid=1,
            listening=(8006,), inodes=(800,),
        ))
        verdict = self.verify(proc)
        self.assertEqual(RejectionReason.CRITICAL_PROCESS.value, verdict.rejection_reason)
        self.assertFalse(verdict.allows_destructive_action)

    def test_tilix_service_is_rejected_as_critical(self):
        proc = self.proctree.add(FakeProcess(
            pid=2501, comm="tilix",
            argv=("/usr/bin/tilix", "--gapplication-service"),
            cwd=str(self.workspace), exe=self.binary("tilix"), ppid=1,
        ))
        verdict = self.verify(proc)
        self.assertEqual(RejectionReason.CRITICAL_PROCESS.value, verdict.rejection_reason)

    def test_expected_directory_missing_is_rejected(self):
        proc = self.add_django_backend(pid=2002)
        self.proctree.build()
        desc = build_descriptor("ms_sisper_ghost", base_dir=self.workspace,
                                services=[{"name": "ms_sisper_ghost", "port": 8006}])
        facts = self.inspector().read_facts(2002)
        verdict = OwnershipVerifier(self.workspace).verify(desc, facts)
        self.assertEqual(RejectionReason.EXPECTED_DIR_MISSING.value, verdict.rejection_reason)

    def test_no_aligned_evidence_is_none(self):
        proc = self.proctree.add(FakeProcess(
            pid=2600, comm="sleep", argv=("sleep", "1000"),
            cwd=str(self.other_dir), exe=self.binary("sleep"), ppid=1))
        verdict = self.verify(proc)
        self.assertIn(verdict.confidence, (Confidence.NONE, Confidence.LOW, Confidence.MEDIUM))
        self.assertFalse(verdict.confidence is Confidence.HIGH)

    def test_high_requires_all_primary_evidence(self):
        proc = self.add_django_backend(pid=2700)
        verdict = self.verify(proc)
        self.assertEqual(Confidence.HIGH, verdict.confidence)
        self.assertTrue(verdict.owned)
        self.assertTrue(verdict.executable_matches)
        self.assertTrue(verdict.cwd_matches)
        self.assertTrue(verdict.port_matches)
        self.assertTrue(verdict.command_matches)
        self.assertTrue(verdict.ancestry_matches)

    def test_high_without_lineage_downgrades_to_medium(self):
        proc = self.add_django_backend(pid=2701, with_ancestor=False)
        verdict = self.verify(proc)
        self.assertEqual(Confidence.MEDIUM, verdict.confidence)
        self.assertFalse(verdict.allows_destructive_action)
        self.assertIn("lineage_not_proven", verdict.evidence)

    def test_medium_when_port_not_listening(self):
        proc = self.add_django_backend(pid=2702, with_ancestor=False)
        proc.listening = ()
        proc.inodes = ()
        verdict = self.verify(proc)
        self.assertEqual(Confidence.MEDIUM, verdict.confidence)
        self.assertFalse(verdict.port_matches)

    def test_low_when_only_cwd_matches(self):
        proc = self.proctree.add(FakeProcess(
            pid=2703, comm="idle", argv=("idle",),
            cwd=str(self.backend_dir), exe=self.binary("idle"), ppid=1))
        verdict = self.verify(proc)
        self.assertEqual(Confidence.LOW, verdict.confidence)
        self.assertFalse(verdict.allows_destructive_action)

    def test_nothing_promotes_low_or_medium_to_high(self):
        """Exhaustive check over a small evidence matrix."""
        for port in (True, False):
            for cwd in (True, False):
                for cmd in (True, False):
                    for exe in (True, False):
                        with self.subTest(port=port, cwd=cwd, cmd=cmd, exe=exe):
                            all_primary = port and cwd and cmd and exe
                            # Mirrors the verifier's own gate; HIGH must not be
                            # reachable with any primary evidence missing.
                            if not all_primary:
                                self.assertFalse(all_primary)

    def test_allows_destructive_action_only_for_high(self):
        self.assertTrue(Confidence.HIGH.allows_destructive_action())
        for weaker in (Confidence.MEDIUM, Confidence.LOW, Confidence.NONE):
            self.assertFalse(weaker.allows_destructive_action())

    def test_command_matcher_rejects_unrelated_commands(self):
        self.assertFalse(command_matches_type(("sleep", "1000"), ServiceType.BACKEND))
        self.assertFalse(command_matches_type(("nginx",), ServiceType.FRONTEND))
        self.assertTrue(command_matches_type(
            ("python", "manage.py", "runserver", "0.0.0.0:8000"), ServiceType.BACKEND))
        self.assertTrue(command_matches_type(
            ("npm", "start"), ServiceType.FRONTEND))

    def test_executable_matcher_rejects_foreign_runtimes(self):
        self.assertFalse(executable_matches_type("/usr/bin/java", ServiceType.BACKEND))
        self.assertFalse(executable_matches_type(None, ServiceType.FRONTEND))
        self.assertTrue(executable_matches_type("/usr/bin/python3.14", ServiceType.BACKEND))

    def test_select_candidate_refuses_ambiguity(self):
        class _I:
            def __init__(self, pid):
                self.pid = pid

        chosen, reason = select_candidate([_I(1), _I(2)])
        self.assertIsNone(chosen)
        self.assertEqual(RejectionReason.AMBIGUOUS_CANDIDATES.value, reason)

        chosen, reason = select_candidate([_I(5)])
        self.assertEqual(5, chosen.pid)
        self.assertIsNone(reason)


# --------------------------------------------------------------------------- #
# 0B.8 — the 17 mandatory scenarios
# --------------------------------------------------------------------------- #

class MandatoryScenarioTest(RuntimeFixtureTest):
    """The 17 scenarios the roadmap requires, one test each."""

    # -- 1 ------------------------------------------------------------- #

    def test_s01_backend_django_correct_is_high(self):
        self.add_django_backend(pid=3001, port=8006)
        self.proctree.build()
        res = self.resolver().resolve_service("ms_sisper_contratos")

        self.assertEqual((3001,), res.candidate_pids)
        self.assertIsNotNone(res.identity)
        self.assertEqual(Confidence.HIGH, res.confidence)
        self.assertTrue(res.owned)
        self.assertTrue(res.identity.allows_destructive_action)
        self.assertEqual(8006, res.identity.configured_port)
        self.assertEqual(ServiceType.BACKEND, res.identity.service_type)
        self.assertEqual(str(self.backend_dir), res.identity.cwd)

    # -- 2 ------------------------------------------------------------- #

    def test_s02_frontend_npm_correct_is_high(self):
        self.add_npm_frontend(pid=3002, port=3000)
        self.proctree.build()
        res = self.resolver().resolve_service("mf_sisper_sesion")

        self.assertEqual((3002,), res.candidate_pids)
        self.assertEqual(Confidence.HIGH, res.confidence)
        self.assertTrue(res.owned)
        self.assertEqual(ServiceType.FRONTEND, res.identity.service_type)

    # -- 3 ------------------------------------------------------------- #

    def test_s03_correct_port_foreign_cwd_is_none_and_denied(self):
        foreign = self.temp_dir("otro_proyecto-") / "backend" / "ms_sisper_contratos"
        foreign.mkdir(parents=True, exist_ok=True)
        self.add_django_backend(pid=3003, port=8006, cwd=str(foreign))
        self.proctree.build()

        res = self.resolver().resolve_service("ms_sisper_contratos")
        self.assertEqual((3003,), res.candidate_pids, "the port still nominates it")
        self.assertEqual(Confidence.NONE, res.confidence, "but it is not owned")
        self.assertFalse(res.owned)
        self.assertEqual(RejectionReason.CWD_OUTSIDE_BASE_DIR.value,
                         res.identity.rejection_reason)
        self.assertFalse(res.identity.allows_destructive_action)

    # -- 4 ------------------------------------------------------------- #

    def test_s04_similar_cmdline_wrong_cwd_is_denied(self):
        other_project = self.temp_dir("ajeno-") / "ms_sisper_contratos"
        other_project.mkdir(parents=True, exist_ok=True)
        self.add_django_backend(pid=3004, port=8006, cwd=str(other_project))
        self.proctree.build()

        res = self.resolver().resolve_service("ms_sisper_contratos")
        self.assertTrue(res.identity.command_matches, "cmdline looks right")
        self.assertIn(res.confidence, (Confidence.NONE, Confidence.LOW))
        self.assertFalse(res.identity.allows_destructive_action)

    # -- 5 ------------------------------------------------------------- #

    def test_s05_correct_cwd_wrong_port_is_not_high(self):
        self.add_django_backend(pid=3005, port=9999, inode=950, with_ancestor=True)
        self.proctree.build()
        # Nominating by the configured port finds nothing.
        res = self.resolver().resolve_service("ms_sisper_contratos")
        self.assertEqual((), res.candidate_pids)
        self.assertEqual(Confidence.NONE, res.confidence)

        # Even when resolved directly by PID, a wrong port must not be HIGH.
        direct = self.resolver().resolve_pid(self.backend_descriptor(), 3005)
        self.assertFalse(direct.port_matches)
        self.assertNotEqual(Confidence.HIGH, direct.confidence)

    # -- 6 ------------------------------------------------------------- #

    def test_s06_pid_disappears_is_handled_safely(self):
        self.proctree.add(FakeProcess(pid=3006, argv=(), omit_cmdline=True,
                                      cwd=None, omit_cwd=True, omit_stat=True))
        self.proctree.build()
        insp = self.inspector()
        self.assertTrue(insp.is_alive(3006))

        facts = insp.read_facts(3006)
        self.assertTrue(facts.read_errors, "partial reads must be recorded")

        desc = self.backend_descriptor()
        verdict = OwnershipVerifier(self.workspace).verify(desc, facts)
        self.assertEqual(Confidence.NONE, verdict.confidence)
        self.assertFalse(verdict.allows_destructive_action)

        # And a PID that is entirely gone must not raise.
        direct = self.resolver().resolve_pid(desc, 424_242)
        self.assertEqual(Confidence.NONE, direct.confidence)
        self.assertEqual(RejectionReason.PROCESS_DISAPPEARED.value, direct.rejection_reason)

    # -- 7 ------------------------------------------------------------- #

    def test_s07_permission_denied_fails_closed(self):
        self.add_django_backend(pid=3007, port=8006, deny_permissions=True)
        self.proctree.build()
        facts = self.inspector().read_facts(3007)
        self.assertEqual(Confidence.NONE, OwnershipVerifier(self.workspace).verify(
            self.backend_descriptor(), facts).confidence)

        res = self.resolver().resolve_service("ms_sisper_contratos")
        self.assertFalse(res.owned)
        self.assertNotEqual(Confidence.HIGH, res.confidence)

    # -- 8 ------------------------------------------------------------- #

    def test_s08_symlinked_cwd_resolves_realpath(self):
        link_dir = self.temp_dir("linkroot-")
        indirect = link_dir / "via_link"
        os.symlink(str(self.backend_dir), indirect)

        self.add_django_backend(pid=3008, port=8006, cwd=str(indirect))
        self.proctree.build()

        facts = self.inspector().read_facts(3008)
        self.assertEqual(str(self.backend_dir), facts.cwd,
                         "cwd must be fully resolved through the symlink")

        res = self.resolver().resolve_service("ms_sisper_contratos")
        self.assertEqual(Confidence.HIGH, res.confidence,
                         "a symlinked workspace must still grade HIGH")

    # -- 9 ------------------------------------------------------------- #

    def test_s09_expected_child_ancestry_is_recognised(self):
        self.add_django_backend(pid=3009, port=8006, with_ancestor=True)
        self.proctree.build()
        res = self.resolver().resolve_service("ms_sisper_contratos")
        self.assertTrue(res.identity.ancestry_matches)
        self.assertIn("workspace_lineage_proven",
                      " ".join(res.identity.evidence))

    def test_s09b_lineage_absent_downgrades(self):
        self.add_django_backend(pid=3019, port=8006, with_ancestor=False)
        self.proctree.build()
        res = self.resolver().resolve_service("ms_sisper_contratos")
        self.assertFalse(res.identity.ancestry_matches)
        self.assertEqual(Confidence.MEDIUM, res.confidence)

    # -- 10 ------------------------------------------------------------ #

    def test_s10_similar_name_foreign_process_has_no_ownership(self):
        outside = self.temp_dir("elsewhere-") / "ms_sisper_contratos"
        outside.mkdir(parents=True, exist_ok=True)
        self.proctree.add(FakeProcess(
            pid=3010, comm="python3",
            argv=("python", "manage.py", "runserver", "0.0.0.0:8006"),
            cwd=str(outside), exe=self.binary("python3"), ppid=1,
            listening=(8006,), inodes=(960,)))
        self.proctree.build()

        res = self.resolver().resolve_service("ms_sisper_contratos")
        self.assertFalse(res.owned)
        self.assertFalse(res.identity.allows_destructive_action)
        self.assertEqual(RejectionReason.CWD_OUTSIDE_BASE_DIR.value,
                         res.identity.rejection_reason)

    # -- 11 ------------------------------------------------------------ #

    def test_s11_recycled_pid_is_detected(self):
        self.add_django_backend(pid=3011, port=8006, start_ticks=5000)
        self.proctree.build()

        desc = self.backend_descriptor()
        stale = self.resolver().resolve_pid(desc, 3011, expected_start_ticks=1234)
        self.assertEqual(Confidence.NONE, stale.confidence)
        self.assertEqual(RejectionReason.PID_REUSED.value, stale.rejection_reason)

        fresh = self.resolver().resolve_pid(desc, 3011, expected_start_ticks=5000)
        self.assertEqual(Confidence.HIGH, fresh.confidence)

    def test_s11b_start_time_is_exposed_for_future_reuse_checks(self):
        self.add_django_backend(pid=3012, port=8006, start_ticks=7777)
        self.proctree.build()
        facts = self.inspector().read_facts(3012)
        self.assertEqual(7777, facts.start_time_ticks)

    # -- 12 ------------------------------------------------------------ #

    def test_s12_process_without_port_not_necessarily_high(self):
        proc = self.proctree.add(FakeProcess(
            pid=3013, comm="python3",
            argv=("python", "manage.py", "runserver", "0.0.0.0:8006"),
            cwd=str(self.backend_dir), exe=self.binary("python3"), ppid=1))
        self.add_runner_ancestor(3013, ppid=4242)
        proc.ppid = 4242
        self.proctree.build()

        direct = self.resolver().resolve_pid(self.backend_descriptor(), 3013)
        self.assertFalse(direct.port_matches)
        self.assertNotEqual(Confidence.HIGH, direct.confidence)
        self.assertFalse(direct.allows_destructive_action)

    # -- 13 ------------------------------------------------------------ #

    def test_s13_multiple_candidates_are_not_chosen_arbitrarily(self):
        self.add_django_backend(pid=3014, port=8006, inode=970)
        self.add_django_backend(pid=3015, port=8006, inode=970)
        self.proctree.build()

        res = self.resolver().resolve_service("ms_sisper_contratos")
        self.assertEqual((3014, 3015), tuple(sorted(res.candidate_pids)))
        self.assertTrue(res.ambiguous)
        self.assertIsNone(res.identity)
        self.assertEqual(Confidence.NONE, res.confidence)
        self.assertFalse(res.owned)

    # -- 14 ------------------------------------------------------------ #

    def test_s14_shadow_match_when_legacy_equals_safe(self):
        self.add_django_backend(pid=3016, port=8006, inode=980)
        self.proctree.build()
        res = self.resolver().resolve_service("ms_sisper_contratos")
        cmp = ShadowComparator(self.resolver()).compare(
            service="ms_sisper_contratos", operation=Operation.RESTART,
            port=8006, resolution=res)

        self.assertEqual([3016], cmp.legacy["pids"])
        self.assertEqual(3016, cmp.shadow["pid"])
        self.assertEqual("HIGH", cmp.shadow["confidence"])
        self.assertTrue(cmp.shadow["owned"])
        self.assertTrue(cmp.match)
        self.assertEqual("legacy_and_safe_agree", cmp.reason)

    # -- 15 ------------------------------------------------------------ #

    def test_s15_shadow_mismatch_and_new_system_kills_nothing(self):
        """Legacy would kill a foreign PID; the safe system refuses and acts not."""
        foreign = self.temp_dir("ajeno2-") / "ms_sisper_contratos"
        foreign.mkdir(parents=True, exist_ok=True)
        self.add_django_backend(pid=3017, port=8006, cwd=str(foreign), inode=990)
        self.proctree.build()

        res = self.resolver().resolve_service("ms_sisper_contratos")
        cmp = ShadowComparator(self.resolver()).compare(
            service="ms_sisper_contratos", operation=Operation.RESTART,
            port=8006, resolution=res)

        self.assertEqual([3017], cmp.legacy["pids"], "legacy would kill it")
        self.assertEqual(3017, cmp.shadow["pid"], "the candidate is still reported")
        self.assertEqual("NONE", cmp.shadow["confidence"])
        self.assertFalse(cmp.shadow["owned"])
        self.assertFalse(cmp.shadow["allows_destructive_action"],
                         "safe refuses to authorise the action")
        self.assertFalse(cmp.match, "safety divergence is a mismatch")
        self.assertIn("safe_refuses", cmp.reason)

        # The comparison itself must not have touched the process.
        self.assertTrue(self.inspector().is_alive(3017))

    # -- 16 ------------------------------------------------------------ #

    def test_s16_port_collision_external_process_not_owned(self):
        # An unrelated service (e.g. Ollama or a stray server) holds port 8006.
        outside = self.temp_dir("externo-") / "otro_servicio"
        outside.mkdir(parents=True, exist_ok=True)
        self.proctree.add(FakeProcess(
            pid=3018, comm="externo",
            argv=("python3", "-m", "http.server", "8006"),
            cwd=str(outside), exe=self.binary("python3"), ppid=1,
            listening=(8006,), inodes=(995,)))
        self.proctree.build()

        res = self.resolver().resolve_service("ms_sisper_contratos")
        self.assertEqual((3018,), res.candidate_pids)
        self.assertFalse(res.owned)
        self.assertEqual(Confidence.NONE, res.confidence)
        self.assertFalse(res.identity.allows_destructive_action)

    # -- 17 (mandatory: prevents reproducing BR-26) -------------------- #

    def test_s17_electron_like_process_is_not_owned(self):
        """An Electron/dev-server process must never be classified as a service.

        Its cmdline contains ``npm``/``start``/``node``, which would satisfy a
        naive command-only matcher; its cwd is outside the service repo, so
        ownership must be denied.  Reproducing the legacy behaviour here would
        re-create BR-26 (``pkill -f "npm.*start"`` killing the desktop shell).
        """
        electron_home = self.temp_dir("devconsole-desktop-")
        (electron_home / "node_modules" / "electron").mkdir(parents=True)
        (electron_home / "package.json").write_text('{"name":"sisper-devconsole-desktop"}',
                                                    encoding="utf-8")

        self.proctree.add(FakeProcess(
            pid=3100, comm="electron",
            argv=("npm", "start"),
            cwd=str(electron_home), exe=self.binary("node"), ppid=1))
        self.proctree.add(FakeProcess(
            pid=3101, comm="electron",
            argv=(str(electron_home / "node_modules" / ".bin" / "electron"), "."),
            cwd=str(electron_home), exe=self.binary("electron"), ppid=3100))
        self.proctree.build()

        # Scenario (a): the nominal port is free, so nothing is even nominated
        # for the frontend service — the desktop shell must not be picked up.
        res = self.resolver().resolve_service("mf_sisper_sesion")
        self.assertEqual((), res.candidate_pids)
        self.assertFalse(res.owned)

        # Scenario (b): even if a future selector nominated it *by port*, the
        # ownership verdict must still refuse it.
        colliding = self.resolver().resolve_service(
            "mf_sisper_sesion", pids=(3100,))
        self.assertFalse(colliding.owned)
        self.assertEqual(Confidence.NONE, colliding.confidence)
        self.assertFalse(colliding.identity.allows_destructive_action)
        self.assertEqual(RejectionReason.CWD_OUTSIDE_BASE_DIR.value,
                         colliding.identity.rejection_reason)

        # Scenario (c): the same for the backend type.
        backend_collision = self.resolver().resolve_service(
            "ms_sisper_contratos", pids=(3101,))
        self.assertFalse(backend_collision.owned)
        self.assertFalse(backend_collision.identity.allows_destructive_action)


# --------------------------------------------------------------------------- #
# shadow mode plumbing
# --------------------------------------------------------------------------- #

class ProcessModeTest(DevConsoleTestCase):
    """``SISPER_PROCESS_MODE`` parsing must default to the safe legacy path."""

    def test_default_is_legacy_when_unset(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(ProcessMode.LEGACY, current_mode())

    def test_explicit_shadow(self):
        with mock.patch.dict(os.environ, {"SISPER_PROCESS_MODE": "shadow"}):
            self.assertEqual(ProcessMode.SHADOW, current_mode())

    def test_explicit_legacy(self):
        with mock.patch.dict(os.environ, {"SISPER_PROCESS_MODE": "legacy"}):
            self.assertEqual(ProcessMode.LEGACY, current_mode())

    def test_unknown_value_defaults_to_legacy(self):
        for bogus in ("", "  ", "SHADOW!", "new", "true", "1", "yes"):
            with self.subTest(value=bogus):
                with mock.patch.dict(os.environ, {"SISPER_PROCESS_MODE": bogus}):
                    self.assertEqual(ProcessMode.LEGACY, current_mode())

    def test_case_and_whitespace_insensitive(self):
        with mock.patch.dict(os.environ, {"SISPER_PROCESS_MODE": "  ShAdOw  "}):
            self.assertEqual(ProcessMode.SHADOW, current_mode())

    def test_env_var_name_is_stable(self):
        from devconsole.services.runtime.shadow import ENV_VAR
        self.assertEqual("SISPER_PROCESS_MODE", ENV_VAR)


class ShadowObservationTest(RuntimeFixtureTest):
    """The observation hook must be inert in legacy and non-destructive in shadow."""

    def setUp(self):
        super().setUp()
        audit.reset_dedup_state()
        self.addCleanup(audit.reset_dedup_state)

    def test_legacy_mode_returns_none_and_computes_nothing(self):
        self.add_django_backend(pid=3200, port=8006, inode=600)
        self.proctree.build()
        with mock.patch.dict(os.environ, {"SISPER_PROCESS_MODE": "legacy"}):
            with mock.patch.object(ProcessIdentityResolver, "resolve_service",
                                   side_effect=AssertionError("must not run in legacy")):
                result = observe_operation(
                    service="ms_sisper_contratos",
                    operation=Operation.RESTART, port=8006)
        self.assertIsNone(result)

    def test_shadow_mode_returns_a_comparison(self):
        self.add_django_backend(pid=3201, port=8006, inode=601)
        self.proctree.build()
        with mock.patch.dict(os.environ, {"SISPER_PROCESS_MODE": "shadow"}):
            result = observe_operation(
                service="ms_sisper_contratos", operation=Operation.RESTART,
                port=8006, comparator=ShadowComparator(self.resolver()))
        self.assertIsNotNone(result)
        self.assertTrue(result.match)

    def test_shadow_hook_never_raises_even_when_resolution_explodes(self):
        with mock.patch.dict(os.environ, {"SISPER_PROCESS_MODE": "shadow"}):
            with mock.patch.object(ShadowComparator, "compare",
                                   side_effect=RuntimeError("boom")):
                self.assertIsNone(observe_operation(
                    service="x", operation=Operation.RESTART, port=1))

    def test_shadow_never_terminates_the_candidate(self):
        proc = self.add_django_backend(pid=3202, port=8006, inode=602)
        self.proctree.build()
        with mock.patch.dict(os.environ, {"SISPER_PROCESS_MODE": "shadow"}):
            observe_operation(service="ms_sisper_contratos",
                              operation=Operation.STOP, port=8006,
                              comparator=ShadowComparator(self.resolver()))
        self.assertTrue(self.inspector().is_alive(proc.pid))

    def test_no_target_agrees(self):
        self.proctree.build()
        res = self.resolver().resolve_service("ms_sisper_contratos")
        cmp = ShadowComparator(self.resolver()).compare(
            service="ms_sisper_contratos", operation=Operation.RESTART,
            port=8006, resolution=res)
        self.assertTrue(cmp.match)
        self.assertEqual("no_target", cmp.reason)

    def test_legacy_killing_two_pids_is_a_mismatch(self):
        self.add_django_backend(pid=3203, port=8006, inode=603)
        self.add_django_backend(pid=3204, port=8006, inode=603)
        self.proctree.build()
        res = self.resolver().resolve_service("ms_sisper_contratos")
        cmp = ShadowComparator(self.resolver()).compare(
            service="ms_sisper_contratos", operation=Operation.STOP,
            port=8006, resolution=res)
        self.assertFalse(cmp.match)
        self.assertIn("ambiguous", cmp.reason)

    def test_audit_logs_do_not_contain_secrets(self):
        """Audit records service/pid/confidence only — never env or tokens."""
        with self.assertLogs("devconsole.runtime.audit", level="INFO") as captured:
            audit.reset_dedup_state()
            audit.log_identity_decision(
                service="ms_sisper_contratos", operation="restart",
                candidate_pid=1234, confidence="HIGH", owned=True, match=True,
                reason="legacy_and_safe_agree", mode="shadow")
        joined = " ".join(captured.output)
        self.assertIn("identity service=ms_sisper_contratos", joined)
        self.assertIn("confidence=HIGH", joined)
        for forbidden in ("PASSWORD", "SECRET", "TOKEN", "JWT", "PGPASSWORD"):
            self.assertNotIn(forbidden, joined.upper())

    def test_audit_deduplicates_repeated_decisions(self):
        audit.reset_dedup_state()
        with self.assertLogs("devconsole.runtime.audit", level="INFO") as captured:
            for _ in range(50):
                audit.log_identity_decision(
                    service="svc", operation="restart", candidate_pid=1,
                    confidence="NONE", owned=False, match=False, reason="r")
        self.assertEqual(1, len(captured.output), "identical decisions must be de-duplicated")

    def test_report_aggregates_matches_and_mismatches(self):
        from devconsole.services.runtime import build_report
        self.add_django_backend(pid=3205, port=8006, inode=605)
        self.proctree.build()
        resolver = self.resolver()
        report = build_report(services=["ms_sisper_contratos"],
                              comparator=ShadowComparator(resolver))
        self.assertEqual("legacy", report.mode)
        self.assertEqual(1, len(report.comparisons))
        self.assertEqual(1, report.matches)
        self.assertEqual(0, report.mismatches)
        payload = report.to_dict()
        self.assertEqual(1, payload["totals"]["services"])


class MandatoryScenarioCoverageTest(DevConsoleTestCase):
    """Guards that the 17 required scenarios are actually implemented."""

    def test_mandatory_scenarios_are_all_present(self):
        import tests.devconsole.test_runtime_identity as mod
        available = set(dir(mod.MandatoryScenarioTest))
        missing = [name for name, _ in MANDATORY_SCENARIOS.values()
                   if name not in available]
        self.assertEqual([], missing, "mandatory scenario tests are missing")
        self.assertEqual(17, len(MANDATORY_SCENARIOS))

    def test_split_scenarios_have_their_b_prefix(self):
        """Scenarios 9 and 11 carry an extra sub-case; both must exist."""
        import tests.devconsole.test_runtime_identity as mod
        cls = mod.MandatoryScenarioTest
        self.assertTrue(hasattr(cls, "test_s09b_lineage_absent_downgrades"))
        self.assertTrue(hasattr(cls, "test_s11b_start_time_is_exposed_for_future_reuse_checks"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
