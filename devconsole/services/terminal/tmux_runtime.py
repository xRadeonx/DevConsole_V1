# devconsole/services/terminal/tmux_runtime.py
"""Thin, policy-free wrapper around the ``tmux`` CLI.

Responsibilities are deliberately narrow: run ``tmux`` correctly and safely, and
parse what it prints.  **No decisions** about ownership, states or service
selection live here — those belong to
:mod:`devconsole.services.terminal.tmux_backend`.

Subprocess safety
-----------------
Every invocation is ``subprocess.run(["tmux", ...])`` with an argument vector.
``shell=True`` is never used, and ``shlex`` is never needed, because tmux accepts
the pane command as **separate argv elements** — when more than one element is
given tmux execs them directly instead of handing a string to a shell.  That is
the mechanism that keeps untrusted-ish values (service names, directories) out of
a shell parser entirely; see :meth:`TmuxRuntime.new_session`.

The single place a string could still reach a shell is ``respawn-pane`` on a
session created by something else, so :meth:`TmuxRuntime.respawn_pane` accepts
only an argv tuple and asserts the same multi-element property.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

#: Field wrapper used for one tmux call.  Kept small: a hung tmux must not hang
#: DevConsole's request thread.
DEFAULT_TIMEOUT = 10.0

#: Separator for ``-F`` formats.  ASCII unit separator: it cannot appear in a
#: session name, a path or a user-option value that DevConsole writes.
SEP = "\x1f"


class TmuxError(RuntimeError):
    """A tmux command failed."""


class TmuxUnavailable(TmuxError):
    """The tmux binary is missing or unusable."""


@dataclass(frozen=True)
class TmuxSession:
    """One tmux session as observed from the outside."""

    name: str
    windows: int
    attached: int
    pane_pid: int | None
    pane_dead: bool
    pane_cwd: str | None
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def has_live_pane(self) -> bool:
        """True when the pane's process is still alive."""
        return self.pane_pid is not None and not self.pane_dead


