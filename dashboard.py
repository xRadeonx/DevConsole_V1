#!/usr/bin/env python3
"""
SISPER DevConsole & Platform (Modular Architecture Edition)
Plataforma Integral de Desarrollo, Orquestación de Tilix,
Gestión Multi-Entorno (.env, Git DEVELOP/TEST/MAIN), CI/CD & Kubernetes.

Ejecutar: python3 dashboard.py
Acceder:  http://localhost:9099
"""

import sys
from pathlib import Path

# Ensure root directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Backward-compatible exports
from devconsole.config import (
    PORT,
    CONFIG,
    CONFIG_FILE,
    STATIC_DIR,
    SERVICES_BACKEND,
    SERVICES_FRONTEND,
    SLICES,
    ENVIRONMENTS,
    is_port_open,
    load_config,
    get_service_repo_dir,
)
from devconsole.auth import ADMIN_PIN, verify_admin_pin, is_admin_request
from devconsole.api.handlers import DevConsoleHandler
from devconsole.server import main

# Expose HTML_TEMPLATE for legacy scripts that might inspect it
HTML_TEMPLATE_FILE = STATIC_DIR / "index.html"
HTML_TEMPLATE = HTML_TEMPLATE_FILE.read_text(encoding="utf-8") if HTML_TEMPLATE_FILE.exists() else ""

if __name__ == "__main__":
    main()
