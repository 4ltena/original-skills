---
metadata:
  author: 4ltena
  version: '1.2'
name: gh-read-inspection
description: Inspect GitHub within the active host's read policy and required validator
  boundary.
---

# GitHub reads

Follow the active host's read policy before choosing a command. A required validator stays mandatory; a legacy preset cannot make it optional. Direct gh or REST/GraphQL reads are permitted only when that active policy explicitly authorizes them; inspect the endpoint, HTTP method and operation first.

Use the validator command recorded in the host read policy (Codex: `~/.codex/host-read-policy.md`; Claude: its active host-home `host-read-policy.md`). On Windows it is `<python> -I <skills-dir>/gh-read-inspection/scripts/gh-read-windows.py <command...>`, which binds GitHub CLI at its default install path (2.93.0 or newer) and preserves the existing Credential Manager login. Other platforms require their explicit verified host binding.

Use accepted bounded selectors and stdout formats. The validator excludes generic API, browser/watch/editor, output files, authentication changes and mutations. Never display authentication tokens or execute extensions/aliases. Downloads and checkout are not pure inspection; `gh pr create --dry-run` may push and requires the applicable write permissions.

Exit 64 means policy denial; 124 means timeout. Missing tooling, GitHub denial or runtime failure grants no alternate dispatch or broader permission.
