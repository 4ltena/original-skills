#!/usr/bin/env python3
"""Read-only original-skills installation diagnosis; Python standard library only."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PureWindowsPath
import re
import stat
import subprocess
import sys


MAX_JSON = 1024 * 1024
MAX_ARTIFACT = 1024 * 1024
MAX_OBSERVATIONS = 16384
EVENTS = {"SessionStart", "UserPromptSubmit", "PostToolUse", "Stop", "Interrupt", "SessionEnd"}
SURFACES = {"cli", "desktop", "ide", "chat"}
NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
FRONTMATTER_NAME = re.compile(r"(?m)^name:\s*(?:[\"']([^\"']+)[\"']|([^\s#]+))\s*(?:#.*)?$")
HASH = re.compile(r"^[0-9a-f]{64}$")
ENV = Path(__file__).resolve().parent
SOURCE_ROOT = ENV.parent if ENV.name == "environment" and (ENV / "install.py").is_file() else None


class DiagnosticError(Exception):
    def __init__(self, code):
        self.code = code


def unsafe_component(path):
    for part in [*reversed(path.parents), path]:
        if not part.exists() and not part.is_symlink():
            continue
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            return True
    return False


def read_bytes(path, limit):
    path = Path(path).absolute()
    if unsafe_component(path):
        raise DiagnosticError("unsafe_path")
    try:
        info = path.lstat()
    except FileNotFoundError:
        raise DiagnosticError("missing")
    if not stat.S_ISREG(info.st_mode):
        raise DiagnosticError("not_regular")
    if info.st_size > limit:
        raise DiagnosticError("oversize")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        raise DiagnosticError("unreadable") from None
    try:
        opened = os.fstat(descriptor)
        if (not stat.S_ISREG(opened.st_mode) or opened.st_size != info.st_size
                or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino)):
            raise DiagnosticError("changed_during_read")
        chunks = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65536, limit + 1 - total))
            if not chunk:
                break
            chunks.append(chunk); total += len(chunk)
            if total > limit:
                raise DiagnosticError("oversize")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def read_object(path, limit=MAX_JSON):
    try:
        value = json.loads(read_bytes(path, limit))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise DiagnosticError("malformed_json") from None
    if not isinstance(value, dict):
        raise DiagnosticError("object_required")
    return value


def relative_path(value):
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise DiagnosticError("invalid_receipt")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or len(path.parts) > 20:
        raise DiagnosticError("invalid_receipt")
    return path


def hash_artifact(path, expected_size):
    if type(expected_size) is not int or not 0 <= expected_size <= MAX_ARTIFACT:
        return "invalid_receipt", None
    try:
        raw = read_bytes(path, MAX_ARTIFACT)
    except DiagnosticError as exc:
        return exc.code, None
    if len(raw) != expected_size:
        return "drift", None
    return "current", hashlib.sha256(raw).hexdigest()


def load_inputs(plan_path, answers_path, host, home, project):
    plan = answers = None
    if plan_path:
        plan = read_object(plan_path)
        answers = plan.get("answers")
        if not isinstance(answers, dict):
            raise DiagnosticError("invalid_plan")
        if plan.get("home") != str(home):
            raise DiagnosticError("selection_mismatch")
    if answers_path:
        supplied = read_object(answers_path)
        if answers is not None and supplied != answers:
            raise DiagnosticError("selection_mismatch")
        answers = supplied
    if answers is not None:
        requested = answers.get("host")
        if requested not in {host, "both"}:
            raise DiagnosticError("selection_mismatch")
        if project is not None and answers.get("project_path") not in {None, str(project)}:
            raise DiagnosticError("selection_mismatch")
    selected = plan.get("selected_skills") if isinstance(plan, dict) else None
    if selected is not None and (not isinstance(selected, list) or any(not NAME.fullmatch(str(n)) for n in selected)):
        raise DiagnosticError("invalid_plan")
    if selected is None and answers is not None and answers.get("skills") == "custom":
        selected = answers.get("skill_names")
    return answers or {}, sorted(set(selected or []))


def load_receipt(root, host):
    path = root / "original-skills/install-receipt.json"
    try:
        value = read_object(path)
    except DiagnosticError as exc:
        return None, {"status": exc.code, "path": str(path)}
    if value.get("version") != 1 or value.get("host") != host or value.get("root") != str(root):
        return None, {"status": "invalid_receipt", "path": str(path)}
    selection = value.get("selection")
    source = value.get("source")
    projection = value.get("projection")
    if not isinstance(selection, dict) or not isinstance(source, dict) or not isinstance(projection, dict):
        return None, {"status": "invalid_receipt", "path": str(path)}
    selected = selection.get("selected_skills")
    files = projection.get("files")
    preserved = projection.get("preserved", [])
    surface = selection.get("surface")
    source_root = source.get("root")
    valid_root = (isinstance(source_root, str) and len(source_root) <= 4096
                  and (Path(source_root).is_absolute() or PureWindowsPath(source_root).is_absolute())
                  and ".." not in Path(source_root).parts and ".." not in PureWindowsPath(source_root).parts)
    if (not isinstance(selected, list) or len(selected) > 128 or any(not NAME.fullmatch(str(n)) for n in selected)
            or (surface is not None and (not isinstance(surface, str) or surface not in SURFACES))
            or not valid_root or not HASH.fullmatch(str(source.get("sha256", "")))
            or not isinstance(files, list) or len(files) > 4096
            or not isinstance(preserved, list) or len(preserved) > 512
            or any(not isinstance(path, str) or len(path) > 4096 for path in preserved)
            or not valid_hooks(value.get("hooks"))):
        return None, {"status": "invalid_receipt", "path": str(path)}
    plugins = selection.get("plugins", [])
    if (not isinstance(plugins, list) or len(plugins) > 32
            or any(not NAME.fullmatch(str(name)) for name in plugins)
            or not valid_source_entries(source.get("files"), selected, plugins)
            or any(not valid_projection_entry(item, source.get("files", []), selected, plugins) for item in files)):
        return None, {"status": "invalid_receipt", "path": str(path)}
    return value, {"status": "current", "path": str(path)}


def safe_source_path(value):
    try:
        path = relative_path(value)
    except DiagnosticError:
        return None
    return path


def valid_source_entries(entries, selected, plugins):
    if not isinstance(entries, list) or len(entries) > 4096:
        return False
    for item in entries:
        if not isinstance(item, dict) or not HASH.fullmatch(str(item.get("sha256", ""))):
            return False
        path = safe_source_path(item.get("path"))
        if path is None or type(item.get("size")) is not int or not 0 <= item["size"] <= MAX_ARTIFACT:
            return False
        parts = path.parts
        hidden_plugin_metadata = (parts[0] == "plugins" and all(not part.startswith(".") or part in {".claude-plugin", ".codex-plugin"} for part in parts))
        if any(part.startswith(".") for part in parts) and not hidden_plugin_metadata:
            return False
        allowed = (str(path) in {"environment/runtime.py", "environment/doctor.py", "environment/HOSTS.md", "environment/scripts/git_guard.py"}
                   or (len(parts) >= 3 and parts[0] == "skills" and parts[1] in selected)
                   or (len(parts) >= 5 and parts[:3] == ("plugins", "workflow", "skills") and parts[3] in selected)
                   or (len(parts) >= 3 and parts[:3] == ("skills", "growth-loop", "growth-loop") and "growth-loop" in plugins)
                   or (len(parts) >= 3 and parts[0] == "plugins" and parts[1] in plugins))
        if not allowed:
            return False
    return True


def valid_projection_entry(item, source_entries, selected, plugins):
    if not isinstance(item, dict) or not HASH.fullmatch(str(item.get("sha256", ""))):
        return False
    path = safe_source_path(item.get("path"))
    if path is None or type(item.get("size")) is not int or not 0 <= item["size"] <= MAX_ARTIFACT:
        return False
    source_paths = {entry["path"] for entry in source_entries if isinstance(entry, dict) and isinstance(entry.get("path"), str)}
    text = str(path)
    if len(path.parts) >= 3 and path.parts[0] == "skills" and path.parts[1] in selected:
        suffix = "/".join(path.parts[2:])
        return (text in source_paths or "plugins/workflow/skills/" + path.parts[1] + "/" + suffix in source_paths
                or "plugins/" + path.parts[1] + "/skills/" + path.parts[1] + "/" + suffix in source_paths)
    if len(path.parts) == 3 and path.parts[0] == "original-skills" and path.parts[1] in plugins and path.parts[2] == "binding.json":
        return True
    if len(path.parts) == 4 and path.parts[0] == "original-skills" and path.parts[1] in plugins and path.parts[2:] == ("hooks", "hooks.json"):
        return True
    if len(path.parts) >= 3 and path.parts[:2] == ("original-skills", "growth-loop"):
        return "skills/growth-loop/growth-loop/" + "/".join(path.parts[2:]) in source_paths
    if len(path.parts) >= 3 and path.parts[0] == "original-skills" and path.parts[1] in plugins:
        return "plugins/" + path.parts[1] + "/" + "/".join(path.parts[2:]) in source_paths
    generated = {"original-skills/runtime.py", "original-skills/doctor.py", "original-skills/git_guard.py",
                 "original-skills/HOSTS.md", "original-skills/binding.json", "original-skills/host-policy.md",
                 "original-skills/manual-git.rules.candidate", "original-skills/readers.rules.candidate",
                 "original-skills-settings.candidate.json", "CLAUDE.md", "CLAUDE.md.candidate", "AGENTS.md",
                 "AGENTS.md.candidate", "settings.json", "hooks.json", "rules/original-skills-manual-git.rules",
                 "rules/original-skills-readers.rules", "standard-github-policy.md", "local-policy.md",
                 "host-read-policy.md"}
    if text in generated:
        return True
    return False


def projection_status(root, receipt):
    records = {}
    counts = {"current": 0, "drift": 0, "missing": 0, "unsafe": 0, "invalid": 0}
    for item in receipt.get("projection", {}).get("files", []):
        if not isinstance(item, dict) or not HASH.fullmatch(str(item.get("sha256", ""))):
            counts["invalid"] += 1; continue
        try:
            relative = relative_path(item.get("path"))
        except DiagnosticError:
            counts["invalid"] += 1; continue
        state, digest = hash_artifact(root / relative, item.get("size"))
        if state == "current" and digest != item["sha256"]:
            state = "drift"
        bucket = state if state in counts else ("unsafe" if state in {"unsafe_path", "not_regular"} else "invalid")
        counts[bucket] += 1
        records[str(relative)] = state
    return records, counts


def source_status(receipt):
    source = receipt.get("source", {})
    matches_current = SOURCE_ROOT is not None and source.get("root") == str(SOURCE_ROOT)
    recorded = {"identity": "current_source" if matches_current else None, "sha256": source.get("sha256")}
    if not matches_current:
        return {**recorded, "status": "recorded_only"}
    files = source.get("files")
    if not isinstance(files, list) or len(files) > 512:
        return {**recorded, "status": "invalid_receipt"}
    current = []
    for item in files:
        if not isinstance(item, dict) or not HASH.fullmatch(str(item.get("sha256", ""))):
            return {**recorded, "status": "invalid_receipt"}
        try:
            relative = relative_path(item.get("path"))
        except DiagnosticError:
            return {**recorded, "status": "invalid_receipt"}
        state, digest = hash_artifact(SOURCE_ROOT / relative, item.get("size"))
        if state != "current":
            return {**recorded, "status": "drift"}
        current.append({"path": str(relative), "sha256": digest, "size": item["size"]})
    digest = hashlib.sha256(json.dumps(current, sort_keys=True).encode()).hexdigest()
    return {**recorded, "status": "current" if digest == source.get("sha256") else "drift"}


def skill_status(root, receipt, records, selected_fallback):
    if receipt is None:
        return [{"name": name, "state": "unknown"} for name in selected_fallback]
    selected = receipt["selection"]["selected_skills"]
    preserved = set(receipt.get("projection", {}).get("preserved", []))
    result = []
    for name in selected:
        prefix = "skills/" + name + "/"
        states = [state for path, state in records.items() if path.startswith(prefix)]
        custom = str(root / "skills" / name) in preserved
        if not states:
            state = "custom_preserved" if custom else "unknown"
        elif any(value == "missing" for value in states):
            state = "missing"
        elif any(value != "current" for value in states):
            state = "drift"
        elif custom:
            # A preserved directory can still contain an earlier receipt's known
            # projection. Its hashes are stronger evidence than the preserved flag.
            state = "current"
        else:
            source_files = receipt.get("source", {}).get("files", [])
            source_hashes = {item.get("sha256") for item in source_files if isinstance(item, dict)}
            target_items = receipt.get("projection", {}).get("files", [])
            transformed = any(item.get("path", "").startswith(prefix) and item.get("sha256") not in source_hashes
                              for item in target_items if isinstance(item, dict))
            state = "transformed_current" if transformed else "current"
        result.append({"name": name, "state": state})
    return result


def binding_status(root, host, receipt, probe):
    path = root / "original-skills/binding.json"
    try:
        value = read_object(path, 16384)
    except DiagnosticError as exc:
        return {"status": exc.code, "path": str(path), "prerequisite": "unknown"}
    executable = value.get("executable")
    version = value.get("version")
    platform = value.get("platform")
    if (not isinstance(executable, str) or not Path(executable).is_absolute()
            or not isinstance(version, list) or len(version) != 3 or any(type(n) is not int for n in version)
            or platform not in {"darwin", "linux", "win32"}):
        return {"status": "malformed", "path": str(path), "prerequisite": "unknown"}
    recorded = receipt.get("binding") if receipt else None
    status = "recorded_current" if isinstance(recorded, dict) and all(value.get(k) == recorded.get(k) for k in ("executable", "version", "platform")) else "unrecorded"
    windows_alias = "windowsapps" in executable.lower()
    exists = Path(executable).is_file() and not windows_alias
    prerequisite = "unsupported" if windows_alias or version[:2] < [3, 10] else "declared"
    result = {"status": status, "path": str(path), "executable": executable,
              "version": version, "platform": platform, "present": exists,
              "prerequisite": prerequisite, "executed": False}
    if probe:
        result["probe_matches_binding"] = (probe.get("status") == "verified"
            and Path(probe["executable"]).resolve() == Path(executable).resolve()
            and probe["version"] == version and probe.get("platform") == platform)
        if result["probe_matches_binding"]:
            result["prerequisite"] = "verified"
    return result


def probe_python(executable):
    if executable is None:
        return {"status": "not_requested"}
    path = Path(executable).expanduser().absolute()
    if not path.is_absolute() or "windowsapps" in str(path).lower() or not path.is_file():
        return {"status": "rejected"}
    try:
        completed = subprocess.run([str(path), "-I", "-X", "utf8", "-c",
            "import sys,json;print(json.dumps({'version':list(sys.version_info[:3]),'executable':sys.executable,'platform':sys.platform}))"],
            capture_output=True, text=True, encoding="utf-8", timeout=10, check=True)
        value = json.loads(completed.stdout)
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError, json.JSONDecodeError):
        return {"status": "failed"}
    version = value.get("version")
    actual = value.get("executable")
    if (not isinstance(version, list) or len(version) != 3 or any(type(n) is not int for n in version)
            or version[:2] < [3, 10] or not isinstance(actual, str)
            or Path(actual).resolve() != path.resolve() or value.get("platform") not in {"darwin", "linux", "win32"}):
        return {"status": "failed"}
    return {"status": "verified", "executable": actual, "version": version, "platform": value["platform"]}


def catalog(home, scope, host):
    suffix = ".claude" if host == "claude" else ".codex"
    roots = [home / suffix / "skills", home / ".agents/skills"]
    if scope != home:
        roots += [scope / suffix / "skills", scope / ".agents/skills"]
    names = {}
    scanned = []
    skipped = 0
    for root in dict.fromkeys(roots):
        if not root.exists():
            scanned.append({"path": str(root), "status": "missing"}); continue
        if unsafe_component(root) or not root.is_dir():
            scanned.append({"path": str(root), "status": "unsafe"}); continue
        scanned.append({"path": str(root), "status": "scanned"})
        try:
            entries = list(root.iterdir())
        except OSError:
            scanned[-1]["status"] = "unreadable"; continue
        for entry in entries:
            try:
                info = entry.lstat()
            except OSError:
                skipped += 1; continue
            if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)
                    or getattr(info, "st_file_attributes", 0) & 0x400):
                skipped += 1; continue
            try:
                raw = read_bytes(entry / "SKILL.md", 65536).decode("utf-8")
            except (DiagnosticError, UnicodeDecodeError):
                skipped += 1; continue
            match = FRONTMATTER_NAME.search(raw)
            name = (match.group(1) or match.group(2)) if match else None
            if not name or not NAME.fullmatch(name):
                skipped += 1; continue
            names.setdefault(name, []).append(str(root))
    duplicates = [{"name": name, "roots": paths} for name, paths in sorted(names.items()) if len(paths) > 1]
    return {"scope": "known_roots_only", "roots": scanned, "duplicates": duplicates, "skipped": skipped}


def hook_summary(value, runtime_root):
    """Return counts only; hook commands and unrelated settings never escape."""
    hooks = value.get("hooks", {}) if isinstance(value, dict) else None
    result = {"status": "declared", "current": 0, "stale": 0, "other": 0,
              "duplicates": 0, "events": {}}
    if not isinstance(hooks, dict):
        result["status"] = "malformed"
        return result
    seen = set()
    for event, groups in hooks.items():
        if not isinstance(event, str) or not isinstance(groups, list):
            result["status"] = "malformed"
            continue
        counts = {"current": 0, "stale": 0, "other": 0}
        for group in groups:
            values = group.get("hooks") if isinstance(group, dict) else None
            if not isinstance(values, list):
                result["status"] = "malformed"
                continue
            for item in values:
                command = item.get("command") if isinstance(item, dict) else None
                args = item.get("args", []) if isinstance(item, dict) else None
                if not isinstance(command, str) or not isinstance(args, list) or any(not isinstance(arg, str) for arg in args):
                    result["status"] = "malformed"
                    continue
                text = "\0".join([command, *args])
                state = "current" if str(runtime_root) in text else ("stale" if "original-skills" in text else "other")
                signature = json.dumps([event, command, args], ensure_ascii=False, sort_keys=True)
                if signature in seen:
                    result["duplicates"] += 1
                seen.add(signature)
                result[state] += 1
                counts[state] += 1
        result["events"][event] = counts
    return result


def valid_hook_summary(value):
    if not isinstance(value, dict) or value.get("status") not in {"declared", "not_requested"}:
        return False
    if value["status"] == "not_requested":
        return set(value) == {"status"}
    if set(value) != {"status", "current", "stale", "other", "duplicates", "events"}:
        return False
    if any(type(value[key]) is not int or value[key] < 0 for key in ("current", "stale", "other", "duplicates")):
        return False
    events = value["events"]
    if not isinstance(events, dict) or len(events) > len(EVENTS | {"PreToolUse"}):
        return False
    for event, counts in events.items():
        if event not in EVENTS | {"PreToolUse"} or not isinstance(counts, dict) or set(counts) != {"current", "stale", "other"}:
            return False
        if any(type(number) is not int or number < 0 for number in counts.values()):
            return False
    return True


def sanitized_hook_summary(value):
    if not valid_hook_summary(value):
        return {"status": "invalid_receipt"}
    if value["status"] == "not_requested":
        return {"status": "not_requested"}
    return {"status": "declared", "current": value["current"], "stale": value["stale"],
            "other": value["other"], "duplicates": value["duplicates"],
            "events": {event: {key: counts[key] for key in ("current", "stale", "other")}
                       for event, counts in value["events"].items()}}


def valid_hooks(value):
    return (isinstance(value, dict) and valid_hook_summary(value.get("candidate"))
            and valid_hook_summary(value.get("installed")))


def live_hooks(root, host):
    targets = {"candidate": root / "original-skills-settings.candidate.json",
               "installed": root / ("settings.json" if host == "claude" else "hooks.json")}
    result = {}
    for name, path in targets.items():
        try:
            result[name] = hook_summary(read_object(path), root / "original-skills")
        except DiagnosticError as exc:
            result[name] = {"status": exc.code}
    return result


def plugin_binding_status(root, host, receipt):
    if receipt is None:
        return []
    result = []
    selected = receipt.get("selection", {}).get("plugins", [])
    if not isinstance(selected, list) or len(selected) > 32:
        return [{"name": "unknown", "status": "invalid_receipt"}]
    expected_binding = receipt.get("binding", {})
    for name in selected:
        if not NAME.fullmatch(str(name)):
            return [{"name": "unknown", "status": "invalid_receipt"}]
        path = root / "original-skills" / name / "binding.json"
        try:
            value = read_object(path, 16384)
        except DiagnosticError as exc:
            result.append({"name": name, "status": exc.code})
            continue
        expected = {"runtime": host, **{key: expected_binding.get(key) for key in ("executable", "version", "platform")}}
        if name == "growth-loop":
            expected["version"] = 1
            expected["root"] = str(root / "skills")
        if all(value.get(key) == item for key, item in expected.items()):
            result.append({"name": name, "status": "recorded_current"})
        else:
            result.append({"name": name, "status": "drift"})
    return result


def checkpoint_status(root):
    path = root / "original-skills-data/goal-checkpoint/goal-checkpoint/hook-observations.json"
    try:
        value = read_object(path, MAX_OBSERVATIONS)
    except DiagnosticError as exc:
        return {"receipt": {"status": exc.code, "path": str(path)},
                "delivery": "unknown", "trust": "unknown"}
    observations = value.get("observations")
    if value.get("version") != 1 or not isinstance(observations, list) or len(observations) > 32:
        return {"receipt": {"status": "malformed", "path": str(path)}, "delivery": "unknown", "trust": "unknown"}
    events = {}; outcomes = {}; latest = None; maximum = 0
    for item in observations:
        if not isinstance(item, dict) or set(item) != {"event", "at", "elapsed_ms", "outcome"}:
            return {"receipt": {"status": "malformed", "path": str(path)}, "delivery": "unknown", "trust": "unknown"}
        event, at, elapsed, outcome = item["event"], item["at"], item["elapsed_ms"], item["outcome"]
        if (event not in EVENTS or outcome not in {"ok", "error"}
                or isinstance(at, bool) or not isinstance(at, (int, float)) or not math.isfinite(at) or at < 0
                or isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)) or not math.isfinite(elapsed) or elapsed < 0):
            return {"receipt": {"status": "malformed", "path": str(path)}, "delivery": "unknown", "trust": "unknown"}
        events[event] = events.get(event, 0) + 1; outcomes[outcome] = outcomes.get(outcome, 0) + 1
        latest = at if latest is None else max(latest, at); maximum = max(maximum, elapsed)
    return {"receipt": {"status": "valid_unverified_origin", "path": str(path), "count": len(observations),
        "latest_at": latest, "events": events, "outcomes": outcomes, "max_elapsed_ms": maximum},
        "delivery": "unknown", "trust": "unknown"}


def diagnose_host(host, home, scope, answers, selected, probe):
    root = scope / (".claude" if host == "claude" else ".codex")
    receipt, receipt_state = load_receipt(root, host)
    records, projection = projection_status(root, receipt) if receipt else ({}, {"current": 0, "drift": 0, "missing": 0, "unsafe": 0, "invalid": 0})
    if receipt and not selected:
        selected = receipt["selection"]["selected_skills"]
    hooks = receipt.get("hooks") if receipt else None
    observed_hooks = live_hooks(root, host)
    surface = receipt.get("selection", {}).get("surface") if receipt else answers.get("surface")
    eligible = False if host == "claude" and surface == "chat" else (True if surface else None)
    findings = []
    if receipt is None:
        findings.append({"code": "receipt_unknown", "level": "unknown"})
    if projection["drift"] or projection["missing"] or projection["unsafe"] or projection["invalid"]:
        findings.append({"code": "installed_projection_changed", "level": "warning"})
    if hooks:
        for where in ("candidate", "installed"):
            item = hooks.get(where, {})
            if item.get("duplicates", 0):
                findings.append({"code": where + "_hook_duplicate", "level": "warning"})
            if item.get("stale", 0):
                findings.append({"code": where + "_hook_stale", "level": "warning"})
    return {
        "host": host, "root": str(root), "surface": surface or "unknown",
        "version": {"status": "unknown", "value": None},
        "receipt": receipt_state, "source": source_status(receipt) if receipt else {"status": "unknown"},
        "projection": projection, "python": binding_status(root, host, receipt, probe),
        "skills": skill_status(root, receipt, records, selected), "catalog": catalog(home, scope, host),
        "plugin_bindings": plugin_binding_status(root, host, receipt),
        "hooks": {"declared_eligible": eligible, "support": "unknown",
                  "candidate": {"receipt": sanitized_hook_summary(hooks.get("candidate")) if hooks else {"status": "unknown"},
                                "current": observed_hooks["candidate"]},
                  "installed": {"receipt": sanitized_hook_summary(hooks.get("installed")) if hooks else {"status": "unknown"},
                                "current": observed_hooks["installed"]},
                  "runtime_delivery": "unknown"},
        "trust": {"status": "unknown", "evidence": None},
        "runtime": {"status": "unknown", "evidence": None},
        "checkpoint": checkpoint_status(root), "findings": findings,
    }


def run(args):
    home = Path(args.home).expanduser().absolute()
    project = Path(args.project).expanduser().absolute() if args.project else None
    if unsafe_component(home) or not home.is_dir() or project and (unsafe_component(project) or not project.is_dir()):
        raise DiagnosticError("unsafe_selection")
    scope = project or home
    answers, selected = load_inputs(args.plan, args.answers, args.host, home, project)
    probe = probe_python(args.probe_python)
    hosts = ["claude", "codex"] if args.host == "both" else [args.host]
    reports = [diagnose_host(host, home, scope, answers, selected, probe) for host in hosts]
    warnings = sum(item["level"] == "warning" for report in reports for item in report["findings"])
    unknowns = sum(item["level"] == "unknown" for report in reports for item in report["findings"])
    return {"version": 1, "read_only": True,
            "selection": {"host": args.host, "home": str(home), "project": str(project) if project else None,
                          "plan": bool(args.plan), "answers": bool(args.answers)},
            "optional_probe": probe, "hosts": reports,
            "summary": {"warnings": warnings, "unknowns": unknowns,
                        "runtime_verified": False, "trust_verified": False}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", choices=("claude", "codex", "both"), required=True)
    parser.add_argument("--home", required=True)
    parser.add_argument("--project")
    parser.add_argument("--plan")
    parser.add_argument("--answers")
    parser.add_argument("--probe-python")
    args = parser.parse_args()
    try:
        output = run(args)
    except DiagnosticError as exc:
        output = {"version": 1, "read_only": True, "error": {"code": exc.code}}
        print(json.dumps(output, ensure_ascii=False, indent=2)); return 1
    print(json.dumps(output, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__":
    sys.exit(main())
