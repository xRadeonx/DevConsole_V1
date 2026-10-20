from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest import mock

from devconsole import security
from devconsole import v11_read_policy


class _Trust:
    def __init__(self, allowed=True, status=200):
        self.allowed = allowed
        self.status = status

    def as_response(self):
        return {"success": False, "message": "untrusted client"}


class V11ReadPolicyTests(unittest.TestCase):
    def caller(self, role):
        return SimpleNamespace(role=role)

    def decide_as(self, path, role, *, trusted=True):
        with mock.patch.object(security, "resolve_caller", return_value=self.caller(role)), \
             mock.patch.object(security, "require_client_trust", return_value=_Trust(trusted, 403)):
            return v11_read_policy.decision(path, {}, ("127.0.0.1", 12345))

    def test_normal_qa_status_read_remains_unrestricted_by_role_policy(self):
        allowed, status, payload = v11_read_policy.decision(
            "/api/status", {}, ("127.0.0.1", 12345)
        )
        self.assertTrue(allowed)
        self.assertEqual(200, status)
        self.assertEqual({}, payload)

    def test_viewer_cannot_read_raw_environment(self):
        allowed, status, payload = self.decide_as(
            "/api/env/get", security.Role.VIEWER
        )
        self.assertFalse(allowed)
        self.assertEqual(403, status)
        self.assertEqual("dev", payload["required_role"])

    def test_developer_can_read_environment(self):
        allowed, status, payload = self.decide_as(
            "/api/env/get", security.Role.DEV
        )
        self.assertTrue(allowed)
        self.assertEqual(200, status)
        self.assertEqual("dev", payload["current_role"])

    def test_developer_cannot_read_user_level_telemetry(self):
        for path in (
            "/api/analytics/connections",
            "/api/activity/feed",
            "/api/activity/detail",
            "/api/telemetry/live",
            "/api/telemetry/mirror_view",
        ):
            with self.subTest(path=path):
                allowed, status, payload = self.decide_as(path, security.Role.DEV)
                self.assertFalse(allowed)
                self.assertEqual(403, status)
                self.assertEqual("admin", payload["required_role"])

    def test_admin_keeps_all_sensitive_read_capabilities(self):
        for path in v11_read_policy.READ_MIN_ROLE:
            with self.subTest(path=path):
                allowed, status, _payload = self.decide_as(path, security.Role.ADMIN)
                self.assertTrue(allowed)
                self.assertEqual(200, status)

    def test_client_trust_still_applies_before_role(self):
        allowed, status, payload = self.decide_as(
            "/api/env/get", security.Role.ADMIN, trusted=False
        )
        self.assertFalse(allowed)
        self.assertEqual(403, status)
        self.assertIn("untrusted", payload["message"])


if __name__ == "__main__":
    unittest.main()
