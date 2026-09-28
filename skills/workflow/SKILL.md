---
name: workflow
description: Guide software changes through scope, specification, implementation, review, verification and handoff. Use for multi-stage development or resuming unfinished work, not for a standalone answer or read-only review.
---

# Development workflow

Start with the user's outcome, the project's current state and the relevant source. Resume at the unfinished work; keep approved decisions and prior evidence unless a changed requirement or result makes them stale. Use the current runtime's tools and permission rules. A phase selects the work to focus on; it never grants file, Git, network or publication authority.

## Select the path

For a local, reversible change without security, migration, public API, dependency, deployment or cross-component impact, keep a brief change contract in context: the observed need, intended behavior, affected paths and focused check. Continue directly with the necessary work. If investigation reveals wider impact, record the new boundary and use the full path.

For substantive work, define observable behavior, exclusions and acceptance criteria; then plan the affected components, dependencies, owners, recovery and checks. Resolve decisions that would alter the implementation before it begins. Obtain the approval required by the project's instructions for the current specification and plan. An existing approved plan remains usable until its assumptions or scope change materially. Keep private project records in the project's established location; do not create duplicate status files.

## Work through the relevant phases

| Phase | Work and exit evidence |
| --- | --- |
| `general` | Answer or investigate a request with no software change to carry forward. |
| `brainstorm` | Compare materially different approaches only when the direction is open; record the chosen direction or unresolved decision. |
| `specify` | Establish what must hold, why, and how it will be checked. For substantive work, connect the approved specification, plan and tasks to acceptance criteria. |
| `implement` | Make the smallest sufficient approved change while preserving existing work, validation, recovery, security and accessibility. Record the actual changed paths and focused results. |
| `review` | Inspect the current change against the approved behavior and likely regressions. Resolve findings with concrete evidence and distinguish self-check from independent review. |
| `verify` | Run required and focused checks on the current result; map outcomes and missing evidence to acceptance criteria. A passing command alone does not establish every requested behavior. |
| `deliver` | State what is complete, what was observed, what remains unverified or blocked, and the exact next task. Update the existing handoff when the project requires one. |

Use only phases that add value to the request. A routine fix does not need invented brainstorming artifacts or a full plan. A substantial change does not become routine because its first edit is small. Read [execution details](references/execution.md) when implementing, debugging or coordinating review.

## Keep evidence current

If a requirement, plan, task boundary or final artifact changes, identify the affected downstream work. Recheck its review and verification evidence against the new version; keep earlier results as history, not proof of the current result. A failed or unrun check stays failed or unrun until observed otherwise. Do not turn missing approval, unknown side effects or a model's completion claim into a passing gate. When a gate cannot be met, report the specific gap and next action rather than repeating the same step without new evidence.
