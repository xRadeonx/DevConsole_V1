from __future__ import annotations

import dataclasses
import unittest
from unittest import mock

from devconsole import security
from devconsole import v11_access


class V11AccessPolicyTests(unittest.TestCase):
    def tearDown(self) -> None:
        v11_access.lock_developer()

    def _ctx(self, role: security.Role):
        return security.CallerContext(
            role=role,
            role_header=role.value,
            admin_session_valid=(role is security.Role.ADMIN),
            local_token_valid=True,
            local_token_required=False,
            origin=None,
            origin_allowed=True,
            host_header="127.0.0.1:9099",
            host_allowed=True,
            client_ip="127.0.0.1",
            notes=(),
        )

    def test_developer_is_locked_by_default(self):
        ctx = self._ctx(security.Role.DEV)
        result = v11_access.enforce_context(ctx, {"X-Auth-Role": "dev"})
        self.assertIs(result.role, security.Role.VIEWER)
        self.assertIn("developer_locked", result.notes)

    def test_valid_unlock_preserves_developer_role(self):
        v11_access.unlock_developer(ttl_seconds=60)
        ctx = self._ctx(security.Role.DEV)
        result = v11_access.enforce_context(ctx, {"X-Auth-Role": "dev"})
        self.assertIs(result.role, security.Role.DEV)

    def test_viewer_is_never_promoted(self):
        v11_access.unlock_developer(ttl_seconds=60)
        ctx = self._ctx(security.Role.VIEWER)
        result = v11_access.enforce_context(ctx, {"X-Auth-Role": "viewer"})
        self.assertIs(result.role, security.Role.VIEWER)

    def test_unlock_expires(self):
        with mock.patch("devconsole.v11_access.time.time", return_value=100.0):
            v11_access.unlock_developer(ttl_seconds=10)
        self.assertTrue(v11_access.developer_unlocked(now=105.0))
        self.assertFalse(v11_access.developer_unlocked(now=111.0))

    def test_status_contains_no_secret_material(self):
        data = v11_access.status()
        self.assertEqual("viewer", data["default_role"])
        self.assertNotIn("pin", " ".join(data.keys()).lower())


if __name__ == "__main__":
    unittest.main()
