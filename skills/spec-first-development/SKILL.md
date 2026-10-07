---
name: spec-first-development
description: Specify and obtain approval for substantial implementation or a new project; resume approved work without repeating planning.
metadata:
  author: "4ltena"
  version: "1.2"
---

# Specification first

For local reversible changes without material security, migration, API, dependency, deployment or cross-component impact, keep the behavior, paths and focused checks in context; the implementation request authorizes this fast path. Otherwise define a specification before implementation.

Record purpose, exclusions, constraints, acceptance criteria and unresolved consequential decisions in the project's existing specification layout, defaulting to `.project-notes/specs/YYYY-MM-DD-<slug>.md`. Include ordered milestones, dependencies, owned paths, recovery and verification gates.

Use an available independent read-only reviewer for a substantive specification; report when independent review is unavailable. Use plan-review-loop for a substantial plan explanation/review when needed, and ux-spike only for unsettled UI direction. Resolve supported blocking findings and obtain specification approval before implementation. Existing decisions remain approved unless scope, assumptions or acceptance materially change.

Execute the approved milestones through available workflow guidance. Independent bundles require non-overlapping ownership, satisfied dependencies and bounded requirements/checks; otherwise work sequentially. The root integrates and verifies each dependent gate. Require available independent change review at final or high-risk gates, resolve confirmed blockers and report unmet gates honestly.

Use task-relay only for long sequential plans that benefit from saved context. Preserve applicable handoff, reporting and publication rules; this skill grants no permission to commit, push, publish or bypass a denial. An approved plan must not recursively restart this procedure.
