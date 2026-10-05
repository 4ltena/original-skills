---
metadata:
  author: "DietrichGebert"
  maintainer: "4ltena"
  version: "1.1"
name: ponytail-audit
description: >
  Whole-repo audit for over-engineering. Like ponytail-review, but scans the
  entire codebase instead of a diff: a ranked list of what to delete, simplify,
  or replace with stdlib/native equivalents. Use when the user says "audit this
  codebase", "audit for over-engineering", "what can I delete from this repo",
  "find bloat", "ponytail-audit", or "/ponytail-audit". One-shot report, does
  not apply fixes.
---

ponytail-review, repo-wide. Scan the whole tree instead of a diff. Rank
findings biggest cut first.

## Tags

Same as ponytail-review:

- `delete:` dead code, unused flexibility, speculative feature. Replacement: nothing.
- `stdlib:` hand-rolled thing the standard library ships. Name the function.
- `native:` dependency or code doing what the platform already does. Name the feature.
- `yagni:` abstraction with one implementation, config nobody sets, layer with one caller.
- `shrink:` same logic, fewer lines. Show the shorter form.

## Hunt

Deps the stdlib or platform already ships, single-implementation interfaces,
factories with one product, wrappers that only delegate, files exporting one
thing, dead flags and config, hand-rolled stdlib.

## Output

One line per finding, ranked: `<tag> <what to cut>. <replacement>. [path]`.
End with `net: -<N> lines, -<M> deps possible.` Nothing to cut: `Lean already. Ship.`

## Boundaries

Scope: over-engineering and complexity only. Correctness bugs, security holes,
and performance are explicitly out of scope. Route them to a normal review
pass. Lists findings, applies nothing. One-shot.
"stop ponytail-audit" or "normal mode" to revert.

## Codex adaptation

Use available Git read validators for inspection. Read-only findings must identify actual callers and required behavior before recommending removal; a single implementation alone is not proof of needless abstraction. Keep required validation, recovery, and security behavior. Quantify possible removals only when measured. Output findings in Japanese. Do not invoke Claude slash commands or apply fixes without a scoped user request. Source: ponytail 4.8.4; license is included.
