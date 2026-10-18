"""Ephemeral local-trust token for the DevConsole API (roadmap phase 0C.4).

Separates two concepts that must not be conflated:

* **User authentication** (:mod:`devconsole.auth`) — *who* is calling, expressed
  as ``viewer`` / ``dev`` / ``admin`` and gated by the admin PIN.
* **Local client trust** (this module) — *which process* is allowed to drive the
  future Desktop API at all.  A correct PIN must never be the only barrier
  between the orchestrator and an arbitrary local or remote process.

Delivery mechanism
------------------
The token is published to a **runtime file** with ``0600`` permissions:

    $XDG_RUNTIME_DIR/sisper-devconsole/token

``XDG_RUNTIME_DIR`` is per-user, ``0700``, and cleared on logout, which makes it
the correct Linux channel for a same-user handshake.  It is deliberately **not**
``/tmp`` (world-traversable) and deliberately **not** an environment variable on
the server process (which would leak into every child process, including the
microservices DevConsole spawns).

The future Electron process reads that file directly; the browser is handed the
same token through an ``HttpOnly; SameSite=Strict`` cookie, so no
token-dispensing endpoint exists.

Properties
----------
* Generated with :func:`secrets.token_urlsafe` (256 bits of entropy).
* Never hardcoded, never versioned, never logged, never returned by the API.
* Lifetime is bound to the server process: regenerated on every start and
  removed on exit.  Nothing is persisted.
* Comparison uses :func:`secrets.compare_digest` (constant time).

Enforcement is opt-in via ``SISPER_LOCAL_TOKEN_REQUIRED``; the default (``0``)
preserves today's behaviour exactly.
"""

from __future__ import annotations

import atexit
import os
import secrets
import stat
from pathlib import Path

#: Environment variable that turns enforcement on.  Default ``0`` (off).
ENV_REQUIRED = "SISPER_LOCAL_TOKEN_REQUIRED"

#: Test/ops override for the token file location.
ENV_TOKEN_PATH = "SISPER_LOCAL_TOKEN_PATH"

#: Directory created under ``XDG_RUNTIME_DIR``.
RUNTIME_SUBDIR = "sisper-devconsole"

#: File name inside the runtime directory.
TOKEN_FILENAME = "token"

#: HTTP header a non-browser client may use to present the token.
HEADER_NAME = "X-Sisper-Local-Token"

#: Cookie the browser is given for same-origin requests.
COOKIE_NAME = "sisper_local_trust"

#: 32 bytes of entropy, urlsafe-encoded.
TOKEN_BYTES = 32

#: Directory mode for the runtime directory.
DIR_MODE = 0o700

#: File mode for the token file.
FILE_MODE = 0o600

_process_token: str | None = None
_published_path: Path | None = None


# --------------------------------------------------------------------------- #
# generation
# --------------------------------------------------------------------------- #

