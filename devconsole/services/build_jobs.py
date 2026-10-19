"""Persistent, cancellable build jobs for the additive V1.1 build path."""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from devconsole.services.container_engine import ContainerEngine
from devconsole.services.git_worktree import temporary_worktree


@dataclass
class BuildJob:
    id: str
    service: str
    image: str
    ref: str
    push: bool
    status: str = "queued"
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    returncode: int | None = None
    message: str = ""
    logs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BuildJobStore:
    def __init__(
        self,
        path: Path | None = None,
        *,
        log_limit: int = 2000,
        job_limit: int = 100,
    ) -> None:
        default = (
            Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
            / "sisper-devconsole"
            / "build_jobs.json"
        )
        self.path = path or default
        self.log_limit = log_limit
        self.job_limit = job_limit
        self._lock = threading.RLock()
        self._jobs: dict[str, BuildJob] = {}
        self._load()

    def _load(self) -> None:
        recovered = False
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            for raw in payload if isinstance(payload, list) else []:
                job = BuildJob(**raw)
                if job.status in {"queued", "running", "cancelling"}:
                    job.status = "interrupted"
                    job.finished_at = time.time()
                    job.message = "Proceso anterior interrumpido; estado recuperado al iniciar DevConsole."
                    recovered = True
                self._jobs[job.id] = job
        except Exception:
            self._jobs = {}
        if recovered:
            try:
                self._persist()
            except OSError:
                # A read-only state directory must not prevent DevConsole from
                # starting; the recovered in-memory status is still truthful.
                pass

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.path.parent, 0o700)
        except OSError:
            pass
        ordered = sorted(
            self._jobs.values(),
            key=lambda j: j.created_at,
            reverse=True,
        )[: self.job_limit]
        # Keep the in-memory store bounded as well as the on-disk payload.
        self._jobs = {job.id: job for job in ordered}
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps([j.to_dict() for j in ordered], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        tmp.replace(self.path)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def create(self, service: str, image: str, ref: str, push: bool) -> BuildJob:
        with self._lock:
            job = BuildJob(uuid.uuid4().hex, service, image, ref, push)
            self._jobs[job.id] = job
            self._persist()
            return job

    def get(self, job_id: str) -> BuildJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                j.to_dict()
                for j in sorted(
                    self._jobs.values(),
                    key=lambda x: x.created_at,
                    reverse=True,
                )
            ]

    def update(self, job: BuildJob) -> None:
        with self._lock:
            job.logs = job.logs[-self.log_limit :]
            self._jobs[job.id] = job
            self._persist()


class BuildCoordinator:
    def __init__(self, store: BuildJobStore | None = None) -> None:
        self.store = store or BuildJobStore()
        self._cancel: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def start(
        self,
        *,
        service: str,
        repo_dir: Path,
        image: str,
        tag: str,
        ref: str = "HEAD",
        push: bool = False,
        engine_name: str | None = None,
        build_args: dict[str, str] | None = None,
    ) -> BuildJob:
        repo = Path(repo_dir).resolve()
        full_image = f"{image}:{tag}"
        job = self.store.create(service, full_image, ref, push)
        cancel = threading.Event()
        with self._lock:
            self._cancel[job.id] = cancel

        def run() -> None:
            job.status = "running"
            job.started_at = time.time()
            self.store.update(job)

            def log(line: str) -> None:
                job.logs.append(line)
                self.store.update(job)

            try:
                engine = ContainerEngine.discover(engine_name)
                log(f"engine={engine.name} ref={ref} image={full_image}")
                with temporary_worktree(repo, ref) as worktree:
                    result = engine.build(
                        full_image,
                        worktree,
                        build_args=build_args,
                        on_line=log,
                        cancel_event=cancel,
                    )
                    if result.cancelled:
                        job.status = "cancelled"
                        job.message = "Build cancelado por el usuario."
                        job.returncode = result.returncode
                    elif not result.ok:
                        job.status = "failed"
                        job.message = "Build falló."
                        job.returncode = result.returncode
                    elif push:
                        pushed = engine.push(
                            full_image,
                            worktree,
                            on_line=log,
                            cancel_event=cancel,
                        )
                        job.returncode = pushed.returncode
                        if pushed.cancelled:
                            job.status = "cancelled"
                            job.message = "Push cancelado por el usuario."
                        elif not pushed.ok:
                            job.status = "failed"
                            job.message = "Push falló."
                        else:
                            job.status = "success"
                            job.message = "Build y push completados."
                    else:
                        job.status = "success"
                        job.returncode = result.returncode
                        job.message = "Build completado."
            except Exception as exc:
                job.status = "failed"
                job.message = f"{type(exc).__name__}: {exc}"
                log(job.message)
            finally:
                job.finished_at = time.time()
                self.store.update(job)
                with self._lock:
                    self._cancel.pop(job.id, None)

        threading.Thread(
            target=run,
            name=f"build-{job.id[:8]}",
            daemon=True,
        ).start()
        return job

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            event = self._cancel.get(job_id)
        if event is None:
            return False
        event.set()
        job = self.store.get(job_id)
        if job and job.status == "running":
            job.status = "cancelling"
            self.store.update(job)
        return True


_COORDINATOR: BuildCoordinator | None = None
_COORDINATOR_LOCK = threading.Lock()


def get_build_coordinator() -> BuildCoordinator:
    global _COORDINATOR
    with _COORDINATOR_LOCK:
        if _COORDINATOR is None:
            _COORDINATOR = BuildCoordinator()
        return _COORDINATOR
