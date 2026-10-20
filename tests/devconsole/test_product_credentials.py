from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from devconsole import auth, pins


class ProductCredentialTests(unittest.TestCase):
    def setUp(self) -> None:
        pins._FALLOS.clear()
        self.addCleanup(pins._FALLOS.clear)

    def _isolated_environment(self):
        td = tempfile.TemporaryDirectory(prefix="devconsole-product-credentials-")
        self.addCleanup(td.cleanup)
        secrets_file = Path(td.name) / "secrets.json"
        env = {
            "SISPER_SECRETS_FILE": str(secrets_file),
            "SISPER_ADMIN_SESSIONS_FILE": str(Path(td.name) / "sessions.json"),
        }
        return mock.patch.dict(os.environ, env, clear=False), secrets_file

    def test_runtime_admin_export_has_no_builtin_plaintext_default(self):
        # The compatibility symbol may expose an explicitly supplied env value,
        # but runtime source must not manufacture a known product password.
        source = Path(auth.__file__).read_text(encoding="utf-8")
        self.assertNotIn('"sisper2026"', source)
        self.assertNotIn("'sisper2026'", source)

    def test_pins_source_has_no_legacy_plaintext_fallback(self):
        source = Path(pins.__file__).read_text(encoding="utf-8")
        self.assertNotIn("_PIN_ARRANQUE_ADMIN", source)
        self.assertNotIn('or "sisper2026"', source)
        self.assertNotIn("or 'sisper2026'", source)

    def test_roles_are_locked_when_no_explicit_credential_exists(self):
        patcher, _ = self._isolated_environment()
        with patcher:
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("SISPER_ADMIN_PIN", None)
                os.environ.pop("SISPER_DEV_PIN", None)
                os.environ.pop("CREDENTIALS_DIRECTORY", None)
                self.assertFalse(pins.verify("admin", "anything-at-all"))
                self.assertFalse(pins.verify("dev", "anything-at-all"))
                status = pins.estado()
                self.assertEqual("sin credencial (rol bloqueado)", status["admin"])
                self.assertEqual("sin credencial (rol bloqueado)", status["dev"])

    def test_each_environment_credential_unlocks_only_its_own_role(self):
        patcher, _ = self._isolated_environment()
        with patcher, mock.patch.dict(
            os.environ,
            {
                "SISPER_ADMIN_PIN": "admin-explicit-test",
                "SISPER_DEV_PIN": "developer-explicit-test",
            },
            clear=False,
        ):
            self.assertTrue(pins.verify("admin", "admin-explicit-test"))
            self.assertFalse(pins.verify("dev", "admin-explicit-test"))
            pins._FALLOS.clear()
            self.assertTrue(pins.verify("dev", "developer-explicit-test"))
            self.assertFalse(pins.verify("admin", "developer-explicit-test"))

    def test_scrypt_product_hash_has_precedence_and_never_persists_plaintext(self):
        patcher, secrets_file = self._isolated_environment()
        with patcher, mock.patch.dict(
            os.environ,
            {
                "SISPER_ADMIN_PIN": "wrong-env-pin",
                "SISPER_DEV_PIN": "wrong-dev-env-pin",
            },
            clear=False,
        ):
            pins.set_pin("admin", "product-admin-test")
            pins.set_pin("dev", "product-developer-test")
            raw = secrets_file.read_text(encoding="utf-8")
            self.assertNotIn("product-admin-test", raw)
            self.assertNotIn("product-developer-test", raw)
            self.assertTrue(pins.verify("admin", "product-admin-test"))
            self.assertTrue(pins.verify("dev", "product-developer-test"))
            self.assertFalse(pins.verify("admin", "wrong-env-pin"))


if __name__ == "__main__":
    unittest.main()
