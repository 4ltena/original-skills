---
name: git-read-inspection
description: "Use the pinned validator for Git state, content, refs, diffs and history without writes or external helpers."
---

# Git reads

Run `/usr/bin/python3 -I /home/altena/.codex/skills/git-read-inspection/scripts/git-read <subcommand...>`.

Use accepted reads/options; put `--` before paths starting with `-`. `config --get` is limited to allowed non-secret metadata keys. Mutations, arbitrary config, external helpers, output files, caller global options and ambiguous arguments need explicit review. Exit 64 means policy denial; 124 means timeout.
