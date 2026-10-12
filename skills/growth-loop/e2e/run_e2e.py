#!/usr/bin/env python3
"""Offline growth-loop evaluation: prepare, request, grade-case, then grade.

No command invokes a model, host CLI, or authentication store.
"""
import argparse
import contextlib
import importlib.util
import io
import json
import os
import runpy
import sys
from pathlib import Path

E2E_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = E2E_ROOT.parent.parent.parent
CASES_DIR = E2E_ROOT / "cases"
RUNNERS = {"native-host", "benchmark-execution"}
TRUSTED_RUNTIME = PROJECT_ROOT / "skills" / "growth-loop" / "growth-loop"


def load_cases():
    return [json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(CASES_DIR.glob("*.json"))]


def installer_module():
    environment = PROJECT_ROOT / "environment"
    sys.path.insert(0, str(environment))
    try:
        spec = importlib.util.spec_from_file_location("evaluation_install", environment / "install.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def inside(root, path):
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        raise ValueError("fixture path escapes its prepared root: %s" % path)
    return path


def regular_inside(root, path):
    inside(root, path)
    if not path.is_file() or path.is_symlink():
        raise ValueError("fixture artifact is not a regular file: %s" % path)
    return path


def plant_skills(skills_root, specs):
    for spec in specs or []:
        target = skills_root / spec["slug"] / "SKILL.md"
        if target.exists() or target.is_symlink():
            raise ValueError("fixture plant target already exists: %s" % target)
        target.parent.mkdir(parents=True)
        target.write_text("---\nname: %s\ndescription: %s\n---\n\n%s\n" %
                          (spec["slug"], spec["description"], spec.get("body", "N/A")),
                          encoding="utf-8")


def inspect_prepared_fixture(root, runtime, home, host):
    prefix = ".claude" if host == "claude" else ".codex"
    required = (runtime / "binding.json", runtime / "bin" / "gl-run",
                home / prefix / "skills" / "learn" / "SKILL.md",
                home / prefix / "skills" / "forget" / "SKILL.md")
    inspected = []
    for path in required:
        inside(root, path)
        if not path.is_file() or path.is_symlink():
            raise ValueError("prepared fixture is missing a regular file: %s" % path)
        inspected.append(str(path.relative_to(root)))
    binding = json.loads((runtime / "binding.json").read_text(encoding="utf-8"))
    skill_root = home / prefix / "skills"
    if binding.get("runtime") != host or binding.get("root") != str(skill_root):
        raise ValueError("prepared binding does not match host fixture")
    return inspected


def prepare(destination, host="claude"):
    """Prepare every preserved case in its own guided-install fixture home."""
    if host not in {"claude", "codex"}:
        raise ValueError("prepare host must be claude or codex")
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError("fixture destination must not already exist: %s" % destination)
    destination.mkdir(parents=True)
    installer = installer_module()
    prefix = ".claude" if host == "claude" else ".codex"
    prepared_cases = []
    for case in load_cases():
        case_root = destination / "cases" / case["name"]
        home, work = case_root / "home", case_root / "work"
        home.mkdir(parents=True); work.mkdir()
        answers = {"host": host, "scope": "user", "skills": "custom", "skill_names": [],
                   "plugins": ["growth-loop"], "git_mode": "manual-git",
                   "growth_root": "selected-skills", "auto_delete": "no", "settings": "skills-only"}
        if host == "claude":
            answers["surface"] = "cli"
        plan = installer.plan(answers, home, executable=sys.executable)
        applied = installer.apply(plan, plan["plan_id"])
        runtime = home / prefix / "original-skills" / "growth-loop"
        skills_root = home / prefix / "skills"
        plant_skills(skills_root, case.get("plant_skills"))
        prepared_cases.append({"name": case["name"], "case_root": str(case_root),
                               "home": str(home), "work": str(work), "runtime": str(runtime),
                               "skill_root": str(skills_root), "before_skills": sorted(
                                   path.parent.name for path in skills_root.glob("*/SKILL.md")),
                               "expect": case.get("expect", {}), "expect_codex": case.get("expect_codex", {}),
                               "inspected_artifacts": inspect_prepared_fixture(destination, runtime, home, host),
                               "installer_runtime_verified": applied["runtime_verified"]})
    manifest = {"version": 1, "stage": "prepared", "host": host, "cases": prepared_cases,
                "notice": "Prepared source placement only; registration, trust, and live delivery remain unverified."}
    (destination / "fixture.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def request(fixture_path, destination, host, model, runner, runner_receipt=None):
    fixture = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    if fixture.get("stage") != "prepared" or host != fixture.get("host"):
        raise ValueError("request host must match the prepared fixture binding")
    # Caller-supplied JSON is an assertion, not effective runner verification.
    # An authorized native host/runner must verify its scope before executing.
    if runner in RUNNERS and model not in (None, "unknown"):
        status, reason = "not_run", "runner verification unavailable in this offline tool"
    elif model in (None, "unknown"):
        status, reason = "not_run", "unknown model"
    else:
        status, reason = "not_run", "unsupported runner"
    handoff = []
    fixture_root = Path(fixture_path).resolve().parent
    for case in fixture["cases"]:
        paths = {"work": case["work"], "runtime": case["runtime"], "skills": case["skill_root"],
                 "policy": str(Path(case["home"]) / (".claude" if host == "claude" else ".codex") / "original-skills" / "host-policy.md")}
        for path in paths.values(): inside(fixture_root, Path(path))
        handoff.append({"name": case["name"], **paths})
    payload = {"version": 1, "stage": "requested", "status": status,
               "fixture": str(Path(fixture_path).resolve()), "host": host, "model": model,
               "runner": runner, "runner_support": "unverified" if runner in RUNNERS else "unsupported",
               "reason": reason, "cases": handoff,
               "notice": "Request only; no model or CLI was spawned."}
    Path(destination).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def loaded_fixture_case(fixture_path, name):
    fixture_path = Path(fixture_path).resolve()
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    if fixture.get("stage") != "prepared":
        raise ValueError("grade-case requires a prepared fixture")
    for case in fixture["cases"]:
        if case["name"] == name:
            root = fixture_path.parent
            for field in ("case_root", "home", "work", "runtime", "skill_root"):
                inside(root, Path(case[field]))
            return fixture, case, root
    raise ValueError("unknown prepared case: " + name)


def journey_locates(runtime, slug, binding):
    """Check installed artifacts, then use trusted source without fixture imports."""
    for relative in ("bin/gl-run", "bin/gl-journey"):
        installed, trusted = runtime / relative, TRUSTED_RUNTIME / relative
        if not installed.is_file() or installed.is_symlink() or installed.read_bytes() != trusted.read_bytes():
            raise ValueError("installed helper differs from trusted source: " + relative)
    old_argv, old_env = sys.argv[:], dict(os.environ)
    output = io.StringIO()
    try:
        trusted = TRUSTED_RUNTIME / "bin/gl-journey"
        sys.argv = [str(trusted), "--locate", slug]
        os.environ["GROWTH_LOOP_HOME"] = binding["data"]
        os.environ["GROWTH_LOOP_SKILL_ROOTS"] = binding["root"]
        os.environ["GROWTH_LOOP_RUNTIME"] = binding["runtime"]
        with contextlib.redirect_stdout(output):
            try:
                runpy.run_path(str(trusted), run_name="__main__")
            except SystemExit as exc:
                return exc.code or 0, output.getvalue().strip()
        return 0, output.getvalue().strip()
    finally:
        sys.argv = old_argv; os.environ.clear(); os.environ.update(old_env)


def grade_case(fixture_path, name, native_result):
    fixture, case, root = loaded_fixture_case(fixture_path, name)
    if not isinstance(native_result, dict) or not isinstance(native_result.get("exit_code"), int):
        raise ValueError("native result needs an integer exit_code")
    invoked = native_result.get("invoked_skills")
    if invoked is not None and (not isinstance(invoked, list) or not all(isinstance(x, str) for x in invoked)):
        raise ValueError("invoked_skills must be an array of strings or null")
    for field in ("routes", "slugs"):
        value = native_result.get(field)
        if value is not None and (not isinstance(value, list) or not all(isinstance(x, str) for x in value)):
            raise ValueError(field + " must be an array of strings or null")
    skill_root, home, runtime = map(Path, (case["skill_root"], case["home"], case["runtime"]))
    binding_path = regular_inside(root, runtime / "binding.json")
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    data_raw = binding.get("data")
    data = Path(data_raw) if isinstance(data_raw, str) and data_raw else None
    if (binding.get("runtime") != fixture["host"] or binding.get("root") != str(skill_root)
            or data is None or data.is_symlink()):
        raise ValueError("fixture binding does not match its prepared case")
    inside(root, data)
    after = {path.parent.name for path in skill_root.glob("*/SKILL.md") if inside(root, path)}
    before = set(case["before_skills"])
    new = after - before
    checks = []
    expect = {**case["expect"], **(case["expect_codex"] if fixture["host"] == "codex" else {})}
    if "no_new_skill_directory" in expect:
        checks.append({"name": "no_new_skill_directory", "status": "pass" if not new else "fail",
                       "evidence": "skills-root"})
    if "exactly_one_new_skill_directory" in expect:
        ok = len(new) == 1 and (skill_root / next(iter(new), "") / "SKILL.md").is_file()
        checks.append({"name": "exactly_one_new_skill_directory", "status": "pass" if ok else "fail",
                       "evidence": "skills-root"})
    if expect.get("journey_lists_new_skill"):
        slug = next(iter(new), "")
        code, location = journey_locates(runtime, slug, binding) if slug else (1, "")
        ok = code == 0 and Path(location).resolve() == (skill_root / slug).resolve()
        checks.append({"name": "journey_lists_new_skill", "status": "pass" if ok else "fail",
                       "evidence": "installed-gl-run"})
    values = {"home": str(home), "skills_root": str(skill_root)}
    for template in expect.get("files_present", []):
        path = inside(root, Path(template.format(**values)))
        if path.exists() or path.is_symlink(): regular_inside(root, path)
        checks.append({"name": "files_present", "status": "pass" if path.is_file() else "fail", "evidence": str(path.relative_to(root))})
    for template in expect.get("files_absent", []):
        path = inside(root, Path(template.format(**values)))
        if path.exists() or path.is_symlink(): regular_inside(root, path)
        checks.append({"name": "files_absent", "status": "pass" if not path.exists() else "fail", "evidence": str(path.relative_to(root))})
    for key, expected_present in (("stdout_contains", True), ("stdout_absent", False)):
        routes, slugs = native_result.get("routes"), native_result.get("slugs")
        for token in expect.get(key, []):
            reported = routes if token.startswith("/growth-loop:") else slugs
            status = "unknown" if reported is None else ("pass" if (token in reported) == expected_present else "fail")
            checks.append({"name": key, "status": status, "evidence": "native-routes-or-slugs"})
    profile = data / "profile.md"
    if profile.exists(): regular_inside(root, profile)
    profile_text = profile.read_text(encoding="utf-8") if profile.is_file() else ""
    for needle in expect.get("profile_contains", []):
        checks.append({"name": "profile_contains", "status": "pass" if needle in profile_text else "fail", "evidence": "profile.md"})
    for needle in expect.get("profile_absent", []):
        checks.append({"name": "profile_absent", "status": "pass" if needle not in profile_text else "fail", "evidence": "profile.md"})
    expected_skill = case["name"].split("-", 1)[0]
    invoked_status = "unknown" if invoked is None else ("pass" if expected_skill in invoked else "fail")
    checks.append({"name": "structured_invocation", "status": invoked_status, "evidence": "native-result"})
    checks.append({"name": "exit_code", "status": "pass" if native_result["exit_code"] == 0 else "fail", "evidence": "native-result"})
    outcome = "fail" if any(c["status"] == "fail" for c in checks) else ("unknown" if any(c["status"] == "unknown" for c in checks) else "pass")
    return {"version": 1, "case": name, "host": fixture["host"], "model": native_result.get("model", "unknown"),
            "variant": native_result.get("variant", "current"), "run": native_result.get("run", 1), "outcome": outcome,
            "checks": checks, "invoked_skills": invoked, "loaded_documents": None, "git_writes": None,
            "elapsed_ms": None, "token_usage": None,
            "conditions": {"fixture": str(root), "runner": native_result.get("runner", "native-host"), "task": name},
            "fixture_root": str(root)}


def main():
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="command", required=True)
    prepared = sub.add_parser("prepare"); prepared.add_argument("--output", required=True); prepared.add_argument("--host", choices=("claude", "codex"), default="claude")
    requested = sub.add_parser("request"); requested.add_argument("--fixture", required=True); requested.add_argument("--output", required=True); requested.add_argument("--host", required=True); requested.add_argument("--model", default="unknown"); requested.add_argument("--runner", required=True); requested.add_argument("--runner-receipt")
    case_grade = sub.add_parser("grade-case"); case_grade.add_argument("--fixture", required=True); case_grade.add_argument("--case", required=True); case_grade.add_argument("--native-result", required=True)
    graded = sub.add_parser("grade"); graded.add_argument("--records", required=True); graded.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "prepare": result = prepare(args.output, args.host)
    elif args.command == "request": result = request(args.fixture, args.output, args.host, args.model, args.runner, json.loads(args.runner_receipt) if args.runner_receipt else None)
    elif args.command == "grade-case": result = grade_case(args.fixture, args.case, json.loads(Path(args.native_result).read_text(encoding="utf-8")))
    else:
        from evaluation import grade_file
        result = grade_file(args.records, args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()
