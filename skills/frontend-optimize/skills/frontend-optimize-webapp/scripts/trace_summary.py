#!/usr/bin/env python3
"""Index Chrome trace JSON slices; coverage is wall-time coverage, NOT CPU use."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import gzip
import json
import math
from pathlib import Path
import sys
from typing import Any

class TraceError(ValueError):
    pass

def finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        return None
    try:
        value = float(value)
    except OverflowError:
        return None
    return value if math.isfinite(value) else None

def load_trace(path: Path, max_mib: int = 128) -> Any:
    opener = gzip.open if path.suffix == ".gz" else open
    limit = max_mib * 1024 * 1024
    with opener(path, "rb") as handle:
        raw = handle.read(limit + 1)
    if len(raw) > limit:
        raise TraceError("Decoded trace exceeds size limit")
    def reject_constant(value: str) -> None:
        raise TraceError(f"Non-finite JSON number: {value}")
    return json.loads(raw, parse_constant=reject_constant)

def union_length(intervals: list[tuple[float, float]]) -> float:
    if not intervals:
        return 0.0
    ordered = sorted(intervals)
    start, end = ordered[0]
    total = 0.0
    for a, b in ordered[1:]:
        if a <= end:
            end = max(end, b)
        else:
            total += end - start
            start, end = a, b
    return total + end - start

def summarize(data: Any, *, start_us: float | None = None, end_us: float | None = None,
              pid_filter: str | None = None, tid_filter: str | None = None,
              top: int = 20) -> dict[str, Any]:
    events = data.get("traceEvents") if isinstance(data, dict) else data
    if not isinstance(events, list):
        raise TraceError("Expected Chrome traceEvents array or a top-level event array; binary Perfetto unsupported")
    if len(events) > 1_000_000:
        raise TraceError("More than 1,000,000 events; narrow the capture or use Trace Processor")
    if start_us is not None and finite(start_us) is None:
        raise TraceError("start-us must be finite")
    if end_us is not None and finite(end_us) is None:
        raise TraceError("end-us must be finite")
    if start_us is not None and end_us is not None and end_us <= start_us:
        raise TraceError("end-us must be greater than start-us")
    if not 1 <= top <= 100:
        raise TraceError("top must be 1..100")
    tracks: dict[tuple[str, str], list[tuple[float, float, str]]] = defaultdict(list)
    stacks: dict[tuple[str, str], list[tuple[float, str]]] = defaultdict(list)
    processes, threads = {}, {}
    diagnostics: Counter[str] = Counter()
    phases: Counter[str] = Counter()
    def emit(key: tuple[str, str], start: float, end: float, name: str) -> None:
        if not math.isfinite(start) or not math.isfinite(end):
            diagnostics["nonfinite_slice_endpoints"] += 1
            return
        if end < start:
            diagnostics["negative_duration_slices"] += 1
            return
        a = max(start, start_us) if start_us is not None else start
        b = min(end, end_us) if end_us is not None else end
        if b <= a:
            diagnostics["empty_or_outside_window"] += 1
            return
        tracks[key].append((a, b, name[:256]))
    for event in events:
        if not isinstance(event, dict):
            diagnostics["non_object_events"] += 1
            continue
        ph = str(event.get("ph", "?")); phases[ph] += 1
        pid, tid = str(event.get("pid", "?")), str(event.get("tid", "?"))
        if ph == "M":
            args = event.get("args", {})
            if isinstance(args, dict):
                if event.get("name") == "process_name": processes[pid] = str(args.get("name", ""))[:256]
                if event.get("name") == "thread_name": threads[(pid, tid)] = str(args.get("name", ""))[:256]
            continue
        if pid_filter is not None and pid != pid_filter: continue
        if tid_filter is not None and tid != tid_filter: continue
        if ph not in ("X", "B", "E"): continue
        if pid == "?" or tid == "?":
            diagnostics["missing_pid_or_tid"] += 1
            continue
        key = (pid, tid)
        ts = finite(event.get("ts"))
        if ts is None:
            diagnostics["invalid_timestamps"] += 1
            continue
        if ph == "X":
            dur = finite(event.get("dur"))
            if dur is None:
                diagnostics["invalid_durations"] += 1
                continue
            emit(key, ts, ts + dur, str(event.get("name", "(unnamed)")))
        elif ph == "B":
            stacks[key].append((ts, str(event.get("name", "(unnamed)"))))
        elif stacks[key]:
            begin, name = stacks[key].pop()
            emit(key, begin, ts, name)
        else:
            diagnostics["unmatched_end_events"] += 1
    diagnostics["unmatched_begin_events"] = sum(len(stack) for stack in stacks.values())
    results = []
    for (pid, tid), slices in sorted(tracks.items()):
        by_name: dict[str, list[float]] = defaultdict(list)
        for start, end, name in slices:
            by_name[name].append((end - start) / 1000)
        top_events = [{"name": name, "count": len(durations),
                       "inclusive_slice_sum_ms": sum(durations), "max_slice_ms": max(durations)}
                      for name, durations in by_name.items()]
        top_events.sort(key=lambda row: row["inclusive_slice_sum_ms"], reverse=True)
        results.append({"pid": pid, "tid": tid, "process_name": processes.get(pid),
                        "thread_name": threads.get((pid, tid)), "slice_count": len(slices),
                        "covered_slice_wall_ms": union_length([(a, b) for a, b, _ in slices]) / 1000,
                        "top_events": top_events[:top]})
    return {"schema_version": 1, "status": "slice-index-only" if results else "no-supported-slices",
            "input_time_unit": "microseconds (Chrome trace timestamps, not displayTimeUnit)",
            "window_us": {"start": start_us, "end": end_us},
            "threads": results, "phases_seen": dict(phases), "diagnostics": dict(diagnostics),
            "warnings": ["NOT CPU utilization or a critical-path/presentation analyzer.",
                         "Inclusive slice sums double-count nesting; never add them as CPU time.",
                         "covered_slice_wall_ms is the union of observed slice intervals and can include waits.",
                         "Only X and stack-paired B/E slices are indexed; async, flows, counters and GPU dependencies are not reconstructed.",
                         "B/E events are paired in input order per PID/TID; malformed/unmatched events are reported, not inferred.",
                         "Missing data, dropped trace events and symbols cannot be recovered.",
                         "Names may contain sensitive labels from the input; output stays local and should be reviewed before sharing."]}

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--start-us", type=float)
    parser.add_argument("--end-us", type=float)
    parser.add_argument("--pid")
    parser.add_argument("--tid")
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--max-mib", type=int, default=128)
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.max_mib <= 1024:
            raise TraceError("max-mib must be 1..1024")
        report = summarize(load_trace(args.trace, args.max_mib), start_us=args.start_us,
                           end_us=args.end_us, pid_filter=args.pid, tid_filter=args.tid, top=args.top)
        payload = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8") as handle: handle.write(payload)
        else:
            sys.stdout.write(payload)
        return 0 if report["threads"] else 3
    except (OSError, ValueError, TypeError, OverflowError, RecursionError) as exc:
        print(json.dumps({"status": "input-error", "error": str(exc)}), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
