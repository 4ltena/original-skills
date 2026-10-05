---
metadata:
  author: 4ltena
  version: '1.1'
name: workflow
description: Guide multi-stage software changes through scope, implementation, review, verification and handoff, or resume approved work. Not for standalone answers or read-only reviews.
---

# Development workflow

Read the project's current state and relevant source. Resume unfinished work, preserving approved decisions and valid evidence. Follow current permissions; this workflow grants no additional authority.

## Scope

- For a small, local, reversible change with no material security, migration, public API, dependency, deployment or cross-component impact, keep the need, intended behavior, affected paths and focused check in context; proceed directly.
- For substantive work, establish behavior, exclusions, acceptance criteria and a dependency-aware plan covering ownership, recovery and checks. Resolve consequential choices and obtain required approval before implementation. Revisit an approved plan only when scope or assumptions materially change.

Use only stages that help the request. Compare approaches when direction is open; do not invent planning artifacts for routine work or classify substantial work by the size of its first edit.

## Execute and finish

- **Implement:** Make the smallest sufficient change, preserving existing work and required validation, recovery, security and accessibility. Follow dependencies; delegate only worthwhile independent work with distinct ownership. The parent remains responsible for integration and completion.
- **Review:** Check the actual final change against requirements and likely regressions. Require evidence for findings, resolve confirmed blockers and recheck affected behavior. Distinguish self-check from independent review; an unavailable required review remains an unmet gate.
- **Verify:** Run required and focused checks on the integrated result. Map observed results and missing evidence to acceptance criteria. Revalidate only evidence affected by a changed requirement or artifact; earlier results remain history. Passing commands or worker claims alone do not prove completion.
- **Deliver:** Report completed work, actual checks, limitations, blockers and the exact next task. Update the existing handoff when required; preserve the project's document layout. Do not report failed or unrun checks as passed.

Read [execution details](references/execution.md) for delegation, debugging or uncertain retries. When a gate cannot be met, identify the missing decision or evidence rather than repeating work without progress.
