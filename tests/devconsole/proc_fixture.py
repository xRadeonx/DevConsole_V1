"""Synthetic ``/proc`` fixture builder for the runtime tests (roadmap 0B.8).

The runtime layer reads procfs through the injectable ``proc_root`` parameter of
:class:`~devconsole.services.runtime.process_inspector.ProcessInspector`, so the
tests build a small fake procfs instead of mocking individual reads.  This keeps
every test hermetic — no real process is ever inspected, signalled or killed.

Layout produced::

    <root>/
      net/tcp, net/tcp6
      sys/kernel/random/boot_id
      <pid>/cmdline            NUL-separated argv
      <pid>/cwd                symlink → real directory
      <pid>/exe                symlink → fake binary
      <pid>/stat               pid (comm) state ppid pgrp session ... starttime
      <pid>/status             Uid: line
      <pid>/fd/<n>             symlink → socket:[inode]
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

LISTEN_STATE = "0A"

_NET_HEADER = (
    "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when "
    "retrnsmt   uid  timeout inode\n"
)


def _hex_port(port: int) -> str:
    return f"{port:04X}"


def _hex_ip_v4(ip: str = "0.0.0.0") -> str:
    return "".join(f"{int(o):02X}" for o in ip.split("."))


@dataclass
class FakeProcess:
    """One synthetic process in the fixture procfs."""

    pid: int
    comm: str = "synthetic"
    argv: tuple[str, ...] = ()
    cwd: str | None = None
    exe: str | None = None
    ppid: int = 1
    pgid: int | None = None
    sid: int | None = None
    start_time_ticks: int = 1000
    uid: int = 1000
    listening: tuple[int, ...] = ()
    inodes: tuple[int, ...] = ()
    #: When set, no ``cmdline`` file is written at all (simulates a process
    #: that vanished between the directory listing and the read).
    omit_cmdline: bool = False
    omit_stat: bool = False
    omit_cwd: bool = False
    #: chmod 000 on the pid directory → readlink raises PermissionError.
    deny_permissions: bool = False
    #: Make ``fd`` unreadable so inode→pid mapping cannot be proven.
    deny_fd: bool = False
    #: Extra raw stat fields appended verbatim (for malformed-stat tests).
    stat_override: str | None = None


@dataclass
class FakeProcTree:
    """Builder/owner of a synthetic procfs rooted at :attr:`root`."""

    root: Path
    processes: dict[int, FakeProcess] = field(default_factory=dict)

    # ------------------------------------------------------------------ #

    @classmethod
    def create(cls, root: Path) -> "FakeProcTree":
        tree = cls(root=root)
        (root / "net").mkdir(parents=True, exist_ok=True)
        (root / "sys" / "kernel" / "random").mkdir(parents=True, exist_ok=True)
        (root / "sys" / "kernel" / "random" / "boot_id").write_text(
            "11111111-2222-3333-4444-555555555555\n", encoding="utf-8")
        return tree

    # ------------------------------------------------------------------ #

    def add(self, proc: FakeProcess) -> FakeProcess:
        self.processes[proc.pid] = proc
        return proc

    def build(self) -> "FakeProcTree":
        """Materialise every process plus ``/proc/net/tcp``."""
        for proc in self.processes.values():
            self._write_process(proc)
        self._write_net()
        return self

    # ------------------------------------------------------------------ #

    def _write_process(self, proc: FakeProcess) -> None:
        pdir = self.root / str(proc.pid)
        pdir.mkdir(parents=True, exist_ok=True)

        if not proc.omit_cmdline:
            raw = b"".join(a.encode() + b"\0" for a in proc.argv)
            (pdir / "cmdline").write_bytes(raw)

        if not proc.omit_stat:
            (pdir / "stat").write_text(self._stat_line(proc), encoding="utf-8")

        (pdir / "status").write_text(
            f"Name:\t{proc.comm}\nState:\tS (sleeping)\nUid:\t{proc.uid}\t{proc.uid}\t{proc.uid}\t{proc.uid}\n",
            encoding="utf-8")

        if not proc.omit_cwd and proc.cwd:
            target = Path(proc.cwd)
            target.mkdir(parents=True, exist_ok=True)
            link = pdir / "cwd"
            if link.is_symlink() or link.exists():
                link.unlink()
            os.symlink(str(target), link)

        if proc.exe:
            exe_target = Path(proc.exe)
            exe_target.parent.mkdir(parents=True, exist_ok=True)
            if not exe_target.exists():
                exe_target.write_text("#!/bin/sh\n", encoding="utf-8")
            link = pdir / "exe"
            if link.is_symlink() or link.exists():
                link.unlink()
            os.symlink(str(exe_target), link)

        fd_dir = pdir / "fd"
        fd_dir.mkdir(exist_ok=True)
        for index, inode in enumerate(proc.inodes):
            f = fd_dir / str(index + 3)
            if f.is_symlink() or f.exists():
                f.unlink()
            os.symlink(f"socket:[{inode}]", f)

        if proc.deny_fd:
            os.chmod(fd_dir, 0o000)
        if proc.deny_permissions:
            os.chmod(pdir, 0o000)

    @staticmethod
    def _stat_line(proc: FakeProcess) -> str:
        if proc.stat_override is not None:
            return proc.stat_override
        pgid = proc.pgid if proc.pgid is not None else proc.pid
        sid = proc.sid if proc.sid is not None else proc.pid
        # fields: state ppid pgrp session tty tpgid flags minflt cminflt
        #         majflt cmajflt utime stime cutime cstime priority nice
        #         num_threads itrealvalue starttime
        tail = [
            "S", str(proc.ppid), str(pgid), str(sid), "0", "0", "0",
            "0", "0", "0", "0", "0", "0", "0", "0", "20", "0", "1", "0",
            str(proc.start_time_ticks),
        ]
        return f"{proc.pid} ({proc.comm}) " + " ".join(tail) + "\n"

    def _write_net(self) -> None:
        rows4: list[str] = []
        rows6: list[str] = []
        sl = 0
        for proc in self.processes.values():
            for port, inode in zip(proc.listening, proc.inodes):
                sl += 1
                row = (
                    f"{sl:4d}: {_hex_ip_v4()}:{_hex_port(port)} 00000000:0000 "
                    f"{LISTEN_STATE} 00000000:00000000 00:00000000 00000000  "
                    f"{proc.uid:5d}        0 {inode} 1 0000000000000000 100 0 0 10 0\n"
                )
                rows4.append(row)
        (self.root / "net" / "tcp").write_text(_NET_HEADER + "".join(rows4), encoding="utf-8")
        (self.root / "net" / "tcp6").write_text(_NET_HEADER + "".join(rows6), encoding="utf-8")

    # ------------------------------------------------------------------ #

    def cleanup(self) -> None:
        """Undo restrictive modes so the temporary directory can be removed."""
        for proc in self.processes.values():
            pdir = self.root / str(proc.pid)
            if pdir.exists():
                try:
                    os.chmod(pdir, 0o755)
                except OSError:
                    pass
            fd_dir = pdir / "fd"
            if fd_dir.exists():
                try:
                    os.chmod(fd_dir, 0o755)
                except OSError:
                    pass
        shutil.rmtree(self.root, ignore_errors=True)
