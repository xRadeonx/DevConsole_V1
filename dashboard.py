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

# V1.1 compatibility policies are installed before handlers import auth/security
# and service functions by value. They enrich/guard the existing V1 contracts
# instead of replacing them, so every current feature stays available during
# the incremental migration.
from devconsole.v11_access import install as install_v11_access
from devconsole.v11_capabilities import install as install_v11_capabilities
from devconsole.v11_catalog_aliases import install as install_v11_catalog_aliases
from devconsole.v11_db_name_recovery import install as install_v11_db_name_recovery
from devconsole.v11_env_safety import install as install_v11_env_safety
from devconsole.v11_environment_secrets import install as install_v11_environment_secrets
from devconsole.v11_git_safety import install as install_v11_git_safety
from devconsole.v11_infra_catalog import install as install_v11_infra_catalog
from devconsole.v11_k8s_configmaps import install as install_v11_k8s_configmaps
from devconsole.v11_k8s_secrets import install as install_v11_k8s_secrets
from devconsole.v11_legacy_profile import install as install_v11_legacy_profile
from devconsole.v11_local_env_catalog import install as install_v11_local_env_catalog
from devconsole.v11_multienv import install_telemetry as install_v11_multienv_telemetry
from devconsole.v11_runtime_compat import install as install_v11_runtime_compat
from devconsole.v11_telemetry_compat import install as install_v11_telemetry_compat
from devconsole.v11_yaml_catalog import install as install_v11_yaml_catalog
from devconsole.v11_yaml_promotion import install as install_v11_yaml_promotion

install_v11_access()
install_v11_capabilities()
install_v11_git_safety()
install_v11_env_safety()
install_v11_yaml_promotion()
# Recover the workstation's existing SISPER DEVELOP/TEST/MAIN catalog, when the
# selected workspace is an older DevConsole checkout. The importer parses only
# known literal structures; it never executes the legacy Python/JavaScript and
# never persists recovered credentials into this repository.
install_v11_legacy_profile()
# Many SISPER workspaces already describe DEVELOP/TEST/MAIN inside the project's
# config/*.yaml Kubernetes manifests. Recover only allow-listed endpoint/user/
# credential variables from those local files, in memory, before overlaying the
# explicit 0600 secrets store. This avoids asking the operator to duplicate
# configuration that already exists in the selected project.
install_v11_yaml_catalog()
# Normalize the additional names used by real SISPER manifests (for example
# CONTRATOS_DB, CTTO_USER, DESTINACIONES_DATABASE, PGDATABASE/PGUSER) before the
# specialized .env/ConfigMap/Secret adapters parse their sources.
install_v11_catalog_aliases()
# Local service .env files describe DEVELOP. Recover only non-secret connection
# metadata (Keycloak endpoint/realm/client_id and PostgreSQL host/port/name/user)
# so the local environment does not require duplicate panel.json entries.
install_v11_local_env_catalog()
# Kubernetes ConfigMaps commonly supply the same non-secret connection metadata
# to TEST/MAIN through configMapKeyRef/envFrom. Resolve those references before
# evaluating readiness; no ConfigMap value is persisted by this adapter.
install_v11_k8s_configmaps()
# Kubernetes Secret.data values are base64-encoded and workloads may reference
# them through secretKeyRef/envFrom. Decode and resolve those references only in
# memory before the explicit local secrets store is applied. This avoids treating
# the base64 transport representation itself as the credential.
install_v11_k8s_secrets()
# Credentials are never committed. If the operator saved them in the existing
# 0600 config/secrets.json store, overlay them on the recovered catalog in
# memory so TEST/MAIN telemetry can use their own credentials.
install_v11_environment_secrets()
# Some deployments omit DATABASE_NAME while still exposing a service-specific
# PostgreSQL account or a PostgreSQL URL. Recover only the missing DB name from
# those already-discovered values; never invent cross-environment configuration.
install_v11_db_name_recovery()
# Legacy map telemetry formats ``cfg["name"]`` directly. YAML-recovered TEST or
# MAIN targets may be fully usable without that decorative field, so supply a
# safe non-secret label while leaving endpoints and credentials untouched.
install_v11_telemetry_compat()
# A partial panel.json (for example DEVELOP only) must not hide TEST/MAIN rows
# recovered from the local V1 catalog. Compose all non-secret infrastructure
# sources per environment while keeping explicit local rows authoritative.
install_v11_infra_catalog()
# Fresh ZIP checkouts do not contain panel.json/services.json. Install the
# compatibility guards before handlers import infra/telemetry functions by
# value so filesystem discovery and the read-only dashboard still work.
install_v11_runtime_compat()
# V1 used DEVELOP whenever a requested telemetry environment was absent. That
# is unsafe for TEST/MAIN because the UI appeared to switch while querying the
# wrong environment. Strict wrappers now make the effective env explicit and
# fail closed when that env is not configured.
install_v11_multienv_telemetry()

from devconsole.auth import ADMIN_PIN, verify_admin_pin, is_admin_request
from devconsole.api import handlers as handlers_module
from devconsole.api.handlers import DevConsoleHandler
from devconsole.v11_multienv import install_handler as install_v11_multienv_handler
from devconsole.v11_read_policy import install as install_v11_read_policy
from devconsole.v11_ui import install as install_v11_ui

# Add the secret-free environment capability endpoint and a bundled SVG fallback
# before the read-policy/UI wrappers are layered on top of the complete V1 GET
# dispatcher.
install_v11_multienv_handler(DevConsoleHandler, handlers_module)
# The read policy wraps API reads first. The additive UI wrapper is installed
# afterwards and intercepts only / and /index.html; every API request continues
# through the authorization wrapper and the untouched V1 dispatcher.
install_v11_read_policy(DevConsoleHandler)
install_v11_ui(DevConsoleHandler, handlers_module)

from devconsole.server import main

# Expose HTML_TEMPLATE for legacy scripts that might inspect it
HTML_TEMPLATE_FILE = STATIC_DIR / "index.html"
HTML_TEMPLATE = HTML_TEMPLATE_FILE.read_text(encoding="utf-8") if HTML_TEMPLATE_FILE.exists() else ""

if __name__ == "__main__":
    main()
