"""Central TLS policy for internal HTTPS clients.

Verification is ON by default.  Internal/private CAs can be supplied with
``SISPER_KEYCLOAK_CA_BUNDLE`` (preferred) or ``SSL_CERT_FILE``.  Disabling
verification is possible only through the explicit laboratory escape hatch
``SISPER_ALLOW_INSECURE_KEYCLOAK_TLS=1`` and is surfaced in diagnostics.
"""
from __future__ import annotations

import os
import ssl
from dataclasses import dataclass
from pathlib import Path

_TRUE = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class TLSPolicy:
    verify: bool
    ca_bundle: str | None
    source: str

    @property
    def insecure(self) -> bool:
        return not self.verify

    def to_dict(self) -> dict:
        return {"verify": self.verify, "ca_bundle": self.ca_bundle, "source": self.source, "insecure": self.insecure}


def keycloak_tls_policy() -> TLSPolicy:
    insecure = os.environ.get("SISPER_ALLOW_INSECURE_KEYCLOAK_TLS", "").strip().lower() in _TRUE
    if insecure:
        return TLSPolicy(False, None, "SISPER_ALLOW_INSECURE_KEYCLOAK_TLS")

    configured = (os.environ.get("SISPER_KEYCLOAK_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE") or "").strip()
    if configured:
        path = Path(configured).expanduser()
        return TLSPolicy(True, str(path), "custom-ca")
    return TLSPolicy(True, None, "system-ca")


def create_keycloak_ssl_context() -> ssl.SSLContext:
    policy = keycloak_tls_policy()
    if policy.insecure:
        # Explicit opt-in only.  This is intentionally noisier than the old
        # unconditional CERT_NONE behaviour and never becomes the default.
        context = ssl._create_unverified_context()  # noqa: SLF001 - stdlib escape hatch is deliberate here
        context.check_hostname = False
        return context
    if policy.ca_bundle:
        return ssl.create_default_context(cafile=policy.ca_bundle)
    return ssl.create_default_context()
