import json
from pathlib import Path
import tempfile
import unittest

from account_catalog.catalog import Catalog
from account_catalog.codec import Failure


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.catalog = Catalog(self.root)
        self.put("entries", "github", {"schema_version": 1, "id": "github", "service": "GitHub",
                 "domains": ["github.com"], "accounts": [{"id": "example", "username": "github",
                 "profile_url": "https://github.com/github"}], "license_notations": []})

    def put(self, kind, name, value):
        folder = self.root / kind
        folder.mkdir(exist_ok=True)
        (folder / (name + ".json")).write_text(json.dumps(value), encoding="utf-8")

    def test_exact_field_does_not_use_username_or_url_as_display_name(self):
        self.assertEqual(self.catalog.identity("example", "display_name", "github"),
                         {"status": "needs_user", "missing": ["display_name"]})
        self.assertEqual(self.catalog.identity("example", "username", "github")["value"], "github")
        self.assertEqual(self.catalog.identity("missing", "username", "github")["status"], "needs_user")

    def test_exact_domain_and_ambiguity(self):
        self.assertEqual(self.catalog.find("github.com")["status"], "found")
        self.assertEqual(self.catalog.find("github.co")["matches"], [])
        self.put("targets", "second", {"schema_version": 2, "id": "second", "service": "GitHub"})
        self.assertEqual(self.catalog.find("GitHub")["status"], "needs_user")

    def test_secret_field_and_duplicate_json_are_rejected(self):
        self.put("identities", "user", {"schema_version": 2, "id": "user", "username": "public", "password": "dummy"})
        with self.assertRaises(Failure):
            self.catalog.identity("user", "username")
        path = self.root / "entries" / "github.json"
        path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
        with self.assertRaises(Failure):
            self.catalog.legacy("github")

    def test_v2_unknown_secret_fields_are_not_printable(self):
        for field in ("client_secret", "authorization", "unrecognized_extension"):
            self.put("targets", "web", {"schema_version": 2, "id": "web", field: "dummy-canary"})
            with self.subTest(field=field), self.assertRaises(Failure):
                self.catalog.read("targets", "web")

    def test_three_license_kinds_and_missing_identity(self):
        self.put("licenses", "mit", {"schema_version": 2, "id": "mit", "name": "MIT", "spdx_expression": "MIT"})
        self.put("notations", "project", {"schema_version": 2, "id": "project", "wording": "Recorded wording"})
        self.put("entitlements", "product", {"schema_version": 2, "id": "product", "product": "Example"})
        self.assertEqual(self.catalog.read("licenses", "mit")["spdx_expression"], "MIT")
        self.assertEqual(self.catalog.notation("project")["value"], "Recorded wording")
        self.assertEqual(self.catalog.read("entitlements", "product")["product"], "Example")
        self.put("identities", "holder", {"schema_version": 2, "id": "holder", "username": "github"})
        self.put("notations", "project", {"schema_version": 2, "id": "project", "wording": "Recorded wording",
                 "rights_holder_id": "holder"})
        self.assertEqual(self.catalog.notation("project")["status"], "needs_user")
