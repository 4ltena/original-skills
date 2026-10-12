"""Validation and aggregation for explicit, privacy-safe evaluation records."""
import json
from collections import defaultdict
from pathlib import Path
from statistics import median

VARIANTS = ("none", "current", "improved")
OUTCOMES = ("pass", "fail", "unknown")


def _list_or_null(value, field):
    if value is not None and (not isinstance(value, list) or
                              not all(isinstance(item, str) for item in value)):
        raise ValueError("%s must be an array of strings or null" % field)


def validate_record(record):
    required = ("version", "case", "host", "model", "variant", "run", "outcome",
                "checks", "invoked_skills", "elapsed_ms", "token_usage", "conditions")
    missing = [name for name in required if name not in record]
    if missing:
        raise ValueError("record missing: " + ", ".join(missing))
    if record["version"] != 1 or record["variant"] not in VARIANTS:
        raise ValueError("unsupported record version or variant")
    if (record["outcome"] not in OUTCOMES or not isinstance(record["run"], int)
            or isinstance(record["run"], bool) or record["run"] < 1):
        raise ValueError("invalid outcome or run")
    for field in ("case", "host"):
        if not isinstance(record[field], str) or not record[field]:
            raise ValueError("%s must be a non-empty string" % field)
    if record["model"] is not None and not isinstance(record["model"], str):
        raise ValueError("model must be a string or null")
    for field in ("invoked_skills", "loaded_documents", "git_writes"):
        _list_or_null(record.get(field), field)
    for field in ("elapsed_ms", "token_usage"):
        if record[field] is not None and (not isinstance(record[field], int)
                or isinstance(record[field], bool) or record[field] < 0):
            raise ValueError("%s must be a non-negative integer or null" % field)
    if (not isinstance(record["conditions"], dict) or not all(
            isinstance(value, str) and value for value in record["conditions"].values())
            or not all(key in record["conditions"] for key in ("fixture", "runner", "task"))):
        raise ValueError("conditions require non-empty fixture, runner, and task")
    checks = record["checks"]
    if not isinstance(checks, list) or not all(isinstance(check, dict) and
            isinstance(check.get("name"), str) and check.get("status") in OUTCOMES
            for check in checks):
        raise ValueError("checks must name pass, fail, or unknown results")
    if record["outcome"] == "pass" and record["invoked_skills"] is None:
        raise ValueError("pass cannot treat unknown invoked_skills as a trigger result")
    if record["outcome"] == "pass" and (not checks or not all(
            check["status"] == "pass" and isinstance(check.get("evidence"), str) and check["evidence"]
            for check in checks)):
        raise ValueError("pass requires every check to pass with artifact or trace evidence")
    return record


def _distribution(values):
    if not values:
        return {"count": 0, "min": None, "median": None, "max": None}
    return {"count": len(values), "min": min(values), "median": median(values), "max": max(values)}


def condition_key(record):
    conditions = record["conditions"]
    return (record["case"], record["host"], record["model"],
            tuple(sorted((key, value) for key, value in conditions.items()
                         if key != "source_revision")))


def grade(records):
    records = [validate_record(record) for record in records]
    variants = {variant: [] for variant in VARIANTS}
    for record in records:
        variants[record["variant"]].append(record)
    summary = {}
    for variant, rows in variants.items():
        passed = sum(row["outcome"] == "pass" for row in rows)
        failed = sum(row["outcome"] == "fail" for row in rows)
        unknown = sum(row["outcome"] == "unknown" for row in rows)
        known = passed + failed
        summary[variant] = {
            "total": len(rows), "passed": passed, "failed": failed, "unknown": unknown,
            "pass_rate": (passed / known) if known else None,
            "elapsed_ms": _distribution([row["elapsed_ms"] for row in rows if row["elapsed_ms"] is not None]),
            "token_usage": _distribution([row["token_usage"] for row in rows if row["token_usage"] is not None]),
        }
    grouped = defaultdict(lambda: defaultdict(list))
    for record in records:
        grouped[condition_key(record)][record["variant"]].append(record)
    comparisons = []
    for key, rows in sorted(grouped.items(), key=lambda item: repr(item[0])):
        missing = [variant for variant in VARIANTS if not rows[variant]]
        known = {variant: any(row["outcome"] != "unknown" for row in rows[variant])
                 for variant in VARIANTS}
        run_sets = {variant: {row["run"] for row in rows[variant]} for variant in VARIANTS}
        model_known = key[2] not in (None, "unknown")
        duplicate_runs = any(len(run_sets[variant]) != len(rows[variant]) for variant in VARIANTS)
        comparable = (not missing and all(known.values()) and model_known and not duplicate_runs
                      and len(set(map(tuple, map(sorted, run_sets.values())))) == 1)
        if comparable:
            reason = None
        elif missing:
            reason = "missing variants: " + ", ".join(missing)
        elif not model_known:
            reason = "model is unknown"
        elif not all(known.values()):
            reason = "one or more variants have only unknown outcomes"
        elif duplicate_runs:
            reason = "duplicate run IDs within a variant"
        else:
            reason = "variant run sets differ"
        comparisons.append({"case": key[0], "host": key[1], "model": key[2],
                            "conditions": dict(key[3]),
                            "variants": {name: len(value) for name, value in rows.items()},
                            "comparable": comparable, "reason": reason})
    return {"version": 1, "records": len(records), "aggregate_status":
            "no_records" if not records else "observations_supplied", "observation_scope":
            "supplied checks and trace/artifact references; claims are not independently re-run",
            "variants": summary, "comparisons": comparisons}


def grade_file(input_path, output_path=None):
    raw = json.loads(Path(input_path).read_text(encoding="utf-8"))
    records = raw["records"] if isinstance(raw, dict) else raw
    result = grade(records)
    if output_path:
        Path(output_path).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result
