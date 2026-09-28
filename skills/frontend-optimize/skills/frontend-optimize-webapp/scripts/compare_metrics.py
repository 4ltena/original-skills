#!/usr/bin/env python3
"""Compare explicit per-run metrics; no benchmark execution or significance test."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import statistics
import sys
from typing import Any

MAX_BYTES = 8 * 1024 * 1024
CONTEXT_FIELDS = ("environment_id", "scenario_id", "dataset_id", "cache_state",
                  "instrumentation_id", "measurement_kind")
RULES = {"statistic", "max_regression_percent", "max_regression_absolute",
         "min_improvement_percent", "min_improvement_absolute", "target"}

class InputError(ValueError):
    pass

def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result

def _constant(value: str) -> None:
    raise InputError(f"Non-finite JSON number: {value}")

def load_json(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        raw = handle.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise InputError(f"Input exceeds {MAX_BYTES} bytes: {path}")
    value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
    if not isinstance(value, dict):
        raise InputError(f"Expected JSON object: {path}")
    return value

def number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputError(f"{label}: expected a number")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise InputError(f"{label}: invalid number") from exc
    if not math.isfinite(result) or result < 0:
        raise InputError(f"{label}: expected a finite non-negative number")
    return result

def text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{label}: expected a non-empty string")
    return value

def version(value: Any, label: str) -> None:
    if type(value) is not int or value != 1:
        raise InputError(f"{label}: schema_version must be integer 1")

def validate_measurement(data: dict[str, Any], label: str) -> None:
    version(data.get("schema_version"), label)
    if type(data.get("synthetic")) is not bool:
        raise InputError(f"{label}: explicit synthetic boolean required")
    context = data.get("context")
    if not isinstance(context, dict):
        raise InputError(f"{label}: context object required")
    for key in CONTEXT_FIELDS:
        text(context.get(key), f"{label}.context.{key}")
    build = data.get("build")
    if not isinstance(build, dict):
        raise InputError(f"{label}: build object required")
    for key in ("revision", "configuration"):
        text(build.get(key), f"{label}.build.{key}")
    metrics = data.get("metrics")
    if not isinstance(metrics, dict) or not metrics:
        raise InputError(f"{label}: non-empty metrics object required")
    for name, metric in metrics.items():
        text(name, f"{label}: metric name")
        if not isinstance(metric, dict):
            raise InputError(f"{label}.{name}: metric object required")
        text(metric.get("unit"), f"{label}.{name}.unit")
        if metric.get("direction") not in ("lower", "higher"):
            raise InputError(f"{label}.{name}: direction must be lower or higher")
        if metric.get("sample_unit") != "run":
            raise InputError(f"{label}.{name}: sample_unit must be run; aggregate frames within each run first")
        samples = metric.get("samples")
        if not isinstance(samples, list) or not samples:
            raise InputError(f"{label}.{name}: non-empty samples array required")
        for i, sample in enumerate(samples):
            number(sample, f"{label}.{name}.samples[{i}]")
        if "run_ids" in metric:
            ids = metric["run_ids"]
            if not isinstance(ids, list) or len(ids) != len(samples):
                raise InputError(f"{label}.{name}: run_ids must match sample count")
            for identifier in ids:
                text(identifier, f"{label}.{name}.run_ids")
            if len(set(ids)) != len(ids):
                raise InputError(f"{label}.{name}: duplicate run_ids")

def validate_policy(policy: dict[str, Any]) -> None:
    version(policy.get("schema_version"), "policy")
    unknown = set(policy) - {"schema_version", "min_samples", "metrics", "notes"}
    if unknown:
        raise InputError(f"Unknown policy keys: {sorted(unknown)}")
    count = policy.get("min_samples")
    if type(count) is not int or count < 2:
        raise InputError("policy.min_samples must be integer >= 2")
    metrics = policy.get("metrics")
    if not isinstance(metrics, dict) or not metrics:
        raise InputError("policy.metrics must be non-empty")
    for name, rule in metrics.items():
        if not isinstance(rule, dict):
            raise InputError(f"policy.{name}: rule must be an object")
        unknown = set(rule) - RULES
        if unknown:
            raise InputError(f"policy.{name}: unknown rules {sorted(unknown)}")
        if rule.get("statistic") not in ("median", "p95"):
            raise InputError(f"policy.{name}: statistic must be median or p95")
        if not (set(rule) - {"statistic"}):
            raise InputError(f"policy.{name}: at least one gate required")
        for key, value in rule.items():
            if key != "statistic":
                number(value, f"policy.{name}.{key}")

def describe(samples: list[float]) -> dict[str, float | int]:
    values = sorted(float(x) for x in samples)
    n = len(values)
    return {"n": n, "median": statistics.median(values),
            "p95": values[math.ceil(0.95 * n) - 1],
            "min": values[0], "max": values[-1],
            "sample_stdev": statistics.stdev(values) if n > 1 else 0.0}

def compare(baseline: dict[str, Any], candidate: dict[str, Any],
            policy: dict[str, Any], *, allow_synthetic: bool = False) -> tuple[dict[str, Any], int]:
    validate_measurement(baseline, "baseline")
    validate_measurement(candidate, "candidate")
    validate_policy(policy)
    if baseline["context"] != candidate["context"]:
        raise InputError("Contexts differ. Do not combine different scenarios, environments or instrumentation.")
    if baseline["build"]["configuration"] != candidate["build"]["configuration"]:
        raise InputError("Build configurations differ")
    if baseline["synthetic"] != candidate["synthetic"]:
        raise InputError("Cannot compare synthetic and measured evidence")
    synthetic = baseline["synthetic"]
    if synthetic and not allow_synthetic:
        raise InputError("Synthetic input refused; --allow-synthetic is for demonstrations only")
    warnings = ["Descriptive numeric gates only: no significance test, causal proof or correctness/a11y validation.",
                "Independent runs and representative measurement conditions cannot be verified from JSON.",
                "p95 uses nearest-rank ceil(0.95*n); each sample must represent one independent run."]
    rows = []
    insufficient = False
    failed = False
    for name, rule in policy["metrics"].items():
        if name not in baseline["metrics"] or name not in candidate["metrics"]:
            raise InputError(f"Required metric missing: {name}")
        b = baseline["metrics"][name]
        c = candidate["metrics"][name]
        for field in ("unit", "direction", "sample_unit"):
            if b[field] != c[field]:
                raise InputError(f"{name}: {field} differs")
        bd, cd = describe(b["samples"]), describe(c["samples"])
        statistic = rule["statistic"]
        before, after = float(bd[statistic]), float(cd[statistic])
        improvement = before - after if b["direction"] == "lower" else after - before
        percent = 100 * improvement / before if before != 0 else None
        if percent is not None and not math.isfinite(percent):
            raise InputError(f"{name}: derived percentage exceeds finite numeric range")
        if percent is None and any(k.endswith("_percent") for k in rule):
            raise InputError(f"{name}: zero baseline cannot evaluate percentage rules; use absolute gates")
        gates = []
        for key, threshold in rule.items():
            if key == "statistic":
                continue
            limit = float(threshold)
            if key == "max_regression_percent":
                passed = percent >= -limit
            elif key == "max_regression_absolute":
                passed = improvement >= -limit
            elif key == "min_improvement_percent":
                passed = percent >= limit
            elif key == "min_improvement_absolute":
                passed = improvement >= limit
            else:  # target is directional
                passed = after <= limit if b["direction"] == "lower" else after >= limit
            gates.append({"rule": key, "threshold": threshold, "passed": passed})
        enough = min(bd["n"], cd["n"]) >= policy["min_samples"]
        insufficient = insufficient or not enough
        failed = failed or any(not gate["passed"] for gate in gates)
        if statistic == "p95" and min(bd["n"], cd["n"]) < 100:
            warnings.append(f"{name}: fewer than 100 run samples; tail estimate is especially unstable. 100 is not a guarantee.")
        rows.append({"metric": name, "unit": b["unit"], "direction": b["direction"],
                     "sample_unit": "run", "statistic": statistic,
                     "baseline": bd, "candidate": cd,
                     "absolute_improvement": improvement, "improvement_percent": percent,
                     "enough_samples": enough, "gates": gates})
    unused = sorted((set(baseline["metrics"]) | set(candidate["metrics"])) - set(policy["metrics"]))
    if unused:
        warnings.append(f"Metrics not covered by policy: {', '.join(unused)}")
    if synthetic:
        warnings.append("SYNTHETIC FIXTURE: not an actual app measurement or accepted optimization.")
    if insufficient:
        status, code = "insufficient-samples", 3
    elif failed:
        status, code = "failed-numeric-gates", 1
    else:
        status, code = "passed-numeric-gates", 0
    report = {"schema_version": 1, "status": status,
              "evidence_kind": "synthetic" if synthetic else "declared-measured",
              "acceptance": "not-determined-by-this-tool",
              "context": baseline["context"], "baseline_build": baseline["build"],
              "candidate_build": candidate["build"], "metrics": rows, "warnings": warnings}
    return report, code

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--out", type=Path, help="New output file only; existing files are not overwritten")
    parser.add_argument("--allow-synthetic", action="store_true")
    args = parser.parse_args(argv)
    try:
        report, code = compare(load_json(args.baseline), load_json(args.candidate),
                               load_json(args.policy), allow_synthetic=args.allow_synthetic)
        payload = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8") as handle:
                handle.write(payload)
        else:
            sys.stdout.write(payload)
        return code
    except (InputError, OSError, ValueError, TypeError, OverflowError, RecursionError) as exc:
        print(json.dumps({"status": "input-error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
