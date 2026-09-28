#!/usr/bin/env python3
"""Validate the published skill layout and exercise the bundled Python helpers."""

import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "frontend-optimize-apple",
    "frontend-optimize-linux",
    "frontend-optimize-webapp",
    "frontend-optimize-windows",
}
LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys)


def check_skill(skill):
    if (skill / "LICENSE").read_bytes() != (ROOT / "LICENSE").read_bytes():
        raise ValueError("standalone skill license differs from repository license: " + skill.name)
    entry = skill / "SKILL.md"
    content = entry.read_text(encoding="utf-8")
    if not content.startswith("---\n") or "\n---\n" not in content[4:]:
        raise ValueError("missing YAML frontmatter: " + str(entry))
    frontmatter = content[4:].split("\n---\n", 1)[0]
    fields = dict(re.findall(r"^([a-z][a-z-]*):\s*(.+)$", frontmatter, re.MULTILINE))
    if fields.get("name") != skill.name:
        raise ValueError("skill name does not match directory: " + str(entry))
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", skill.name) or len(skill.name) > 64:
        raise ValueError("invalid skill name: " + skill.name)
    description = fields.get("description", "").strip("'\"")
    if not description or len(description) > 1024:
        raise ValueError("invalid description: " + str(entry))
    if fields.get("license") != "MIT":
        raise ValueError("missing MIT license declaration: " + str(entry))
    for markdown in skill.rglob("*.md"):
        body = markdown.read_text(encoding="utf-8")
        for match in LINK.finditer(body):
            url = match.group(1).strip()
            parsed = urlsplit(url)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (markdown.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(skill.resolve()) or not target.exists():
                raise ValueError("broken or escaping link: {} -> {}".format(markdown, url))
    for asset in skill.rglob("*.json"):
        load_json(asset)
    for script in skill.rglob("*.py"):
        compile(script.read_text(encoding="utf-8"), str(script), "exec")


def exercise_comparison(skill):
    assets = skill / "assets"
    command = [
        sys.executable,
        str(skill / "scripts" / "compare_metrics.py"),
        str(assets / "synthetic-baseline.json"),
        str(assets / "synthetic-candidate.json"),
        "--policy",
        str(assets / "policy-example.json"),
    ]
    refused = subprocess.run(command, capture_output=True, text=True)
    if refused.returncode != 2 or "Synthetic input refused" not in refused.stderr:
        raise ValueError("comparison helper accepted synthetic input by default: " + skill.name)
    accepted = subprocess.run(command + ["--allow-synthetic"], capture_output=True, text=True)
    if accepted.returncode != 0:
        raise ValueError("comparison example failed: {} {}".format(skill.name, accepted.stderr))
    report = json.loads(accepted.stdout)
    if report["status"] != "passed-numeric-gates" or report["acceptance"] != "not-determined-by-this-tool":
        raise ValueError("unexpected comparison result: " + skill.name)


def exercise_trace_summary(skill):
    with tempfile.TemporaryDirectory() as directory:
        trace = Path(directory) / "trace.json"
        trace.write_text(json.dumps({"traceEvents": [
            {"ph": "X", "pid": 1, "tid": 2, "ts": 1000, "dur": 1000, "name": "example"}
        ]}), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(skill / "scripts" / "trace_summary.py"), str(trace)],
            capture_output=True, text=True,
        )
    if result.returncode != 0:
        raise ValueError("trace summary failed: " + result.stderr)
    report = json.loads(result.stdout)
    if report["status"] != "slice-index-only" or report["threads"][0]["covered_slice_wall_ms"] != 1.0:
        raise ValueError("unexpected trace summary result")


def main():
    skills_root = ROOT / "skills"
    found = {path.name for path in skills_root.iterdir() if path.is_dir()}
    if found != EXPECTED:
        raise ValueError("unexpected skill directories: " + repr(found ^ EXPECTED))
    for name in sorted(EXPECTED):
        skill = skills_root / name
        check_skill(skill)
        exercise_comparison(skill)
    exercise_trace_summary(skills_root / "frontend-optimize-webapp")
    print("Validated 4 skills, local links, JSON, Python, comparison fixtures, and trace summary.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, IndexError) as error:
        print("Validation failed: " + str(error), file=sys.stderr)
        raise SystemExit(1)
