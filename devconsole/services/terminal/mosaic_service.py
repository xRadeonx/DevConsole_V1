# devconsole/services/terminal/mosaic_service.py
"""Lightweight read-only service mosaic with bounded log previews (Phase 5A).

Delivers Phase 5A: high-efficiency overview of all services without creating
heavy terminal emulators or WebGL instances. Previews are captured via
tmux capture-pane snapshots on demand with strict limits on lines, bytes,
and execution time.
"""

from __future__ import annotations

import os
import re
import socket
import time
from dataclasses import asdict, dataclass
from typing import Any, Sequence

import devconsole.config as dcfg
from devconsole.services.runtime import ProcessIdentityResolver
from devconsole.services.terminal.tmux_backend import TmuxBackend

#: Default maximum lines to return per preview
DEFAULT_MAX_LINES = 6

#: Absolute upper bound for requested max_lines (expanded for live monitor consoles)
HARD_MAX_LINES = 200

#: Maximum characters per preview line (truncate to avoid heavy JSON payloads)
MAX_LINE_CHARS = 500

_STANDBY_PATTERNS = [
    re.compile(r"\[MODO STANDBY\]", re.IGNORECASE),
    re.compile(r"Opción \[r=reintentar", re.IGNORECASE),
    re.compile(r"La consola queda en PAUSA", re.IGNORECASE),
]

_ERROR_PATTERNS = [
    re.compile(r"((?:Error|Exception):? .+)", re.IGNORECASE),
    re.compile(r"(Traceback \(most recent call last\):)", re.IGNORECASE),
    re.compile(r"(ModuleNotFoundError: .+)", re.IGNORECASE),
    re.compile(r"(SyntaxError: .+)", re.IGNORECASE),
    re.compile(r"(Failed to compile\.)", re.IGNORECASE),
    re.compile(r"(ConnectionRefusedError: .+)", re.IGNORECASE),
]



@dataclass(frozen=True)
class MosaicItem:
    name: str
    service_type: str
    port: int
    status: str
    runtime_host: str
    pid: int | None
    uptime_seconds: int | None
    environment: str
    recent_lines: list[str]
    recent_error: str | None
    is_standby: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def is_port_listening(port: int, host: str = "127.0.0.1") -> bool:
    if not port or port <= 0:
        return False
    s = socket.socket()
    s.settimeout(0.1)
    try:
        return s.connect_ex((host, port)) == 0
    except Exception:
        return False
    finally:
        s.close()


def get_process_uptime(pid: int) -> int | None:
    """Compute precise process uptime in seconds from /proc/<pid>/stat."""
    if not pid or pid <= 0:
        return None
    try:
        with open(f"/proc/{pid}/stat", "r") as f:
            fields = f.read().split()
            # field 22 (0-indexed 21) is starttime ticks after system boot
            ticks = int(fields[21])
        with open("/proc/uptime", "r") as uf:
            sys_uptime = float(uf.read().split()[0])
        clk_tck = os.sysconf(os.sysconf_names.get("SC_CLK_TCK", "SC_CLK_TCK")) or 100
        proc_uptime = sys_uptime - (ticks / clk_tck)
        return max(0, int(proc_uptime))
    except Exception:
        return None


class MosaicService:
    def __init__(self, backend: TmuxBackend | None = None, resolver: ProcessIdentityResolver | None = None):
        self.backend = backend or TmuxBackend()
        self.resolver = resolver or ProcessIdentityResolver()

    def get_service_preview(self, service_cfg: dict[str, Any], max_lines: int = DEFAULT_MAX_LINES) -> MosaicItem:
        max_lines = max(1, min(max_lines, HARD_MAX_LINES))
        name = service_cfg["name"]
        port = service_cfg.get("port", 0)
        stype = "backend" if (service_cfg in dcfg.SERVICES_BACKEND or name.startswith("ms_")) else "frontend"
        env_name = getattr(dcfg, "CURRENT_ENV", "develop") or "develop"

        sess_name = self.backend.session_name(name)
        sess = self.backend.runtime.find_session(sess_name)
        runtime_host = "tmux" if sess is not None else "legacy"

        # Resolve live PID
        r = self.resolver.resolve_service(name)
        pid = r.identity.pid if r.identity else None
        port_open = is_port_listening(port) if port else False

        # Read last lines via tmux capture-pane if session exists
        recent_lines: list[str] = []
        is_standby = False
        recent_error: str | None = None

        target_pid = pid or (sess.pane_pid if sess else None)
        uptime = get_process_uptime(target_pid) if target_pid else None


        if sess is not None:
            try:
                proc = self.backend.runtime._run(
                    ["capture-pane", "-p", "-t", sess_name, "-S", "-200"],
                    check=False,
                )


                if proc.returncode == 0:
                    raw_out = proc.stdout
                    filtered = [
                        line[:MAX_LINE_CHARS].rstrip()
                        for line in raw_out.splitlines()
                        if line.strip()
                    ]
                    recent_lines = filtered[-max_lines:]

                    # Detect STANDBY & Errors
                    for line in filtered:
                        if any(pat.search(line) for pat in _STANDBY_PATTERNS):
                            is_standby = True
                        for err_pat in _ERROR_PATTERNS:
                            m = err_pat.search(line)
                            if m:
                                recent_error = m.group(1)[:120]
            except Exception:
                pass

        # Determine consolidated status
        if is_standby:
            status = "STANDBY"
        elif port_open:
            status = "RUNNING"
        elif sess:
            status = "FAILED" if recent_error else "STARTING"
        else:
            status = "STOPPED"

        return MosaicItem(
            name=name,
            service_type=stype,
            port=port,
            status=status,
            runtime_host=runtime_host if port_open or sess else "none",
            pid=pid,
            uptime_seconds=uptime,
            environment=env_name,
            recent_lines=recent_lines,
            recent_error=recent_error,
            is_standby=is_standby,
        )

    def get_service_preview_by_name(self, name: str, max_lines: int = DEFAULT_MAX_LINES) -> MosaicItem | None:
        all_services = list(dcfg.SERVICES_BACKEND) + list(dcfg.SERVICES_FRONTEND)
        for s in all_services:
            if s["name"] == name:
                return self.get_service_preview(s, max_lines=max_lines)
        return None

    def get_services_batch_preview(self, names: Sequence[str], max_lines: int = DEFAULT_MAX_LINES) -> list[dict[str, Any]]:
        name_set = set(names)
        all_services = list(dcfg.SERVICES_BACKEND) + list(dcfg.SERVICES_FRONTEND)
        matched = [s for s in all_services if s["name"] in name_set]
        return [self.get_service_preview(s, max_lines=max_lines).to_dict() for s in matched]

    def get_mosaic_overview(self, max_lines: int = DEFAULT_MAX_LINES) -> list[dict[str, Any]]:
        services = list(dcfg.SERVICES_BACKEND) + list(dcfg.SERVICES_FRONTEND)
        return [self.get_service_preview(s, max_lines=max_lines).to_dict() for s in services]
