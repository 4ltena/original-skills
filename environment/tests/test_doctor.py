import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch


sys.dont_write_bytecode = True
ENV = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENV))
import doctor
import install


def answers(host="claude", **override):
    value = {"host": host, "scope": "user", "skills": "basic", "plugins": [],
             "git_mode": "manual-git", "settings": "candidates"}
    if host != "codex":
        value["surface"] = "cli"
    return {**value, **override}


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name).resolve()

    def tearDown(self):
        self.temp.cleanup()

    def diagnose(self, host="claude", **override):
        return doctor.run(SimpleNamespace(host=host, home=str(self.home), project=None,
                                           plan=None, answers=None, probe_python=None,
                                           **override))

    def install(self, value):
        result = install.plan(value, self.home)
        install.apply(result, result["plan_id"])
        return self.home / (".claude" if value["host"] == "claude" else ".codex")

    def test_default_diagnosis_is_read_only_and_legacy_install_is_unknown(self):
        legacy = self.home / ".claude/skills/workflow"
        legacy.mkdir(parents=True)
        (legacy / "SKILL.md").write_text("legacy", encoding="utf-8")
        before = sorted(str(path.relative_to(self.home)) for path in self.home.rglob("*"))
        with patch.object(doctor.subprocess, "run", side_effect=AssertionError("default must not execute")):
            report = self.diagnose()
        after = sorted(str(path.relative_to(self.home)) for path in self.home.rglob("*"))
        host = report["hosts"][0]
        self.assertEqual(before, after)
        self.assertTrue(report["read_only"])
        self.assertEqual(host["receipt"]["status"], "missing")
        self.assertEqual(host["source"]["status"], "unknown")
        self.assertEqual(host["trust"]["status"], "unknown")
        self.assertEqual(host["runtime"]["status"], "unknown")

    def test_receipt_exact_source_and_projection_drift(self):
        root = self.install(answers())
        exact = self.diagnose()["hosts"][0]
        self.assertEqual(exact["receipt"]["status"], "current")
        self.assertEqual(exact["source"]["status"], "current")
        self.assertGreater(exact["projection"]["current"], 0)

        runtime = root / "original-skills/runtime.py"
        runtime.write_text(runtime.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
        changed = self.diagnose()["hosts"][0]
        self.assertGreater(changed["projection"]["drift"], 0)
        self.assertIn("installed_projection_changed", [item["code"] for item in changed["findings"]])

    def test_custom_preserved_and_missing_or_changed_binding_are_distinguished(self):
        custom = self.home / ".claude/skills/code-inspection"
        custom.mkdir(parents=True)
        (custom / "SKILL.md").write_text("personal", encoding="utf-8")
        root = self.install(answers(skills="custom", skill_names=["code-inspection"]))
        report = self.diagnose()["hosts"][0]
        self.assertEqual(report["skills"], [{"name": "code-inspection", "state": "custom_preserved"}])

        binding = root / "original-skills/binding.json"
        value = json.loads(binding.read_text(encoding="utf-8"))
        value["version"] = [9, 9, 9]
        binding.write_text(json.dumps(value), encoding="utf-8")
        self.assertEqual(self.diagnose()["hosts"][0]["python"]["status"], "unrecorded")
        binding.unlink()
        self.assertEqual(self.diagnose()["hosts"][0]["python"]["status"], "missing")

    def test_hook_summary_catalog_duplicates_and_claude_chat_capability(self):
        summary = install.hook_summary({"hooks": {
            "Stop": [{"hooks": [{"command": "/old/original-skills/hook.py", "args": []},
                                  {"command": "/old/original-skills/hook.py", "args": []}]}],
            "SessionEnd": [{"hooks": [{"command": "/unrelated/tool", "args": []}]}],
        }}, Path("/current/original-skills"))
        self.assertEqual(summary["stale"], 2)
        self.assertEqual(summary["duplicates"], 1)
        self.assertEqual(summary["other"], 1)

        legacy = self.home / ".claude/skills/frontend-design"
        legacy.mkdir(parents=True)
        (legacy / "SKILL.md").write_text("---\nname: frontend-design\n---\nlegacy", encoding="utf-8")
        alternate = self.home / ".agents/skills/alternate"
        alternate.mkdir(parents=True)
        (alternate / "SKILL.md").write_text("---\nname: frontend-design\n---\nother", encoding="utf-8")
        (self.home / ".agents/skills/empty").mkdir()
        root = self.install(answers(surface="chat"))
        report = self.diagnose()["hosts"][0]
        self.assertFalse(report["hooks"]["declared_eligible"])
        self.assertEqual(report["hooks"]["support"], "unknown")
        self.assertEqual(report["catalog"]["scope"], "known_roots_only")
        self.assertEqual(report["catalog"]["duplicates"], [{"name": "frontend-design", "roots": [
            str(self.home / ".claude/skills"), str(self.home / ".agents/skills")]}])
        self.assertGreaterEqual(report["catalog"]["skipped"], 1)
        self.assertEqual(root.name, ".claude")

    def test_live_hook_removal_is_not_hidden_by_the_receipt(self):
        root = self.install(answers(host="codex", plugins=["goal-checkpoint"], checkpoint="enabled",
                                    settings="apply-selected"))
        hooks = root / "hooks.json"
        hooks.unlink()
        report = self.diagnose(host="codex")["hosts"][0]["hooks"]
        self.assertEqual(report["installed"]["receipt"]["status"], "declared")
        self.assertEqual(report["installed"]["current"]["status"], "missing")

    def test_malformed_receipt_and_plugin_binding_are_bounded(self):
        root = self.install(answers(host="codex", plugins=["goal-checkpoint"], checkpoint="enabled"))
        baseline = self.diagnose(host="codex")["hosts"][0]
        self.assertEqual(baseline["plugin_bindings"], [{"name": "goal-checkpoint", "status": "recorded_current"}])
        binding = root / "original-skills/goal-checkpoint/binding.json"
        value = json.loads(binding.read_text(encoding="utf-8"))
        value["runtime"] = "claude"
        binding.write_text(json.dumps(value), encoding="utf-8")
        self.assertEqual(self.diagnose(host="codex")["hosts"][0]["plugin_bindings"][0]["status"], "drift")

        receipt = root / "original-skills/install-receipt.json"
        original = json.loads(receipt.read_text(encoding="utf-8"))
        corrupt = copy.deepcopy(original)
        corrupt["projection"]["preserved"] = [123]
        receipt.write_text(json.dumps(corrupt), encoding="utf-8")
        self.assertEqual(self.diagnose(host="codex")["hosts"][0]["receipt"]["status"], "invalid_receipt")

        corrupt = copy.deepcopy(original)
        corrupt["hooks"] = {"candidate": {"status": "declared", "current": 0, "stale": 0, "other": 0,
                                              "duplicates": 0, "events": {"Stop": {"token": "secret"}}},
                            "installed": {"status": "not_requested"}}
        receipt.write_text(json.dumps(corrupt), encoding="utf-8")
        report = self.diagnose(host="codex")["hosts"][0]
        self.assertEqual(report["receipt"]["status"], "invalid_receipt")
        self.assertEqual(report["plugin_bindings"], [])
        self.assertNotIn("secret", json.dumps(report))

    def test_unapproved_receipt_paths_are_rejected_without_hashing_them(self):
        root = self.install(answers())
        receipt_path = root / "original-skills/install-receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["source"]["files"].append({"path": ".git/config", "sha256": "0" * 64, "size": 1})
        receipt["projection"]["files"].append({"path": "auth.json", "sha256": "0" * 64, "size": 1})
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        with patch.object(doctor, "hash_artifact", side_effect=AssertionError("unapproved path read")):
            report = self.diagnose()["hosts"][0]
        self.assertEqual(report["receipt"]["status"], "invalid_receipt")

    def test_source_identity_and_surface_tampering_are_safe(self):
        root = self.install(answers())
        receipt_path = root / "original-skills/install-receipt.json"
        original = json.loads(receipt_path.read_text(encoding="utf-8"))

        altered = copy.deepcopy(original)
        altered["source"]["root"] = "/tmp/token=SECRET"
        receipt_path.write_text(json.dumps(altered), encoding="utf-8")
        report = self.diagnose()["hosts"][0]["source"]
        self.assertEqual(report["status"], "recorded_only")
        self.assertIsNone(report["identity"])
        self.assertNotIn("SECRET", json.dumps(report))

        altered = copy.deepcopy(original)
        altered["source"]["sha256"] = "not-a-hash"
        receipt_path.write_text(json.dumps(altered), encoding="utf-8")
        self.assertEqual(self.diagnose()["hosts"][0]["receipt"]["status"], "invalid_receipt")

        for surface in ("unrecognized", [], {}):
            with self.subTest(surface=surface):
                altered = copy.deepcopy(original)
                altered["selection"]["surface"] = surface
                receipt_path.write_text(json.dumps(altered), encoding="utf-8")
                self.assertEqual(self.diagnose()["hosts"][0]["receipt"]["status"], "invalid_receipt")

    def test_corrupt_telemetry_and_synthetic_windows_binding_do_not_claim_runtime(self):
        root = self.install(answers())
        telemetry = root / "original-skills-data/goal-checkpoint/goal-checkpoint/hook-observations.json"
        telemetry.parent.mkdir(parents=True)
        telemetry.write_text('{"version":1,"observations":[]}', encoding="utf-8")
        self.assertEqual(self.diagnose()["hosts"][0]["checkpoint"]["receipt"]["status"], "valid_unverified_origin")
        telemetry.write_text('{"token":"must not appear"}', encoding="utf-8")
        receipt_path = root / "original-skills/install-receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        synthetic = {"executable": "/synthetic/python.exe", "version": [3, 11, 0], "platform": "win32"}
        (root / "original-skills/binding.json").write_text(json.dumps(synthetic), encoding="utf-8")
        receipt["binding"] = copy.deepcopy(synthetic)
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

        report = self.diagnose()["hosts"][0]
        rendered = json.dumps(report)
        self.assertEqual(report["python"]["platform"], "win32")
        self.assertFalse(report["python"]["present"])
        mismatch = {"status": "verified", "executable": "/synthetic/python.exe", "version": [3, 11, 0], "platform": "darwin"}
        self.assertFalse(doctor.binding_status(root, "claude", receipt, mismatch)["probe_matches_binding"])
        self.assertEqual(report["checkpoint"]["receipt"]["status"], "malformed")
        self.assertEqual(report["checkpoint"]["trust"], "unknown")
        self.assertEqual(report["runtime"]["status"], "unknown")
        self.assertNotIn("must not appear", rendered)


if __name__ == "__main__":
    unittest.main()
