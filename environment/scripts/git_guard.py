"""Conservative manual-Git Claude PreToolUse guard. No command is executed."""
import argparse
import json
import re
import shlex
import sys

GIT_WRITES = {"add", "commit", "push", "merge", "tag", "reset", "clean", "rebase",
              "restore", "switch", "checkout", "cherry-pick", "revert", "stash", "fetch", "pull", "config"}
GH_READS = {("pr", "view"), ("pr", "list"), ("pr", "diff"), ("pr", "checks"),
            ("issue", "view"), ("issue", "list"), ("repo", "view"), ("run", "view"),
            ("run", "list"), ("release", "view"), ("release", "list"), ("workflow", "list"),
            ("workflow", "view"), ("search", "repos"), ("search", "issues"), ("search", "prs")}
READ_PROGRAMS = {"pwd", "ls", "rg", "cat", "head", "tail", "wc", "stat"}


def decision(text, trusted_helper=None, python=None):
    # A shell parser is not an authorization oracle. Expansion/wrappers are asked.
    if not isinstance(text, str) or re.search(r"[\n\r`$()]", text):
        return "ask"
    try:
        tokens = list(shlex.shlex(text, posix=True, punctuation_chars=";&|<>"))
    except ValueError:
        return "ask"
    groups, group = [], []
    for token in tokens:
        if token in {";", "&&", "||", "|"}:
            groups.append(group); group = []
        elif token and all(c in ";&|<>" for c in token):
            return "ask"
        else:
            group.append(token)
    groups.append(group)
    for args in groups:
        if not args:
            return "ask"
        program = args[0].replace("\\", "/").rsplit("/", 1)[-1].removesuffix(".exe")
        if trusted_helper and python and args[:6] == [python, "-X", "utf8", "-B", trusted_helper, "owned"]:
            if any(arg == '--binding' or arg.startswith('--binding=') for arg in args):
                return 'deny'
            if len(args) < 8 or args[6] not in {'create', 'status', 'update', 'delete', 'recover'}:
                return 'ask'
            # The exact installed helper validates root/generation/payload; no raw rm grant.
            continue
        if program == "git":
            rest = args[1:]
            while rest and rest[0] in {"-C", "--git-dir", "--work-tree"}:
                if len(rest) < 3:
                    return "ask"
                rest = rest[2:]
            if not rest or rest[0].startswith("-"):
                return "ask"
            if rest[0] == "push" and any(x == "--delete" or x.startswith(":") for x in rest[1:]):
                return "deny"
            if rest[0] in GIT_WRITES or rest[0] not in {"status", "log", "diff", "show", "rev-parse", "ls-files"}:
                return "ask"
        elif program == "gh":
            if "delete" in args[1:3]:
                return "deny"
            if tuple(args[1:3]) not in GH_READS:
                return "ask"
        elif program not in READ_PROGRAMS:
            return "ask"
    return "allow"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--trusted-helper')
    parser.add_argument('--python')
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("oversize")
        event = json.loads(raw)
        value = decision(event.get("tool_input", {}).get("command"), args.trusted_helper, args.python)
    except (ValueError, TypeError, AttributeError):
        value = "ask"
    if value != "allow":
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
            "permissionDecision": value, "permissionDecisionReason":
            "manual-git: confirm the explicitly requested operation and existing safety gates; unknown commands require review"}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
