import argparse
import contextlib
import os
from pathlib import Path
import secrets
import sys
import threading
import time

from . import adapters
from .broker import Broker
from .codec import Failure, canonical, fields
from .crypto import PORTABLE
from .protectors import DPAPI, SYSTEMD
from .storage import Store, check_path, deployment_roles, principal, read_json, unprivileged
from .transport import serve, send_management
from .vault import Vault


def deployment_check(broker):
    unprivileged()
    check_path(sys.executable, broker, secret=False)
    for entry in sys.path:
        if entry:
            check_path(entry, broker, secret=False)
        else:
            raise Failure("not_authorized")
    for module in tuple(sys.modules.values()):
        path = getattr(module, "__file__", None)
        if path and Path(path).exists():
            check_path(path, broker, secret=False)
    for path in Path(__file__).parent.glob("*.py"):
        check_path(path, broker, secret=False)


@contextlib.contextmanager
def instance(store):
    path = store.path("instance.lock")
    if path.exists():
        check_path(path, store.broker)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        if os.name == "nt":
            import msvcrt
            if os.fstat(fd).st_size == 0:
                os.write(fd, b"\0")
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    except OSError:
        raise Failure("unavailable") from None
    finally:
        os.close(fd)


def ui(broker, start):
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    window = tk.Tk()
    window.title("Account Broker — private management")
    frame = ttk.Frame(window, padding=16)
    frame.grid()
    text = tk.StringVar(value="locked")
    phrase = tk.StringVar()
    ttk.Label(frame, text="Unlock phrase").grid(row=0, column=0)
    ttk.Entry(frame, textvariable=phrase, show="*", width=42).grid(row=0, column=1)

    def perform(action):
        try:
            with broker.mutex:
                action()
            text.set("completed")
        except Failure as exc:
            text.set(exc.code)
        except Exception:
            text.set("unavailable")

    def initialize():
        destination = filedialog.asksaveasfilename(title="Separate recovery key", defaultextension=".json")
        if not destination:
            return
        generated = secrets.token_urlsafe(32)
        phrase.set(generated)
        perform(lambda: broker.vault.initialize(destination, generated, protector.get()))
        if text.get() == "completed":
            messagebox.showinfo("Unlock phrase", generated, parent=window)

    def unlock():
        perform(lambda: broker.unlock(phrase.get() or None))
        phrase.set("")
        if text.get() == "completed":
            perform(start)

    protector = tk.StringVar(value=PORTABLE)
    choices = [PORTABLE]
    if os.name == "nt":
        choices.append(DPAPI)
    if sys.platform == "linux" and os.environ.get("CREDENTIALS_DIRECTORY"):
        choices.append(SYSTEMD)
    ttk.Combobox(frame, textvariable=protector, values=choices, state="readonly", width=40).grid(row=1, column=1)
    buttons = ttk.Frame(frame)
    buttons.grid(row=2, columnspan=2)
    ttk.Button(buttons, text="Initialize", command=initialize).grid(row=0, column=0)
    ttk.Button(buttons, text="Unlock / start", command=unlock).grid(row=0, column=1)
    ttk.Button(buttons, text="Lock", command=lambda: perform(broker.lock)).grid(row=0, column=2)
    credential_id, username, password, passphrase = (tk.StringVar() for _ in range(4))
    for row, (label, variable, secret) in enumerate((
            ("Credential ID", credential_id, False), ("Login username", username, True),
            ("Password (Web)", password, True), ("Key passphrase (SSH)", passphrase, True)), start=3):
        ttk.Label(frame, text=label).grid(row=row, column=0)
        ttk.Entry(frame, textvariable=variable, show="*" if secret else "", width=42).grid(row=row, column=1)

    def save():
        def action():
            values = {"username": username.get()}
            if password.get():
                values["password"] = password.get()
            elif passphrase.get():
                values["passphrase"] = passphrase.get()
            broker.vault.save(credential_id.get(), values)
        perform(action)
        username.set("")
        password.set("")
        passphrase.set("")

    def register():
        source = filedialog.askopenfilename(title="Protected target binding JSON")
        if source:
            perform(lambda: broker.vault.register(read_json(check_path(source, broker.vault.store.broker))))

    def restore():
        source = filedialog.askdirectory(title="Private encrypted backup directory")
        old_recovery = filedialog.askopenfilename(title="Backup recovery key")
        new_recovery = filedialog.asksaveasfilename(title="New separate recovery key", defaultextension=".json")
        if not all((source, old_recovery, new_recovery)):
            return
        generated = secrets.token_urlsafe(32)
        phrase.set(generated)
        def action():
            broker.clear()
            broker.vault.restore(Store(source, broker.vault.store.broker), old_recovery, new_recovery,
                                 generated, protector.get())
        perform(action)
        if text.get() == "completed":
            messagebox.showinfo("New unlock phrase", generated, parent=window)

    ttk.Button(frame, text="Save credential", command=save).grid(row=7, column=0)
    ttk.Button(frame, text="Register target", command=register).grid(row=7, column=1)
    ttk.Button(frame, text="Restore / rotate", command=restore).grid(row=8, column=0)
    ttk.Label(frame, textvariable=text).grid(row=9, columnspan=2)
    def tick():
        if broker.unlock_deadline and time.monotonic() >= broker.unlock_deadline:
            perform(broker.lock)
            text.set("unlock_required")
        window.after(1000, tick)
    window.after(1000, tick)
    try:
        window.mainloop()
    finally:
        with broker.mutex:
            broker.lock()


