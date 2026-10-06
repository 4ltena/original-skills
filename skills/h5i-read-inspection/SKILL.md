---
metadata:
  author: "4ltena"
  version: "1.1"
name: h5i-read-inspection
description: "Inspect h5i through its pinned read validator; capture large, non-secret project reads with its capture command."
---

# h5i reads

Run `/usr/bin/python3 -I /home/altena/.codex/skills/h5i-read-inspection/scripts/h5i-read <command...>` using documented read families only.

For large non-secret reads use its `capture <reader...>` command under `h5i-capture-read`. It supplies the outer capture; never wrap it again. Issue bounded line ranges, single-file searches and short listings directly.

Raw object content, repair/mutation, output files, pager/browser/shell and unknown options need explicit review. Exit 64 means policy denial; 124 means timeout.
