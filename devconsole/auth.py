# devconsole/auth.py
"""Credential-backed administrator sessions for DevConsole.

Session tokens live in a per-user runtime directory with mode 0600 and may be
carried either by an explicit header or an HttpOnly SameSite cookie.  V1.1 also
removes authority from the historical built-in administrator PIN: an admin
credential must come from the configured hash store, a systemd credential or an
explicit environment value.
"""

import json
import os
import time
import uuid
from pathlib import Path

from devconsole.local_trust import runtime_dir

# Kept only for backwards-compatible imports. There is no built-in clear-text
# fallback anymore; empty means "not explicitly supplied by environment".
ADMIN_PIN = os.environ.get("SISPER_ADMIN_PIN", "")

ADMIN_COOKIE_NAME = "sisper_admin_session"
SESSION_TTL_HOURS = 24
_FILE_MODE = 0o600


def _sessions_file() -> Path:
    override = os.environ.get("SISPER_ADMIN_SESSIONS_FILE")
    if override:
        return Path(override).expanduser()
    return runtime_dir() / "admin_sessions.json"


ADMIN_SESSIONS_FILE = _sessions_file()


def _load_admin_sessions() -> dict[str, float]:
    path = _sessions_file()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        now = time.time()
        return {
            key: float(created)
            for key, created in data.items()
            if (now - float(created)) < (SESSION_TTL_HOURS * 3600)
        }
    except Exception:
        return {}


def _save_admin_sessions(sessions: dict[str, float]):
    path = _sessions_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(path.parent, 0o700)
        except OSError:
            pass
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, _FILE_MODE)
        try:
            os.write(fd, json.dumps(sessions).encode("utf-8"))
        finally:
            os.close(fd)
        os.chmod(path, _FILE_MODE)
    except Exception:
        pass


def _role_has_explicit_credential(role: str) -> bool:
    """Reject the historical implicit fallback while preserving real sources."""
    from devconsole import pins

    try:
        state = str(pins.estado().get(role, ""))
    except Exception:
        return False
    return state.startswith(("credencial", "scrypt", "variable"))


def verify_pin(pin: str, role: str = "admin") -> tuple[bool, str]:
    """Validate a configured role PIN; admin receives a session token.

    No built-in/default credential is accepted. Product-distributed scrypt
    verifiers in the configured secrets store remain fully supported, so the
    same approved product credential can still be used across installations.
    """
    from devconsole import pins

    if role not in ("admin", "dev") or not _role_has_explicit_credential(role):
        return False, ""
    if not pins.verify(role, pin):
        return False, ""
    if role != "admin":
        return True, ""
    token = str(uuid.uuid4())
    sessions = _load_admin_sessions()
    sessions[token] = time.time()
    _save_admin_sessions(sessions)
    return True, token


def verify_admin_pin(pin: str) -> tuple[bool, str]:
    return verify_pin(pin, "admin")


def is_valid_admin_token(token: str) -> bool:
    if not token:
        return False
    return token in _load_admin_sessions()


def invalidate_admin_token(token: str) -> bool:
    if not token:
        return False
    sessions = _load_admin_sessions()
    if token not in sessions:
        return False
    sessions.pop(token, None)
    _save_admin_sessions(sessions)
    return True


def cookie_value(cookie_header: str | None, name: str) -> str | None:
    if not cookie_header or not name:
        return None
    for part in cookie_header.split(";"):
        key, _, value = part.strip().partition("=")
        if key == name:
            return value or None
    return None


def build_admin_cookie(token: str) -> str:
    return (
        f"{ADMIN_COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Strict; "
        f"Max-Age={SESSION_TTL_HOURS * 3600}"
    )


def build_admin_cookie_clear() -> str:
    return f"{ADMIN_COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0"


def admin_token_from(headers) -> str:
    try:
        header_token = (headers.get("X-Auth-Token") or "").strip()
    except Exception:
        header_token = ""
    if header_token:
        return header_token
    try:
        return (cookie_value(headers.get("Cookie"), ADMIN_COOKIE_NAME) or "").strip()
    except Exception:
        return ""


def is_admin_request(headers) -> bool:
    return is_valid_admin_token(admin_token_from(headers))


def is_viewer_request(headers) -> bool:
    try:
        return (headers.get("X-Auth-Role", "dev") or "dev").lower() == "viewer"
    except Exception:
        return False
