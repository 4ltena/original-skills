"""Agent-led installation: questions -> reviewed plan -> bounded writes. No CLI dependency."""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
import subprocess
import platform

from runtime import probe, python_command, safe_path

ENV = Path(__file__).resolve().parent
REPO = ENV.parent
PLUGIN_NAMES = {"workflow", "growth-loop", "goal-checkpoint"}
BASIC = {"workflow", "smallest-change", "spec-first-development", "project-handoff", "completion-report"}
DOCUMENTS = {"document-writing", "document-rewriting", "document-authoring", "document-sources",
             "document-style-ja", "document-files", "document-translation", "japanese-writing-refine"}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def inventory():
    result = {}
    # Prefer maintained plugin copies for the duplicated workflow skills.
    for base in (REPO / "skills", REPO / "plugins"):
        for path in sorted(base.rglob("SKILL.md")):
            match = re.search(r"^name:\s*[\"']?([a-z0-9-]+)", path.read_text(encoding="utf-8"), re.M)
            if not match:
                raise ValueError("missing skill name: " + str(path))
            result[match[1]] = path.parent
    return result


def questions(answers, home=None):
    definitions = json.loads((ENV / "questions.json").read_text(encoding="utf-8"))["questions"]
    known = {q["id"] for q in definitions} | {"project_path", "skill_names", "growth_root", "surface"}
    if set(answers) - known:
        raise ValueError("unknown answer ID")
    for q in definitions:
        condition = q.get("when")
        applicable = (not condition or
            "plugins" in condition and condition["plugins"] in answers.get("plugins", []) or
            "host" in condition and answers.get("host") in condition["host"])
        if not applicable:
            if q["id"] in answers:
                raise ValueError("inapplicable answer: " + q["id"])
            continue
        if q["id"] not in answers:
            if q['id'] == 'growth_root':
                scope = safe_path(answers['project_path']) if answers['scope'] == 'project' else safe_path(home or Path.home())
                hosts = ['claude', 'codex'] if answers['host'] == 'both' else [answers['host']]
                q = {**q, 'paths': {host: str(scope / ('.claude' if host == 'claude' else '.codex') / 'skills') for host in hosts}}
            return q
        answer = answers[q["id"]]
        if q.get("type") == "multi":
            if (not isinstance(answer, list) or len(answer) != len(set(answer))
                    or not set(answer) <= set(q["options"])):
                raise ValueError("invalid choices: " + q["id"])
        elif answer not in q["options"]:
            raise ValueError("invalid answer: " + q["id"])
        if q["id"] == "scope" and answer == "project" and not answers.get("project_path"):
            return {"id": "project_path", "prompt": "既存projectの絶対pathを指定してください。", "type": "path"}
        if q["id"] == "skills" and answer == "custom" and "skill_names" not in answers:
            return {"id": "skill_names", "prompt": "導入するSkill名を配列で指定してください。", "options": sorted(inventory()), "type": "multi"}
    if answers.get("host") == "codex" and "surface" in answers:
        raise ValueError("surface is only a Claude selection")
    return None


def skill_selection(answers, available):
    choice = answers["skills"]
    if choice == "all":
        selected = set(available)
    elif choice == "basic":
        selected = BASIC.copy()
    elif choice == "documents":
        selected = DOCUMENTS.copy()
    elif choice == "development":
        selected = BASIC | {n for n in available if n.startswith(("git-", "gh-", "frontend-optimize"))}
    else:
        values = answers["skill_names"]
        if not isinstance(values, list) or any(not isinstance(n, str) for n in values):
            raise ValueError("skill_names must be an array")
        selected = set(values)
    if not selected <= set(available):
        raise ValueError("unknown skill names")
    plugins = set(answers["plugins"])
    growth = {"learn", "forget", "refine", "jot", "journey", "profile", "recall"}
    if selected & growth and "growth-loop" not in plugins:
        raise ValueError("selected growth-loop skills require selecting its runtime plugin")
    if "goal-checkpoint" in selected and "goal-checkpoint" not in plugins:
        raise ValueError("goal-checkpoint requires selecting its runtime plugin")
    for name in plugins:
        base = (REPO / "skills/growth-loop/growth-loop/skills") if name == "growth-loop" else REPO / "plugins" / name / "skills"
        selected |= {p.parent.name for p in base.glob("*/SKILL.md")}
    # Procedures that require a companion Skill bring it into the review plan explicitly.
    dependencies = {"workflow": {"spec-first-development", "project-handoff", "completion-report"},
        "spec-first-development": {"plan-review-loop"}, "git-operations": {"git-read-inspection", "git-writing"},
        "gh-operations": {"gh-read-inspection"}, "h5i-capture-read": {"h5i-read-inspection"},
        "releasing": {"git-operations", "gh-operations"}, "document-translation": {"document-style-ja"}}
    required = selected.copy()
    while True:
        expanded = required | {d for n in required for d in dependencies.get(n, set())}
        if expanded == required:
            break
        required = expanded
    return sorted(required), sorted(required - selected)


