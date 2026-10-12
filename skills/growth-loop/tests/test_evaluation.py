import importlib.util
import json
import shutil
import sys
import unittest
from pathlib import Path

from fixtures import tmpdir

E2E = Path(__file__).resolve().parent.parent / "e2e"
sys.path.insert(0, str(E2E))
import evaluation
sys.path.pop(0)


def record(variant="current", outcome="pass", run=1):
    return {"version": 1, "case": "learn-safe", "host": "claude", "model": "model-a",
            "variant": variant, "run": run, "outcome": outcome,
            "checks": [{"name": "artifact", "status": "pass", "evidence": "fixture/result.json"}],
            "invoked_skills": [], "loaded_documents": None, "git_writes": None,
            "elapsed_ms": None, "token_usage": None,
            "conditions": {"fixture": "guided-v1", "runner": "native-host", "task": "same"}}


class TestEvaluation(unittest.TestCase):
    def test_pass_needs_artifact_evidence(self):
        row = record(); row["checks"][0].pop("evidence")
        with self.assertRaisesRegex(ValueError, "artifact or trace"):
            evaluation.validate_record(row)

    def test_pass_cannot_hide_unknown_invocations(self):
        row = record(); row["invoked_skills"] = None
        with self.assertRaisesRegex(ValueError, "unknown invoked_skills"):
            evaluation.validate_record(row)

    def test_null_and_empty_invocations_remain_distinct(self):
        rows = [record("none", "unknown"), record("current"), record("improved")]
        rows[0]["invoked_skills"] = None
        result = evaluation.grade(rows)
        self.assertEqual(result["records"], 3)
        self.assertEqual(result["variants"]["none"]["unknown"], 1)
        self.assertFalse(result["comparisons"][0]["comparable"])

    def test_unknown_metrics_are_not_zero_or_passes(self):
        result = evaluation.grade([record(outcome="unknown")])
        current = result["variants"]["current"]
        self.assertEqual(current["unknown"], 1)
        self.assertIsNone(current["pass_rate"])
        self.assertEqual(current["elapsed_ms"]["count"], 0)

    def test_comparison_requires_all_variants_with_known_outcomes(self):
        rows = [record("none"), record("current"), record("improved", "unknown")]
        self.assertFalse(evaluation.grade(rows)["comparisons"][0]["comparable"])

    def test_pass_rejects_a_contradictory_check(self):
        row = record(); row["checks"].append({"name": "other", "status": "fail", "evidence": "trace:2"})
        with self.assertRaisesRegex(ValueError, "every check"):
            evaluation.validate_record(row)

    def test_unknown_model_and_different_run_sets_are_incomparable(self):
        rows = [record("none"), record("current"), record("improved", run=2)]
        self.assertFalse(evaluation.grade(rows)["comparisons"][0]["comparable"])
        for row in rows:
            row["model"] = "unknown"
        self.assertEqual(evaluation.grade(rows)["comparisons"][0]["reason"], "model is unknown")

    def test_condition_values_and_boolean_metrics_are_rejected(self):
        row = record(); row["conditions"]["unsafe"] = []
        with self.assertRaises(ValueError):
            evaluation.validate_record(row)

    def test_duplicate_run_ids_and_empty_input_are_not_successful(self):
        rows = [record("none"), record("current"), record("current"), record("improved")]
        result = evaluation.grade(rows)
        self.assertFalse(result["comparisons"][0]["comparable"])
        self.assertEqual(result["comparisons"][0]["reason"], "duplicate run IDs within a variant")
        self.assertEqual(evaluation.grade([])["aggregate_status"], "no_records")
        row = record(); row["elapsed_ms"] = True
        with self.assertRaises(ValueError):
            evaluation.validate_record(row)

    def test_prepare_uses_guided_install_only_in_fixture_home(self):
        spec = importlib.util.spec_from_file_location("run_e2e", E2E / "run_e2e.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        root = tmpdir() / "fixture"
        try:
            fixture = module.prepare(root)
            self.assertTrue((root / "fixture.json").is_file())
            first = fixture["cases"][0]
            self.assertTrue(Path(first["runtime"], "binding.json").is_file())
            self.assertFalse(first["installer_runtime_verified"])
            self.assertIn("cases/%s/home/.claude/original-skills/growth-loop/bin/gl-run" % first["name"], first["inspected_artifacts"])
            self.assertEqual(len(fixture["cases"]), 4)
        finally:
            shutil.rmtree(root.parent, ignore_errors=True)

    def test_prepared_hosts_match_requests_and_artifact_grade_rejects_noop(self):
        spec = importlib.util.spec_from_file_location("run_e2e", E2E / "run_e2e.py")
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        parent = tmpdir()
        try:
            claude = module.prepare(parent / "claude", "claude")
            codex = module.prepare(parent / "codex", "codex")
            self.assertEqual(claude["host"], "claude")
            self.assertEqual(codex["host"], "codex")
            fixture = parent / "claude" / "fixture.json"
            with self.assertRaisesRegex(ValueError, "must match"):
                module.request(fixture, parent / "bad.json", "codex", "model-a", "native-host")
            pending = module.request(fixture, parent / "pending.json", "claude", "unknown", "native-host")
            self.assertEqual(pending["status"], "not_run")
            unsupported = module.request(fixture, parent / "unsupported.json", "claude", "model-a", "other-runner")
            self.assertEqual(unsupported["status"], "not_run")
            unverified = module.request(fixture, parent / "unverified.json", "claude", "model-a", "native-host")
            self.assertIn("unavailable", unverified["reason"])
            claimed = module.request(fixture, parent / "claimed.json", "claude", "model-a", "native-host",
                                   {"runner": "native-host", "verified": True})
            self.assertEqual(claimed["status"], "not_run")
            self.assertEqual(unsupported["runner_support"], "unsupported")
            no_op = module.grade_case(fixture, "learn-writes-where-journey-reads",
                                      {"exit_code": 0, "invoked_skills": ["learn"]})
            self.assertEqual(no_op["outcome"], "fail")
            case = next(c for c in claude["cases"] if c["name"] == "learn-writes-where-journey-reads")
            new = Path(case["skill_root"]) / "fixture-skill" / "SKILL.md"
            new.parent.mkdir(); new.write_text("---\nname: fixture-skill\ndescription: fixture\n---\n", encoding="utf-8")
            passed = module.grade_case(fixture, case["name"], {"exit_code": 0, "invoked_skills": ["learn"]})
            self.assertEqual(passed["outcome"], "pass")
            Path(case["runtime"], "bin", "difflib.py").write_text("raise RuntimeError('fixture shadow module executed')\n", encoding="utf-8")
            cached = sys.modules.pop("difflib", None)
            try:
                safe = module.grade_case(fixture, case["name"], {"exit_code": 0, "invoked_skills": ["learn"]})
                self.assertEqual(safe["outcome"], "pass")
            finally:
                if cached is not None:
                    sys.modules["difflib"] = cached
            missing_invocation = module.grade_case(fixture, case["name"], {"exit_code": 0, "invoked_skills": None})
            self.assertEqual(missing_invocation["outcome"], "unknown")
            Path(case["runtime"], "bin", "gl-run").write_text("raise SystemExit('tampered')\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "differs from trusted"):
                module.grade_case(fixture, case["name"], {"exit_code": 0, "invoked_skills": ["learn"]})
            forget = next(c for c in claude["cases"] if c["name"] == "forget-holds-without-confirmation")
            Path(forget["skill_root"], "old-thing", "SKILL.md").unlink()
            deleted = module.grade_case(fixture, forget["name"], {"exit_code": 0, "invoked_skills": ["forget"], "routes": ["old-thing"]})
            self.assertEqual(deleted["outcome"], "fail")
            profile_case = next(c for c in claude["cases"] if c["name"] == "profile-refuses-dishonesty")
            broken = module.grade_case(fixture, profile_case["name"], {"exit_code": 0, "invoked_skills": ["profile"]})
            self.assertEqual(broken["outcome"], "fail")
            binding = json.loads(Path(profile_case["runtime"], "binding.json").read_text())
            profile = Path(binding["data"]) / "profile.md"; profile.parent.mkdir(parents=True, exist_ok=True)
            profile.write_text("- pnpm\n", encoding="utf-8")
            intact = module.grade_case(fixture, profile_case["name"], {"exit_code": 0, "invoked_skills": ["profile"]})
            self.assertEqual(intact["outcome"], "pass")
        finally:
            shutil.rmtree(parent, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
