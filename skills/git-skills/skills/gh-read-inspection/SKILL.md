---
name: gh-read-inspection
description: "Inspect GitHub through direct read-only gh commands in Codex standard, or the pinned validator in other presets."
---

# GitHub reads

For Codex standard, read `/home/altena/.codex/standard-github-policy.md`. Direct read-only gh commands and REST/GraphQL queries are pre-authorized; the pinned validator is optional. Inspect the endpoint, HTTP method and GraphQL operation before treating API calls as reads. Do not display authentication tokens, execute extensions/aliases, or treat auth changes, downloads, checkouts and mutations as pure reads. `gh pr create --dry-run` may still push Git changes, so it is not a read-only inspection; use `gh-operations` and `git-operations` when appropriate.

For other presets, run `/usr/bin/python3 -I /home/altena/.codex/skills/gh-read-inspection/scripts/gh-read <command...>` with its accepted selectors and stdout formats. Exclude generic API, browser/watch/editor, output files, auth and mutations. Exit 64 means policy denial; 124 means timeout. Preserve normal gh authentication. GitHub or runtime denials are not permission to bypass a restriction.
