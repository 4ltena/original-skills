"""Score supplied checkpoint decisions against the maintained review scenarios."""
import argparse
import json
from pathlib import Path
import sys

CASES = Path(__file__).resolve().parents[1] / "plugins/goal-checkpoint/tests/review_cases.json"


def grade(case, review):
    expected = case["expected"]
    if review.get("case") != case["id"]:
        raise ValueError("checkpoint case mismatch")
    result = {"case": case["id"], "checks": {}}
    for field in ("decision", "verdict", "next_action_kind"):
        if field not in review:
            status = "unknown"
        else:
            status = "pass" if review[field] == expected[field] else "fail"
        result["checks"][field] = status
    statuses = set(result["checks"].values())
    result["outcome"] = "fail" if "fail" in statuses else ("unknown" if "unknown" in statuses else "pass")
    result["scope"] = "supplied decision; evidence relevance still requires independent review"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reviews", help="non-secret JSON array of review observations")
    args = parser.parse_args()
    try:
        cases = {case["id"]: case for case in json.loads(CASES.read_text(encoding="utf-8"))}
        source = Path(args.reviews)
        if source.is_symlink() or source.stat().st_size > 1024 * 1024:
            raise ValueError("invalid review observations")
        reviews = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(reviews, list) or not reviews:
            raise ValueError("missing review observations")
        if len({review["case"] for review in reviews}) != len(reviews):
            raise ValueError("duplicate review observation")
        results = [grade(cases[review["case"]], review) for review in reviews]
        print(json.dumps(results, ensure_ascii=False))
        return 1 if any(result["outcome"] != "pass" for result in results) else 0
    except (OSError, ValueError, KeyError, TypeError):
        print("checkpoint evaluation refused: invalid scenarios or observations", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
