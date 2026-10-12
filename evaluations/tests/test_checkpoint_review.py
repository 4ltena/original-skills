import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("checkpoint_evaluation", ROOT / "score_checkpoint.py")
scorer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scorer)
CASES = {case["id"]: case for case in json.loads(scorer.CASES.read_text())}


class CheckpointReviewTests(unittest.TestCase):
    def test_activity_without_criterion_progress_fails(self):
        review = {"case": "export-drift", "decision": "ack", "verdict": "progress", "next_action_kind": "cosmetic_cleanup"}
        self.assertEqual(scorer.grade(CASES[review["case"]], review)["outcome"], "fail")

    def test_necessary_recovery_fix_is_progress(self):
        review = {"case": "recovery-fix", "decision": "ack", "verdict": "progress", "next_action_kind": "verify_remaining_recovery_case"}
        self.assertEqual(scorer.grade(CASES[review["case"]], review)["outcome"], "pass")
        review["verdict"] = "stalled"
        self.assertEqual(scorer.grade(CASES[review["case"]], review)["outcome"], "fail")

    def test_completed_goal_cannot_restart(self):
        review = {"case": "completed-goal", "decision": "ack", "verdict": "progress", "next_action_kind": "implement_missing_criterion"}
        self.assertEqual(scorer.grade(CASES[review["case"]], review)["outcome"], "fail")

    def test_missing_judgment_stays_unknown(self):
        self.assertEqual(scorer.grade(CASES["export-drift"], {"case": "export-drift"})["outcome"], "unknown")


if __name__ == "__main__":
    unittest.main()
