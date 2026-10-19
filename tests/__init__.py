"""Test suite for SISPER DevConsole.

This package intentionally lives outside ``devconsole/``, ``backend/`` and
``frontend/`` so that it is never picked up by
``devconsole.config.discover_services()`` (which only scans ``backend/`` and
``frontend/``) nor by ``devconsole.services.tilix_service.scan_tilix_sessions()``
(which only globs ``*.json`` in ``BASE_DIR``, ``backend/``, ``frontend/`` and
``config/sessions/``).

Tests use explicit, test-only role credentials.  Production code intentionally
has no built-in plaintext PIN fallback; setting these here keeps legacy security
fixtures deterministic without reintroducing a product secret in runtime code.

Run with::

    python3 -m unittest discover -s tests -t . -v
"""

import os

os.environ.setdefault("SISPER_ADMIN_PIN", "devconsole-test-admin-pin")
os.environ.setdefault("SISPER_DEV_PIN", "devconsole-test-developer-pin")
