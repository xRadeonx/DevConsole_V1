"""Safety helpers for Kubernetes operations in DevConsole V1.1."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class KubectlResult:
    ok: bool
    command: tuple[str, ...]
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0


def _run(args: list[str], timeout: int = 30) -> KubectlResult:
    cmd = ["kubectl", *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return KubectlResult(proc.returncode == 0, tuple(cmd), proc.stdout.strip(), proc.stderr.strip(), proc.returncode)
    except subprocess.TimeoutExpired:
        return KubectlResult(False, tuple(cmd), stderr=f"timeout después de {timeout}s", returncode=124)
    except OSError as exc:
        return KubectlResult(False, tuple(cmd), stderr=str(exc), returncode=127)


def current_context() -> str:
    result = _run(["config", "current-context"], timeout=10)
    return result.stdout if result.ok else ""


def namespace_exists(namespace: str) -> bool:
    return _run(["get", "namespace", namespace, "-o", "name"], timeout=10).ok


def preflight(namespace: str, expected_context: str | None = None) -> dict:
    context = current_context()
    errors: list[str] = []
    warnings: list[str] = []
    if not context:
        errors.append("No se pudo determinar el contexto kubectl actual")
    if expected_context and context and context != expected_context:
        errors.append(f"Contexto actual {context!r} != esperado {expected_context!r}")
    if namespace and not namespace_exists(namespace):
        errors.append(f"Namespace no disponible: {namespace}")
    if namespace.lower() in {"prod", "production", "produccion", "producción"}:
        warnings.append("Destino identificado como producción; requiere confirmación reforzada")
    return {"ok": not errors, "context": context, "namespace": namespace, "errors": errors, "warnings": warnings}


def diff_manifest(manifest: Path | str, namespace: str) -> KubectlResult:
    return _run(["diff", "-f", str(Path(manifest)), "-n", namespace], timeout=45)


def apply_manifest(manifest: Path | str, namespace: str) -> KubectlResult:
    return _run(["apply", "-f", str(Path(manifest)), "-n", namespace], timeout=60)


def rollout_undo(deployment: str, namespace: str) -> KubectlResult:
    name = deployment if deployment.startswith("deployment/") else f"deployment/{deployment}"
    return _run(["rollout", "undo", name, "-n", namespace], timeout=60)
