---
metadata:
  author: "4ltena"
  version: "1.1"
name: git-read-inspection
description: "Use the pinned validator for Git state, content, refs, diffs and history without writes or external helpers."
---

# Git reads

Run `/usr/bin/python3 -I /home/altena/.codex/skills/git-read-inspection/scripts/git-read <subcommand...>`.

Use accepted reads/options; put `--` before paths starting with `-`. `config --get` is limited to allowed non-secret metadata keys. Mutations, arbitrary config, external helpers, output files, caller global options and ambiguous arguments need explicit review. Exit 64 means policy denial; 124 means timeout.

On Windows, run `C:/Users/nisim/AppData/Local/Programs/Python/Python310/python.exe -I C:/Users/nisim/.agents/skills/git-read-inspection/scripts/git-read-windows.py <subcommand...>`. It applies the same grammar with `C:\Program Files\Git\cmd\git.exe` (2.54.0 or newer, so Git updates keep working). Repositories on drives without ownership records (exFAT, e.g. `F:`) are read only when listed in the user's global `safe.directory`; adding one is a global config change that needs approval.
