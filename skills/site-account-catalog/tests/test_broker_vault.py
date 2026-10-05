import copy
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from account_catalog.broker import Broker
from account_catalog.codec import Failure, canonical, result
from account_catalog.crypto import PORTABLE
from account_catalog.storage import Store, atomic_json, read_json, roles
from account_catalog.transport import validate_response
from account_catalog.vault import Vault

PHRASE = "dummy-only-phrase-with-at-least-32-characters"
CANARY = "dummy-secret-never-in-output"


class FixtureStore(Store):
    """Unit fixture; no assertion about OS isolation."""
    def __init__(self, root, broker="broker"):
        self.root, self.broker = Path(root), broker
        self.root.mkdir(exist_ok=True)

    def read(self, *parts):
        return read_json(self.path(*parts))

    def write(self, parts, value, exclusive=False):
        atomic_json(self.path(*parts), value, exclusive)


def target():
    return {"target_id": "test-web", "credential_id": "credential", "provider": "https-basic-v1",
            "callers": ["agent", "other-agent"], "config": {"origin": "https://example.com",
            "login_path": "/private", "health_path": "/health", "expected_status": 200}}


class Session:
    def __init__(self):
        self.closed = False
    def login(self):
        pass
    def health(self):
        return True
    def close(self):
        self.closed = True


class VaultTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.boundary = patch("account_catalog.vault.check_path", side_effect=lambda path, *a, **k: Path(path))
        self.boundary.start()
        self.addCleanup(self.boundary.stop)
        self.store = FixtureStore(self.root / "vault")
        self.vault = Vault(self.store)
        self.recovery = self.root / "offline.json"
        self.vault.initialize(self.recovery, PHRASE)
        self.vault.unlock(PHRASE)
        self.vault.save("credential", {"username": CANARY, "password": CANARY})
        self.vault.register(target())

    def test_atomic_replace_failure_keeps_old_document(self):
        path = self.root / "atomic.json"
        atomic_json(path, {"value": 1})
        with patch("account_catalog.storage.os.replace", side_effect=OSError("dummy fault")), self.assertRaises(OSError):
            atomic_json(path, {"value": 2})
        self.assertEqual(read_json(path), {"value": 1})

    def test_restore_without_old_wrapper_rotates_and_requires_registration(self):
        meta = self.vault.metadata()
        self.store.path(meta["generation"], "key.json").unlink()
        destination = Vault(FixtureStore(self.root / "destination"))
        destination.restore(self.store, self.recovery, self.root / "new-offline.json", PHRASE)
        new_meta = destination.metadata()
        self.assertNotEqual(new_meta["key_id"], meta["key_id"])
        self.assertEqual(new_meta["bindings"], [])
        self.assertTrue(destination.locked())
        destination.unlock(PHRASE)
        self.assertEqual(destination.values(new_meta, "credential")["password"], CANARY)

    def test_rotation_failure_never_switches_manifest(self):
        before = self.vault.metadata()
        with patch.object(self.vault, "_stage", side_effect=Failure()), self.assertRaises(Failure):
            self.vault.restore(self.store, self.recovery, self.root / "rotate-offline.json", PHRASE)
        self.assertEqual(self.vault.metadata(), before)
        self.assertEqual(self.vault.values(before, "credential")["password"], CANARY)

    def test_persistent_lock_corrupt_state_and_expiry(self):
        self.vault.lock()
        self.assertTrue(Vault(self.store).locked())
        self.vault.unlock(PHRASE)
        self.assertFalse(self.vault.locked())
        self.store.write(("state.json",), {"schema_version": 1, "locked": False, "unlock_until": time.time() - 1})
        self.assertTrue(self.vault.locked())
        self.store.write(("state.json",), {"locked": False})
        self.assertTrue(self.vault.locked())

    def test_recovery_cannot_overwrite_existing_key(self):
        before = self.recovery.read_bytes()
        with self.assertRaises(FileExistsError):
            self.vault.restore(self.store, self.recovery, self.recovery, PHRASE)
        self.assertEqual(self.recovery.read_bytes(), before)

    def test_broker_no_raw_secret_and_session_bindings(self):
        sessions = []
        def factory(config, values, owner):
            self.assertEqual(values["password"], CANARY)
            session = Session()
            sessions.append(session)
            return session
        broker = Broker(self.vault, factory=factory, agent_ids={"agent", "other-agent"})
        broker.unlock(PHRASE)
        request = {"schema_version": 1, "target_id": "test-web", "action_id": "sign_in"}
        self.assertEqual(broker.execute(request, "agent"), result("test-web"))
        self.assertNotIn(CANARY.encode(), canonical(broker.execute({**request, "action_id": "health-check"}, "agent")))
        self.assertEqual(len(sessions), 1)
        broker.execute({**request, "action_id": "health-check"}, "other-agent")
        self.assertEqual(len(sessions), 2)
        self.assertEqual(broker.execute(request, "intruder")["error_code"], "not_authorized")
        self.assertEqual(broker.execute({**request, "action_id": "shell"}, "agent")["error_code"], "not_authorized")
        self.assertEqual(broker.execute({**request, "url": CANARY}, "agent")["error_code"], "invalid_record")
        broker.lock()
        self.assertTrue(all(session.closed for session in sessions))
        self.assertEqual(broker.execute(request, "agent")["status"], "needs_user")

    def test_external_exception_is_fixed_code(self):
        def factory(*args):
            raise RuntimeError(CANARY)
        broker = Broker(self.vault, factory=factory, agent_ids={"agent", "other-agent"})
        broker.unlock(PHRASE)
        response = broker.execute({"schema_version": 1, "target_id": "test-web", "action_id": "sign_in"}, "agent")
        self.assertEqual(response["error_code"], "unavailable")
        self.assertNotIn(CANARY.encode(), canonical(response))

    def test_admin_actions_are_not_execution_api_and_reject_agent(self):
        broker = Broker(self.vault, agent_ids={"agent", "other-agent"})
        request = {"schema_version": 1, "admin_action": "unlock", "arguments": {"phrase": PHRASE}}
        self.assertEqual(broker.manage(request, "agent")["error_code"], "not_authorized")
        self.assertEqual(broker.manage(request, "broker")["status"], "completed")
        self.assertEqual(broker.execute(request, "agent")["error_code"], "invalid_record")

    def test_client_rejects_forged_result_fields(self):
        with self.assertRaises(Failure):
            validate_response({**result("test-web"), "password": CANARY}, "test-web")
        with self.assertRaises(Failure):
            validate_response({**result("test-web"), "error_code": CANARY}, "test-web")

    def test_same_identity_and_missing_role_binding_are_rejected(self):
        for agents in (None, {"broker"}, set()):
            with self.assertRaises(Failure):
                Broker(self.vault, agent_ids=agents)
        for agents in (["broker"], [], ["0"], ["agent", "agent"]):
            with self.assertRaises(Failure):
                roles({"schema_version": 1, "broker_id": "broker", "agent_ids": agents}, "broker")

    def test_native_provider_restart_requires_explicit_unlock(self):
        from account_catalog.protectors import DPAPI
        import os
        if os.name != "nt":
            self.skipTest("Windows DPAPI")
        native = Vault(FixtureStore(self.root / "native"))
        native.initialize(self.root / "native-offline.json", None, DPAPI)
        native.unlock()
        native.save("credential", {"username": CANARY, "password": CANARY})
        native.register(target())
        restarted = Broker(Vault(native.store), factory=lambda *a: Session(), agent_ids={"agent"})
        request = {"schema_version": 1, "target_id": "test-web", "action_id": "sign_in"}
        self.assertEqual(restarted.execute(request, "agent")["error_code"], "unlock_required")
        restarted.unlock()
        self.assertEqual(restarted.execute(request, "agent")["status"], "authenticated")