def files_in(root):
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("symlink in source")
        if path.is_file() and not any(p in {"__pycache__", ".DS_Store"} for p in path.parts):
            yield path


def plan(answers, home, executable=None):
    missing = questions(answers, home)
    if missing:
        raise ValueError("answer required: " + missing["id"])
    home = safe_path(home)
    if not home.is_dir():
        raise ValueError("target home must exist")
    scope = home
    if answers["scope"] == "project":
        scope = safe_path(answers["project_path"])
        if not scope.is_dir() or not Path(answers["project_path"]).is_absolute():
            raise ValueError("project_path must name an existing absolute directory")
    binding = probe(executable)
    available = inventory()
    selected, dependencies = skill_selection(answers, available)
    hosts = ["claude", "codex"] if answers["host"] == "both" else [answers["host"]]
    operations, preserved, registrations = [], [], []

    def add(target, raw, replace=False):
        target = safe_path(target)
        old = target.read_bytes() if target.is_file() else None
        if target.exists() and not target.is_file():
            raise ValueError("non-file destination")
        if old is not None and not replace:
            if old != raw:
                preserved.append(str(target))
            return
        if old == raw:
            return
        operations.append({"path": str(target), "before": sha(old) if old is not None else None,
            "content": raw.decode("utf-8"), "diff": "".join(difflib.unified_diff(
                (old.decode("utf-8") if old else "").splitlines(True), raw.decode("utf-8").splitlines(True),
                fromfile=str(target), tofile=str(target)))})

    for host in hosts:
        root = scope / (".claude" if host == "claude" else ".codex")
        skill_root = root / "skills"
        runtime_root = root / "original-skills"
        for name in selected:
            target = skill_root / name
            if target.exists():
                safe_path(target)
                preserved.append(str(target)); continue
            for source in files_in(available[name]):
                content = source.read_bytes()
                if source.name == "SKILL.md":
                    if host == 'codex':
                        # Claude-only discovery fields are represented by agents/openai.yaml on Codex.
                        header, body = content.split(b'\n---\n', 1)
                        header = b'\n'.join(line for line in header.split(b'\n')
                            if not line.startswith((b'argument-hint:', b'disable-model-invocation:')))
                        content = header + b'\n---\n' + body
                    content = content.replace(b"../../RUNTIME.md", str(runtime_root / "growth-loop/RUNTIME.md").encode())
                    content = content.replace(b"/growth-loop:", b"/").replace(b"$growth-loop:", b"$")
                    if name in {"learn", "forget", "refine", "jot", "journey", "profile", "recall"}:
                        op = "recall" if name == "recall" else "journey"
                        commands = [python_command(binding, runtime_root / "growth-loop/bin/gl-run", op)]
                        if name in {"learn", "forget", "refine"}:
                            commands.append(python_command(binding, runtime_root / "growth-loop/bin/gl-run", "owned"))
                        grants = ", ".join("Bash(" + cmd + " *)" for cmd in commands)
                        content = content.replace(b"\n---\n", ("\nallowed-tools: " + json.dumps(grants) + "\n---\n").encode(), 1)
                    content += ("\n\n## Installed host binding\n\nRead `" + str(runtime_root / "host-policy.md")
                        + "` for this host's policy and commands. Runtime scripts are in `" + str(runtime_root)
                        + "`; use its verified Python binding.\n").encode()
                    if name == 'goal-checkpoint':
                        content = content.replace(b'../../scripts/host_adapter.py', str(runtime_root / 'goal-checkpoint/scripts/host_adapter.py').encode())
                        content = content.replace(b'../../scripts/checkpoint.py', str(runtime_root / 'goal-checkpoint/scripts/checkpoint.py').encode())
                add(target / source.relative_to(available[name]), content)
        for source in (ENV / "runtime.py", ENV / "scripts/git_guard.py"):
            add(runtime_root / source.name, source.read_bytes())
        add(runtime_root / "HOSTS.md", (ENV / "HOSTS.md").read_bytes())
        add(runtime_root / "binding.json", (json.dumps(binding, indent=2) + "\n").encode())
        data_paths = {}
        for plugin in answers["plugins"]:
            source_root = REPO / "skills/growth-loop/growth-loop" if plugin == "growth-loop" else REPO / "plugins" / plugin
            target = runtime_root / plugin
            if target.exists():
                safe_path(target); preserved.append(str(target))
                registrations.append({"host": host, "plugin": plugin, "state": "existing source preserved; refresh explicitly"})
                continue
            for source in files_in(source_root):
                relative = source.relative_to(source_root)
                # Skills are placed once in the host Skill root. Runtime packages are hooks/helpers only.
                if not {'hooks', 'skills', 'tests'}.intersection(relative.parts):
                    content = source.read_bytes()
                    if relative.name == 'plugin.json':
                        manifest = json.loads(content)
                        manifest.pop('skills', None)
                        content = (json.dumps(manifest, indent=2) + '\n').encode()
                    add(target / relative, content)
            data = root / "original-skills-data" / plugin
            data_paths[plugin] = str(data)
            if plugin == "growth-loop":
                if answers['growth_root'] != 'selected-skills':
                    raise ValueError('explicit selected Skill root confirmation required')
                managed = safe_path(skill_root)
                config = {"version": 1, "data": str(data), "root": str(managed),
                          "auto_delete": answers["auto_delete"] == "yes", "runtime": host}
                add(target / "binding.json", (json.dumps({**binding, **config}, indent=2) + "\n").encode())
            elif plugin == "goal-checkpoint":
                add(target / "binding.json", (json.dumps({**binding, "data": str(data), "runtime": host}, indent=2) + "\n").encode())
            if plugin in {"growth-loop", "goal-checkpoint"}:
                subset = settings_for(host, answers, runtime_root, binding, {plugin: str(data)})["hooks"]
                subset.pop("PreToolUse", None)
                add(target / "hooks/hooks.json", (json.dumps({"hooks": subset}, indent=2) + "\n").encode())
            registrations.append({"host": host, "plugin": plugin, "state": "Skills placed once; runtime hooks/helpers prepared; registration/trust/runtime unverified"})
        policy = host_policy(host, answers, runtime_root, skill_root, binding, data_paths)
        add(runtime_root / "host-policy.md", policy.encode())
        if answers["settings"] != "skills-only":
            for filename in ("standard-github-policy.md", "local-policy.example.md"):
                source = ENV / host / filename
                if not source.exists():
                    source = ENV / "codex" / filename
                target_name = "local-policy.md" if filename == "local-policy.example.md" else filename
                body = source.read_text(encoding='utf-8').replace('<Japanese>', "the user's language").replace('- <github.com/OWNER/REPOSITORY>', 'None.')
                add(root / target_name, body.encode())
            suffix = "-windows.py" if binding["platform"] == "win32" else ""
            reader = "# Host read policy\n\nUse these standalone pinned validators before Git/GitHub inspection. Missing or denied bindings block the operation; no alternate dispatch. Do not inspect credentials.\n\n"
            for tool, skill in (("git", "git-read-inspection"), ("gh", "gh-read-inspection")):
                if skill in selected:
                    reader += "- " + tool + ": `" + python_command(binding, skill_root / skill / "scripts" / (tool + "-read" + suffix)) + " <arguments>`\n"
            reader += "\nPreserve an existing host's fixed reader bindings. Validate tool/executable/version prerequisites before claiming runtime success.\n"
            add(root / "host-read-policy.md", reader.encode())
            if host == "codex" and answers["git_mode"] == "manual-git":
                rules = "# Manual Git: explicit user request still required by host-policy.md.\n"
                for op in ("add", "commit", "push", "merge", "tag"):
                    rules += 'prefix_rule(pattern=["git", ' + json.dumps(op) + '], decision="prompt")\n'
                for op in ("api", "pr", "issue", "repo", "release", "secret", "variable", "workflow", "run"):
                    rules += 'prefix_rule(pattern=["gh", ' + json.dumps(op) + '], decision="prompt")\n'
                target = root / "rules/original-skills-manual-git.rules" if answers["settings"] == "apply-selected" else runtime_root / "manual-git.rules.candidate"
                add(target, rules.encode())
        if answers["settings"] != "skills-only":
            settings = settings_for(host, answers, runtime_root, binding, data_paths)
            candidate = root / "original-skills-settings.candidate.json"
            add(candidate, (json.dumps(settings, ensure_ascii=False, indent=2) + "\n").encode())
            instructions = "CLAUDE.md" if host == "claude" else "AGENTS.md"
            current = root / instructions
            directive = "\n\nRead `" + str(runtime_root / "host-policy.md") + "` for the selected original-skills host policy.\n"
            old = current.read_text(encoding="utf-8") if current.is_file() else ""
            source = (ENV / "claude/CLAUDE.md").read_text(encoding="utf-8") if host == "claude" else (ENV / "codex/AGENTS.md").read_text(encoding="utf-8")
            if host == "claude":
                source = source.replace("~/.claude", str(root))
            proposed = (old or source) + ("" if directive.strip() in old else directive)
            if answers["settings"] == "apply-selected":
                add(current, proposed.encode(), replace=True)
                if host == "claude":
                    target = root / "settings.json"
                    existing = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}
                    add(target, (json.dumps(merge_settings(existing, settings), ensure_ascii=False, indent=2) + "\n").encode(), replace=True)
                else:
                    # Codex hook trust and full sandbox/security TOML are intentionally a separate reviewed operation.
                    registrations.append({"host": host, "state": "candidate hooks require supported plugin registration and trust; config.toml not changed"})
            else:
                add(root / (instructions + ".candidate"), proposed.encode())
    result = {"version": 1, "answers": answers, "home": str(home), "scope": str(scope),
        "machine": sha(json.dumps([platform.node(), platform.system(), platform.machine(), home.stat().st_dev, home.stat().st_ino]).encode()),
        "binding": binding, "selected_skills": selected, "added_dependencies": dependencies,
        "operations": operations, "preserved": preserved, "registrations": registrations,
        "backup": "each replaced file gets a sibling timestamp/unique backup", "runtime_verified": False}
    result["plan_id"] = sha(json.dumps(result, sort_keys=True, ensure_ascii=False).encode())
    return result


