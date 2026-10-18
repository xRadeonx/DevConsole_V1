"""Read-only process inspection backed by ``/proc`` (roadmap phase 0B.3/0B.4).

Everything here is observational.  No method in this module terminates,
signals or reconfigures a process.

Two design points worth calling out:

1. **``port → pid`` uses ``/proc`` only.**  The kernel exposes listening
   sockets through ``/proc/net/tcp`` (and ``tcp6``) carrying a socket *inode*;
   the owning PID is found by matching that inode against the
   ``socket:[inode]`` symlinks in ``/proc/<pid>/fd``.  This avoids spawning a
   process entirely and is trivially testable against a fixture tree.
   ``fuser <port>/tcp`` remains available as an explicit *fallback*, strictly
   in query mode.
2. **``proc_root`` is injectable.**  Tests build a synthetic ``/proc`` tree, so
   no test ever depends on (or perturbs) the real system.
"""

from __future__ import annotations

import errno
import os
import subprocess
from pathlib import Path
from typing import Iterable

from devconsole.services.runtime.process_identity import ProcessFacts

#: Listening state in /proc/net/tcp.
_TCP_LISTEN = "0A"


class PermissionDeniedError(PermissionError):
    """Raised when ``/proc`` data cannot be read due to permissions.

    Callers must treat this as *fail closed*: unknown ownership is never
    ownership.
    """


