"""Test suite for SISPER DevConsole.

This package intentionally lives outside ``devconsole/``, ``backend/`` and
``frontend/`` so that it is never picked up by
``devconsole.config.discover_services()`` (which only scans ``backend/`` and
``frontend/``) nor by ``devconsole.services.tilix_service.scan_tilix_sessions()``
(which only globs ``*.json`` in ``BASE_DIR``, ``backend/``, ``frontend/`` and
``config/sessions/``).

Run with::

    python3 -m unittest discover -s tests -t . -v
"""
