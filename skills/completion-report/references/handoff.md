# Project handoff

Run once after final code/test verification before reporting completion, or on exit; do not recurse during handoff updates. Skip configuration homes, empty/disposable work and sessions with no project state; explain why.

Search README/docs for existing overview, architecture, status, specs and plans. Update canonical equivalents, never duplicate for a preferred filename. Only if orientation is absent, create `docs/overview.md` with verified purpose, architecture, repo map, commands, constraints and links; avoid file inventories.

Update active specs/plans. Preserve `task-relay`'s `## Tasks` checkboxes and concise downstream facts in `## Handoff notes`.

Update one status document, defaulting to `.project-notes/CURRENT.md`. Keep it short; link rather than copy specs/plans. Include timestamp/scope, active spec/plan, milestone/completed work, exact next task or `none`, blockers/decisions/assumptions, paths/ownership, actual verification commands/results, and minimal next-session reading.

Record missing evidence as `not run`/`unknown`; invent no next work. Return changed paths and unknowns. Do not commit, push, create/merge PRs, publish or perform destructive operations. Next session reads status first, then only relevant links.
