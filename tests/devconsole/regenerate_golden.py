"""Regenerate the golden discovery snapshot.

Run **only** when the workspace legitimately changes (a service is added or
removed, or a port is deliberately reassigned)::

    python3 -m tests.devconsole.regenerate_golden

The generated file is ``tests/devconsole/fixtures/golden_discovery.json`` and is
consumed by :class:`tests.devconsole.test_config_discovery.GoldenDiscoveryTest`.

This module performs **read-only** discovery: it never starts, stops or
restarts anything.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import devconsole.config as dcfg  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "golden_discovery.json"


def _slim(entries):
    return [
        {
            "name": e["name"],
            "port": e["port"],
            "group": e.get("group"),
            "k8s_deploy": e.get("k8s_deploy"),
            "k8s_file": e.get("k8s_file"),
            "has_consumer": e.get("has_consumer"),
            "has_worker": e.get("has_worker"),
        }
        for e in entries
    ]


def _current_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL, timeout=5,
        ).decode().strip()
    except Exception:
        return "unknown"


def main() -> int:
    backend, frontend = dcfg.discover_services()
    payload = {
        "_comment": (
            "Golden snapshot of devconsole.config.discover_services() against the "
            "real workspace. Regenerate with: python3 -m tests.devconsole.regenerate_golden"
        ),
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "captured_at_commit": _current_commit(),
        "base_dir": str(dcfg.BASE_DIR),
        "backend_count": len(backend),
        "frontend_count": len(frontend),
        "backend": _slim(backend),
        "frontend": _slim(frontend),
    }
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
    print(f"wrote {FIXTURE}")
    print(f"  backend={len(backend)} frontend={len(frontend)} commit={payload['captured_at_commit'][:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
