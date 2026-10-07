"""Merge config.standard.toml into a Codex config.toml.

Dry run by default: prints a unified diff. Pass --apply to write; the previous
file is kept as config.toml.bak-<timestamp>. Standard library only (Python 3.8+).

Merge rules:
- every key in the template is set or added in the same table, so entries
  you added yourself (extra domains, paths) are kept;
- [permissions.standard.workspace_roots] is replaced by the --workspace-root
  values; Codex must be able to set ACLs on each root, so use directories
  your account owns;
- legacy `sandbox_mode` and [sandbox_workspace_write] are removed, since they
  cannot be combined with `default_permissions`;
- [windows] is skipped on other platforms; everything else is left untouched.
"""
import argparse
import difflib
import os
import re
import shutil
import sys
import time

HEADER = re.compile(r"^\s*\[\[?\s*([^\]]+?)\s*\]\]?\s*(#.*)?$")
KEY = re.compile(r"""^\s*("[^"]*"|'[^']*'|[A-Za-z0-9_.-]+)\s*=""")
REMOVED_TABLES = {"sandbox_workspace_write"}
REMOVED_KEYS = {"sandbox_mode"}
REPLACED_TABLES = {"permissions.standard.workspace_roots"}
ROOT_LINE = re.compile(r"^.*<workspace-root>.*\n?", re.M)


def split_tables(text):
    """Return [(table_name or None, [lines])] keeping every line in order."""
    tables, name, lines = [], None, []
    for line in text.splitlines(keepends=True):
        m = HEADER.match(line)
        if m:
            tables.append((name, lines))
            name, lines = m.group(1), [line]
        else:
            lines.append(line)
    tables.append((name, lines))
    return tables


def key_of(line):
    m = KEY.match(line)
    return m.group(1).strip("\"'") if m else None


def set_keys(lines, entries):
    """Replace existing keys in a table body and append missing ones before trailing blanks."""
    lines = list(lines)
    for key, entry in entries:
        idx = [i for i, l in enumerate(lines) if key_of(l) == key]
        if idx:
            lines[idx[0]] = entry
            for i in reversed(idx[1:]):
                del lines[i]
        else:
            end = len(lines)
            while end > 0 and not lines[end - 1].strip():
                end -= 1
            lines.insert(end, entry)
    return lines


def merge(target, template, roots, windows):
    template = ROOT_LINE.sub(lambda m: "".join(
        m.group(0).rstrip("\n").replace("<workspace-root>", r) + "\n" for r in roots), template)
    tpl_keys = {}
    for name, lines in split_tables(template):
        entries = [(key_of(l), l if l.endswith("\n") else l + "\n") for l in lines if key_of(l)]
        if entries or name:
            tpl_keys[name] = entries
    if not windows:
        tpl_keys.pop("windows", None)

    out, seen = [], set()
    for name, lines in split_tables(target):
        if name in REMOVED_TABLES:
            continue
        if name is None:
            lines = [l for l in lines if key_of(l) not in REMOVED_KEYS]
        if name in REPLACED_TABLES and name in tpl_keys:
            blanks = len(lines) - len("".join(lines).rstrip("\n").splitlines(True))
            lines = lines[:1] + [e for _, e in tpl_keys[name]] + ["\n"] * blanks
            seen.add(name)
        elif name in tpl_keys:
            lines = set_keys(lines, tpl_keys[name])
            seen.add(name)
        out.append(lines)

    for name, entries in tpl_keys.items():
        if name not in seen:
            out.append(["\n", "[%s]\n" % name] + [e for _, e in entries])

    text = "".join(l for lines in out for l in lines)
    return re.sub(r"\n{3,}", "\n\n", text).lstrip("\n")


def validate(text):
    try:
        import tomllib as toml
    except ImportError:
        try:
            import tomli as toml
        except ImportError:
            return "skipped (Python 3.11+ or tomli needed)"
    toml.loads(text)
    return "ok"


def self_test():
    target = (
        'model = "x"\nsandbox_mode = "workspace-write"\n\n[features]\nmemories = true\n\n'
        '[permissions.standard]\nextends = ":workspace"\n\n[permissions.standard.network.domains]\n'
        '"old.example" = "allow"\n\n[sandbox_workspace_write]\nnetwork_access = true\n\n[tui]\nx = 1\n'
    )
    template = (
        'approval_policy = "on-request"\ndefault_permissions = "standard"\n\n[features]\n'
        'network_proxy = true\n\n[permissions.standard]\nextends = ":workspace"\n\n'
        "[permissions.standard.workspace_roots]\n'<workspace-root>' = true\n\n[windows]\n"
        'sandbox = "elevated"\n'
    )
    got = merge(target, template, [r"D:\work"], windows=False)
    assert "sandbox_mode" not in got and "sandbox_workspace_write" not in got
    assert 'model = "x"' in got and 'default_permissions = "standard"' in got
    assert "memories = true" in got and "network_proxy = true" in got
    assert "old.example" in got and r"'D:\work' = true" in got
    assert "[windows]" not in got and "[tui]" in got
    assert got.index('default_permissions') < got.index("[features]")
    assert merge(got, template, [r"D:\work"], windows=False) == got, "not idempotent"
    moved = merge(got, template, [r"D:", r"D:"], windows=False)
    assert r"'D:\work'" not in moved and r"'D:' = true" in moved and r"'D:' = true" in moved
    print("self-test ok; toml parse:", validate(got))


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    home = os.environ.get("CODEX_HOME") or os.path.join(os.path.expanduser("~"), ".codex")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workspace-root", action="append",
                    help="directory you own that holds repositories (repeatable)")
    ap.add_argument("--config", default=os.path.join(home, "config.toml"))
    ap.add_argument("--template", default=os.path.join(here, "config.standard.toml"))
    ap.add_argument("--apply", action="store_true", help="write the result (default: dry run)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.workspace_root:
        ap.error("--workspace-root is required")
    if any("'" in r for r in args.workspace_root):
        ap.error("--workspace-root must not contain a single quote")
    roots = [os.path.abspath(r) for r in args.workspace_root]

    with open(args.template, encoding="utf-8") as f:
        template = f.read()
    original = ""
    if os.path.exists(args.config):
        with open(args.config, encoding="utf-8") as f:
            original = f.read()

    merged = merge(original, template, roots, sys.platform == "win32")
    status = validate(merged)
    diff = "".join(difflib.unified_diff(original.splitlines(True), merged.splitlines(True),
                                        args.config, args.config + " (merged)"))
    print(diff or "no changes")
    print("toml parse:", status)
    if not args.apply or not diff:
        if diff:
            print("dry run; re-run with --apply to write")
        return

    if os.path.exists(args.config):
        backup = "%s.bak-%s" % (args.config, time.strftime("%Y%m%d%H%M%S"))
        shutil.copy2(args.config, backup)
        print("backup:", backup)
    with open(args.config, "w", encoding="utf-8", newline="") as f:
        f.write(merged)
    print("written:", args.config)


if __name__ == "__main__":
    main()
