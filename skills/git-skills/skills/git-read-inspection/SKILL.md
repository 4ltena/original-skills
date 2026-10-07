---
metadata:
  author: 4ltena
  version: '1.2'
name: git-read-inspection
description: Use the pinned validator for Git state, content, refs, diffs and history
  without writes or external helpers.
---

# Git reads

Follow the active host's mandatory read policy and verified validator binding. Only accepted read commands/options belong to this path. Never substitute an unapproved executable, wrapper, configuration or output destination when a binding is unavailable.

Run the validator command recorded in the host read policy (`~/.codex/host-read-policy.md`). On Windows it is `<python> -I <skills-dir>/git-read-inspection/scripts/git-read-windows.py <subcommand...>`, which binds Git at its default install path (2.54.0 or newer). Other platforms require their explicit verified host binding; a Windows skill installation does not establish those paths.

Put `--` before paths beginning with `-`; `config --get` is limited to allowed non-secret metadata. Caller global/config options, mutations, external helpers, output files and ambiguous arguments need explicit review. Use the command tool's working directory rather than caller Git global options. Exit 64 is policy denial; 124 is timeout.

Drives without ownership records, such as exFAT, are readable only when the repository is in the user's existing global safe.directory. Adding it is a global configuration change requiring approval. Denial never grants a bypass.
