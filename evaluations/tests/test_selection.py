import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("selection", ROOT / "score_selection.py")
selection = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(selection)
CASES = {case["id"]: case for case in json.loads((ROOT / "skill-selection.json").read_text())["cases"]}


def record(case, **changes):
    value = {"version": 1, "case": case, "host": "codex", "model": "fixture", "variant": "current", "run": 1,
             "invoked_skills": CASES[case]["required_skills"], "loaded_documents": [], "git_writes": [],
             "trace_ref": "fixture:observed", "conditions": {"fixture": case, "runner": "offline"}}
    value.update(changes)
    return value


class SelectionTests(unittest.TestCase):
    def test_same_cases_can_score_both_hosts(self):
        for host in ("claude", "codex"):
            for case in CASES.values():
                self.assertEqual(selection.grade(case, record(case["id"], host=host))["outcome"], "pass")

    def test_approved_plan_replanning_fails(self):
        result = selection.grade(CASES["approved-development"], record("approved-development", invoked_skills=["workflow", "spec-first-development"]))
        self.assertEqual(result["outcome"], "fail")

    def test_routine_design_false_trigger_fails(self):
        result = selection.grade(CASES["routine-ui-fix"], record("routine-ui-fix", invoked_skills=["frontend-design"]))
        self.assertEqual(result["outcome"], "fail")

    def test_unrequested_git_write_and_excessive_reads_fail(self):
        for changes in ({"git_writes": ["commit"]}, {"loaded_documents": ["architecture", "deployment", "database"]}, {"invoked_skills": ["smallest-change"] * 3}):
            result = selection.grade(CASES["manual-git-local-fix"], record("manual-git-local-fix", **changes))
            self.assertEqual(result["outcome"], "fail")

    def test_missing_observation_is_unknown_not_empty(self):
        for field in ("invoked_skills", "loaded_documents", "git_writes", "trace_ref"):
            result = selection.grade(CASES["routine-typo"], record("routine-typo", **{field: None}))
            self.assertEqual(result["outcome"], "unknown")
        self.assertEqual(selection.grade(CASES["routine-typo"], record("routine-typo"))["outcome"], "pass")

    def test_metrics_are_not_fabricated(self):
        result = selection.grade(CASES["routine-typo"], record("routine-typo"))
        self.assertIsNone(result["elapsed_ms"])
        self.assertIsNone(result["token_usage"])

    def test_invalid_metric_and_missing_conditions_are_refused(self):
        for changes in ({"elapsed_ms": -1}, {"token_usage": True}, {"conditions": {}}):
            with self.assertRaises(ValueError):
                selection.grade(CASES["routine-typo"], record("routine-typo", **changes))

    def test_task_identity_cannot_override_the_case(self):
        changes = {"conditions": {"fixture": "fixture", "runner": "offline", "task": "routine-typo"}}
        with self.assertRaisesRegex(ValueError, "task does not match"):
            selection.grade(CASES["approved-development"], record("approved-development", **changes))


if __name__ == "__main__":
    unittest.main()