def generate_token() -> str:
    """Return a fresh cryptographically strong token."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def get_token() -> str:
    """Return this process's token, generating it on first use.

    The value is per-process: a restart produces a new token, so a token
    captured from a previous run is worthless.
    """
    global _process_token
    if _process_token is None:
        _process_token = generate_token()
    return _process_token


def reset_token() -> None:
    """Discard the in-memory token (used by tests and rotation)."""
    global _process_token
    _process_token = None


# --------------------------------------------------------------------------- #
# location
# --------------------------------------------------------------------------- #

def runtime_dir() -> Path:
    """Return the directory that will hold the token file.

    ``XDG_RUNTIME_DIR`` when available; otherwise a per-user directory under
    ``/run/user/<uid>``; otherwise a ``0700`` directory inside the system temp
    directory as a last resort.  ``/tmp`` itself is never used directly.
    """
    override = os.environ.get(ENV_TOKEN_PATH)
    if override:
        return Path(override).expanduser().resolve().parent

    xdg = os.environ.get("XDG_RUNTIME_DIR")
    if xdg:
        return Path(xdg) / RUNTIME_SUBDIR

    uid = os.getuid()
    fallback = Path(f"/run/user/{uid}")
    if fallback.is_dir() and os.access(fallback, os.W_OK):
        return fallback / RUNTIME_SUBDIR

    import tempfile
    return Path(tempfile.gettempdir()) / f"{RUNTIME_SUBDIR}-{uid}"


def token_path() -> Path:
    """Return the full path of the published token file."""
    override = os.environ.get(ENV_TOKEN_PATH)
    if override:
        return Path(override).expanduser()
    return runtime_dir() / TOKEN_FILENAME


# --------------------------------------------------------------------------- #
# publication
# --------------------------------------------------------------------------- #

def publish_token(token: str | None = None) -> Path | None:
    """Write the token to a ``0600`` file, returning its path.

    Returns ``None`` when publication is not possible (read-only runtime dir,
    unsupported platform).  Failure to publish is never fatal: the in-process
    token still works, and enforcement reports a clear error instead of silently
    accepting everyone.
    """
    global _published_path
    token = token or get_token()
    path = token_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(path.parent, DIR_MODE)
        except OSError:
            pass
        # Create with restrictive permissions *before* writing any content, so
        # the secret is never briefly world-readable.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, FILE_MODE)
        try:
            os.write(fd, token.encode("utf-8"))
        finally:
            os.close(fd)
        os.chmod(path, FILE_MODE)
        _published_path = path
        return path
    except OSError:
        return None


def cleanup_token() -> None:
    """Remove the published token file.  Safe to call multiple times."""
    global _published_path
    path = _published_path or token_path()
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass
    _published_path = None


def register_cleanup() -> None:
    """Arrange for the token file to be removed when the process exits."""
    atexit.register(cleanup_token)


def read_published_token() -> str | None:
    """Read the token from the runtime file.

    This is the client-side entry point: the future Electron main process calls
    it to obtain the token.  It performs no permission relaxation — if the file
    is not readable by this user, it returns ``None``.
    """
    try:
        return token_path().read_text(encoding="utf-8").strip() or None
    except (OSError, PermissionError):
        return None


def published_permissions() -> int | None:
    """Return the published file's mode, or ``None`` if it is not there."""
    try:
        return stat.S_IMODE(token_path().stat().st_mode)
    except OSError:
        return None


# --------------------------------------------------------------------------- #
# validation
# --------------------------------------------------------------------------- #

def validate_token(provided: str | None) -> bool:
    """Constant-time comparison against this process's token."""
    if not provided or not isinstance(provided, str):
        return False
    expected = get_token()
    try:
        return secrets.compare_digest(provided, expected)
    except (TypeError, ValueError):
        return False


def token_required() -> bool:
    """Is enforcement enabled?

    Only the exact string ``1`` enables it; anything else (unset, empty,
    ``true``, ``yes``, garbage) leaves it **off**, which is the fail-safe
    direction for a security feature that would otherwise lock the UI out.
    """
    return os.environ.get(ENV_REQUIRED, "0").strip() == "1"


def enforce_request_token(headers_get) -> tuple[bool, str]:
    """Validate the token on an incoming request.

    ``headers_get`` is a callable equivalent to ``headers.get`` so a
    ``Cookie``-bearing request and a header-only client are both supported.

    Returns ``(ok, reason)``.  When enforcement is disabled this always
    succeeds and reports ``"not_required"``.
    """
    if not token_required():
        return True, "not_required"

    header_token = headers_get(HEADER_NAME)
    if header_token and validate_token(header_token):
        return True, "header"

    cookie_token = _token_from_cookie(headers_get("Cookie"))
    if cookie_token and validate_token(cookie_token):
        return True, "cookie"

    return False, "missing_or_invalid_local_token"


def _token_from_cookie(cookie_header: str | None) -> str | None:
    """Extract this module's cookie value from a raw ``Cookie`` header."""
    if not cookie_header:
        return None
    for part in cookie_header.split(";"):
        name, _, value = part.strip().partition("=")
        if name == COOKIE_NAME:
            return value or None
    return None


def build_cookie_header(token: str | None = None, *, max_age: int = 86400) -> str:
    """Build the ``Set-Cookie`` value for the local-trust cookie.

    ``HttpOnly`` keeps it away from page scripts; ``SameSite=Strict`` ensures a
    cross-origin page can never cause the browser to attach it, which is what
    makes the cookie safe to use as a CSRF-resistant trust channel.
    """
    token = token or get_token()
    return (
        f"{COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Strict; "
        f"Max-Age={max_age}"
    )
