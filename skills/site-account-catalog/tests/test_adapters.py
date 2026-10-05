import unittest
from unittest.mock import patch

from account_catalog.adapters import HTTPSBasic, binding
from account_catalog.codec import Failure


class AdapterTests(unittest.TestCase):
    def config(self):
        return {"target_id": "web", "credential_id": "credential", "provider": "https-basic-v1",
                "callers": ["agent"], "config": {"origin": "https://example.com", "login_path": "/login",
                "health_path": "/health", "expected_status": 200}}

    def test_redirect_is_not_followed(self):
        adapter = HTTPSBasic(self.config()["config"], {"username": "dummy", "password": "dummy"}, "broker")
        with patch("account_catalog.adapters.http.client.HTTPSConnection") as connection:
            connection.return_value.getresponse.return_value.status = 302
            with self.assertRaises(Failure):
                adapter.login()
            self.assertEqual(connection.return_value.request.call_count, 1)
            connection.return_value.getresponse.return_value.read.assert_not_called()

    def test_unsafe_origin_and_path(self):
        for field, value in (("origin", "http://example.com"), ("origin", "https://user:pass@example.com"),
                             ("origin", "https://example.com/elsewhere"), ("login_path", "//evil.example"),
                             ("login_path", "/login\r\nHeader: injected")):
            config = self.config()
            config["config"][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(Failure):
                binding(config)
