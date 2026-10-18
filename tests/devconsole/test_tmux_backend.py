"""Phase 3 characterization: tmux session model, backend logic and real fixture.

Three layers, deliberately separated:

* **Pure** — naming, metadata schema, layout extraction and group membership.
* **Backend with a fake tmux** — every runtime state, the ``run_action``
  dispatcher, the exact ``argv`` handed to tmux, and adversarial inputs.  No real
  process is ever created here.
* **Real tmux fixture** — a dedicated socket, a ``TemporaryDirectory`` and an
  innocuous ``sleep``-based command, used to prove the primitives empirically.
  Skipped when tmux is unavailable.

No microservice, port, database, npm or Django process is involved anywhere in
this file.
"""

from __future__ import annotations

import enum
import json
import os
import re
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
from dataclasses import dataclass, replace
from pathlib import Path
from unittest import mock

from tests.devconsole.support import (
    DevConsoleTestCase,
    build_balanced_session,
    write_session,
)

import devconsole.config as dcfg
from devconsole.services.terminal.tmux_backend import (
    ActionResult,
    Classification,
    RuntimeState,
    TmuxBackend,
)
from devconsole.services.terminal import tmux_attach, tmux_layout
from devconsole.services.terminal.tmux_layout import (
    BACKEND_PORTS,
    FRONTEND_PORTS,
    LAYOUT_FILES,
    META_AUX_TYPE,
    META_CWD,
    META_ENVIRONMENT,
    META_MANAGED,
    META_PORT,
    META_SCHEMA,
    META_SERVICE,
    META_SERVICE_TYPE,
    SCHEMA_VERSION,
    build_metadata,
    classify_directory,
    extract_layout_services,
    parse_override_command,
    parse_tmux_session_name,
    sanitize_component,
    service_to_tmux_session_name,
    services_for_ports,
    validate_metadata,
)
from devconsole.services.terminal.tmux_runtime import (
    SEP,
    TmuxError,
    TmuxRuntime,
    TmuxSession,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Fields parse across processes by tmux.
_UNSAFE_TARGET = re.compile(r"[:.\s]")


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #

@dataclass
class FakeIdentity:
    pid: int
    cwd: str | None = None
    allows_destructive_action: bool = True


class FakeResolution:
    def __init__(self, *, identity=None, candidates=(), ambiguous=False,
                 owned=None, confidence="HIGH"):
        self.identity = identity
        self.candidate_pids = tuple(candidates)
        self.ambiguous = ambiguous
        self.rejected = ()
        self.owned = bool(identity and (owned if owned is not None else True))
        self._confidence = confidence

    @property
    def confidence(self):
        return type("C", (), {"value": self._confidence})()


class FakeResolver:
    """Process-identity resolver whose answers the test dictates per service."""

    def __init__(self, answers: dict | None = None):
        self.answers = answers or {}
        self.asked: list[str] = []

    def resolve_service(self, name, **kwargs):
        self.asked.append(name)
        answer = self.answers.get(name)
        if answer is None:
            return FakeResolution()
        if callable(answer):
            return answer()
        return answer


class FakeRuntime:
    """In-memory tmux server.  Records every call as an exact argv-shaped tuple."""

    def __init__(self, *, available=True, server=True):
        self.sessions: dict[str, TmuxSession] = {}
        self.calls: list[tuple] = []
        self._available = available
        self._server = server
        self._pid = 5000

    # -- availability ---------------------------------------------------- #
    def version(self):
        return "tmux 9.9-fake" if self._available else None

    def available(self):
        return self._available

    def server_running(self):
        return self._server

    # -- reading --------------------------------------------------------- #
    def list_sessions(self):
        if not self._server:
            return []
        return list(self.sessions.values())

    def find_session(self, name):
        return self.sessions.get(name)

    def session_names(self):
        return list(self.sessions)

    def pane_command(self, name):
        return None

    # -- writing --------------------------------------------------------- #
    def new_session(self, *, name, cwd, command, environment=None,
                    width=200, height=50, window_name=None):
        self.calls.append(("new_session", name, str(cwd), list(command),
                           dict(environment or {}), width, height, window_name))
        self._pid += 1
        session = TmuxSession(name=name, windows=1, attached=0, pane_pid=self._pid,
                              pane_dead=False, pane_cwd=str(cwd), metadata={})
        self.sessions[name] = session
        return session

    def set_options(self, name, options):
        self.calls.append(("set_options", name, dict(options)))
        session = self.sessions[name]
        self.sessions[name] = replace(session,
                                      metadata={**session.metadata, **options})

    def respawn_pane(self, name, *, cwd, command, environment=None, kill=True):
        self.calls.append(("respawn_pane", name, str(cwd), list(command),
                           dict(environment or {}), kill))
        self._pid += 1
        session = self.sessions[name]
        self.sessions[name] = replace(session, pane_pid=self._pid)

    def kill_session(self, name):
        self.calls.append(("kill_session", name))
        return self.sessions.pop(name, None) is not None

    # -- test helpers ---------------------------------------------------- #
    def seed(self, name, *, metadata=None, cwd="/x", pid=1234, attached=0,
             pane_dead=False):
        session = TmuxSession(name=name, windows=1, attached=attached, pane_pid=pid,
                              pane_dead=pane_dead, pane_cwd=cwd,
                              metadata=dict(metadata or {}))
        self.sessions[name] = session
        return session

    def kinds(self):
        return [c[0] for c in self.calls]


# --------------------------------------------------------------------------- #
# 1. Pure: naming
# --------------------------------------------------------------------------- #

class SessionNamingTest(DevConsoleTestCase):
    """``service_to_tmux_session_name`` is deterministic, safe and reversible."""

    def test_real_service_names_are_used_verbatim_and_are_reversible(self):
        for service in ("ms_sisper_contratos", "mf_sisper_sesion", "ms_sisper_a"):
            with self.subTest(service=service):
                name = service_to_tmux_session_name(service)
                self.assertEqual(f"sisper_{service}", name)
                parsed = parse_tmux_session_name(name)
                self.assertEqual(service, parsed["service"])
                self.assertIsNone(parsed["aux_type"])

    def test_deterministic(self):
        self.assertEqual(service_to_tmux_session_name("ms_x"),
                         service_to_tmux_session_name("ms_x"))

    def test_auxiliary_sessions_are_distinct_and_reversible(self):
        names = {t: service_to_tmux_session_name("ms_x", t) for t in
                 ("consumer", "worker", "beat", "shell")}
        self.assertEqual(4, len(set(names.values())))
        self.assertEqual("sisper_aux_ms_x_worker", names["worker"])
        for aux_type, name in names.items():
            parsed = parse_tmux_session_name(name)
            self.assertEqual("ms_x", parsed["service"])
            self.assertEqual(aux_type, parsed["aux_type"])

    def test_service_and_auxiliary_never_collide(self):
        self.assertNotEqual(service_to_tmux_session_name("ms_x"),
                            service_to_tmux_session_name("ms_x", "worker"))

    def test_charset_is_safe_for_tmux_targets(self):
        for raw in ("ms.a", "ms:a", "ms a", "ms/a", "../../etc/passwd",
                    "ms$(whoami)", "ms;rm -rf /", "ms`id`", 'ms"x"', "ms\nx"):
            with self.subTest(raw=raw):
                name = service_to_tmux_session_name(raw)
                self.assertIsNone(_UNSAFE_TARGET.search(name), name)
                self.assertRegex(name, r"^[A-Za-z0-9_-]+$")

    def test_sanitised_names_never_collide(self):
        raw = ["ms.a", "ms:a", "ms a", "ms/a", "ms-a", "ms_a"]
        names = [service_to_tmux_session_name(r) for r in raw]
        self.assertEqual(len(raw), len(set(names)), names)

    def test_length_is_bounded(self):
        name = service_to_tmux_session_name("m" * 400)
        self.assertLessEqual(len(name), tmux_layout.MAX_SESSION_NAME)
        self.assertTrue(name.startswith("sisper_"))

    def test_empty_and_bad_input_is_rejected(self):
        for bad in ("", "   ", None, 123):
            with self.subTest(bad=bad):
                with self.assertRaises((ValueError, TypeError)):
                    service_to_tmux_session_name(bad)

    def test_unknown_aux_type_is_rejected(self):
        with self.assertRaises(ValueError):
            service_to_tmux_session_name("ms_x", "nonsense")

    def test_parse_rejects_foreign_names(self):
        for name in ("other_session", "sisper_", "systemd", ""):
            with self.subTest(name=name):
                self.assertIsNone(parse_tmux_session_name(name))

    def test_sanitize_component_leaves_safe_values_untouched(self):
        self.assertEqual("ms_sisper_x", sanitize_component("ms_sisper_x"))
        self.assertEqual("ms_sisper_x", sanitize_component("  ms_sisper_x  "))


# --------------------------------------------------------------------------- #
# 2. Pure: metadata
# --------------------------------------------------------------------------- #

class MetadataSchemaTest(DevConsoleTestCase):
    """Ownership metadata is what authorises an action — not the name."""

    def _meta(self, **over):
        base = build_metadata(service="ms_x", service_type="backend",
                              cwd="/w/backend/ms_x", environment="develop",
                              port=8006)
        base.update(over)
        return base

    def test_build_metadata_shape(self):
        meta = self._meta()
        self.assertEqual("1", meta[META_MANAGED])
        self.assertEqual("ms_x", meta[META_SERVICE])
        self.assertEqual("backend", meta[META_SERVICE_TYPE])
        self.assertEqual("8006", meta[META_PORT])
        self.assertEqual("develop", meta[META_ENVIRONMENT])
        self.assertEqual("/w/backend/ms_x", meta[META_CWD])
        self.assertEqual(SCHEMA_VERSION, meta[META_SCHEMA])

    def test_valid_metadata_passes(self):
        ok, reason = validate_metadata(self._meta(), service="ms_x",
                                       cwd="/w/backend/ms_x", service_type="backend",
                                       port=8006)
        self.assertTrue(ok, reason)

    def test_similar_name_with_wrong_metadata_is_rejected(self):
        ok, reason = validate_metadata(self._meta(), service="ms_other")
        self.assertFalse(ok)
        self.assertEqual("service_mismatch", reason)

    def test_cwd_mismatch_is_rejected(self):
        ok, reason = validate_metadata(self._meta(), cwd="/elsewhere")
        self.assertFalse(ok)
        self.assertEqual("cwd_mismatch", reason)

    def test_port_mismatch_is_rejected(self):
        ok, reason = validate_metadata(self._meta(), port=9999)
        self.assertFalse(ok)
        self.assertEqual("port_mismatch", reason)

    def test_schema_mismatch_is_rejected(self):
        ok, reason = validate_metadata(self._meta(**{META_SCHEMA: "99"}))
        self.assertFalse(ok)
        self.assertTrue(reason.startswith("schema_mismatch"))

    def test_not_managed_is_rejected(self):
        ok, reason = validate_metadata(self._meta(**{META_MANAGED: "0"}))
        self.assertFalse(ok)
        self.assertEqual("not_managed", reason)

    def test_missing_required_keys_are_rejected(self):
        for key in (META_MANAGED, META_SERVICE, META_SERVICE_TYPE, META_CWD,
                    META_SCHEMA):
            with self.subTest(key=key):
                meta = self._meta()
                meta.pop(key)
                ok, reason = validate_metadata(meta)
                self.assertFalse(ok)
                self.assertIn("missing_metadata", reason)

    def test_unknown_service_type_is_rejected(self):
        ok, reason = validate_metadata(self._meta(**{META_SERVICE_TYPE: "alien"}))
        self.assertFalse(ok)
        self.assertTrue(reason.startswith("unknown_service_type"))

    def test_auxiliary_metadata_carries_the_aux_type(self):
        meta = build_metadata(service="ms_x", service_type="auxiliary",
                              cwd="/w/backend/ms_x", environment="develop",
                              aux_type="worker")
        self.assertEqual("worker", meta[META_AUX_TYPE])
        self.assertTrue(validate_metadata(meta)[0])


# --------------------------------------------------------------------------- #
# 3. Pure: layouts and groups
# --------------------------------------------------------------------------- #

class LayoutExtractionTest(DevConsoleTestCase):
    """Layout definitions are read as workspace membership, deterministically."""

    def setUp(self):
        super().setUp()
        self.root = Path(self.temp_dir())
        for name in ("a", "b", "c"):
            (self.root / "backend" / f"ms_{name}").mkdir(parents=True, exist_ok=True)
        (self.root / "frontend" / "mf_a").mkdir(parents=True, exist_ok=True)

    def test_extraction_returns_directories_in_layout_order(self):
        data = build_balanced_session(
            [str(self.root / "backend" / "ms_a"),
             str(self.root / "backend" / "ms_b"),
             str(self.root / "backend" / "ms_c")])
        services = extract_layout_services(data, self.root)
        self.assertEqual(["ms_a", "ms_b", "ms_c"], [s["service"] for s in services])
        self.assertEqual(["backend"] * 3, [s["service_type"] for s in services])

    def test_declared_vs_absent_override_command(self):
        data = build_balanced_session([str(self.root / "backend" / "ms_a")])
        # Checked-in layouts carry no overrideCommand: the profile supplies it
        self.assertEqual("profile_default",
                         extract_layout_services(data, self.root)[0]["command_kind"])
        self.assertEqual({"kind": "profile_default", "path": None},
                         parse_override_command(None))

    def test_generated_default_command_is_recognised_as_the_runner(self):
        cmd = 'bash -c \'cd "/w/backend/ms_a" && exec "/w/tilix_runner.sh"\''
        self.assertEqual({"kind": "runner", "path": "/w/tilix_runner.sh"},
                         parse_override_command(cmd))

    def test_generated_auxiliary_script_is_recognised(self):
        self.assertEqual({"kind": "script", "path": "/tmp/aux.sh"},
                         parse_override_command("/tmp/aux.sh"))

    def test_arbitrary_command_is_refused_rather_than_guessed(self):
        for cmd in ("rm -rf /", "python manage.py runserver", "bash -c 'x'"):
            with self.subTest(cmd=cmd):
                self.assertEqual("unknown", parse_override_command(cmd)["kind"])

    def test_directories_outside_the_workspace_are_dropped(self):
        data = build_balanced_session(["/etc", "/tmp"])
        self.assertEqual([], extract_layout_services(data, self.root))

    def test_duplicate_directories_collapse_to_one_service(self):
        data = build_balanced_session([str(self.root / "backend" / "ms_a")] * 4)
        self.assertEqual(1, len(extract_layout_services(data, self.root)))

    def test_classify_directory_handles_nested_and_flat_shapes(self):
        self.assertEqual("backend",
                         classify_directory(self.root / "backend" / "ms_a", self.root)["service_type"])
        self.assertEqual("frontend",
                         classify_directory(self.root / "frontend" / "mf_a", self.root)["service_type"])
        self.assertEqual("unknown",
                         classify_directory(self.root / "loose", self.root)["service_type"])
        self.assertIsNone(classify_directory("/etc", self.root))

    # -- the nine real layouts ------------------------------------------- #

    def test_all_nine_real_layouts_extract_deterministically(self):
        """The 9 checked-in layouts must yield a stable, non-empty service set."""
        from devconsole.services.terminal import tilix_backend
        sessions = tilix_backend.scan_tilix_sessions()
        self.assertEqual(9, len(sessions), "expected the 9 real layout files")
        for entry in sessions:
            with self.subTest(layout=entry["name"]):
                data = json.loads(Path(entry["abs_path"]).read_text(encoding="utf-8"))
                first = extract_layout_services(data, dcfg.BASE_DIR)
                second = extract_layout_services(data, dcfg.BASE_DIR)
                self.assertEqual(first, second, "extraction must be deterministic")
                self.assertEqual(entry["terminals"], len(first),
                                 "every terminal must map to a service")
                for svc in first:
                    self.assertIn(svc["service_type"], ("backend", "frontend"))

    def test_real_layout_backend_union_matches_the_legacy_port_group(self):
        """Cross-check: layout membership and PORTS_BACKEND must agree."""
        from devconsole.services.terminal import tilix_backend
        found = set()
        for entry in tilix_backend.scan_tilix_sessions():
            data = json.loads(Path(entry["abs_path"]).read_text(encoding="utf-8"))
            for svc in extract_layout_services(data, dcfg.BASE_DIR):
                if svc["service_type"] == "backend":
                    found.add(svc["service"])
        configured = {s["name"]: s["port"] for s in dcfg.SERVICES_BACKEND}
        layout_ports = {configured[n] for n in found if n in configured}
        self.assertTrue(layout_ports <= set(BACKEND_PORTS),
                        f"layouts reference ports outside PORTS_BACKEND: "
                        f"{layout_ports - set(BACKEND_PORTS)}")

    def test_port_groups_match_start_tilix_sh(self):
        """The group must be re-derived from the real script, not trusted."""
        text = (REPO_ROOT / "start_tilix.sh").read_text(encoding="utf-8")

        def ports(var: str) -> tuple[int, ...]:
            match = re.search(rf"^{var}=\(([^)]*)\)", text, re.MULTILINE)
            self.assertIsNotNone(match, f"{var} not found in start_tilix.sh")
            return tuple(int(p) for p in match.group(1).split())

        self.assertEqual(ports("PORTS_BACKEND"), BACKEND_PORTS)
        self.assertEqual(ports("PORTS_FRONTEND"), FRONTEND_PORTS)

    def test_services_for_ports_selects_exactly_the_group(self):
        services = [{"name": "a", "port": 8000}, {"name": "b", "port": 3010},
                    {"name": "c", "port": 9999}]
        self.assertEqual(["a"], [s["name"] for s in services_for_ports(services, BACKEND_PORTS)])
        self.assertEqual(["b"], [s["name"] for s in services_for_ports(services, FRONTEND_PORTS)])

    def test_layout_files_reference_real_files(self):
        for key, rel in LAYOUT_FILES.items():
            with self.subTest(layout=key):
                self.assertTrue((dcfg.BASE_DIR / rel).is_file(), rel)


# --------------------------------------------------------------------------- #
# 4. Backend with a fake tmux
# --------------------------------------------------------------------------- #

def _configured_ports() -> dict[str, int]:
    """name -> port for every configured service (real config)."""
    out = {s["name"]: s["port"] for s in dcfg.SERVICES_BACKEND}
    out.update({s["name"]: s["port"] for s in dcfg.SERVICES_FRONTEND})
    return out


class TmuxBackendTestCase(DevConsoleTestCase):
    """Base class wiring a backend onto a fake runtime and fake identities."""

    def setUp(self):
        super().setUp()
        self.root = Path(self.temp_dir())
        for name in ("ms_a", "ms_b", "mf_a"):
            (self.root / "backend" / name).mkdir(parents=True, exist_ok=True)
        (self.root / "frontend" / "mf_a").mkdir(parents=True, exist_ok=True)
        (self.root / "tilix_runner.sh").write_text("#!/bin/bash\n", encoding="utf-8")
        self.runtime = FakeRuntime()
        self.resolver = FakeResolver()
        self.backend = TmuxBackend(runtime=self.runtime, resolver=self.resolver,
                                   base_dir=self.root)
        self._listening = set()
        self._patch_listening()

    def _patch_listening(self):
        listen = self._listening
        patcher = mock.patch.object(TmuxBackend, "_port_listening",
                                    staticmethod(lambda port: port in listen))
        patcher.start()
        self.addCleanup(patcher.stop)

    def _answer(self, service, *, pid=4242, confidence="HIGH", owned=True,
                ambiguous=False, candidates=None):
        identity = FakeIdentity(pid=pid) if pid else None
        self.resolver.answers[service] = FakeResolution(
            identity=identity,
            candidates=candidates if candidates is not None else ((pid,) if pid else ()),
            owned=owned, confidence=confidence, ambiguous=ambiguous)

    def _services(self, mapping):
        """Patch the configured service list the backend reads."""
        backends = [{"name": n, "port": p, "service_type": "backend"}
                    for n, p in mapping.items()]
        patcher = mock.patch.object(TmuxBackend, "_configured_services",
                                    lambda self: backends)
        patcher.start()
        self.addCleanup(patcher.stop)


class RuntimeStateTest(TmuxBackendTestCase):
    """Every state, and the guarantee that only safe states lead to a write."""

    def test_stopped_when_nothing_is_running(self):
        c = self.backend.classify("ms_a", port=8000, service_type="backend")
        self.assertIs(RuntimeState.STOPPED, c.state)
        self.assertFalse(c.state.blocks_launch)

    def test_legacy_running_when_verified_process_holds_the_port(self):
        self._listening.add(8000)
        self._answer("ms_a", pid=111)
        c = self.backend.classify("ms_a", port=8000, service_type="backend")
        self.assertIs(RuntimeState.LEGACY_RUNNING, c.state)
        self.assertTrue(c.state.blocks_launch, "must never duplicate a legacy service")
        self.assertEqual(111, c.identity_pid)

    def test_medium_confidence_is_an_external_conflict(self):
        self._listening.add(8000)
        self._answer("ms_a", pid=111, confidence="MEDIUM")
        c = self.backend.classify("ms_a", port=8000, service_type="backend")
        self.assertIs(RuntimeState.EXTERNAL_CONFLICT, c.state)
        self.assertTrue(c.state.blocks_launch)

    def test_unowned_process_is_an_external_conflict(self):
        self._listening.add(8000)
        self._answer("ms_a", pid=111, owned=False)
        c = self.backend.classify("ms_a", port=8000, service_type="backend")
        self.assertIs(RuntimeState.EXTERNAL_CONFLICT, c.state)

    def test_ambiguous_fails_closed(self):
        self._listening.add(8000)
        self._answer("ms_a", pid=None, ambiguous=True, candidates=(1, 2))
        c = self.backend.classify("ms_a", port=8000, service_type="backend")
        self.assertIs(RuntimeState.AMBIGUOUS, c.state)
        self.assertTrue(c.state.blocks_launch)
        self.assertEqual([1, 2], c.details["candidates"])

    def test_busy_port_with_no_identified_process_is_a_conflict(self):
        self._listening.add(8000)
        c = self.backend.classify("ms_a", port=8000, service_type="backend")
        self.assertIs(RuntimeState.EXTERNAL_CONFLICT, c.state)
        self.assertEqual("port_busy_unidentified", c.reason)

    def test_managed_session_with_port_open_is_running(self):
        self._listening.add(8000)
        self._answer("ms_a", pid=None, candidates=())
        meta = build_metadata(service="ms_a", service_type="backend",
                              cwd=str(self.root / "backend" / "ms_a"),
                              environment="develop", port=8000)
        self.runtime.seed("sisper_ms_a", metadata=meta,
                          cwd=str(self.root / "backend" / "ms_a"))
        c = self.backend.classify("ms_a", port=8000, service_type="backend")
        self.assertIs(RuntimeState.TMUX_RUNNING, c.state)
        self.assertFalse(c.state.blocks_launch)

    def test_managed_session_with_port_closed_is_stale(self):
        meta = build_metadata(service="ms_a", service_type="backend",
                              cwd=str(self.root / "backend" / "ms_a"),
                              environment="develop", port=8000)
        self.runtime.seed("sisper_ms_a", metadata=meta,
                          cwd=str(self.root / "backend" / "ms_a"))
        c = self.backend.classify("ms_a", port=8000, service_type="backend")
        self.assertIs(RuntimeState.TMUX_STALE, c.state)
        self.assertTrue(c.state.is_owned_by_tmux)

    def test_session_with_foreign_metadata_is_a_conflict(self):
        """A familiar-looking name must not be enough to claim ownership."""
        self.runtime.seed("sisper_ms_a", metadata={META_MANAGED: "1"},
                          cwd=str(self.root / "backend" / "ms_a"))
        c = self.backend.classify("ms_a", port=8000, service_type="backend")
        self.assertIs(RuntimeState.EXTERNAL_CONFLICT, c.state)
        self.assertTrue(c.reason.startswith("session_metadata_invalid"))

    def test_session_for_a_different_service_is_a_conflict(self):
        meta = build_metadata(service="ms_b", service_type="backend",
                              cwd=str(self.root / "backend" / "ms_b"),
                              environment="develop", port=8001)
        self.runtime.seed("sisper_ms_a", metadata=meta,
                          cwd=str(self.root / "backend" / "ms_b"))
        c = self.backend.classify("ms_a", port=8000, service_type="backend")
        self.assertIs(RuntimeState.EXTERNAL_CONFLICT, c.state)

    def test_classify_all_uses_a_single_inventory_call(self):
        """One tmux inventory for N services, not N inventories."""
        self._services({"ms_a": 8000, "ms_b": 8001})
        calls = []
        real = self.runtime.list_sessions

        def counting():
            calls.append(1)
            return real()

        self.runtime.list_sessions = counting
        self.backend.classify_all()
        self.assertEqual(1, len(calls))


class LaunchTest(TmuxBackendTestCase):
    """Creation paths, exact argv, and the refusal to duplicate anything."""

    def test_create_session_argv_and_metadata(self):
        self._services({"ms_a": 8000})
        ok, msg, count = self.backend.launch_services(["ms_a"], "develop")
        self.assertTrue(ok, msg)
        self.assertEqual(1, count)
        kind, name, cwd, command, env, width, height, window_name = self.runtime.calls[0]
        self.assertEqual("new_session", kind)
        # La ventana toma el nombre del servicio: es lo que se lee en la barra de
        # tmux ("[sesion:bash*]" por defecto resultaba poco informativo).
        self.assertEqual("ms_a", window_name)
        self.assertEqual("sisper_ms_a", name)
        self.assertEqual(str(self.root / "backend" / "ms_a"), cwd)
        # multi-element argv: tmux execs it directly instead of using a shell
        self.assertEqual(["bash", str(self.root / "tilix_runner.sh")], command)
        self.assertGreater(len(command), 1)
        self.assertEqual({"SISPER_ENV": "develop"}, env)

    def test_metadata_is_written_immediately_after_creation(self):
        self._services({"ms_a": 8000})
        self.backend.launch_services(["ms_a"], "test")
        kinds = self.runtime.kinds()
        self.assertEqual(["new_session", "set_options"], kinds[:2])
        _, name, options = self.runtime.calls[1]
        self.assertEqual("sisper_ms_a", name)
        ok, reason = validate_metadata(options, service="ms_a",
                                       cwd=str(self.root / "backend" / "ms_a"),
                                       port=8000)
        self.assertTrue(ok, reason)
        self.assertEqual("test", options[META_ENVIRONMENT])

    def test_environment_reaches_the_pane(self):
        self._services({"ms_a": 8000})
        for env in ("develop", "test", "main"):
            with self.subTest(env=env):
                self.runtime.sessions.clear()
                self.runtime.calls.clear()
                self.backend.launch_services(["ms_a"], env)
                self.assertEqual({"SISPER_ENV": env}, self.runtime.calls[0][4])

    def test_already_managed_service_is_not_duplicated(self):
        self._services({"ms_a": 8000})
        self.backend.launch_services(["ms_a"], "develop")
        # the service comes up: managed session + listening port
        self._listening.add(8000)
        self.runtime.calls.clear()
        ok, msg, count = self.backend.launch_services(["ms_a"], "develop")
        self.assertTrue(ok)
        self.assertEqual(1, count)
        self.assertNotIn("new_session", self.runtime.kinds(),
                         "an already-managed service must not be created twice")

    def test_legacy_running_service_is_never_replaced(self):
        self._services({"ms_a": 8000})
        self._listening.add(8000)
        self._answer("ms_a", pid=999)
        ok, msg, count = self.backend.launch_services(["ms_a"], "develop")
        self.assertEqual([], self.runtime.calls, "no tmux write on a legacy service")
        self.assertEqual(0, count)

    def test_external_conflict_is_refused(self):
        self._services({"ms_a": 8000})
        self._listening.add(8000)
        self._answer("ms_a", pid=999, confidence="MEDIUM")
        ok, msg, count = self.backend.launch_services(["ms_a"], "develop")
        self.assertFalse(ok)
        self.assertIn("EXTERNAL_CONFLICT", msg)
        self.assertEqual([], self.runtime.calls)

    def test_duplicate_service_request_creates_one_session(self):
        self._services({"ms_a": 8000})
        self.backend.launch_services(["ms_a", "ms_a"], "develop")
        self.assertEqual(1, self.runtime.kinds().count("new_session"))

    def test_missing_directory_is_reported_not_created(self):
        self._services({"ms_gone": 8000})
        ok, msg, count = self.backend.launch_services(["ms_gone"], "develop")
        self.assertFalse(ok)
        self.assertIn("directorio no encontrado", msg)
        self.assertEqual([], self.runtime.calls)

    def test_all_services_uses_the_configured_list(self):
        self._services({"ms_a": 8000, "ms_b": 8001})
        ok, msg, count = self.backend.launch_services(None, "develop")
        self.assertTrue(ok, msg)
        self.assertEqual(2, count)

    def test_auxiliary_sessions_are_independent(self):
        """An auxiliary has no port, so the live pane is its liveness signal."""
        ok, msg = self.backend.launch_auxiliary("ms_a", "worker", "develop")
        self.assertTrue(ok, msg)
        ok, msg = self.backend.launch_auxiliary("ms_a", "beat", "develop")
        self.assertTrue(ok, msg)
        created = [c[1] for c in self.runtime.calls if c[0] == "new_session"]
        self.assertEqual(["sisper_aux_ms_a_worker", "sisper_aux_ms_a_beat"], created)
        self.assertEqual(2, len(self.runtime.sessions))
        # each auxiliary has its own metadata, so neither is mistaken for a service
        for session in self.runtime.sessions.values():
            self.assertEqual("auxiliary", session.metadata[META_SERVICE_TYPE])
            self.assertIn(session.metadata[META_AUX_TYPE], ("worker", "beat"))

    def test_unknown_auxiliary_type_is_rejected(self):
        ok, msg = self.backend.launch_auxiliary("ms_a", "nonsense")
        self.assertFalse(ok)
        self.assertIn("no reconocido", msg)
        self.assertEqual([], self.runtime.calls)

    def test_selected_auxiliaries_report_count(self):
        ok, msg, count = self.backend.launch_selected_auxiliaries(
            ["ms_a", "ms_b"], "consumer")
        self.assertTrue(ok, msg)
        self.assertEqual(2, count)
        self.assertEqual(2, len(self.runtime.sessions))

    def test_empty_selected_auxiliaries_keeps_the_legacy_tuple(self):
        self.assertEqual((False, "No se seleccionaron servicios.", 0),
                         self.backend.launch_selected_auxiliaries([], "consumer"))

    def test_launch_session_creates_one_session_per_layout_service(self):
        layout = self.root / "layout.json"
        write_session(layout, build_balanced_session(
            [str(self.root / "backend" / "ms_a"),
             str(self.root / "backend" / "ms_b")]))
        self._services({"ms_a": 8000, "ms_b": 8001})
        self.assertTrue(self.backend.launch_session(layout, "develop"))
        self.assertEqual(2, self.runtime.kinds().count("new_session"))
        self.assertEqual({"sisper_ms_a", "sisper_ms_b"}, set(self.runtime.sessions))

    def test_launch_session_on_a_missing_file_fails(self):
        self.assertFalse(self.backend.launch_session(self.root / "nope.json"))

    def test_scan_sessions_keeps_the_public_layout_contract(self):
        sessions = self.backend.scan_sessions()
        self.assertEqual(9, len(sessions))
        self.assertEqual({"name", "rel_path", "abs_path", "terminals", "is_default"},
                         set(sessions[0].keys()))


class StopRestartTest(TmuxBackendTestCase):
    """Stop and restart are exact, and never global."""

    def setUp(self):
        super().setUp()
        self._services({"ms_a": 8000, "ms_b": 8001})
        self.backend.launch_services(["ms_a", "ms_b"], "develop")
        self.runtime.calls.clear()

    def test_restart_single_targets_exactly_one_session(self):
        report = self.backend.run_action("restart-single", ("ms_a", "8000"), wait=True)
        self.assertTrue(report["ok"], report)
        self.assertEqual(["respawn_pane"], self.runtime.kinds())
        self.assertEqual("sisper_ms_a", self.runtime.calls[0][1])
        self.assertIn("sisper_ms_b", self.runtime.sessions, "the other session survives")

    def test_restart_single_preserves_the_session_and_the_cwd(self):
        before = self.runtime.find_session("sisper_ms_a")
        self.backend.run_action("restart-single", ("ms_a", "8000"), wait=True)
        after = self.runtime.find_session("sisper_ms_a")
        self.assertIsNotNone(after, "respawn must keep the session")
        self.assertNotEqual(before.pane_pid, after.pane_pid, "the process must change")
        self.assertEqual(str(self.root / "backend" / "ms_a"), self.runtime.calls[0][2])

    def test_restart_all_touches_only_managed_sessions(self):
        self.runtime.seed("foreign_session", metadata={})
        self.runtime.calls.clear()
        report = self.backend.run_action("restart", wait=True)
        self.assertEqual(2, len(report["results"]))
        self.assertEqual({"sisper_ms_a", "sisper_ms_b"},
                         {c[1] for c in self.runtime.calls if c[0] == "respawn_pane"})
        self.assertIn("foreign_session", self.runtime.sessions)

    def test_stop_terminates_only_managed_sessions(self):
        self.runtime.seed("sisper_foreign", metadata={})
        report = self.backend.run_action("stop", wait=True)
        self.assertEqual({"sisper_ms_a", "sisper_ms_b"},
                         {c[1] for c in self.runtime.calls if c[0] == "kill_session"})
        self.assertIn("sisper_foreign", self.runtime.sessions)

    def test_stop_serves_stop_close_too(self):
        report = self.backend.run_action("stop-close", wait=True)
        self.assertTrue(report["results"])
        self.assertNotIn("tilix", " ".join(str(c) for c in self.runtime.calls))

    def test_stop_ignores_a_session_whose_metadata_is_not_ours(self):
        """A familiar name is not enough: invalid metadata means "not ours"."""
        self.runtime.seed("sisper_ms_other", metadata={META_MANAGED: "1"})
        report = self.backend.run_action("stop", wait=True)
        self.assertEqual({"ms_a", "ms_b"}, {r["service"] for r in report["results"]})
        self.assertIn("sisper_ms_other", self.runtime.sessions,
                      "a foreign session must survive untouched")

    def test_stop_service_returns_false_for_a_service_with_no_session(self):
        self.assertFalse(self.backend.stop_service("ms_not_a"))
        self.assertIn("sisper_ms_a", self.runtime.sessions)

    def test_stop_service_raises_when_metadata_belongs_to_someone_else(self):
        meta = build_metadata(service="ms_b", service_type="backend",
                              cwd=str(self.root / "backend" / "ms_b"),
                              environment="develop", port=8001)
        self.runtime.seed("sisper_ms_a", metadata=meta,
                          cwd=str(self.root / "backend" / "ms_b"))
        with self.assertRaises(TmuxError):
            self.backend.stop_service("ms_a")

    def test_restart_backends_selects_the_backend_group(self):
        report = self.backend.run_action("restart-backends", wait=True)
        self.assertEqual(2, len(report["results"]))
        self.assertEqual({"sisper_ms_a", "sisper_ms_b"},
                         {c[1] for c in self.runtime.calls if c[0] == "respawn_pane"})

    def test_restart_frontends_selects_nothing_when_no_frontend_is_managed(self):
        report = self.backend.run_action("restart-frontends", wait=True)
        self.assertEqual([], report["results"])
        self.assertEqual([], self.runtime.calls)

    def test_restart_of_a_missing_session_is_reported(self):
        report = self.backend.run_action("restart-single", ("ms_gone", "9999"), wait=True)
        self.assertFalse(report["ok"])
        self.assertEqual([], self.runtime.calls)

    def test_no_global_kill_primitive_is_ever_used(self):
        """The whole point: no pkill, no fuser -k, no kill-server."""
        for action in ("stop", "stop-close", "restart", "restart-backends",
                       "restart-frontends"):
            with self.subTest(action=action):
                self.runtime.calls.clear()
                self.backend.run_action(action, wait=True)
                rendered = " ".join(str(c) for c in self.runtime.calls)
                for forbidden in ("pkill", "fuser", "kill-server", "killall"):
                    self.assertNotIn(forbidden, rendered)

    def test_stop_is_idempotent(self):
        self.backend.run_action("stop", wait=True)
        self.runtime.calls.clear()
        report = self.backend.run_action("stop", wait=True)
        self.assertEqual([], report["results"])
        self.assertEqual([], self.runtime.calls)

    def test_stale_session_is_restarted_not_duplicated(self):
        self._listening.discard(8000)
        self.runtime.calls.clear()
        self.backend.launch_services(["ms_a"], "develop")
        self.assertEqual(["respawn_pane"], self.runtime.kinds())
        self.assertEqual(2, len(self.runtime.sessions), "no new session for a stale one")


class ActionDispatcherTest(TmuxBackendTestCase):
    """The dispatcher accepts the real vocabulary and nothing invented."""

    def _mirror_layout(self, key: str) -> set[str]:
        """Write a test-local copy of a real layout, keeping its membership.

        Service *names* come from the real checked-in layout; only the
        directories are rebased into the temporary workspace so the extraction
        runs against test-local data.  That keeps the comparison honest — the
        membership under test is the real one.
        """
        data = json.loads((dcfg.BASE_DIR / LAYOUT_FILES[key]).read_text(encoding="utf-8"))
        entries = extract_layout_services(data, dcfg.BASE_DIR)
        names = []
        for entry in entries:
            rel = Path(entry["cwd"]).relative_to(dcfg.BASE_DIR)
            target = self.root / rel
            target.mkdir(parents=True, exist_ok=True)
            names.append(str(target))
        path = self.root / LAYOUT_FILES[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        write_session(path, build_balanced_session(names, name=key))
        return {e["service"] for e in entries}

    def test_unsupported_action_is_refused(self):
        report = self.backend.run_action("self-destruct", wait=True)
        self.assertFalse(report["ok"])
        self.assertIn("no soportada", report["message"])
        self.assertEqual([], self.runtime.calls)

    def test_vocabulary_matches_the_consumers(self):
        """Re-derive the actions the code actually passes to run_action."""
        text = ""
        for rel in ("devconsole/api/handlers.py",
                    "devconsole/services/env_service.py"):
            text += (REPO_ROOT / rel).read_text(encoding="utf-8")
        used = set(re.findall(r'run_action\(\s*\n?\s*"([^"]+)"', text))
        self.assertTrue(used, "expected run_action call sites")
        self.assertTrue(used <= TmuxBackend.ACTIONS,
                        f"actions the tmux backend cannot serve: {used - TmuxBackend.ACTIONS}")

    def test_start_action_creates_one_session(self):
        self._services({"ms_a": 8000})
        report = self.backend.run_action("start", ("ms_a", "8000"), wait=False)
        self.assertTrue(report["ok"], report)
        self.assertEqual(["new_session", "set_options"], self.runtime.kinds())

    def test_group_actions_select_the_same_services_as_the_legacy_layout(self):
        """The tmux group must cover exactly what the legacy layout covers."""
        self._services({name: port for name, port
                        in _configured_ports().items()})
        for action, layout in (("b1", "b1"), ("b2", "b2"), ("front", "front")):
            with self.subTest(action=action):
                expected = self._mirror_layout(layout)
                self.runtime.sessions.clear()
                self.runtime.calls.clear()
                self.backend.run_action(action, wait=False)
                created = {c[1].removeprefix("sisper_") for c in self.runtime.calls
                           if c[0] == "new_session"}
                self.assertEqual(expected, created, action)

    def test_tabs_action_covers_the_union_of_the_three_layouts(self):
        self._services({name: port for name, port in _configured_ports().items()})
        expected = set()
        for layout in ("b1", "b2", "front"):
            expected |= self._mirror_layout(layout)
        self.backend.run_action("tabs", wait=False)
        created = {c[1].removeprefix("sisper_") for c in self.runtime.calls
                   if c[0] == "new_session"}
        self.assertEqual(expected, created)

    def test_single_layout_is_the_union_of_the_three_groups(self):
        """Cross-check on the real files: single == b1 + b2 + front."""
        def members(key):
            data = json.loads((dcfg.BASE_DIR / LAYOUT_FILES[key])
                              .read_text(encoding="utf-8"))
            return {e["service"] for e in extract_layout_services(data, dcfg.BASE_DIR)}
        self.assertEqual(members("single"),
                         members("b1") | members("b2") | members("front"))

    def test_env_actions_carry_the_environment(self):
        self._services({"ms_a": 8000})
        self._mirror_layout("single")
        for action, env in (("develop", "develop"), ("test", "test"), ("main", "main")):
            with self.subTest(action=action):
                self.runtime.sessions.clear()
                self.runtime.calls.clear()
                self.backend.run_action(action, wait=False)
                self.assertTrue(self.runtime.calls, action)
                self.assertEqual({"SISPER_ENV": env}, self.runtime.calls[0][4])


class AdversarialInputTest(TmuxBackendTestCase):
    """Hostile or malformed input must not reach a shell or escape the workspace."""

    def test_injection_strings_in_a_service_name_never_reach_a_shell(self):
        hostile = ["ms;rm -rf /", "ms$(id)", "ms`id`", "ms&&id", "ms|id",
                   "../../etc/passwd", "ms\nid"]
        for raw in hostile:
            with self.subTest(raw=raw):
                self.runtime.sessions.clear()
                self.runtime.calls.clear()
                name = self.backend.session_name(raw)
                self.assertRegex(name, r"^[A-Za-z0-9_-]+$")
                self.assertNotIn(";", name)
                self.assertNotIn("$", name)
                self.assertNotIn(" ", name)

    def test_command_argv_is_never_a_single_shell_string(self):
        self._services({"ms_a": 8000})
        self.backend.launch_services(["ms_a"], "develop")
        command = self.runtime.calls[0][3]
        self.assertIsInstance(command, list)
        self.assertGreater(len(command), 1,
                           "a 1-element command would be handed to a shell by tmux")
        self.assertEqual("bash", command[0])
        self.assertEqual(str(self.root / "tilix_runner.sh"), command[1])

    @staticmethod
    def _code_without_docstrings(path: Path) -> str:
        """Source with docstrings removed.

        The package *documents* that it never uses ``shell=True``, so scanning
        raw text would flag the documentation itself — the same false positive
        Phase 0B hit.
        """
        import ast
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef)):
                body = node.body
                if body and isinstance(body[0], ast.Expr) and \
                        isinstance(body[0].value, ast.Constant) and \
                        isinstance(body[0].value.value, str):
                    node.body = body[1:] or [ast.Pass()]
        return ast.unparse(tree)

    def test_no_shell_true_anywhere_in_the_terminal_package(self):
        for path in (REPO_ROOT / "devconsole" / "services" / "terminal").glob("*.py"):
            with self.subTest(module=path.name):
                self.assertNotIn("shell=True", self._code_without_docstrings(path))

    def test_no_destructive_primitive_in_the_terminal_package(self):
        """The tmux backend must not carry the legacy kill surface."""
        for path in (REPO_ROOT / "devconsole" / "services" / "terminal").glob("*.py"):
            with self.subTest(module=path.name):
                code = self._code_without_docstrings(path)
                for token in ("pkill", "killall", "fuser", "os.kill", "os.killpg",
                              "SIGKILL", "kill-server"):
                    self.assertNotIn(token, code,
                                     f"{path.name} must not reference {token!r}")

    def test_relative_service_dir_outside_the_workspace_is_not_used(self):
        outside = Path(self.temp_dir()) / "outside" / "ms_x"
        outside.mkdir(parents=True)
        self.assertIsNone(self.backend._service_dir("ms_x", Path("/nonexistent-root")))

    def test_cwd_that_is_not_a_directory_is_refused(self):
        with self.assertRaises(ValueError):
            self.runtime_real_new_session(cwd=self.root / "missing")

    def runtime_real_new_session(self, cwd):
        """Delegate to the real runtime's validation (no tmux call reached)."""
        rt = TmuxRuntime(socket_name="sisper-nonexistent-socket")
        return rt.new_session(name="sisper_ms_x", cwd=cwd,
                              command=["bash", "/bin/true"])

    def test_single_element_command_is_refused_by_the_runtime(self):
        rt = TmuxRuntime(socket_name="sisper-nonexistent-socket")
        with self.assertRaises(ValueError):
            rt.new_session(name="sisper_ms_x", cwd=self.root, command=["bash"])

    def test_attach_command_rejects_unsafe_targets(self):
        for bad in ("a:b", "a.b", "a b", "", None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    tmux_attach.attach_command(bad)

    def test_attach_command_shape(self):
        # Sin `exec`: Tilix ejecuta el comando con execve (no hay shell), así que
        # el primer argumento tiene que ser `tmux`.  Con `exec` delante, la
        # ventana fallaba con "Failed to execve: No existe el fichero".
        # Apaga la barra de estado y adjunta en el mismo comando (tmux separa por
        # `;`): la leyenda "[sesion:ventana] título fecha" sólo estorba en una
        # consola de lectura de logs.
        self.assertEqual("tmux set-option -t sisper_ms_a status off ; attach-session -t sisper_ms_a",
                         tmux_attach.attach_command("sisper_ms_a"))


class TmuxFailureTest(TmuxBackendTestCase):
    """tmux errors and races become reports, never crashes or silent success."""

    def test_tmux_server_unavailable_yields_stopped_not_an_exception(self):
        self.backend.runtime = FakeRuntime(server=False)
        c = self.backend.classify("ms_a", port=8000, service_type="backend")
        self.assertIs(RuntimeState.STOPPED, c.state)

    def test_tmux_unavailable_makes_managed_sessions_empty(self):
        self.backend.runtime = FakeRuntime(available=False, server=False)
        self.assertEqual([], self.backend.managed_sessions())

    def test_creation_failure_is_reported_as_failure(self):
        self._services({"ms_a": 8000})
        with mock.patch.object(FakeRuntime, "new_session",
                               side_effect=TmuxError("boom")):
            ok, msg, count = self.backend.launch_services(["ms_a"], "develop")
        self.assertFalse(ok)
        self.assertIn("boom", msg)
        self.assertEqual(0, count)

    def test_disappeared_session_during_restart_is_reported(self):
        session = self.runtime.seed("sisper_ms_a", metadata=build_metadata(
            service="ms_a", service_type="backend",
            cwd=str(self.root / "backend" / "ms_a"), environment="develop", port=8000),
            cwd=str(self.root / "backend" / "ms_a"))
        with mock.patch.object(FakeRuntime, "respawn_pane",
                               side_effect=TmuxError("session vanished")):
            report = self.backend.run_action("restart-single", ("ms_a", "8000"), wait=True)
        self.assertFalse(report["ok"])

    def test_restart_with_absent_cwd_is_refused(self):
        meta = build_metadata(service="ms_a", service_type="backend",
                              cwd="/definitely/not/here", environment="develop",
                              port=8000)
        self.runtime.seed("sisper_ms_a", metadata=meta, cwd="/definitely/not/here")
        report = self.backend.run_action("restart", wait=True)
        self.assertFalse(report["ok"])
        self.assertEqual([], [c for c in self.runtime.calls if c[0] == "respawn_pane"])

    def test_a_foreign_session_never_appears_in_a_stop_report(self):
        self.runtime.seed("sisper_ms_a", metadata={META_MANAGED: "1"})
        report = self.backend.run_action("stop", wait=True)
        self.assertEqual([], report["results"])
        self.assertFalse(report["ok"], "stopping nothing is not a success")
        self.assertIn("sisper_ms_a", self.runtime.sessions)

    def test_a_failed_stop_is_reported_as_not_ok(self):
        self._services({"ms_a": 8000})
        self.backend.launch_services(["ms_a"], "develop")
        self.runtime.calls.clear()
        with mock.patch.object(FakeRuntime, "kill_session",
                               side_effect=TmuxError("boom")):
            report = self.backend.run_action("stop", wait=True)
        self.assertFalse(report["ok"])
        self.assertFalse(report["results"][0]["ok"])
        self.assertIn("rechazado", report["results"][0]["message"])


class ViewerLayoutTest(DevConsoleTestCase):
    """The Tilix attach layout cannot start a service by accident."""

    def test_layout_uses_the_default_profile_not_the_sisper_auto_one(self):
        layout = tmux_attach.build_attach_layout([("sisper_ms_a", "A")])
        self.assertEqual(tmux_attach.DEFAULT_PROFILE_ID, layout["child"]["profile"])
        self.assertNotEqual(tmux_layout.TILIX_PROFILE_ID, layout["child"]["profile"],
                            "the SISPER-Auto profile runs tilix_runner.sh")

    def test_layout_command_attaches_and_never_runs_the_runner(self):
        layout = tmux_attach.build_attach_layout([("sisper_ms_a", "A")])
        command = layout["child"]["overrideCommand"]
        # Sin `exec` delante: Tilix ejecuta el comando con execve, así que el
        # primer argumento debe ser `tmux` (con `exec` fallaba con
        # "Failed to execve: No existe el fichero").
        self.assertEqual("tmux set-option -t sisper_ms_a status off ; attach-session -t sisper_ms_a",
                         command)
        self.assertNotIn("tilix_runner.sh", command)
        # Tilix exige `directory` en cada nodo Terminal: sin él rechaza el
        # fichero ("Key not found: directory") y la ventana no se abre.
        self.assertTrue(layout["child"]["directory"])

    def test_multi_service_layout_attaches_each_session_once(self):
        entries = [("sisper_ms_a", None), ("sisper_ms_b", None), ("sisper_mf_a", None)]
        layout = tmux_attach.build_attach_layout(entries)
        rendered = json.dumps(layout)
        for name, _ in entries:
            self.assertEqual(1, rendered.count(f"attach-session -t {name}"))

    def test_empty_layout_is_empty(self):
        self.assertEqual({}, tmux_attach.build_attach_layout([]))

    def test_layout_is_json_serializable(self):
        layout = tmux_attach.build_attach_layout([("sisper_ms_a", None)])
        self.assertIsInstance(json.dumps(layout), str)

    def test_viewer_argv_uses_new_process(self):
        argv = tmux_attach.viewer_argv(Path("/tmp/some_layout.json"))
        self.assertEqual(["tilix", "--new-process", "--session=/tmp/some_layout.json"], argv)

    def test_viewer_argv_single_format_and_safety(self):
        argv = tmux_attach.viewer_argv_single("sisper_ms_a", "Service A")
        expected = [
            "tilix", "--new-process", "-p", tmux_attach.DEFAULT_PROFILE_ID,
            "-t", "Service A", "-e", "tmux attach-session -t sisper_ms_a"
        ]
        self.assertEqual(expected, argv)

    def test_viewer_argv_single_rejects_unsafe_targets(self):
        for bad in ("", "foo;bar", "foo bar", "foo:bar", "foo.bar"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    tmux_attach.viewer_argv_single(bad)


# --------------------------------------------------------------------------- #
# 5. Real tmux fixture (3K)
# --------------------------------------------------------------------------- #

def _tmux_available() -> bool:
    return shutil.which("tmux") is not None


def _ppid(pid: int) -> int | None:
    try:
        return int(Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[1])
    except (OSError, ValueError, IndexError):
        return None


@unittest.skipUnless(_tmux_available(), "tmux is not installed")
class RealTmuxFixtureTest(unittest.TestCase):
    """Empirical primitives on a dedicated socket with innocuous processes.

    Uses plain :class:`unittest.TestCase`, not the guarded base class: this is
    the one place where running a *real* child process is the entire point.  The
    guard exists to forbid destructive child processes, and everything here runs
    on a dedicated tmux socket inside a ``TemporaryDirectory`` against an
    innocuous ``sleep`` loop — no microservice, port, npm, Django or database.

    Isolation: unique socket name, ``TemporaryDirectory``, a marker-unique
    ``sleep`` loop.  No microservice port, no npm, no Django, no database.

    Process counting is done by *parentage*, not by matching command lines:
    naive text matching is wrong twice over — the harness's own shell contains
    the script text, and the tmux server's argv contains the whole pane command.
    Phase 3 found both of those the hard way.
    """

    MARKER = "SISPERPHASE3FIXTURE"

    _counter = 0

    def setUp(self):
        super().setUp()
        # A unique socket per test.  Sharing one class-level socket made tests
        # interfere: `kill-server` is asynchronous, so a lingering server plus a
        # reused session name let one test observe another's dying pane.  That
        # produced a false "pane_pid is the server" failure.
        type(self)._counter += 1
        self.socket = f"sisper-p3-{os.getpid()}-{type(self)._counter}"
        self.rt = TmuxRuntime(socket_name=self.socket)
        self.tmp = Path(tempfile.mkdtemp(prefix="sisper-p3-"))
        self.service_dir = self.tmp / "backend" / "ms_fixture"
        self.service_dir.mkdir(parents=True)
        self.command = ["bash", "-c",
                        f"while :; do sleep 0.5; done  # {self.MARKER}"]
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        subprocess.run(["tmux", "-L", self.socket, "kill-server"],
                       capture_output=True)
        # kill-server returns before the server is gone; wait so the socket is
        # genuinely free for the next test.
        deadline = time.time() + 5
        while time.time() < deadline and self.rt.server_running():
            time.sleep(0.1)
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- helpers --------------------------------------------------------- #

    def _server_pid(self) -> int | None:
        """The tmux server is the parent of its panes."""
        for session in self.rt.list_sessions():
            if session.pane_pid:
                return _ppid(session.pane_pid)
        return None

    def _fixture_panes(self, name: str, needle: str | None = None) -> list[int]:
        """PIDs that are panes of our server running the given command.

        ``needle`` defaults to the fixture marker; the backend-driven test uses
        the runner path instead, because that is what the backend executes.
        """
        needle = needle or self.MARKER
        server = self._server_pid()
        if server is None:
            return []
        found = []
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            pid = int(entry)
            if _ppid(pid) != server:
                continue
            try:
                cmd = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode()
            except OSError:
                continue
            if needle in cmd:
                found.append(pid)
        return found

    def _spawn_client(self, name: str):
        """Attach a real tmux client through a pty (no Tilix window needed)."""
        import pty
        import select

        pid, fd = pty.fork()
        if pid == 0:
            os.environ["TERM"] = "xterm-256color"
            try:
                os.execvp("tmux", ["tmux", "-L", self.socket, "attach-session", "-t", name])
            finally:  # pragma: no cover
                os._exit(127)
        deadline = time.time() + 6
        while time.time() < deadline:
            try:
                ready, _, _ = select.select([fd], [], [], 0.2)
                if ready:
                    os.read(fd, 65536)
                    break
            except OSError:
                break
        time.sleep(0.4)
        self.addCleanup(self._kill_client, pid, fd)
        return pid, fd

    @staticmethod
    def _kill_client(pid, fd):
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.kill(pid, 9)
        except ProcessLookupError:
            pass
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass

    def _wait_for_pane_exec(self, name="sisper_ms_fixture", expected="bash",
                            timeout=6.0):
        """Wait until the pane's process has exec'd.

        A pane's process is a fork of the tmux server, so until it execs,
        ``/proc/<pane_pid>/exe`` is the *tmux binary* and its cmdline is the
        server's.  That is a race, not a wrong PID — inspection must wait.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            session = self.rt.find_session(name)
            if session and session.pane_pid:
                try:
                    exe = Path(os.readlink(f"/proc/{session.pane_pid}/exe")).name
                except OSError:
                    exe = None
                if exe == expected:
                    return session
            time.sleep(0.05)
        return self.rt.find_session(name)

    def _create(self, name="sisper_ms_fixture", **over):
        kwargs = dict(name=name, cwd=self.service_dir, command=self.command,
                      environment={"SISPER_ENV": "develop", self.MARKER: "1"})
        kwargs.update(over)
        return self.rt.new_session(**kwargs)

    # -- tests ----------------------------------------------------------- #

    def test_tmux_version_is_reported(self):
        self.assertIn("tmux", self.rt.version())

    def test_create_discover_and_metadata_roundtrip(self):
        meta = build_metadata(service="ms_fixture", service_type="backend",
                              cwd=str(self.service_dir), environment="develop",
                              port=59999)
        self._create()
        self.rt.set_options("sisper_ms_fixture", meta)
        session = self.rt.find_session("sisper_ms_fixture")
        self.assertIsNotNone(session)
        ok, reason = validate_metadata(session.metadata, service="ms_fixture",
                                       cwd=str(self.service_dir),
                                       service_type="backend", port=59999)
        self.assertTrue(ok, reason)
        self.assertFalse(validate_metadata(session.metadata, service="other")[0])

    def test_pane_pid_is_the_process_not_the_server(self):
        """Regression guard for a real Phase 3 misreading.

        Immediately after creation the pane process is still an un-exec'd fork
        of the tmux server, so ``/proc/<pane_pid>/exe`` reads ``tmux``.  That
        looked like a wrong PID and was not; this test waits for the exec and
        then asserts the PID really is the pane's own process.
        """
        self._create()
        session = self._wait_for_pane_exec()
        server = self._server_pid()
        self.assertNotEqual(server, session.pane_pid,
                            "the pane PID must not be the tmux server")
        self.assertEqual("bash", Path(os.readlink(f"/proc/{session.pane_pid}/exe")).name)

    def test_pane_pid_matches_between_list_sessions_and_list_panes(self):
        """Two independent tmux views of the same fact must agree."""
        self._create()
        self._wait_for_pane_exec()
        by_session = {s.name: s.pane_pid for s in self.rt.list_sessions()}
        raw = subprocess.run(["tmux", "-L", self.socket, "list-panes", "-a", "-F",
                              "#{session_name}|#{pane_pid}"],
                             capture_output=True, text=True).stdout
        by_pane = dict(line.split("|") for line in raw.strip().splitlines() if "|" in line)
        self.assertEqual(str(by_session["sisper_ms_fixture"]),
                         by_pane["sisper_ms_fixture"])

    def test_an_unexec_d_pane_looks_like_the_server(self):
        """Document the race explicitly so nobody misreads it again."""
        self._create(name="sisper_ms_fixture")
        session = self.rt.find_session("sisper_ms_fixture")
        observed = set()
        deadline = time.time() + 6
        while time.time() < deadline:
            try:
                observed.add(Path(os.readlink(f"/proc/{session.pane_pid}/exe")).name)
            except OSError:
                pass
            if "bash" in observed:
                break
            time.sleep(0.01)
        self.assertIn("bash", observed)
        # the pane PID never changed while its exe did: the PID was right all along
        self.assertEqual(session.pane_pid,
                         self.rt.find_session("sisper_ms_fixture").pane_pid)

    def test_multi_element_argv_is_executed_without_a_shell(self):
        self._create()
        session = self._wait_for_pane_exec()
        cmdline = Path(f"/proc/{session.pane_pid}/cmdline").read_bytes() \
            .replace(b"\0", b" ").decode()
        self.assertTrue(cmdline.startswith("bash -c"), cmdline)
        self.assertFalse(cmdline.startswith("sh -c"), cmdline)
        self.assertFalse(cmdline.startswith("/bin/sh"), cmdline)

    def test_environment_and_cwd_reach_the_pane(self):
        self._create()
        session = self._wait_for_pane_exec()
        env = self.rt.environment_of_pane("sisper_ms_fixture")
        self.assertEqual("1", env.get(self.MARKER))
        self.assertEqual("develop", env.get("SISPER_ENV"))
        self.assertEqual(self.service_dir.resolve(),
                         Path(os.readlink(f"/proc/{session.pane_pid}/cwd")).resolve())

    def test_two_clients_attach_concurrently_without_disturbing_the_service(self):
        self._create()
        pid_before = self.rt.find_session("sisper_ms_fixture").pane_pid
        self._spawn_client("sisper_ms_fixture")
        self.assertEqual(1, self.rt.find_session("sisper_ms_fixture").attached)
        self._spawn_client("sisper_ms_fixture")
        self.assertEqual(2, self.rt.find_session("sisper_ms_fixture").attached)
        self.assertEqual(pid_before, self.rt.find_session("sisper_ms_fixture").pane_pid,
                         "attaching must not restart or duplicate the service")
        self.assertEqual(1, len(self._fixture_panes("sisper_ms_fixture")))

    def test_respawn_pane_changes_the_pid_and_keeps_session_and_clients(self):
        """This is the evidence behind choosing respawn-pane over kill+new."""
        self._create()
        first = self.rt.find_session("sisper_ms_fixture")
        self._spawn_client("sisper_ms_fixture")
        self.assertEqual(1, self.rt.find_session("sisper_ms_fixture").attached)

        self.rt.respawn_pane("sisper_ms_fixture", cwd=self.service_dir,
                             command=self.command,
                             environment={"SISPER_ENV": "test", self.MARKER: "1"})
        time.sleep(1.0)
        second = self.rt.find_session("sisper_ms_fixture")

        self.assertIsNotNone(second, "the session must survive a respawn")
        self.assertNotEqual(first.pane_pid, second.pane_pid, "the process must be new")
        self.assertEqual(1, second.attached, "attached clients must survive a respawn")
        self.assertEqual("test", self.rt.environment_of_pane("sisper_ms_fixture")
                         .get("SISPER_ENV"))
        self.assertEqual(self.service_dir.resolve(),
                         Path(os.readlink(f"/proc/{second.pane_pid}/cwd")).resolve())
        self.assertEqual(1, len(self._fixture_panes("sisper_ms_fixture")),
                         "a restart must not leave the old process behind")
        self.assertFalse(Path(f"/proc/{first.pane_pid}").exists(),
                         "the old pane process must be gone")

    def test_kill_session_removes_the_session_and_its_processes(self):
        self._create()
        self.assertTrue(self.rt.kill_session("sisper_ms_fixture"))
        time.sleep(0.4)
        self.assertIsNone(self.rt.find_session("sisper_ms_fixture"))
        self.assertEqual([], self._fixture_panes("sisper_ms_fixture"))
        self.assertFalse(self.rt.kill_session("sisper_ms_fixture"),
                         "killing a missing session is idempotent")

    def test_backend_end_to_end_on_the_fixture(self):
        """The backend drives the real primitives, with no duplicate processes."""
        backend = TmuxBackend(runtime=self.rt, resolver=FakeResolver(),
                              base_dir=self.tmp,
                              runner=self.service_dir / "runner.sh")
        (self.service_dir / "runner.sh").write_text(
            f"#!/bin/bash\nwhile :; do sleep 0.5; done  # {self.MARKER}\n",
            encoding="utf-8")
        (self.service_dir / "runner.sh").chmod(0o755)

        listening = {"open": False}
        with mock.patch.object(TmuxBackend, "_port_listening",
                               staticmethod(lambda port: listening["open"])):
            # nothing serving yet -> STOPPED -> the session is created
            created = backend.ensure_session(service="ms_fixture",
                                             service_type="backend", port=59999,
                                             cwd=self.service_dir,
                                             environment="develop")
            self.assertIs(RuntimeState.TMUX_STALE, created.state,
                          "created but not yet serving is STALE, not RUNNING")
            listening["open"] = True
            first = backend.classify("ms_fixture", port=59999, service_type="backend")
        self.assertEqual(RuntimeState.TMUX_RUNNING, first.state)
        # the backend runs the runner script, so count by that, not by MARKER
        panes = self._fixture_panes("sisper_ms_fixture", needle="runner.sh")
        self.assertEqual(1, len(panes))

        # restart through the backend: session and clients survive, no duplicate
        self._spawn_client("sisper_ms_fixture")
        with mock.patch.object(TmuxBackend, "_port_listening",
                               staticmethod(lambda port: listening["open"])):
            report = backend.run_action("restart-single",
                                        ("ms_fixture", "59999"), wait=True)
        self.assertTrue(report["ok"], report)
        time.sleep(1.0)
        self.assertEqual(1, len(self._fixture_panes("sisper_ms_fixture",
                                                   needle="runner.sh")),
                         "backend restart must not duplicate the service")
        self.assertEqual(1, self.rt.find_session("sisper_ms_fixture").attached)

        # stop through the backend
        backend.stop_service("ms_fixture")
        time.sleep(0.4)
        self.assertIsNone(self.rt.find_session("sisper_ms_fixture"))
        self.assertEqual([], self._fixture_panes("sisper_ms_fixture",
                                                 needle="runner.sh"))

    def test_foreign_session_is_not_adopted_by_the_backend(self):
        backend = TmuxBackend(runtime=self.rt, resolver=FakeResolver(),
                              base_dir=self.tmp)
        self.rt.new_session(name="sisper_ms_fixture", cwd=self.service_dir,
                            command=self.command)
        # no metadata written: the backend must refuse to consider it its own
        self.assertEqual([], backend.managed_sessions())
        with mock.patch.object(TmuxBackend, "_port_listening",
                               staticmethod(lambda port: True)):
            classification = backend.classify("ms_fixture", port=59999,
                                              service_type="backend")
        self.assertIs(RuntimeState.EXTERNAL_CONFLICT, classification.state)
        self.assertIn("sisper_ms_fixture", self.rt.session_names())

    def test_attach_viewer_success(self):
        backend = TmuxBackend(runtime=self.rt, resolver=FakeResolver(), base_dir=self.tmp)
        self.rt.new_session(name="sisper_ms_fixture", cwd=self.service_dir, command=self.command)
        with mock.patch.object(backend, "_spawn_viewer") as mock_spawn:
            ok, msg = backend.attach_viewer("ms_fixture")
            self.assertTrue(ok)
            self.assertIn("Visor Tilix abierto", msg)
            mock_spawn.assert_called_once()
            args, _ = mock_spawn.call_args
            self.assertEqual(args[0][0], "tilix")
            self.assertEqual(args[0][1], "--new-process")
            self.assertIn("tmux attach-session -t sisper_ms_fixture", args[0][-1])


    def test_attach_viewer_session_missing(self):
        backend = TmuxBackend(runtime=self.rt, resolver=FakeResolver(), base_dir=self.tmp)
        ok, msg = backend.attach_viewer("ms_missing_svc")
        self.assertFalse(ok)
        self.assertIn("no existe", msg)

