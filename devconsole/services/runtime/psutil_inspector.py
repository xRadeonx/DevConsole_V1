"""Optional psutil-backed process inspector for DevConsole V1.1.

The legacy :class:`ProcessInspector` remains the deterministic fallback and the
implementation used by synthetic /proc fixtures.  This adapter is selected only
for the real host when psutil is installed, so introducing the dependency never
removes the existing procfs path.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from devconsole.services.runtime.process_inspector import ProcessInspector

try:  # optional at runtime; installer/preflight can enable it explicitly
    import psutil  # type: ignore
except ImportError:  # pragma: no cover - exercised on minimal installations
    psutil = None  # type: ignore[assignment]


def psutil_available() -> bool:
    return psutil is not None


class PsutilProcessInspector(ProcessInspector):
    """Read-only inspector using psutil where it is stronger than proc parsing.

    A non-standard ``proc_root`` always delegates to the parent implementation;
    this is essential for the existing hermetic process-identity test fixtures.
    """

    def __init__(self, proc_root: Path | str = "/proc", **kwargs: Any) -> None:
        super().__init__(proc_root=proc_root, **kwargs)
        self._native = psutil is not None and Path(proc_root) == Path("/proc")

    def list_pids(self) -> list[int]:
        if not self._native:
            return super().list_pids()
        try:
            return sorted(int(pid) for pid in psutil.pids())
        except Exception:
            return super().list_pids()

    def is_alive(self, pid: int) -> bool:
        if not self._native:
            return super().is_alive(pid)
        try:
            return bool(psutil.pid_exists(int(pid)))
        except Exception:
            return super().is_alive(pid)

    def read_cmdline(self, pid: int) -> tuple[tuple[str, ...], str | None]:
        if not self._native:
            return super().read_cmdline(pid)
        try:
            return tuple(psutil.Process(pid).cmdline()), None
        except psutil.AccessDenied:
            return (), "permission denied reading cmdline"
        except psutil.NoSuchProcess:
            return (), "process disappeared while reading cmdline"
        except Exception as exc:
            return super().read_cmdline(pid) if Path("/proc").exists() else ((), str(exc))

    def read_cwd(self, pid: int) -> tuple[str | None, str | None]:
        if not self._native:
            return super().read_cwd(pid)
        try:
            return os.path.realpath(psutil.Process(pid).cwd()), None
        except psutil.AccessDenied:
            return None, "permission denied reading cwd"
        except psutil.NoSuchProcess:
            return None, "process disappeared while reading cwd"
        except Exception:
            return super().read_cwd(pid)

    def read_executable(self, pid: int) -> tuple[str | None, str | None]:
        if not self._native:
            return super().read_executable(pid)
        try:
            return psutil.Process(pid).exe(), None
        except psutil.AccessDenied:
            return None, "permission denied reading exe"
        except psutil.NoSuchProcess:
            return None, "process disappeared while reading exe"
        except Exception:
            return super().read_executable(pid)

    def read_uid(self, pid: int) -> tuple[int | None, str | None]:
        if not self._native:
            return super().read_uid(pid)
        try:
            return int(psutil.Process(pid).uids().real), None
        except psutil.AccessDenied:
            return None, "permission denied reading status"
        except psutil.NoSuchProcess:
            return None, "process disappeared while reading status"
        except Exception:
            return super().read_uid(pid)

    def read_stat(self, pid: int) -> tuple[dict[str, int] | None, str | None]:
        if not self._native:
            return super().read_stat(pid)
        try:
            proc = psutil.Process(pid)
            ticks = self.clock_ticks()
            start_ticks = max(0, int((proc.create_time() - psutil.boot_time()) * ticks))
            return {
                "state": 0,
                "ppid": int(proc.ppid()),
                "pgid": int(os.getpgid(pid)),
                "sid": int(os.getsid(pid)),
                "start_time_ticks": start_ticks,
            }, None
        except psutil.AccessDenied:
            return None, "permission denied reading stat"
        except psutil.NoSuchProcess:
            return None, "process disappeared while reading stat"
        except Exception:
            return super().read_stat(pid)

    def port_to_pids(self, port: int) -> list[int]:
        if not self._native:
            return super().port_to_pids(port)
        found: set[int] = set()
        try:
            for conn in psutil.net_connections(kind="tcp"):
                if not conn.laddr or conn.status != psutil.CONN_LISTEN:
                    continue
                if int(conn.laddr.port) == int(port) and conn.pid is not None:
                    found.add(int(conn.pid))
        except (psutil.AccessDenied, OSError):
            return super().port_to_pids(port)
        except Exception:
            return super().port_to_pids(port)
        return sorted(found) if found else super().port_to_pids(port)

    def listening_ports_for_pid(self, pid: int) -> list[int]:
        if not self._native:
            return super().listening_ports_for_pid(pid)
        try:
            ports = {
                int(conn.laddr.port)
                for conn in psutil.Process(pid).net_connections(kind="tcp")
                if conn.laddr and conn.status == psutil.CONN_LISTEN
            }
            return sorted(ports)
        except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
            return super().listening_ports_for_pid(pid)
        except Exception:
            return super().listening_ports_for_pid(pid)


def create_process_inspector(
    proc_root: Path | str = "/proc",
    *,
    allow_fuser_fallback: bool = False,
    subprocess_timeout: float = 3.0,
) -> ProcessInspector:
    """Create the configured inspector without making psutil mandatory.

    ``SISPER_PROCESS_INSPECTOR`` accepts ``auto`` (default), ``psutil`` or
    ``procfs``.  A requested-but-unavailable psutil backend fails safely to the
    legacy inspector instead of preventing DevConsole from starting.
    """
    mode = os.environ.get("SISPER_PROCESS_INSPECTOR", "auto").strip().lower()
    kwargs = {
        "proc_root": proc_root,
        "allow_fuser_fallback": allow_fuser_fallback,
        "subprocess_timeout": subprocess_timeout,
    }
    if mode == "procfs" or Path(proc_root) != Path("/proc"):
        return ProcessInspector(**kwargs)
    if mode in {"auto", "psutil"} and psutil_available():
        return PsutilProcessInspector(**kwargs)
    return ProcessInspector(**kwargs)
