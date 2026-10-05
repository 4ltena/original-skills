import copy
import os
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from account_catalog.codec import Failure, canonical, loads
from account_catalog.crypto import (KDF, key_payload, new_key, open_credential, recover,
                                    seal, unwrap_portable, wrap_portable)
from account_catalog import protectors


PHRASE = "dummy-only-phrase-with-at-least-32-characters"


class CryptoTests(unittest.TestCase):
    def test_nist_aes256_gcm_known_answer(self):
        actual = AESGCM(bytes(32)).encrypt(bytes(12), bytes(16), None)
        self.assertEqual(actual.hex(), "cea7403d4d606b6e074ec5d3baf39d18d0d1c8a799996bf0265b98b5d48ab919")

    def test_roundtrip_and_metadata_binding(self):
        key = new_key()
        values = {"username": "dummy-user-canary", "password": "dummy-password-canary"}
        record = seal("credential", "key", key, values)
        self.assertNotIn(b"dummy-user-canary", canonical(record))
        self.assertEqual(open_credential(record, "credential", "key", key), values)
        for field, value in (("key_id", "other"), ("credential_id", "other"),
                             ("protection", "other"), ("schema_version", True),
                             ("nonce_b64", "AAAAAAAAAAAAAAAA"), ("payload_b64", "AAAA")):
            changed = {**record, field: value}
            with self.subTest(field=field), self.assertRaises(Failure):
                open_credential(changed, "credential", "key", key)
        with self.assertRaises(Failure):
            open_credential(record, "credential", "key", new_key())

    def test_nonce_reuse_is_rejected(self):
        nonce = b"\x01" * 12
        with patch("account_catalog.crypto.os.urandom", return_value=nonce), self.assertRaises(Failure):
            seal("credential", "key", bytes(32), {"username": "dummy"}, {nonce})

    def test_portable_wrap_and_kdf_limits_before_derivation(self):
        key = new_key()
        record = wrap_portable("key", key, PHRASE)
        self.assertEqual(unwrap_portable(record, "key", PHRASE), key)
        with self.assertRaises(Failure):
            unwrap_portable(record, "key", PHRASE + "wrong")
        for value in (0, 2**31, True):
            changed = copy.deepcopy(record)
            changed["kdf"]["memory_kib"] = value
            with patch("account_catalog.crypto._derive") as derive, self.assertRaises(Failure):
                unwrap_portable(changed, "key", PHRASE)
            derive.assert_not_called()

    def test_recovery_is_independent_and_no_provider_fallback(self):
        key = new_key()
        self.assertEqual(recover(loads(canonical(key_payload("key", key))), "key"), key)
        with self.assertRaises(Failure):
            protectors.unwrap({}, "missing-provider", "key", "broker")
        with self.assertRaises(Failure):
            recover(key_payload("key", key), "other")

    @unittest.skipUnless(os.name == "nt", "Windows DPAPI")
    def test_real_dpapi_dummy_roundtrip(self):
        key = new_key()
        document = protectors.wrap(protectors.DPAPI, "dummy-key", key)
        from account_catalog.storage import principal
        self.assertEqual(protectors.unwrap(document, protectors.DPAPI, "dummy-key", principal()), key)
        with self.assertRaises(Failure):
            protectors.unwrap(document, protectors.DPAPI, "another-key", principal())

    @unittest.skipUnless(os.name == "nt", "Windows security descriptor")
    def test_private_temp_dacl_is_protected_before_writing(self):
        import ctypes
        from ctypes import wintypes as W
        import tempfile
        from account_catalog.windows import advapi, _bind, free, private_temp
        with tempfile.TemporaryDirectory() as folder:
            fd, name = private_temp(folder)
            os.close(fd)
            descriptor = W.LPVOID()
            get = _bind(advapi, "GetNamedSecurityInfoW", W.DWORD, W.LPWSTR, W.DWORD, W.DWORD,
                        W.LPVOID, W.LPVOID, W.LPVOID, W.LPVOID, ctypes.POINTER(W.LPVOID))
            self.assertEqual(get(name, 1, 4, None, None, None, None, ctypes.byref(descriptor)), 0)
            control, revision = W.WORD(), W.DWORD()
            fn = _bind(advapi, "GetSecurityDescriptorControl", W.BOOL, W.LPVOID,
                       ctypes.POINTER(W.WORD), ctypes.POINTER(W.DWORD))
            try:
                self.assertTrue(fn(descriptor, ctypes.byref(control), ctypes.byref(revision)))
                self.assertTrue(control.value & 0x1000)
            finally:
                free(descriptor)
