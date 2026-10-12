"""Grade observed skill selection; never invoke models or infer missing trace data."""
import argparse
import json
from pathlib import Path
import sys

CASES = Path(__file__).with_name("skill-selection.json")
MAX_INPUT = 1024 * 1024


def load_json(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_INPUT:
        raise ValueError("invalid evaluation input")
    return json.loads(path.read_text(encoding="utf-8"))


def observed_list(record, name):
    value = record.get(name)
    if value is None:
        return None
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
        raise ValueError("invalid observed list")
    return value


def grade(case, record):
    if (type(record.get("version")) is not int or record["version"] != 1 or record.get("case") != case["id"]
            or record.get("host") not in {"claude", "codex"}
            or record.get("variant") not in {"none", "current", "improved"}
            or type(record.get("run")) is not int or record["run"] < 1):
        raise ValueError("invalid selection record identity")
    if record.get("model") is not None and not isinstance(record["model"], str):
        raise ValueError("invalid model identity")
    for name in ("elapsed_ms", "token_usage"):
        value = record.get(name)
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError("invalid metric")
    invoked = observed_list(record, "invoked_skills")
    docs = observed_list(record, "loaded_documents")
    writes = observed_list(record, "git_writes")
    source = record.get("trace_ref")
    if source is not None and (not isinstance(source, str) or not source.strip()):
        raise ValueError("invalid trace reference")
    checks = []

    def check(name, observed, passed):
        status = "unknown" if observed is None or source is None else ("pass" if passed else "fail")
        checks.append({"name": name, "status": status, "evidence": source})

    check("required_skills", invoked, invoked is not None and set(case["required_skills"]) <= set(invoked))
    check("scope_and_companions", invoked, invoked is not None and set(invoked) <= set(case["allowed_skills"]))
    check("skill_load_budget", invoked, invoked is not None and len(invoked) <= case["max_skill_loads"])
    check("document_load_budget", docs, docs is not None and len(docs) <= case["max_document_loads"])
    check("git_write_authorization", writes, writes is not None and (case["git_write_authorized"] or not writes))
    statuses = {item["status"] for item in checks}
    outcome = "fail" if "fail" in statuses else ("unknown" if "unknown" in statuses else "pass")
    conditions = record.get("conditions", {})
    if not isinstance(conditions, dict):
        raise ValueError("invalid conditions")
    if "task" in conditions and conditions["task"] != case["id"]:
        raise ValueError("task does not match case")
    conditions = {**conditions, "task": case["id"]}
    if any(not isinstance(conditions.get(key), str) or not conditions[key] for key in ("fixture", "runner", "task")):
        raise ValueError("missing evaluation conditions")
    return {"version": 1, "case": case["id"], "host": record["host"],
            "model": record.get("model"), "variant": record["variant"], "run": record["run"],
            "outcome": outcome, "checks": checks, "invoked_skills": invoked,
            "loaded_documents": docs, "git_writes": writes,
            "elapsed_ms": record.get("elapsed_ms"), "token_usage": record.get("token_usage"),
            "conditions": conditions}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", help="JSON array of observed selection records")
    parser.add_argument("--cases", default=str(CASES))
    args = parser.parse_args()
    try:
        dataset = load_json(args.cases)
        cases = {case["id"]: case for case in dataset["cases"]}
        records = load_json(args.records)
        if dataset.get("version") != 1 or not isinstance(records, list) or not records:
            raise ValueError("invalid dataset")
        identities = [(record["case"], record["host"], record["variant"], record["run"]) for record in records]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate observation")
        scores = [grade(cases[record["case"]], record) for record in records]
        print(json.dumps(scores, ensure_ascii=False, allow_nan=False))
        return 1 if any(score["outcome"] != "pass" for score in scores) else 0
    except (OSError, ValueError, KeyError, TypeError):
        print("selection evaluation refused: invalid dataset or observations", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
