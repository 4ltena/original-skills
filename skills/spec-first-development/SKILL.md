---
metadata:
  author: "4ltena"
  version: "1.1"
name: spec-first-development
description: "Define approved specifications, acceptance criteria, milestones and safe parallel work for substantial changes or new projects."
---

# Specification first

Fast path: only local, low-risk, reversible changes with focused verification and no security, migration, public API, dependency, deployment or cross-component impact. Record acceptance criteria/checks in context; the implementation request authorizes this path. Otherwise use the full path; uncertainty or scope growth escalates.

When available, `workflow` supplies the execution, debugging and implementation-review contracts for steps 4-6. Enter it at the approved-plan stage; do not restart this specification procedure. Existing private document paths remain valid independently of any plugin installation.

1. Inspect requirements/context; record background, non-goals, constraints, acceptance criteria, open questions and verification in `.project-notes/specs/YYYY-MM-DD-<slug>.md`. Define ordered milestones with goals, dependencies, bundles, owners/isolated paths, acceptance checks and integration gates.
2. Use an independent read-only reviewer for the substantive specification when available. Delegate bounded research only when distinct questions or review requirements justify it; resolve roles and tools from the current catalog. Check contradictions, gaps, security, operations and feasibility. Researchers receive no implementation task. If independent review is unavailable, report that limit honestly.
3. Use available `ux-spike` before unsettled UI direction enters the spec. Before substantial-plan approval use available `plan-review-loop` for explanation followed by review; skip short, already-read plans. Claim independent review only if performed. Present the full spec/milestones and obtain approval before implementation, commit, push or PR. Reapprove material scope, acceptance or dependency changes.
4. Execute milestones in dependency order. Give each bundle owner, deliverable, paths and checks. Parallelize worthwhile independent work only with non-overlapping writes and no shared command side effects; prefer authorized isolation. Otherwise work sequentially. Never exceed independent bundle count. If private specs are inaccessible, include the worker's requirements, constraints, acceptance, integration contract and checks in its prompt.
5. Collect paths and evidence; resolve conflicts, failures and open decisions, then pass integration checks before dependent work. Use available read-only `change-reviewer` at final and high-risk gates, with file:line evidence. Resolve blocking specification, regression, security, operations and coverage findings.
6. Use `task-relay` only for approved long sequential work benefiting from fresh contexts. Complete required checks and focused verification of the changed behavior; repeat or broaden checks only for new changes, failures or unresolved concerns. Then use `completion-report`. No step overrides commit/push/PR/merge/release/destruction approval boundaries.
