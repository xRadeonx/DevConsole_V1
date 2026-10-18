"""Shared helpers for the DevConsole characterization suite.

Design goals
------------
1. **Nothing destructive may ever run.**  :class:`DevConsoleTestCase` installs a
   hard guard that replaces every ``subprocess`` entry point with a stub that
   raises :class:`RealSubprocessError`.  A test that needs subprocess behaviour
   must opt in explicitly (``self.patch_run(...)`` / ``self.patch_popen(...)``).
2. **No real workspace file may be touched.**  Anything that writes uses a
   :class:`tempfile.TemporaryDirectory` fixture.
3. **Deterministic output.**  Tilix session trees contain ``uuid.uuid4()``
   values; :func:`normalize_uuids` replaces them so trees can be compared.

These helpers exist purely so the *existing* behaviour can be frozen before the
Desktop migration refactors it.  They are not a redesign of DevConsole.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from typing import Any, Iterable
from unittest import mock

# --------------------------------------------------------------------------- #
# Import bootstrap
# --------------------------------------------------------------------------- #

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


class RealSubprocessError(AssertionError):
    """Raised when a test attempts to spawn a real child process."""


# --------------------------------------------------------------------------- #
# subprocess guard
# --------------------------------------------------------------------------- #

_SUBPROCESS_ENTRY_POINTS = (
    "Popen",
    "run",
    "call",
    "check_call",
    "check_output",
)


def _explode(name: str):
    def _stub(*args, **kwargs):  # pragma: no cover - guard path
        raise RealSubprocessError(
            f"Test attempted a REAL subprocess.{name}({args!r:.120}, {kwargs!r:.120}). "
            "Patch it explicitly (self.patch_run/patch_popen/patch_check_output)."
        )

    _stub.__name__ = f"_guarded_{name}"
    return _stub


class GuardedSubprocessMixin:
    """Base mixin that forbids real subprocess execution.

    Subclasses may re-patch individual entry points through the ``patch_*``
    helpers below; a later ``mock.patch`` always wins over this guard.
    """

    def setUp(self) -> None:  # noqa: D102 - unittest hook
        super().setUp()
        import subprocess

        self._guard_patchers = []
        for name in _SUBPROCESS_ENTRY_POINTS:
            p = mock.patch.object(subprocess, name, _explode(name))
            p.start()
            self._guard_patchers.append(p)
        self.addCleanup(self._stop_guards)

    def _stop_guards(self) -> None:
        for p in reversed(self._guard_patchers):
            p.stop()
        self._guard_patchers = []

    # -- explicit opt-in helpers ------------------------------------------- #

    def patch_run(self, *, returncode: int = 0, stdout: str = "", stderr: str = ""):
        """Patch ``subprocess.run`` with a deterministic fake."""
        import subprocess

        result = mock.MagicMock()
        result.returncode = returncode
        result.stdout = stdout
        result.stderr = stderr
        p = mock.patch.object(subprocess, "run", return_value=result)
        m = p.start()
        self.addCleanup(p.stop)
        return m

    def patch_check_output(self, *, output: str = "", returncode: int = 0):
        """Patch ``subprocess.check_output`` with a deterministic fake."""
        import subprocess

        def _fake(cmd, *a, **kw):
            if returncode != 0:
                raise subprocess.CalledProcessError(returncode, cmd, output=output)
            return output.encode()

        p = mock.patch.object(subprocess, "check_output", side_effect=_fake)
        m = p.start()
        self.addCleanup(p.stop)
        return m

    def patch_popen(self, *, returncode: int = 0, stdout_lines: Iterable[str] = ()):
        """Patch ``subprocess.Popen`` and record every command that would run.

        Returns ``(mock, recorded_calls)`` where ``recorded_calls`` is a list of
        ``(args, kwargs)`` tuples for later assertions.
        """
        import subprocess

        recorded: list[tuple[Any, Any]] = []

        class _FakeProc:
            def __init__(self, *args, **kwargs):
                recorded.append((args, kwargs))
                self.returncode = returncode
                self.stdout = iter(stdout_lines)

            def wait(self, timeout=None):
                return self.returncode

            def communicate(self, *a, **kw):
                return ("".join(stdout_lines), "")

            def poll(self):
                return self.returncode

        p = mock.patch.object(subprocess, "Popen", _FakeProc)
        m = p.start()
        self.addCleanup(p.stop)
        return m, recorded


class DevConsoleTestCase(GuardedSubprocessMixin, unittest.TestCase):
    """Base class for every DevConsole characterization test."""

    def setUp(self) -> None:
        super().setUp()
        self._tmpdirs: list[tempfile.TemporaryDirectory] = []

    def tearDown(self) -> None:
        for td in self._tmpdirs:
            td.cleanup()
        self._tmpdirs = []
        super().tearDown()

    # -- temp dirs ---------------------------------------------------------- #

    def temp_dir(self, prefix: str = "devconsole-test-") -> Path:
        td = tempfile.TemporaryDirectory(prefix=prefix)
        self._tmpdirs.append(td)
        return Path(td.name)


# --------------------------------------------------------------------------- #
# Fake workspace builder
# --------------------------------------------------------------------------- #

BACKEND_SERVICE = "ms_{name}"
FRONTEND_SERVICE = "mf_{name}"


def make_backend_service(
    root: Path,
    name: str,
    *,
    port: int | None = None,
    with_manage_py: bool = True,
    with_consumer: bool = False,
    with_worker: bool = False,
    extra_env: dict[str, str] | None = None,
) -> Path:
    """Create a minimal fake backend microservice directory tree."""
    d = root / "backend" / name
    d.mkdir(parents=True, exist_ok=True)
    if with_manage_py:
        (d / "manage.py").write_text("# fake\n", encoding="utf-8")
    if port is not None:
        lines = [f"PORT={port}"]
    else:
        lines = []
    for k, v in (extra_env or {}).items():
        lines.append(f"{k}={v}")
    if lines:
        (d / ".env").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if with_consumer:
        (d / "core").mkdir(exist_ok=True)
        (d / "core" / "start_consumer.py").write_text("# fake\n", encoding="utf-8")
    if with_worker:
        (d / "config").mkdir(exist_ok=True)
        (d / "config" / "celery.py").write_text("# fake\n", encoding="utf-8")
    return d


def make_frontend_service(
    root: Path,
    name: str,
    *,
    port: int | None = None,
    with_package_json: bool = True,
    with_git: bool = False,
) -> Path:
    """Create a minimal fake frontend microfrontend directory tree."""
    d = root / "frontend" / name
    d.mkdir(parents=True, exist_ok=True)
    if with_package_json:
        (d / "package.json").write_text('{"name": "%s"}\n' % name, encoding="utf-8")
    if with_git:
        (d / ".git").mkdir(exist_ok=True)
    if port is not None:
        (d / ".env").write_text(f"PORT={port}\n", encoding="utf-8")
    return d


def make_workspace(root: Path) -> Path:
    """Create an empty but structurally complete fake ``BASE_DIR``."""
    (root / "backend").mkdir(parents=True, exist_ok=True)
    (root / "frontend").mkdir(parents=True, exist_ok=True)
    (root / "config" / "sessions").mkdir(parents=True, exist_ok=True)
    (root / "data").mkdir(parents=True, exist_ok=True)
    return root


# --------------------------------------------------------------------------- #
# Tilix session fixtures
# --------------------------------------------------------------------------- #

TILIX_PROFILE_SISPER_AUTO = "c8e01000-0000-0000-0000-000000000001"
TILIX_PROFILE_DEFAULT = "2b7c4080-0ddd-46c5-8f23-563fd3ba789d"


def terminal_node(directory: str, *, profile: str = TILIX_PROFILE_SISPER_AUTO, **extra) -> dict:
    node = {
        "directory": directory,
        "height": 420,
        "profile": profile,
        "readOnly": False,
        "synchronizedInput": False,
        "type": "Terminal",
        "uuid": str(uuid.uuid4()),
        "width": 640,
    }
    node.update(extra)
    return node


def paned_node(child1: dict, child2: dict, *, orientation: int = 0, **extra) -> dict:
    node = {
        "child1": child1,
        "child2": child2,
        "orientation": orientation,
        "position": 50,
        "ratio": 0.5,
        "type": "Paned",
    }
    node.update(extra)
    return node


def session_node(child: dict, *, name: str = "SISPER - Test", **extra) -> dict:
    node = {
        "child": child,
        "height": 1080,
        "width": 1920,
        "name": name,
        "synchronizedInput": False,
        "type": "Session",
        "uuid": str(uuid.uuid4()),
        "version": "1.0",
    }
    node.update(extra)
    return node


def build_balanced_session(directories: list[str], *, name: str = "SISPER - Test") -> dict:
    """Build a Tilix session JSON mirroring the shape the real app produces."""
    if not directories:
        return {}

    def build(items):
        if len(items) == 1:
            return terminal_node(items[0])
        mid = len(items) // 2
        return paned_node(build(items[:mid]), build(items[mid:]))

    return session_node(build(list(directories)), name=name)


def write_session(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


def normalize_uuids(obj: Any, *, key: str | None = None) -> Any:
    """Replace generated UUIDs with ``<uuid>`` so trees compare equal.

    Only values stored under a ``"uuid"`` key are substituted.  The Tilix
    *profile* id is itself UUID-shaped but is a meaningful constant
    (``c8e01000-...`` = the SISPER-Auto profile), so it must survive
    normalization and stay assertable.
    """
    if isinstance(obj, dict):
        return {k: normalize_uuids(v, key=k) for k, v in obj.items()}
    if isinstance(obj, list):
        return [normalize_uuids(v, key=key) for v in obj]
    if isinstance(obj, str) and key == "uuid":
        return _UUID_RE.sub("<uuid>", obj)
    return obj


# --------------------------------------------------------------------------- #
# HTTP handler harness
# --------------------------------------------------------------------------- #

def make_handler(handler_cls, *, path: str, method: str = "GET",
                 headers: dict | None = None, body: bytes = b""):
    """Instantiate ``DevConsoleHandler`` without opening a socket.

    Returns the instance; the captured response is available as
    ``handler.captured`` with keys ``status``, ``headers`` and ``body``.
    """
    import email.message
    import io

    h = handler_cls.__new__(handler_cls)
    h.path = path
    h.command = method
    h.request_version = "HTTP/1.1"
    h.requestline = f"{method} {path} HTTP/1.1"
    h.client_address = ("127.0.0.1", 54321)
    h.server = None
    h.close_connection = True

    msg = email.message.Message()
    for k, v in (headers or {}).items():
        msg[k] = v
    # Real HTTP/1.1 requests always carry Host, and phase 0C validates it
    # (loopback-only when bound to loopback) as the DNS-rebinding defence.
    if not msg.get("Host"):
        msg["Host"] = "127.0.0.1:9099"
    # do_POST() reads exactly Content-Length bytes from rfile; without this the
    # payload would silently be empty.
    if body and not msg.get("Content-Length"):
        msg["Content-Length"] = str(len(body))
    h.headers = msg

    h.rfile = io.BytesIO(body)
    h.wfile = io.BytesIO()
    h.captured = {"status": None, "statuses": [], "headers": []}

    def send_response(code, message=None):
        # Some handlers emit more than one response (see the admin-guard
        # fall-through documented in docs/desktop-migration/phase-0a-baseline.md).
        # ``status`` keeps the last one for backwards compatibility; ``statuses``
        # records every emission in order.
        h.captured["status"] = code
        h.captured["statuses"].append(code)

    def send_header(key, value):
        h.captured["headers"].append((key, value))

    def end_headers():
        # NB: BaseHTTPRequestHandler writes the body *after* end_headers(), so
        # the body is read from wfile at assertion time by json_body()/raw_body().
        pass

    h.send_response = send_response
    h.send_header = send_header
    h.end_headers = end_headers
    h.log_request = lambda *a, **k: None
    h.log_error = lambda *a, **k: None
    h.log_message = lambda *a, **k: None
    return h


def raw_body(handler) -> bytes:
    """Return the captured response body bytes."""
    return handler.wfile.getvalue()


def response_headers(handler) -> dict:
    """Return captured response headers as a lower-cased dict."""
    return {k.lower(): v for k, v in handler.captured["headers"]}


def json_body(handler) -> Any:
    """Decode the captured JSON body, ignoring anything after the first document.

    Normally a handler emits exactly one JSON document.  The admin guard
    fall-through (BR-01) emits two concatenated documents; use
    :func:`json_documents` when that distinction matters.
    """
    docs = json_documents(handler)
    if not docs:
        raise AssertionError("handler produced an empty body")
    return docs[0]


def json_documents(handler) -> list:
    """Decode every JSON document concatenated into the response body.

    Returns a list; ``len(...) == 1`` for a well-behaved handler.
    """
    raw = raw_body(handler).decode("utf-8", errors="replace")
    decoder = json.JSONDecoder()
    docs = []
    idx = 0
    length = len(raw)
    while idx < length:
        while idx < length and raw[idx].isspace():
            idx += 1
        if idx >= length:
            break
        try:
            obj, end = decoder.raw_decode(raw, idx)
        except json.JSONDecodeError:
            break
        docs.append(obj)
        idx = end
    return docs


def fixture_path(name: str) -> Path:
    return FIXTURES_DIR / name


def load_fixture(name: str) -> Any:
    return json.loads(fixture_path(name).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# /tmp redirection
# --------------------------------------------------------------------------- #

def capture_output(testcase):
    """Capture stdout/stderr for the duration of a test.

    Several code paths under characterization print warnings (``[!] Error ...``,
    ``[ENV-WATCHER] ...``).  Capturing them keeps the suite output clean and lets
    the tests assert the diagnostic instead of leaking it to the console.

    Returns ``(stdout, stderr)`` StringIO buffers whose contents are readable
    after the test body runs.
    """
    import contextlib
    import io as _io

    out, err = _io.StringIO(), _io.StringIO()
    ctx = contextlib.ExitStack()
    ctx.enter_context(contextlib.redirect_stdout(out))
    ctx.enter_context(contextlib.redirect_stderr(err))
    ctx.__enter__()
    testcase.addCleanup(ctx.close)
    return out, err


def redirect_tmp_paths(testcase, module, tmpdir: Path):
    """Redirect ``module.Path("/tmp/...")`` writes into ``tmpdir``.

    ``tilix_service`` writes generated Tilix session JSON files to ``/tmp``.
    Tests must not litter the real ``/tmp`` nor depend on its contents, so this
    patches the module's ``Path`` symbol to remap absolute ``/tmp`` paths into a
    per-test temporary directory while leaving every other path untouched.

    Returns ``(real_path_class, captured_paths)`` so expectations can be built.
    """
    import pathlib

    real_path = pathlib.Path
    tmpdir = real_path(tmpdir)
    captured: list[Path] = []

    class _PathProxy:
        """Callable that remaps ``/tmp`` paths but proxies class attributes.

        ``tilix_service`` uses ``Path`` both for the generated session file and
        for ``Path.home()`` inside ``_prepare_tilix_env``; ``__getattr__`` keeps
        every classmethod/classattribute working.
        """

        def __call__(self, value=()):
            p = real_path(value)
            if p.is_absolute() and str(p).startswith("/tmp/"):
                remapped = tmpdir / p.name
                captured.append(remapped)
                return remapped
            return p

        def __getattr__(self, name):
            return getattr(real_path, name)

    patcher = mock.patch.object(module, "Path", _PathProxy())
    patcher.start()
    testcase.addCleanup(patcher.stop)
    return real_path, captured
