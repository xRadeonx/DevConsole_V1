"""Runtime hardening policy for terminal ownership in DevConsole V1.1."""
from __future__ import annotations

import os
import shutil
from pathlib import Path


def activate_safe_terminal_runtime(base_dir: Path | str) -> dict:
    """Prefer tmux safely without removing explicit Tilix support.

    Rules:
    - an explicit ``SISPER_TERMINAL_BACKEND`` always wins;
    - when unset and tmux exists, V1.1 selects tmux as process owner;
    - when tmux is absent, Tilix remains the compatible fallback;
    - tmux uses the safe wrapper that blocks legacy ``fuser -k`` calls;
    - the registry's compile-time default stays Tilix so imports/tests and the
      emergency V1 surface keep their historical contract.
    """
    root = Path(base_dir).resolve()
    explicit = (os.environ.get("SISPER_TERMINAL_BACKEND") or "").strip()
    tmux_available = bool(shutil.which("tmux"))

    if not explicit:
        os.environ["SISPER_TERMINAL_BACKEND"] = "tmux" if tmux_available else "tilix"

    selected = os.environ.get("SISPER_TERMINAL_BACKEND", "tilix").strip().lower() or "tilix"
    wrapper = root / "tmux_safe_runner.sh"
    if selected == "tmux" and wrapper.is_file():
        from devconsole.services.terminal import tmux_backend
        tmux_backend.RUNNER_SCRIPT = wrapper.name

    return {
        "selected": selected,
        "explicit": bool(explicit),
        "tmux_available": tmux_available,
        "safe_wrapper": bool(selected == "tmux" and wrapper.is_file()),
        "tilix_viewer_available": bool(shutil.which("tilix")),
    }