def host_policy(host, answers, runtime_root, skill_root, binding, data):
    text = "# Original-skills host policy\n\nHost: " + host + ". No CLI is required to read/use the installed skills.\n"
    text += "Verified Python: `" + binding["executable"] + "`. Installed Skill root: `" + str(skill_root) + "`.\n"
    text += "Read local policy first. Existing safety gates remain authoritative; a permission denial is never a retry invitation.\n"
    if answers["git_mode"] == "manual-git":
        text += "\n" + (ENV / "profiles/manual-git.md").read_text(encoding="utf-8")
    if host == "claude":
        text += "\nClaude uses its actual permission mode/prompts. Codex approval_policy, auto_review, CODEX_HOME and tool names are not Claude capabilities. Use the Claude host policy beside CLAUDE.md; no Codex CLI fallback is required.\n"
    text += "\nGit/GitHub reads must use the installed host-read-policy.md and its verified validator binding; missing binding blocks those reads.\n"
    for name, location in data.items():
        text += "\n" + name + " data: `" + location + "`. Commands use `" + str(runtime_root / name / "binding.json") + "`.\n"
    text += "\nIf native tools (goals, subagents, terminal controls, provider catalog) are unavailable, use the Skill's documented manual equivalent with explicit local input. Do not claim an unperformed action completed.\n"
    text += "\nRead the installed `" + str(runtime_root / "HOSTS.md") + "` for per-Skill Claude entrypoints and adapters.\n"
    return text


