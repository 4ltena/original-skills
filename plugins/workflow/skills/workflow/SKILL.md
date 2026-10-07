---
name: workflow
description: Coordinate approved multi-stage software changes or resume unfinished implementation, with a fixed completion bar, bounded review and verification, and a final report.
metadata:
  author: 4ltena
  version: '2.0'
---

# Development workflow

Resume from current project state and approved decisions. For substantial work without an approved specification, use the available specification skill first; ordinary reversible edits need only focused checks. This workflow works inside existing approval, security, data-loss and project gates and grants no additional permissions.

## Fix the bar first

Before investigating or editing, write down:

- **Outcome**: one sentence on what must be true when done.
- **Checks**: one to three commands or observations that show it, preferring ones that fail for a plausible broken change.
- **Cap**: run each check once on the final change; repeat only after a failure you changed something for.
- **Non-goals**: nearby work you will not touch.

Use the user's acceptance criteria as given and do not add to them. You have no internal signal that work is done; the bar checks are the measure of progress.

## Implement

Implement in dependency order and preserve existing work. Parallel bundles need non-overlapping owned paths, no shared command side effects, satisfied dependencies and bounded requirements/checks supplied to each isolated worker; otherwise run sequentially. The parent owns integration and milestone gates. Load a specialist skill only when its capability is needed.

Triage every new finding: **blocking** (a bar check fails, a stated requirement is unmet, or the change breaks a trust boundary, loses data or weakens security) gets fixed; **deferred** (adjacent bugs, style, hypothetical edge cases, environment oddities) gets one line in the handoff and nothing more; **decision** goes to the user once with a recommendation. Only blocking findings extend the work.

## Review and commit cadence

- Run one independent review per milestone or before integrating a commit series, not after each increment. Re-review only the fixes. A project being security- or migration-heavy does not turn every increment into a high-risk gate.
- Where commits are authorized for the task, commit each verified increment on the working branch. Do not carry verified work uncommitted across turns; if commits are not authorized, report the uncommitted size.

## Waiting on the user or environment

When progress needs a user action, a permission or an unavailable environment, ask once with the exact action, record the blocker, then continue unblocked work or stop. Do not re-probe the same condition each turn without a new signal from the user or a changed condition.

## Autonomous continuation

In goal, loop or other self-continuing turns, a continuation is not a new user turn. Update the handoff at a milestone change, a new blocker, a stop or before expected compaction, not every continuation. Reload a skill after compaction only when the next step needs it.

## Stop signals

Stop and report instead of starting another round when:

- A check or review of the same target would exceed the cap.
- A correction (erratum, addendum, retry, next version) follows a correction. Question the premise or scope instead.
- Process artifacts (specs, notes, reports, environment diagnosis) grow faster than the product change.
- The same blocker or the same class of finding recurs.
- The only reason for the next step is "to be sure".

Treat a push, progress or status request as its own short task: do it, report, and stop. "After the current work" means finishing the work in progress, not starting the next task.

## Report

Lead with the result against the bar: complete, or incomplete with the unmet item. Give relevant changed paths, actual verification, deferred items and material remaining work. Separate unverified from failed. Never turn unrun checks, worker claims or installed files into proof of runtime behavior. Compose the report from evidence already in context; do not reread the state document or skills to write it. Use a short paragraph for a small change.

Read the relevant section of [execution details](references/execution.md) when diagnosing an uncertain failure, preparing delegated work, handling large output or retrying an interrupted write. Persist a project handoff when continuity is needed.

Do not apply the bar to cut an audit, research or review the user explicitly asked to be exhaustive; there, the requested scope is the bar.
