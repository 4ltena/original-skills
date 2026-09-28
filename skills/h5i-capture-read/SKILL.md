---
name: h5i-capture-read
description: "Capture large non-secret project reads through the authorized h5i validator; not tests, builds or arbitrary commands."
---

# Captured project reads

Only the exact prefix below authorizes h5i object/provenance writes; the child remains read-only:

```sh
/usr/bin/python3 -I /home/altena/.codex/skills/h5i-read-inspection/scripts/h5i-read capture rg -n 'pattern' src
```

Use capture only for output that would crowd context; bounded ranges, single-file searches and short listings stay direct. Split reads. Never nest capture, add a shell/pipeline/redirection/substitution/environment assignment, or wrap in `codex sandbox`. Raw capture remains approval-gated. If prefix recognition fails, diagnose policy loading; do not widen it. Ask for grammar extension when needed, never fall back to raw capture.

Accepted readers: cat, head, tail, nl, wc, sed -n, grep, rg, find, ls, stat. `nl` requires explicit files and numbering options only. `grep` rejects symlink/device/directory-following options (`-R`, `--dereference-recursive`, `-D`, `--devices`, `-d`, `--directories`); pattern files are path-checked. `find` requires explicit roots and read-only predicates; no execution, writes, symlink following or `-print0` (line-oriented filtering).

All non-secret file types are allowed; extension alone proves nothing. Resolve explicit symlinks; reject `.env`, `*.pub`, private keys, credentials/tokens, keychains, SSH/GnuPG/cloud-auth paths. Directory searches inject exclusions. Reject rg preprocessors, hostname/archive subprocesses, config files and traversal options.

No tests, builds, package managers, Git writes, network, process control or uncertain side effects. Never bypass denied paths through another wrapper. A direct non-capturing read is permissible only if existing sandbox policy independently allows that exact read; otherwise report the denial without exposing contents.
