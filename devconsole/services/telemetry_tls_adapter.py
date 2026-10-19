"""Compatibility adapter that prevents legacy telemetry from downgrading TLS.

The V1 telemetry module historically executes::

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

Rewriting that large domain module in the same security change would carry a
large regression risk.  V1.1 therefore replaces only *its module-local* ``ssl``
reference with this proxy.  It returns a real SSLContext through a thin wrapper
that refuses the two downgrade assignments.  urllib only needs SSLContext's
public methods/properties, which are delegated unchanged.

Emergency rollback to the V1 handler does not install this adapter.
"""
from __future__ import annotations

import ssl as _ssl
from typing import Any

from devconsole.services.tls_policy import create_keycloak_ssl_context, keycloak_tls_policy


class HardenedContext:
    """Delegate an SSLContext while enforcing the configured minimum policy."""

    def __init__(self, context: _ssl.SSLContext) -> None:
        object.__setattr__(self, "_context", context)

    @property
    def check_hostname(self) -> bool:
        return self._context.check_hostname

    @check_hostname.setter
    def check_hostname(self, value: bool) -> None:
        if keycloak_tls_policy().insecure:
            self._context.check_hostname = bool(value)
            return
        # The compatibility module attempts False; secure mode refuses it.
        if value:
            self._context.check_hostname = True

    @property
    def verify_mode(self):
        return self._context.verify_mode

    @verify_mode.setter
    def verify_mode(self, value) -> None:
        if keycloak_tls_policy().insecure:
            self._context.verify_mode = value
            return
        if value == _ssl.CERT_NONE:
            return
        self._context.verify_mode = value

    def __getattr__(self, name: str) -> Any:
        return getattr(self._context, name)

    def wrap_socket(self, *args, **kwargs):
        return self._context.wrap_socket(*args, **kwargs)


class HardenedSSLModule:
    """Small module-like facade used only by telemetry_service."""

    CERT_NONE = _ssl.CERT_NONE
    CERT_OPTIONAL = _ssl.CERT_OPTIONAL
    CERT_REQUIRED = _ssl.CERT_REQUIRED

    @staticmethod
    def create_default_context(*args, **kwargs) -> HardenedContext:
        # telemetry_service calls this without arguments.  Preserve unexpected
        # stdlib-compatible callers, but use the central Keycloak policy for the
        # normal path.
        if args or kwargs:
            context = _ssl.create_default_context(*args, **kwargs)
        else:
            context = create_keycloak_ssl_context()
        return HardenedContext(context)

    def __getattr__(self, name: str) -> Any:
        return getattr(_ssl, name)


_PROXY = HardenedSSLModule()


def install_telemetry_tls_policy() -> dict:
    """Install the adapter idempotently and return a non-secret diagnostic."""
    from devconsole.services import telemetry_service

    if not isinstance(getattr(telemetry_service, "ssl", None), HardenedSSLModule):
        telemetry_service.ssl = _PROXY
    return keycloak_tls_policy().to_dict()
