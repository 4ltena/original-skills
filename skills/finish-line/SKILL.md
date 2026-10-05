---
name: finish-line
description: "Use when agent work keeps expanding: investigation, verification, review, specs or errata multiply without reaching completion, or a small fix is routed through heavy process. Fix the completion bar and verification cap first, triage new findings as blocking or deferred, and stop when the bar is met."
---

# Finish line

Finish the requested outcome with proportionate evidence. This works inside existing approval, security, data-loss and project gates; never skip or weaken them. It limits how much you do within the gates, not the gates themselves.

An agent has no internal signal that the work is done. Write the signal down before starting, and treat the bar checks, not your own sense of thoroughness, as the measure of progress.

## 1. Fix the bar first

Before investigating or editing, state in the reply or task note:

- **Outcome**: one sentence on what must be true when done.
- **Checks**: one to three commands or observations that show it, preferring ones that fail for a plausible broken change.
- **Cap**: run each check once on the final change; repeat only after a failure you changed something for. Allow one independent review for non-routine work, then re-review only the fixes.
- **Non-goals**: nearby work you will not touch. Where cheap, make one an absence check, such as a diff showing no edits outside the intended paths.

Use the user's acceptance criteria as given and do not add to them. If no check can be written, ask once with a recommended bar.

## 2. Triage everything new

Classify each finding from investigation or review:

- **Blocking**: a bar check fails, a stated requirement is unmet, or the changed code breaks a trust boundary, loses data or weakens security. Fix it.
- **Deferred**: everything else, such as adjacent bugs, style, hypothetical edge cases, and environment oddities that do not affect the checks. Record one line in the handoff and do not fix, specify or investigate it further.
- **Decision**: needs the user's choice. Ask once with a recommendation.

Only blocking findings extend the work. Widening the bar to cover something found along the way needs the user's agreement.

## 3. Stop signals

Stop, and report instead of starting another round, when any of these holds:

- A check or review of the same target would exceed the cap.
- A correction (erratum, addendum, retry, next version) follows a correction. Question the premise or scope rather than refining the document again.
- Process artifacts (specs, notes, reports, environment diagnosis) grow faster than the product change.
- Review findings are non-blocking, or the same class keeps recurring.
- The only reason for the next step is "to be sure".

The stop report gives the bar, what is met with evidence, what is unmet, the deferred list, and a recommendation: finish now, make one scoped fix, or ask for a decision.

## 4. Match process to change

For a local, low-risk, reversible change, make it, run the bar checks and report. If a project gate requires a spec or approval, send one short proposal with the change, the check and what is deferred, not a new spec chain. Use the full specification path only for security, migration, public API, dependency, deployment or cross-component impact.

## 5. Report

Lead with the result: complete against the bar, or incomplete with the unmet item. Separate unverified from failed. Do not claim completion beyond the bar, and do not add verification only to feel safe.

Do not use this to cut an audit, research or review the user explicitly asked to be exhaustive; there, the requested scope is the bar.