def settings_for(host, answers, root, binding, data):
    def hook_command(script, *args):
        if host == 'claude':
            # Claude exec form bypasses Bash/PowerShell parsing on every OS.
            return {'command': binding['executable'],
                    'args': ['-X', 'utf8', '-B', str(script), *map(str, args)]}
        return {'command': python_command(binding, script, *args)}

    result = {"hooks": {}}
    if host == "claude":
        result = json.loads((ENV / "claude/settings.template.json").read_text(encoding="utf-8"))
        if answers["git_mode"] == "manual-git" and answers.get('surface') != 'chat':
            result["permissions"]["ask"] += ["Bash(git " + op + "*)" for op in sorted({"add", "commit", "push", "merge", "tag"})]
            result["permissions"]["ask"] += ["Bash(gh " + op + "*)" for op in ("pr create", "pr edit", "api", "issue create", "issue edit", "repo edit", "release create")]
            result["hooks"]["PreToolUse"] = [{"matcher": "Bash|PowerShell", "hooks": [{"type": "command",
                **hook_command(root / "git_guard.py", "--trusted-helper", root / "growth-loop/bin/gl-run", "--python", binding["executable"]), "timeout": 10}]}]
    hooks_available = host != 'claude' or answers.get('surface') != 'chat'
    if "growth-loop" in data and hooks_available:
        cmd = hook_command(root / "growth-loop/bin/gl-run", "nudge")
        for event in ("Stop", "SessionEnd"):
            result["hooks"].setdefault(event, []).append({"hooks": [{"type": "command", **cmd, "timeout": 2}]})
    if "goal-checkpoint" in data and answers["checkpoint"] == "enabled" and hooks_available:
        events = ["SessionStart", "UserPromptSubmit", "PostToolUse", "Stop", "SessionEnd"]
        if host == "codex":
            events.append("Interrupt")
        for event in events:
            cmd = hook_command(root / "goal-checkpoint/scripts/host_adapter.py", "hook", "--host", host)
            hook = {"type": "command", **cmd, "timeout": 2}
            if host == "codex" and event in {"SessionStart", "UserPromptSubmit", "PostToolUse"}:
                hook["additionalContextLimit"] = 512
            result["hooks"].setdefault(event, []).append({"hooks": [hook]})
    return result


