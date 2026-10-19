"""Developer-session authentication added by DevConsole V1.1.

Administrator sessions remain owned by :mod:`devconsole.auth` for backwards
compatibility.  V1.1 adds an equivalent, credential-backed Developer session so
``X-Auth-Role: dev`` is no longer authority by itself.
"""
from __future__ import annotations

import json
import os
import secrets
import time
from pathlib import Path

from devconsole import auth, pins
from devconsole.local_trust import runtime_dir

DEV_COOKIE_NAME = "sisper_dev_session"
SESSION_TTL_HOURS = auth.SESSION_TTL_HOURS
_FILE_MODE = 0o600


def _sessions_file() -> Path:
    override = os.environ.get("SISPER_DEV_SESSIONS_FILE")
    if override:
        return Path(override).expanduser()
    return runtime_dir() / "dev_sessions.json"


def _load() -> dict[str, float]:
    path = _sessions_file()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        now = time.time()
        return {
            str(token): float(created)
            for token, created in data.items()
            if now - float(created) < SESSION_TTL_HOURS * 3600
        }
    except Exception:
        return {}


def _save(sessions: dict[str, float]) -> None:
    path = _sessions_file()
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
    try:
        os.chmod(path, _FILE_MODE)
    except OSError:
        pass


def create_dev_session() -> str:
    token = secrets.token_urlsafe(32)
    sessions = _load()
    sessions[token] = time.time()
    _save(sessions)
    return token


def verify_dev_pin(pin: str) -> tuple[bool, str]:
    if not isinstance(pin, str) or not pins.verify("dev", pin):
        return False, ""
    return True, create_dev_session()


def is_valid_dev_token(token: str | None) -> bool:
    return bool(token and token in _load())


def invalidate_dev_token(token: str | None) -> bool:
    if not token:
        return False
    sessions = _load()
    if token not in sessions:
        return False
    sessions.pop(token, None)
    _save(sessions)
    return True


def _cookie_value(cookie_header: str | None, name: str) -> str:
    return auth.cookie_value(cookie_header, name) or ""


def dev_token_from(headers) -> str:
    try:
        header = (headers.get("X-Dev-Auth-Token") or "").strip()
    except Exception:
        header = ""
    if header:
        return header
    try:
        return _cookie_value(headers.get("Cookie"), DEV_COOKIE_NAME).strip()
    except Exception:
        return ""


def effective_role(headers) -> str:
    """Return ``admin``, ``dev`` or ``viewer`` from actual credentials."""
    try:
        if auth.is_admin_request(headers):
            return "admin"
    except Exception:
        pass
    if is_valid_dev_token(dev_token_from(headers)):
        return "dev"
    return "viewer"


def build_dev_cookie(token: str) -> str:
    return (
        f"{DEV_COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Strict; "
        f"Max-Age={SESSION_TTL_HOURS * 3600}"
    )


def build_dev_cookie_clear() -> str:
    return f"{DEV_COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0"
