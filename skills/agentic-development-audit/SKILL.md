---
name: agentic-development-audit
description: "Audit AI-development workflow behavior from run evidence, or compare measured quality and cost when requested. Use for explicit process audits, not ordinary code review."
---

# Development audit

Define the decision, scope, task classes and evidence available. Choose a diagnostic or a comparative audit from the user's question; do not require a cost comparison to diagnose one run.

For a diagnostic audit, compare the intended result with a representative run's actual instructions, Skill activation, tool calls, handoffs, approvals, artifacts, checks and final claim. Identify the first consequential divergence and its likely cause. Separate observed trace facts from inference, missing events and environment limits. Recommend the smallest reversible correction and a counterexample that could disprove it. Do not infer a frequency or improvement rate from one run.

Use only the trace fields and redacted excerpts needed for the audit. Do not reproduce credentials, private payloads or personal data in notes or reports; mark a conclusion unknown when necessary evidence cannot be handled safely.

For a comparative audit, define the period, repositories/teams, candidate workflows and each task class's minimum quality/risk gate from policy, acceptance criteria or the user before comparing cost.

For the comparison, collect available records: elapsed/active time, user interventions, launches/concurrency/retries/stops, first-pass verification, review rework, CI failures, production defects, and recorded model/token/money costs. For each measure record source, coverage, units and missingness. Show calculations for derived metrics; never invent observations or convert launches into unrecorded token/money costs.

Compare within task classes, accounting for size, risk, familiarity and selection bias. Report sample counts, medians, ranges, quality rates and missing data; small/nonrandom samples do not establish causation.

For the comparison, reject candidates below the gate. Among those passing, seek the cheapest reliable workflow; add agents/reasoning only for measured gains exceeding coordination cost. Do not combine quality/time/cost into a score without user-supplied weights. Recommend none if all fail; label a sole passing candidate provisional, not comparatively cheapest.

Report evidence, gaps, confidence and reversible recommendations; use a comparison table when comparing alternatives. Propose a limited matched follow-up for insufficient comparative evidence. Do not change workflows, configuration, code or approval policy without separate implementation authorization.