def merge_settings(old, new):
    if not isinstance(old, dict):
        raise ValueError("settings must be an object")
    merged = json.loads(json.dumps(old))
    for section in ("permissions", "hooks"):
        merged.setdefault(section, {})
        if not isinstance(merged[section], dict):
            raise ValueError('invalid settings section')
        for key, values in new.get(section, {}).items():
            current = merged[section].setdefault(key, [])
            if not isinstance(current, list):
                raise ValueError('invalid settings list')
            for value in values:
                if value not in current:
                    current.append(value)
    return merged


def apply(result, approval):
    if approval != result["plan_id"]:
        raise ValueError("exact reviewed plan_id is required")
    # Recompile against this machine. A saved plan cannot carry stale bindings or approvals.
    fresh = plan(result["answers"], result["home"], result["binding"]["executable"])
    if fresh != result:
        raise ValueError("plan changed; review a fresh plan")
    for item in result["operations"]:
        target = safe_path(item["path"])
        old = target.read_bytes() if target.is_file() else None
        if (sha(old) if old is not None else None) != item["before"]:
            raise ValueError("destination changed")
    written = []
    for item in result["operations"]:
        target = safe_path(item["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        safe_path(target.parent)
        backup = None
        if item["before"] is not None:
            backup = str(target) + ".bak-" + str(time.time_ns())
            shutil.copy2(target, backup)
        fd, temp = tempfile.mkstemp(prefix=".original-skills-", dir=target.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(item["content"]); handle.flush(); os.fsync(handle.fileno())
            safe_path(target)
            old = target.read_bytes() if target.is_file() else None
            if (sha(old) if old is not None else None) != item["before"]:
                raise ValueError("destination changed during apply")
            os.replace(temp, target)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
        written.append({"path": str(target), "backup": backup})
    return {"written": written, "runtime_verified": False, "registrations": result["registrations"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("questions", "plan", "apply", "inventory"))
    parser.add_argument("--home", default=str(Path.home()))
    parser.add_argument("--python")
    parser.add_argument("--approve-plan")
    args = parser.parse_args()
    try:
        payload = {} if args.operation == "inventory" else json.load(sys.stdin)
        if args.operation == "inventory":
            output = {name: str(path.relative_to(REPO)) for name, path in inventory().items()}
        elif args.operation == "questions":
            available = inventory()
            output = {"next": questions(payload, args.home), "skills": sorted(available),
                "sets": {'basic': sorted(BASIC), 'documents': sorted(DOCUMENTS),
                    'development': sorted(BASIC | {n for n in available if n.startswith(('git-', 'gh-', 'frontend-optimize'))}),
                    'all': sorted(available)}}
        elif args.operation == "plan":
            output = plan(payload, args.home, args.python)
        else:
            output = apply(payload, args.approve_plan)
        print(json.dumps(output, ensure_ascii=False, indent=2))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print("install: " + str(exc), file=sys.stderr); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
