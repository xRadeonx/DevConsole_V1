"""Podman/Docker abstraction used by the safe V1.1 build path."""
from __future__ import annotations

import json
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


@dataclass(frozen=True)
class EngineResult:
    returncode: int
    command: tuple[str, ...]
    output: tuple[str, ...] = ()
    cancelled: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.cancelled


class ContainerEngine:
    def __init__(self, binary: str) -> None:
        resolved = shutil.which(binary)
        if not resolved:
            raise FileNotFoundError(f"Container engine no disponible: {binary}")
        self.binary = resolved
        self.name = Path(resolved).name

    @classmethod
    def discover(cls, preferred: str | None = None) -> "ContainerEngine":
        candidates = [preferred] if preferred else []
        candidates.extend(["podman", "docker"])
        seen: set[str] = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            if shutil.which(candidate):
                return cls(candidate)
        raise FileNotFoundError("No se encontró Podman ni Docker en PATH")

    def image_exists(self, image: str) -> bool:
        if self.name == "podman":
            cmd = [self.binary, "image", "exists", image]
        else:
            cmd = [self.binary, "image", "inspect", image]
        try:
            return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10).returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    def inspect(self, image: str) -> dict:
        proc = subprocess.run([self.binary, "image", "inspect", image], capture_output=True, text=True, timeout=15)
        if proc.returncode != 0:
            return {}
        try:
            payload = json.loads(proc.stdout)
            return payload[0] if isinstance(payload, list) and payload else {}
        except json.JSONDecodeError:
            return {}

    def _stream(
        self,
        args: Iterable[str],
        *,
        cwd: Path,
        on_line: Callable[[str], None] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> EngineResult:
        cmd = [self.binary, *list(args)]
        lines: list[str] = []
        proc = subprocess.Popen(cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        cancelled = False
        assert proc.stdout is not None
        while True:
            if cancel_event is not None and cancel_event.is_set() and proc.poll() is None:
                cancelled = True
                proc.terminate()
            line = proc.stdout.readline()
            if line:
                clean = line.rstrip("\n")
                lines.append(clean)
                if on_line:
                    on_line(clean)
            if proc.poll() is not None:
                for rest in proc.stdout:
                    clean = rest.rstrip("\n")
                    lines.append(clean)
                    if on_line:
                        on_line(clean)
                break
        try:
            returncode = proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            returncode = proc.wait(timeout=5)
            cancelled = True
        return EngineResult(returncode, tuple(cmd), tuple(lines), cancelled)

    def build(self, image: str, cwd: Path, *, build_args: dict[str, str] | None = None,
              on_line: Callable[[str], None] | None = None,
              cancel_event: threading.Event | None = None) -> EngineResult:
        args: list[str] = ["build", "-t", image]
        for key, value in sorted((build_args or {}).items()):
            args.extend(["--build-arg", f"{key}={value}"])
        args.append(".")
        return self._stream(args, cwd=cwd, on_line=on_line, cancel_event=cancel_event)

    def push(self, image: str, cwd: Path, *, on_line: Callable[[str], None] | None = None,
             cancel_event: threading.Event | None = None) -> EngineResult:
        return self._stream(["push", image], cwd=cwd, on_line=on_line, cancel_event=cancel_event)