class RemoteManager:
    def __init__(self, store, endpoint):
        self.store, self.endpoint = store, endpoint
        self.vault, self.mutex, self.unlock_deadline = self, threading.RLock(), 0

    def _call(self, action, **arguments):
        send_management(self.endpoint, {"schema_version": 1, "admin_action": action, "arguments": arguments})

    def initialize(self, recovery_path, phrase, protector):
        self._call("initialize", recovery_path=recovery_path, phrase=phrase, protector=protector)

    def unlock(self, phrase=None):
        self._call("unlock", phrase=phrase)

    def lock(self):
        self._call("lock")

    def save(self, credential_id, values):
        self._call("save", credential_id=credential_id, values=values)

    def register(self, target):
        self._call("register", target=target)

    def restore(self, source, recovery_path, new_recovery_path, phrase, protector):
        self._call("restore", source_root=str(source.root), recovery_path=recovery_path,
                   new_recovery_path=new_recovery_path, phrase=phrase, protector=protector)

    def clear(self):
        pass


def main(argv=None):
    parser = argparse.ArgumentParser(prog="account-broker")
    parser.add_argument("--root", required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--manage", action="store_true")
    args = parser.parse_args(argv)
    stop = threading.Event()
    worker = None
    try:
        owner = principal()
        deployment_check(owner)
        store = Store(args.root, owner)
        agents = deployment_roles(store)
        admin_endpoint = args.endpoint + "-admin" if os.name == "nt" else str(store.path("admin.sock"))
        if args.manage:
            ui(RemoteManager(store, admin_endpoint), lambda: None)
            return 0
        with instance(store):
            broker = Broker(Vault(store), agent_ids=agents)
            admin_worker = threading.Thread(target=lambda: serve(admin_endpoint, broker, stop, management=True), daemon=True)
            admin_worker.start()
            def start():
                nonlocal worker
                if worker is None or not worker.is_alive():
                    def run():
                        try:
                            serve(args.endpoint, broker, stop)
                        except Exception:
                            with broker.mutex:
                                broker.lock()
                    worker = threading.Thread(target=run, daemon=True)
                    worker.start()
            if args.headless:
                while admin_worker.is_alive():
                    if store.path("manifest.json").exists():
                        start()
                    with broker.mutex:
                        if broker.vault.locked():
                            broker.clear()
                            broker.vault.drop_key()
                    time.sleep(1)
            else:
                ui(broker, start)
            stop.set()
            broker.lock()
            if worker:
                worker.join(6)
            admin_worker.join(6)
        return 0
    except Failure as exc:
        sys.stderr.write(exc.code + "\n")
        return 2
    except (OSError, ValueError, RuntimeError):
        sys.stderr.write("unavailable\n")
        return 2
    finally:
        stop.set()


if __name__ == "__main__":
    raise SystemExit(main())