class TmuxRuntime:
    """Safe access to a tmux server (default socket unless told otherwise)."""

    def __init__(self, *, binary: str = "tmux", socket_name: str | None = None,
                 timeout: float = DEFAULT_TIMEOUT) -> None:
        self.binary = binary
        self.socket_name = socket_name
        self.timeout = timeout

    # ------------------------------------------------------------------ #
    # plumbing
    # ------------------------------------------------------------------ #

    def _argv(self, args: Sequence[str]) -> list[str]:
        base = [self.binary]
        if self.socket_name:
            base += ["-L", self.socket_name]
        return base + list(args)

    def _run(self, args: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess:
        """Run one tmux command. Never uses a shell; never interpolates input."""
        try:
            proc = subprocess.run(self._argv(args), capture_output=True,
                                  text=True, timeout=self.timeout)
        except FileNotFoundError as exc:
            raise TmuxUnavailable(f"tmux binary not found: {self.binary}") from exc
        except subprocess.TimeoutExpired as exc:
            raise TmuxError(f"tmux timed out after {self.timeout}s: {args[0]}") from exc

        if check and proc.returncode != 0:
            raise TmuxError(
                f"tmux {args[0]} failed ({proc.returncode}): {proc.stderr.strip()}")
        return proc

    @staticmethod
    def _no_server(stderr: str) -> bool:
        """Does this stderr mean 'there is simply no tmux server'?"""
        text = (stderr or "").lower()
        return ("no server running" in text
                or "error connecting to" in text
                or "no such file or directory" in text
                or "connection refused" in text)

    # ------------------------------------------------------------------ #
    # availability
    # ------------------------------------------------------------------ #

    def version(self) -> str | None:
        """Return the tmux version string, or ``None`` if tmux is unusable."""
        try:
            proc = self._run(["-V"], check=False)
        except TmuxUnavailable:
            return None
        if proc.returncode != 0:
            return None
        return proc.stdout.strip() or None

    def available(self) -> bool:
        return self.version() is not None

    def server_running(self) -> bool:
        """True when a tmux server is reachable.  Read-only."""
        proc = self._run(["list-sessions"], check=False)
        if proc.returncode == 0:
            return True
        return not self._no_server(proc.stderr)

    # ------------------------------------------------------------------ #
    # reading
    # ------------------------------------------------------------------ #

    #: ``-F`` format for :meth:`list_sessions`.  Session- and pane-scoped fields
    #: together, so one call inventories everything classification needs.
    #:
    #: ``#{pane_pid}`` here was measured against ``list-panes`` before being
    #: trusted: 10/10 identical values across sessions, and still identical with
    #: two clients attached to different sessions.  It is stable because tmux
    #: evaluates the format per session against that session's active pane.
    #:
    #: Note for whoever debugs this next: the pane process is a **fork of the
    #: tmux server**, so for the instant before it ``exec``s, ``/proc/<pane_pid>``
    #: shows the server's ``exe`` and ``cmdline``.  That looks exactly like a
    #: wrong PID and is not one — wait for the exec instead.  Phase 3 lost time
    #: to precisely that misreading.
    _FORMAT = SEP.join((
        "#{session_name}",
        "#{session_windows}",
        "#{session_attached}",
        "#{pane_pid}",
        "#{pane_dead}",
        "#{pane_current_path}",
        "#{@sisper_managed}",
        "#{@sisper_service}",
        "#{@sisper_service_type}",
        "#{@sisper_port}",
        "#{@sisper_environment}",
        "#{@sisper_cwd}",
        "#{@sisper_schema_version}",
        "#{@sisper_aux_type}",
    ))

    _METADATA_KEYS = (
        "@sisper_managed", "@sisper_service", "@sisper_service_type",
        "@sisper_port", "@sisper_environment", "@sisper_cwd",
        "@sisper_schema_version", "@sisper_aux_type",
    )

    def list_sessions(self) -> list[TmuxSession]:
        """Return every session on the server.  Read-only; empty when none."""
        proc = self._run(["list-sessions", "-F", self._FORMAT], check=False)
        if proc.returncode != 0:
            if self._no_server(proc.stderr):
                return []
            raise TmuxError(f"tmux list-sessions failed: {proc.stderr.strip()}")

        sessions: list[TmuxSession] = []
        for line in proc.stdout.splitlines():
            session = self._parse_line(line)
            if session is not None:
                sessions.append(session)
        return sessions

    def _parse_line(self, line: str) -> TmuxSession | None:
        if not line.strip():
            return None
        parts = line.split(SEP)
        if len(parts) < 6:
            return None

        def _int(value: str) -> int | None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        pid = _int(parts[3])
        metadata = {
            key: value for key, value in zip(self._METADATA_KEYS, parts[6:])
            if value != ""
        }
        return TmuxSession(
            name=parts[0],
            windows=_int(parts[1]) or 0,
            attached=_int(parts[2]) or 0,
            pane_pid=pid if pid else None,
            pane_dead=parts[4] == "1",
            pane_cwd=parts[5] or None,
            metadata=metadata,
        )

    def find_session(self, name: str) -> TmuxSession | None:
        """Return the named session, or ``None`` (including when tmux is down)."""
        for session in self.list_sessions():
            if session.name == name:
                return session
        return None

    def session_names(self) -> list[str]:
        return [s.name for s in self.list_sessions()]

    # ------------------------------------------------------------------ #
    # writing
    # ------------------------------------------------------------------ #

    def new_session(
        self,
        *,
        name: str,
        cwd: str | Path,
        command: Sequence[str],
        environment: Mapping[str, str] | None = None,
        width: int = 200,
        height: int = 50,
        window_name: str | None = None,
    ) -> TmuxSession:
        """Create a **detached** session running ``command`` with ``cwd``.

        ``command`` is passed as separate argv elements so tmux ``exec``s it
        without involving a shell.  A single-element command would be handed to
        the shell instead, which is why the runner is launched as
        ``["bash", "<runner>"]`` rather than ``["<runner>"]``.
        """
        if not command:
            raise ValueError("command must not be empty")
        if len(command) == 1:
            raise ValueError(
                "refusing a single-element command: tmux would run it through a "
                "shell. Pass explicit argv, e.g. ['bash', script]."
            )

        cwd_str = str(cwd)
        if not Path(cwd_str).is_dir():
            raise ValueError(f"cwd is not a directory: {cwd_str}")

        args = ["new-session", "-d", "-s", name, "-c", cwd_str,
                "-x", str(int(width)), "-y", str(int(height))]
        if window_name:
            # Nombre de la ventana: es lo que se lee en la barra de tmux
            # ("[sesion:bash*]" por defecto, poco informativo).
            args += ["-n", window_name]
        for key, value in (environment or {}).items():
            if key and value is not None:
                args += ["-e", f"{key}={value}"]
        # `--` guarantees a command element starting with '-' is not read as an
        # option; everything after it is the command and its arguments.
        args += ["--", *command]

        self._run(args)
        session = self.find_session(name)
        if session is None:  # pragma: no cover - tmux raced us
            raise TmuxError(f"session {name!r} vanished right after creation")
        return session

    def set_options(self, name: str, options: Mapping[str, str]) -> None:
        """Set user options on a session in a **single** tmux invocation.

        Chaining with ``;`` keeps the window during which a session exists
        without its ownership metadata as short as one command.
        """
        if not options:
            return
        args: list[str] = []
        for key, value in options.items():
            if args:
                args.append(";")
            args += ["set-option", "-t", name, key, str(value)]
        self._run(args)

    def respawn_pane(self, name: str, *, cwd: str | Path, command: Sequence[str],
                     environment: Mapping[str, str] | None = None,
                     kill: bool = True) -> None:
        """Restart the pane's process in place, optionally killing it first.

        ``-k`` makes tmux kill the existing process before starting the new one,
        which is what preserves the session (and therefore any attached
        viewers) across a restart.
        """
        if len(command) < 2:
            raise ValueError("respawn-pane requires an explicit multi-element argv")

        args = ["respawn-pane", "-t", name]
        if kill:
            args.append("-k")
        args += ["-c", str(cwd)]
        for key, value in (environment or {}).items():
            if key and value is not None:
                args += ["-e", f"{key}={value}"]
        args += ["--", *command]
        self._run(args)

    def kill_session(self, name: str) -> bool:
        """Terminate one session.  Returns False when it was already gone.

        Only the named session is touched.  There is deliberately no
        ``kill-server`` and no pattern-based kill anywhere in this class: the
        tmux backend must never be able to take out sessions it does not own.
        """
        proc = self._run(["kill-session", "-t", name], check=False)
        if proc.returncode == 0:
            return True
        stderr = (proc.stderr or "").lower()
        if "can't find session" in stderr or "session not found" in stderr:
            return False
        if self._no_server(proc.stderr):
            return False
        raise TmuxError(f"tmux kill-session failed: {proc.stderr.strip()}")

    # ------------------------------------------------------------------ #
    # helpers used by tests and the fixture harness
    # ------------------------------------------------------------------ #

    def pane_command(self, name: str) -> str | None:
        """Return the pane's current command line, for diagnostics."""
        proc = self._run(
            ["list-panes", "-t", name, "-F", "#{pane_pid}#{pane_start_command}"],
            check=False)
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        return proc.stdout.splitlines()[0]

    def environment_of_pane(self, name: str) -> dict[str, str]:
        """Read the pane's environment via ``/proc`` (read-only, no tmux writes).

        Avoids ``show-environment`` because that reports the *server* environment
        rather than what the pane's process actually received.
        """
        session = self.find_session(name)
        if session is None or session.pane_pid is None:
            return {}
        try:
            raw = Path(f"/proc/{session.pane_pid}/environ").read_bytes()
        except OSError:
            return {}
        env: dict[str, str] = {}
        for chunk in raw.split(b"\0"):
            if not chunk or b"=" not in chunk:
                continue
            key, _, value = chunk.decode("utf-8", "replace").partition("=")
            env[key] = value
        return env

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"TmuxRuntime(binary={self.binary!r}, socket={self.socket_name!r})"


def default_runtime() -> TmuxRuntime:
    """Runtime bound to the user's default tmux socket."""
    return TmuxRuntime(socket_name=os.environ.get("SISPER_TMUX_SOCKET") or None)


__all__ = [
    "DEFAULT_TIMEOUT",
    "TmuxError",
    "TmuxRuntime",
    "TmuxSession",
    "TmuxUnavailable",
    "default_runtime",
]
