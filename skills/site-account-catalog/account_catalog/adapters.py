import base64
import http.client
import io
import logging
import socket
import time
from urllib.parse import urlsplit

import paramiko

from .codec import Failure, fields, identifier
from .storage import check_path


def binding(record):
    fields(record, ("target_id", "credential_id", "provider", "callers", "config"))
    identifier(record["target_id"])
    identifier(record["credential_id"])
    if (not isinstance(record["callers"], list) or not record["callers"]
            or len(set(record["callers"])) != len(record["callers"])
            or any(not isinstance(item, str) or len(item) > 256 for item in record["callers"])):
        raise Failure()
    config = record["config"]
    if record["provider"] == "https-basic-v1":
        fields(config, ("origin", "login_path", "health_path", "expected_status"))
        parsed = urlsplit(config["origin"])
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.path or parsed.query or parsed.fragment or "\\" in config["origin"]):
            raise Failure()
        try:
            port = parsed.port
        except ValueError:
            raise Failure() from None
        if port is not None and not 1 <= port <= 65535:
            raise Failure()
        for name in ("login_path", "health_path"):
            path = config[name]
            if (not isinstance(path, str) or not path.startswith("/") or path.startswith("//")
                    or len(path) > 2048 or any(ord(c) < 32 or ord(c) > 126 for c in path) or "\\" in path):
                raise Failure()
        if type(config["expected_status"]) is not int or not 200 <= config["expected_status"] <= 299:
            raise Failure()
    elif record["provider"] == "ssh-key-v1":
        fields(config, ("host", "port", "private_key_path", "host_key_type", "host_key_b64", "health_command"))
        if (not isinstance(config["host"], str) or not 1 <= len(config["host"]) <= 253
                or any(c.isspace() or c in "/\\\x00" for c in config["host"])):
            raise Failure()
        if type(config["port"]) is not int or not 1 <= config["port"] <= 65535:
            raise Failure()
        if not isinstance(config["health_command"], str) or not 1 <= len(config["health_command"]) <= 2048:
            raise Failure()
        if any(c in config["health_command"] for c in "\x00\r\n"):
            raise Failure()
        if config["host_key_type"] not in {"ssh-ed25519", "ecdsa-sha2-nistp256", "ssh-rsa"}:
            raise Failure()
        from .codec import decode
        decode(config["host_key_b64"], maximum=4096)
    else:
        raise Failure("unavailable")
    return record


class HTTPSBasic:
    def __init__(self, config, credentials, broker):
        self.config, self.credentials = config, credentials
        fields(credentials, ("username", "password"))
        if ":" in credentials["username"] or any(c in credentials["username"] + credentials["password"] for c in "\r\n\x00"):
            raise Failure()

    def request(self, path):
        origin = urlsplit(self.config["origin"])
        connection = http.client.HTTPSConnection(origin.hostname, origin.port or 443, timeout=10)
        authorization = base64.b64encode((self.credentials["username"] + ":" + self.credentials["password"]).encode("utf-8"))
        try:
            connection.request("GET", path, headers={"Authorization": "Basic " + authorization.decode("ascii")})
            response = connection.getresponse()
            status = response.status
            response.close()
            if status != self.config["expected_status"]:
                raise Failure("authentication_failed")
            return True
        except (socket.timeout, TimeoutError):
            raise Failure("timeout") from None
        except (OSError, http.client.HTTPException):
            raise Failure("unavailable") from None
        finally:
            connection.close()

    def login(self):
        self.request(self.config["login_path"])

    def health(self):
        return self.request(self.config["health_path"])

    def close(self):
        self.credentials = {}


class SSHKey:
    def __init__(self, config, credentials, broker):
        self.config, self.credentials, self.broker = config, credentials, broker
        fields(credentials, ("username",), ("passphrase",))
        self.client = None

    def login(self):
        path = check_path(self.config["private_key_path"], self.broker)
        with path.open("rb") as file:
            data = file.read(65537)
        if len(data) > 65536:
            raise Failure()
        private = None
        for cls in (paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.RSAKey):
            try:
                private = cls.from_private_key(io.StringIO(data.decode("utf-8")), password=self.credentials.get("passphrase"))
                break
            except (ValueError, UnicodeError, paramiko.SSHException):
                pass
        if private is None:
            raise Failure("authentication_failed")
        from .codec import decode
        cls = {"ssh-ed25519": paramiko.Ed25519Key, "ecdsa-sha2-nistp256": paramiko.ECDSAKey,
               "ssh-rsa": paramiko.RSAKey}[self.config["host_key_type"]]
        hostkey = cls(data=decode(self.config["host_key_b64"], maximum=4096))
        client = paramiko.SSHClient()
        client.set_log_channel("account_catalog.private_ssh")
        logging.getLogger("account_catalog.private_ssh").disabled = True
        host = self.config["host"]
        host_name = host if self.config["port"] == 22 else f"[{host}]:{self.config['port']}"
        client.get_host_keys().add(host_name, hostkey.get_name(), hostkey)
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        try:
            client.connect(host, port=self.config["port"], username=self.credentials["username"], pkey=private,
                           look_for_keys=False, allow_agent=False, timeout=10, auth_timeout=10, banner_timeout=10)
        except paramiko.BadHostKeyException:
            client.close()
            raise Failure("host_key_mismatch") from None
        except paramiko.AuthenticationException:
            client.close()
            raise Failure("authentication_failed") from None
        except (OSError, paramiko.SSHException):
            client.close()
            raise Failure("unavailable") from None
        self.client = client

    def health(self):
        if self.client is None:
            raise Failure("authentication_failed")
        channel = self.client.get_transport().open_session(timeout=10)
        channel.settimeout(10)
        try:
            channel.exec_command(self.config["health_command"])
            deadline, count = time.monotonic() + 10, 0
            while True:
                if channel.recv_ready():
                    count += len(channel.recv(4096))
                if channel.recv_stderr_ready():
                    count += len(channel.recv_stderr(4096))
                if count > 65536:
                    raise Failure("unavailable")
                if channel.exit_status_ready() and not channel.recv_ready() and not channel.recv_stderr_ready():
                    return channel.recv_exit_status() == 0
                if time.monotonic() >= deadline:
                    raise Failure("timeout")
                time.sleep(0.01)
        finally:
            channel.close()

    def close(self):
        if self.client is not None:
            self.client.close()
        self.client, self.credentials = None, {}


def create(record, credentials, broker):
    return {"https-basic-v1": HTTPSBasic, "ssh-key-v1": SSHKey}[record["provider"]](record["config"], credentials, broker)
