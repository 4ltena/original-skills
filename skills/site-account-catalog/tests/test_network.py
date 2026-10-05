import base64
import datetime
import ipaddress
from pathlib import Path
import socket
import ssl
import tempfile
import threading
import unittest
from unittest.mock import patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import http.server
import paramiko

from account_catalog.adapters import HTTPSBasic, SSHKey
from account_catalog.codec import Failure

CANARY = "dummy-network-secret-canary"


class NetworkTests(unittest.TestCase):
    def test_real_local_tls_auth_and_reject_redirect(self):
        expected = "Basic " + base64.b64encode((CANARY + ":" + CANARY).encode()).decode()
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.headers.get("Authorization") != expected:
                    status = 401
                else:
                    status = 302 if self.path == "/redirect" else 200
                self.send_response(status)
                self.send_header("Location", "https://example.com/" + CANARY)
                self.end_headers()
                self.wfile.write(CANARY.encode())
            def log_message(self, *args):
                pass
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "dummy-loopback")])
            now = datetime.datetime.now(datetime.timezone.utc)
            cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
                    .serial_number(x509.random_serial_number()).not_valid_before(now - datetime.timedelta(minutes=1))
                    .not_valid_after(now + datetime.timedelta(hours=1))
                    .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), False)
                    .sign(key, hashes.SHA256()))
            (root / "key.pem").write_bytes(key.private_bytes(serialization.Encoding.PEM,
                     serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
            (root / "cert.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(root / "cert.pem", root / "key.pem")
            server.socket = context.wrap_socket(server.socket, server_side=True)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                config = {"origin": f"https://127.0.0.1:{server.server_address[1]}", "login_path": "/private",
                          "health_path": "/health", "expected_status": 200}
                trusted = ssl.create_default_context(cafile=str(root / "cert.pem"))
                with patch("ssl._create_default_https_context", return_value=trusted):
                    adapter = HTTPSBasic(config, {"username": CANARY, "password": CANARY}, "broker")
                    adapter.login()
                    self.assertTrue(adapter.health())
                    adapter.config = {**config, "login_path": "/redirect"}
                    with self.assertRaises(Failure) as failure:
                        adapter.login()
                    self.assertEqual(str(failure.exception), "authentication_failed")
                    adapter.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(2)

    def ssh_server(self, hostkey, userkey):
        class Server(paramiko.ServerInterface):
            def check_auth_publickey(self, username, key):
                return paramiko.AUTH_SUCCESSFUL if username == CANARY and key == userkey else paramiko.AUTH_FAILED
            def get_allowed_auths(self, username):
                return "publickey"
            def check_channel_request(self, kind, channel_id):
                return paramiko.OPEN_SUCCEEDED if kind == "session" else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
            def check_channel_exec_request(self, channel, command):
                def respond():
                    channel.send(CANARY.encode())
                    channel.send_stderr(CANARY.encode())
                    channel.send_exit_status(0 if command == b"true" else 1)
                    channel.close()
                threading.Thread(target=respond, daemon=True).start()
                return True
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(5)
        finished = threading.Event()
        def run():
            transport = None
            try:
                stream, _ = listener.accept()
                transport = paramiko.Transport(stream)
                transport.set_log_channel("account_catalog.test_server")
                import logging
                logging.getLogger("account_catalog.test_server").disabled = True
                transport.add_server_key(hostkey)
                transport.start_server(server=Server())
                finished.wait(10)
            except (OSError, paramiko.SSHException):
                pass
            finally:
                if transport:
                    transport.close()
                listener.close()
        worker = threading.Thread(target=run, daemon=True)
        worker.start()
        return listener.getsockname()[1], finished, worker

    def test_real_local_ssh_key_pin_and_fixed_health(self):
        with tempfile.TemporaryDirectory() as folder:
            hostkey, userkey = paramiko.RSAKey.generate(2048), paramiko.RSAKey.generate(2048)
            key_path = Path(folder) / "dummy-key"
            userkey.write_private_key_file(str(key_path))
            port, finished, worker = self.ssh_server(hostkey, userkey)
            config = {"host": "127.0.0.1", "port": port, "private_key_path": str(key_path),
                      "host_key_type": "ssh-rsa", "host_key_b64": hostkey.get_base64(), "health_command": "true"}
            adapter = SSHKey(config, {"username": CANARY}, "broker")
            try:
                with patch("account_catalog.adapters.check_path", return_value=key_path):
                    adapter.login()
                self.assertTrue(adapter.health())
            finally:
                adapter.close()
                finished.set()
                worker.join(3)

    def test_real_local_ssh_mismatched_host_key(self):
        with tempfile.TemporaryDirectory() as folder:
            hostkey, userkey, wrongkey = (paramiko.RSAKey.generate(2048) for _ in range(3))
            key_path = Path(folder) / "dummy-key"
            userkey.write_private_key_file(str(key_path))
            port, finished, worker = self.ssh_server(hostkey, userkey)
            config = {"host": "127.0.0.1", "port": port, "private_key_path": str(key_path),
                      "host_key_type": "ssh-rsa", "host_key_b64": wrongkey.get_base64(), "health_command": "true"}
            adapter = SSHKey(config, {"username": CANARY}, "broker")
            try:
                with patch("account_catalog.adapters.check_path", return_value=key_path), self.assertRaises(Failure) as failure:
                    adapter.login()
                self.assertEqual(str(failure.exception), "host_key_mismatch")
            finally:
                adapter.close()
                finished.set()
                worker.join(3)
