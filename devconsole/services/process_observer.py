"""Optional psutil process observer for the DevConsole V1.1 migration.

This module is deliberately *outside* ``services.runtime``.  The current runtime
package is a frozen, standard-library-only safety boundary.  V1.1 first uses
psutil as an observational/shadow source; only after parity evidence exists may
we consider promoting it behind the runtime abstraction.

There are no process mutation methods here.  The observer can enumerate and
read facts only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:  # Optional dependency during the migration.
    import psutil as _psutil
except ImportError:  # pragma: no cover - exercised through dependency injection
    _psutil = None

_AUTO = object()


@dataclass(frozen=True)
class ObservedProcess:
    pid: int
    ppid: int | None = None
    executable: str | None = None
    command_line: tuple[str, ...] = ()
    cwd: str | None = None
    listening_ports: tuple[int, ...] = ()
    username: str | None = None
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "pid": self.pid,
            "ppid": self.ppid,
            "executable": self.executable,
            "command_line": list(self.command_line),
            "cwd": self.cwd,
            "listening_ports": list(self.listening_ports),
            "username": self.username,
            "errors": list(self.errors),
        }


@dataclass(frozen=True)
class ObserverComparison:
    pid: int
    comparable: bool
    matches: dict[str, bool] = field(default_factory=dict)
    differences: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def equivalent(self) -> bool:
        return self.comparable and all(self.matches.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "pid": self.pid,
            "comparable": self.comparable,
            "equivalent": self.equivalent,
            "matches": dict(self.matches),
            "differences": dict(self.differences),
        }


class PsutilObserver:
    """Read-only process observer backed by psutil when available.

    ``psutil_module`` is injectable for deterministic tests.  Omitting it uses
    the installed dependency; passing ``None`` or ``False`` explicitly forces
    the unavailable path, which is useful for proving fallback behaviour.
    """

    def __init__(self, psutil_module=_AUTO) -> None:
        self._psutil = _psutil if psutil_module is _AUTO else psutil_module

    @property
    def available(self) -> bool:
        return bool(self._psutil)

    def status(self) -> dict[str, Any]:
        version = getattr(self._psutil, "__version__", None) if self._psutil else None
        return {"available": self.available, "backend": "psutil", "version": version}

    def list_pids(self) -> list[int]:
        if not self._psutil:
            return []
        try:
            return sorted(int(pid) for pid in self._psutil.pids())
        except Exception:
            return []

    def is_alive(self, pid: int) -> bool:
        if not self._psutil:
            return False
        try:
            return bool(self._psutil.pid_exists(int(pid)))
        except Exception:
            return False

    @staticmethod
    def _safe_call(fn, label: str, errors: list[str], default=None):
        try:
            return fn()
        except Exception as exc:
            errors.append(f"{label}: {type(exc).__name__}")
            return default

    def _listening_ports(self, process, errors: list[str]) -> tuple[int, ...]:
        if not self._psutil:
            return ()
        getter = getattr(process, "net_connections", None)
        if getter is None:
            getter = getattr(process, "connections", None)
        if getter is None:
            errors.append("connections: unsupported")
            return ()
        try:
            connections = getter(kind="inet")
        except Exception as exc:
            errors.append(f"connections: {type(exc).__name__}")
            return ()

        listen = getattr(self._psutil, "CONN_LISTEN", "LISTEN")
        ports: set[int] = set()
        for connection in connections or ():
            if getattr(connection, "status", None) != listen:
                continue
            local = getattr(connection, "laddr", None)
            port = getattr(local, "port", None)
            if port is None and isinstance(local, (tuple, list)) and len(local) >= 2:
                port = local[1]
            try:
                if port:
                    ports.add(int(port))
            except (TypeError, ValueError):
                continue
        return tuple(sorted(ports))

    def observe(self, pid: int) -> ObservedProcess:
        if not self._psutil:
            return ObservedProcess(pid=int(pid), errors=("psutil unavailable",))

        errors: list[str] = []
        try:
            process = self._psutil.Process(int(pid))
        except Exception as exc:
            return ObservedProcess(pid=int(pid), errors=(f"process: {type(exc).__name__}",))

        ppid = self._safe_call(process.ppid, "ppid", errors)
        executable = self._safe_call(process.exe, "exe", errors)
        cmdline = self._safe_call(process.cmdline, "cmdline", errors, default=()) or ()
        cwd = self._safe_call(process.cwd, "cwd", errors)
        username = self._safe_call(process.username, "username", errors)
        ports = self._listening_ports(process, errors)

        if cwd:
            try:
                cwd = str(Path(cwd).resolve())
            except OSError:
                cwd = str(cwd)

        return ObservedProcess(
            pid=int(pid),
            ppid=int(ppid) if ppid is not None else None,
            executable=str(executable) if executable else None,
            command_line=tuple(str(part) for part in cmdline),
            cwd=str(cwd) if cwd else None,
            listening_ports=ports,
            username=str(username) if username else None,
            errors=tuple(errors),
        )


def compare_with_procfs(pid: int, *, observer: PsutilObserver | None = None,
                        proc_inspector=None) -> ObserverComparison:
    """Compare psutil evidence with the existing read-only procfs inspector.

    No caller behaviour changes based on this result.  It exists solely to
    collect parity evidence before any runtime promotion.
    """
    observer = observer or PsutilObserver()
    if not observer.available:
        return ObserverComparison(pid=int(pid), comparable=False)

    if proc_inspector is None:
        from devconsole.services.runtime.process_inspector import ProcessInspector

        proc_inspector = ProcessInspector()

    ps = observer.observe(pid)
    proc = proc_inspector.read_facts(pid)

    pairs = {
        "ppid": (ps.ppid, proc.ppid),
        "executable": (ps.executable, proc.executable),
        "command_line": (tuple(ps.command_line), tuple(proc.command_line)),
        "cwd": (ps.cwd, proc.cwd),
        "listening_ports": (tuple(sorted(ps.listening_ports)), tuple(sorted(proc.listening_ports))),
    }
    matches: dict[str, bool] = {}
    differences: dict[str, dict[str, Any]] = {}
    for key, (left, right) in pairs.items():
        same = left == right
        matches[key] = same
        if not same:
            differences[key] = {"psutil": left, "procfs": right}

    return ObserverComparison(
        pid=int(pid),
        comparable=True,
        matches=matches,
        differences=differences,
    )
