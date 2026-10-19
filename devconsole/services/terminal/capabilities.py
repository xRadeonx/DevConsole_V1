"""Capability discovery for terminal UX without replacing Tilix/tmux."""
from __future__ import annotations

import shutil
from pathlib import Path


def terminal_capabilities(static_dir: Path | str | None = None) -> dict:
    root = Path(static_dir) if static_dir else Path(__file__).resolve().parents[3] / "static"
    vendor = root / "vendor" / "terminal-lab"
    return {
        "tmux": bool(shutil.which("tmux")),
        "tilix": bool(shutil.which("tilix")),
        "xterm": (root / "js" / "xterm.js").is_file(),
        "addons": {
            "fit": (vendor / "addon-fit.js").is_file(),
            "search": (vendor / "addon-search.js").is_file(),
            "clipboard": True,
            "weblinks": True,
            "webgl": False,
        },
        "session_owner": "tmux",
        "external_viewer": "tilix",
        "fallback_renderer": "dom/canvas",
    }
