---
metadata:
  author: "4ltena"
  version: "1.1"
name: smallest-change
description: Use before a non-trivial code change to find the smallest correct fix, reuse existing facilities, address the shared cause, and verify the artifact that actually changed.
---

# Choose the smallest correct change

Understand the problem and the relevant callers before choosing an edit. A small change in the wrong place can introduce another bug.

## Find the smallest sufficient approach

Stop at the first approach that solves the present problem:

1. Is a change needed for the requested behavior?
2. Does the codebase already have a suitable helper, type, or pattern?
3. Can the standard library do it?
4. Can a native platform feature do it, such as an HTML date input or a database constraint?
5. Can an existing dependency do it without adding another one?
6. Can a direct expression or small function do it clearly?
7. Otherwise, write the minimum correct implementation.

Do not add an abstraction for an unrequested future use. Prefer removing obsolete code where the change makes it unnecessary. Keep the edit small after tracing the behavior, not by skipping that trace.

## Fix the shared cause

For a bug, inspect the callers of the affected function. When the same defect can reach several callers, fix it at their shared boundary if that preserves the intended behavior. Check boundary cases before choosing between equally short standard-library options.

When simplifying a physical system, preserve any adjustment needed for calibration, drift, or device variation. If a deliberate simplification creates a known limit, record the limit and what would trigger a more complete implementation.

## Verify the changed artifact

Before concluding, ask whether the thing you measured contains the edit:

- Would the relevant test fail for a plausible broken implementation, or does it only assert rejection?
- Was the running binary rebuilt from the changed source?
- Does the tool output actually describe the code you changed?

For a branch, loop, parser, money calculation, or permission path, keep the smallest meaningful check that would fail when the behavior breaks. Do not build a test framework for an obvious one-line edit.

Never shrink away trust-boundary validation, data-loss recovery, security, basic accessibility, or an explicitly requested part of the solution. If the user asked for the full implementation, deliver it.

Lead with the result and actual verification. Explain material limits or remaining work when they affect the user's decision; give more detail when requested.