class ProcessInspector:
    """Read-only accessor for process facts.

    Parameters
    ----------
    proc_root:
        Root of the procfs to read.  Defaults to ``/proc``; tests pass a
        fixture directory.
    allow_fuser_fallback:
        When ``True``, :meth:`port_to_pids` may fall back to a **query-only**
        ``fuser`` invocation if the procfs scan finds nothing.  Disabled by
        default so tests never spawn anything.
    """

    def __init__(self, proc_root: Path | str = "/proc",
                 allow_fuser_fallback: bool = False,
                 subprocess_timeout: float = 3.0) -> None:
        self.proc_root = Path(proc_root)
        self.allow_fuser_fallback = allow_fuser_fallback
        self.subprocess_timeout = subprocess_timeout

    # ------------------------------------------------------------------ #
    # process enumeration
    # ------------------------------------------------------------------ #

    def list_pids(self) -> list[int]:
        """Return every numeric PID directory present in ``proc_root``."""
        pids: list[int] = []
        try:
            entries = list(self.proc_root.iterdir())
        except (OSError, PermissionError):
            return []
        for entry in entries:
            if entry.name.isdigit():
                pids.append(int(entry.name))
        return sorted(pids)

    def is_alive(self, pid: int) -> bool:
        """Return ``True`` if ``pid`` still has a ``/proc`` entry."""
        return (self.proc_root / str(pid)).exists()

    def boot_id(self) -> str | None:
        """Return the kernel boot id, used to detect PID reuse across boots."""
        try:
            return (self.proc_root / "sys" / "kernel" / "random" / "boot_id") \
                .read_text(encoding="utf-8").strip()
        except (OSError, PermissionError):
            return None

    @staticmethod
    def clock_ticks() -> int:
        try:
            return int(os.sysconf("SC_CLK_TCK"))
        except (ValueError, OSError, AttributeError):
            return 100

    # ------------------------------------------------------------------ #
    # single process
    # ------------------------------------------------------------------ #

    def read_cmdline(self, pid: int) -> tuple[tuple[str, ...], str | None]:
        """Read ``/proc/<pid>/cmdline``.

        Returns ``(argv, error)``.  Kernel threads have an empty cmdline, which
        is reported as an empty tuple rather than an error.
        """
        path = self.proc_root / str(pid) / "cmdline"
        try:
            raw = path.read_bytes()
        except PermissionError:
            return (), "permission denied reading cmdline"
        except FileNotFoundError:
            return (), "process disappeared while reading cmdline"
        except OSError as exc:
            return (), f"cmdline unreadable: {exc.strerror or exc}"
        if not raw:
            return (), None
        parts = raw.split(b"\0")
        argv = tuple(p.decode("utf-8", errors="replace") for p in parts if p)
        return argv, None

    def read_cwd(self, pid: int) -> tuple[str | None, str | None]:
        """Read ``/proc/<pid>/cwd`` resolving symlinks (realpath).

        Resolving the symlink is what makes the ``cwd`` comparison meaningful
        when the workspace is reached through a symlink.
        """
        path = self.proc_root / str(pid) / "cwd"
        try:
            target = os.readlink(path)
        except PermissionError:
            return None, "permission denied reading cwd"
        except FileNotFoundError:
            return None, "process disappeared while reading cwd"
        except OSError as exc:
            return None, f"cwd unreadable: {exc.strerror or exc}"
        # The link target may itself contain symlinks; normalise it.
        try:
            resolved = os.path.realpath(target)
        except OSError:
            resolved = target
        return resolved, None

    def read_executable(self, pid: int) -> tuple[str | None, str | None]:
        """Read ``/proc/<pid>/exe`` (symlink target)."""
        path = self.proc_root / str(pid) / "exe"
        try:
            return os.readlink(path), None
        except PermissionError:
            return None, "permission denied reading exe"
        except FileNotFoundError:
            return None, "process disappeared while reading exe"
        except OSError as exc:
            return None, f"exe unreadable: {exc.strerror or exc}"

    def read_stat(self, pid: int) -> tuple[dict[str, int] | None, str | None]:
        """Parse the numeric fields of ``/proc/<pid>/stat``.

        The ``comm`` field is wrapped in parentheses and may itself contain
        spaces and parentheses, so the remainder is split starting from the
        *last* ``)`` — the standard robust approach.
        """
        path = self.proc_root / str(pid) / "stat"
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except PermissionError:
            return None, "permission denied reading stat"
        except FileNotFoundError:
            return None, "process disappeared while reading stat"
        except OSError as exc:
            return None, f"stat unreadable: {exc.strerror or exc}"

        close = text.rfind(")")
        if close == -1:
            return None, "malformed stat (no closing parenthesis)"
        rest = text[close + 1:].split()
        # rest[0] is `state` (field 3); numeric fields start at field 4 (ppid).
        if len(rest) < 20:
            return None, "malformed stat (too few fields)"
        try:
            return {
                "state": rest[0],
                "ppid": int(rest[1]),
                "pgid": int(rest[2]),
                "sid": int(rest[3]),
                "start_time_ticks": int(rest[19]),
            }, None
        except (ValueError, IndexError) as exc:
            return None, f"malformed stat numbers: {exc}"

    def read_uid(self, pid: int) -> tuple[int | None, str | None]:
        """Read the real UID from ``/proc/<pid>/status``."""
        path = self.proc_root / str(pid) / "status"
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("Uid:"):
                    return int(line.split()[1]), None
        except PermissionError:
            return None, "permission denied reading status"
        except FileNotFoundError:
            return None, "process disappeared while reading status"
        except OSError as exc:
            return None, f"status unreadable: {exc.strerror or exc}"
        return None, "no Uid line in status"

    # ------------------------------------------------------------------ #
    # listening sockets
    # ------------------------------------------------------------------ #

    def _parse_net_tcp(self, filename: str) -> dict[int, int]:
        """Map ``{inode: local_port}`` for LISTEN sockets in a ``net/tcp*`` file."""
        found: dict[int, int] = {}
        path = self.proc_root / "net" / filename
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except (OSError, PermissionError):
            return found
        if not lines:
            return found

        # Column indices in *data* rows of /proc/net/tcp{,6}:
        #   [0]=sl [1]=local_address [2]=rem_address [3]=st [4]=tx:rx
        #   [5]=tr:tm [6]=retrnsmt [7]=uid [8]=timeout [9]=inode ...
        # The header line cannot be used for lookup: it lists "tx_queue" and
        # "rx_queue" as two columns while every data row packs them as a single
        # "tx:rx" field, so header indices past column 3 are shifted by one.
        # These fixed indices are stable across kernels; the header is only
        # consulted to confirm we are looking at a TCP table.
        IDX_LOCAL, IDX_STATE, IDX_INODE = 1, 3, 9

        for line in lines[1:]:
            parts = line.split()
            if len(parts) <= IDX_INODE:
                continue
            if parts[IDX_STATE] != _TCP_LISTEN:
                continue
            local = parts[IDX_LOCAL]
            if ":" not in local:
                continue
            hex_port = local.rsplit(":", 1)[1]
            try:
                port = int(hex_port, 16)
                inode = int(parts[IDX_INODE])
            except ValueError:
                continue
            if inode:
                found[inode] = port
        return found

    def listening_inodes(self, port: int) -> set[int]:
        """Return the socket inodes listening on ``port`` (TCP4 + TCP6)."""
        inodes: set[int] = set()
        for filename in ("tcp", "tcp6"):
            for inode, inode_port in self._parse_net_tcp(filename).items():
                if inode_port == port:
                    inodes.add(inode)
        return inodes

    def list_listening_ports(self) -> dict[int, set[int]]:
        """Return ``{port: {inode, ...}}`` for every listening TCP port."""
        ports: dict[int, set[int]] = {}
        for filename in ("tcp", "tcp6"):
            for inode, inode_port in self._parse_net_tcp(filename).items():
                ports.setdefault(inode_port, set()).add(inode)
        return ports

    def pids_owning_inodes(self, inodes: Iterable[int]) -> dict[int, list[int]]:
        """Map socket inode → PIDs holding an fd on it.

        Unreadable ``fd`` directories (other users' processes) are skipped:
        failing to prove ownership must never be mistaken for ownership.
        """
        wanted = set(inodes)
        if not wanted:
            return {}
        result: dict[int, list[int]] = {}
        for pid in self.list_pids():
            fd_dir = self.proc_root / str(pid) / "fd"
            try:
                fd_entries = list(fd_dir.iterdir())
            except (PermissionError, FileNotFoundError, OSError):
                # Permission denied or process gone: skip, do not guess.
                continue
            for fd in fd_entries:
                try:
                    target = os.readlink(fd)
                except (PermissionError, FileNotFoundError, OSError):
                    continue
                if not target.startswith("socket:["):
                    continue
                try:
                    inode = int(target[len("socket:["):-1])
                except ValueError:
                    continue
                if inode in wanted:
                    result.setdefault(inode, []).append(pid)
        return result

    def port_to_pids(self, port: int) -> list[int]:
        """Resolve the PIDs listening on ``port``.

        Primary path is pure procfs.  The optional ``fuser`` fallback runs
        **query mode only**; ``-k`` is never used and is asserted against.
        """
        inodes = self.listening_inodes(port)
        by_inode = self.pids_owning_inodes(inodes)
        pids: list[int] = []
        for pid_list in by_inode.values():
            pids.extend(pid_list)
        pids = sorted(set(pids))
        if pids:
            return pids
        if self.allow_fuser_fallback:
            return sorted(set(self._fuser_query(port)))
        return []

    def _fuser_query(self, port: int) -> list[int]:
        """Query-only ``fuser`` fallback.  Never passes ``-k``."""
        cmd = ["fuser", f"{int(port)}/tcp"]
        if "-k" in cmd:  # pragma: no cover - defensive, cannot happen
            raise AssertionError("fuser must never be invoked with -k")
        try:
            res = subprocess.run(cmd, capture_output=True, text=True,
                                 timeout=self.subprocess_timeout)
        except (OSError, subprocess.SubprocessError):
            return []
        pids: list[int] = []
        for token in f"{res.stdout} {res.stderr}".split():
            token = token.strip()
            if token.isdigit():
                pids.append(int(token))
        return pids

    # ------------------------------------------------------------------ #
    # aggregate
    # ------------------------------------------------------------------ #

    def socket_inodes_of(self, pid: int) -> set[int]:
        """Return the socket inodes this PID holds an fd on."""
        inodes: set[int] = set()
        fd_dir = self.proc_root / str(pid) / "fd"
        try:
            fd_entries = list(fd_dir.iterdir())
        except (PermissionError, FileNotFoundError, OSError):
            return inodes
        for fd in fd_entries:
            try:
                target = os.readlink(fd)
            except (PermissionError, FileNotFoundError, OSError):
                continue
            if target.startswith("socket:["):
                try:
                    inodes.add(int(target[len("socket:["):-1]))
                except ValueError:
                    continue
        return inodes

    def listening_ports_for_pid(self, pid: int) -> list[int]:
        """Ports ``pid`` is listening on, computed in a single pass.

        Implemented as *my socket inodes* ∩ *listening inodes → port*, which is
        O(processes + fds-of-this-pid) rather than the O(ports × processes × fds)
        a naive per-port scan would cost.
        """
        my_inodes = self.socket_inodes_of(pid)
        if not my_inodes:
            return []
        inode_to_port: dict[int, int] = {}
        for port, inodes in self.list_listening_ports().items():
            for inode in inodes:
                inode_to_port[inode] = port
        return sorted({inode_to_port[i] for i in my_inodes if i in inode_to_port})

    def read_facts(self, pid: int) -> ProcessFacts:
        """Collect every fact available for ``pid``.

        Missing or unreadable files are recorded in ``read_errors`` instead of
        raising, so the ownership verifier can reason about *partial* evidence
        and fail closed.
        """
        errors: list[str] = []

        argv, err = self.read_cmdline(pid)
        if err:
            errors.append(err)
        cwd, err = self.read_cwd(pid)
        if err:
            errors.append(err)
        exe, err = self.read_executable(pid)
        if err:
            errors.append(err)
        stat, err = self.read_stat(pid)
        if err:
            errors.append(err)

        ppid = pgid = sid = start_ticks = None
        if stat:
            ppid = stat.get("ppid")
            pgid = stat.get("pgid")
            sid = stat.get("sid")
            start_ticks = stat.get("start_time_ticks")

        listening: list[int] = []
        try:
            listening = self.listening_ports_for_pid(pid)
        except (OSError, PermissionError):
            errors.append("listening port scan failed")

        return ProcessFacts(
            pid=pid,
            ppid=ppid,
            pgid=pgid,
            sid=sid,
            start_time_ticks=start_ticks,
            executable=exe,
            command_line=argv,
            cwd=cwd,
            listening_ports=tuple(listening),
            read_errors=tuple(errors),
        )

    def read_ancestry(self, pid: int, *, max_depth: int = 16) -> list[int]:
        """Return the ancestor chain ``[pid, ppid, ..., 1]``.

        Stops early on a missing/unreadable stat or on a cycle, so a corrupt
        procfs cannot cause an infinite loop.
        """
        chain: list[int] = []
        seen: set[int] = set()
        current = pid
        for _ in range(max_depth):
            if current in seen or current <= 0:
                break
            seen.add(current)
            chain.append(current)
            stat, err = self.read_stat(current)
            if err or not stat:
                break
            parent = stat.get("ppid")
            if not parent or parent == current:
                break
            current = parent
        return chain
