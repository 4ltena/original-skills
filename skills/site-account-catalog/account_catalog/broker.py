import time
import threading

from . import adapters
from .codec import Failure, canonical, fields, identifier, result, version


class Broker:
    def __init__(self, vault, factory=adapters.create, clock=time.monotonic, agent_ids=None):
        self.vault, self.factory, self.clock = vault, factory, clock
        self.sessions = {}
        self.unlock_deadline = 0
        self.mutex = threading.RLock()
        self.agent_ids = frozenset(agent_ids or ())
        if not self.agent_ids or self.vault.store.broker in self.agent_ids:
            raise Failure("not_authorized")
        self.vault.lock()

    def clear(self):
        for session, _, _ in self.sessions.values():
            try:
                session.close()
            except Exception:
                pass
        self.sessions.clear()

    def unlock(self, phrase=None):
        self.clear()
        self.vault.unlock(phrase)
        self.unlock_deadline = self.clock() + 900

    def lock(self):
        self.vault.lock()
        self.clear()
        self.unlock_deadline = 0

    def manage(self, request, caller):
        try:
            if caller != self.vault.store.broker:
                raise Failure("not_authorized")
            fields(request, ("schema_version", "admin_action", "arguments"))
            version(request)
            action, args = request["admin_action"], request["arguments"]
            shapes = {"unlock": (("phrase",), self.unlock), "lock": ((), self.lock),
                      "initialize": (("recovery_path", "phrase", "protector"), self.vault.initialize),
                      "save": (("credential_id", "values"), self.vault.save),
                      "register": (("target",), self.vault.register)}
            with self.mutex:
                if action == "restore":
                    fields(args, ("source_root", "recovery_path", "new_recovery_path", "phrase", "protector"))
                    from .storage import Store
                    self.clear()
                    self.vault.restore(Store(args["source_root"], self.vault.store.broker), args["recovery_path"],
                                       args["new_recovery_path"], args["phrase"], args["protector"])
                else:
                    if action not in shapes:
                        raise Failure("not_authorized")
                    required, method = shapes[action]
                    fields(args, required)
                    if action == "register" and not set(args["target"]["callers"]) <= self.agent_ids:
                        raise Failure("not_authorized")
                    method(**args)
            return {"schema_version": 1, "status": "completed"}
        except Failure as exc:
            return {"schema_version": 1, "status": "failed", "error_code": exc.code}
        except Exception:
            return {"schema_version": 1, "status": "failed", "error_code": "unavailable"}

    def execute(self, request, caller):
        with self.mutex:
            return self._execute(request, caller)

    def _execute(self, request, caller):
        target, session = "invalid", None
        try:
            fields(request, ("schema_version", "target_id", "action_id"))
            version(request)
            target = identifier(request["target_id"])
            action = request["action_id"]
            if action not in {"sign_in", "health-check"}:
                raise Failure("not_authorized")
            meta = self.vault.metadata()
            targets = [row for row in meta["bindings"] if row["target_id"] == target]
            if not targets:
                raise Failure("not_found")
            config = targets[0]
            if (caller == self.vault.store.broker or caller not in config["callers"]
                    or (self.agent_ids and caller not in self.agent_ids)):
                raise Failure("not_authorized")
            if self.vault.locked():
                self.clear()
                self.vault.drop_key()
                raise Failure("unlock_required")
            from .crypto import PORTABLE
            if meta["protector"] == PORTABLE and self.clock() >= self.unlock_deadline:
                self.lock()
                raise Failure("unlock_required")
            fingerprint = canonical(meta)
            identity = (caller, target)
            existing = self.sessions.pop(identity, None)
            if existing:
                session, expiry, snapshot = existing
                if self.clock() >= expiry or snapshot != fingerprint or action == "sign_in":
                    session.close()
                    existing = None
            if existing is None:
                values = self.vault.values(meta, config["credential_id"])
                session = self.factory(config, values, self.vault.store.broker)
                try:
                    session.login()
                except Exception:
                    session.close()
                    raise
                expiry = self.clock() + 300
            healthy = session.health() if action == "health-check" else None
            if self.vault.locked() or canonical(self.vault.metadata()) != fingerprint:
                session.close()
                raise Failure("unlock_required")
            self.sessions[identity] = (session, expiry, fingerprint)
            return result(target, healthy=healthy)
        except Failure as exc:
            if session is not None:
                try:
                    session.close()
                except Exception:
                    pass
            return result(target, "needs_user" if exc.code == "unlock_required" else "failed", exc.code)
        except Exception:
            if session is not None:
                try:
                    session.close()
                except Exception:
                    pass
            return result(target, "failed", "unavailable")
