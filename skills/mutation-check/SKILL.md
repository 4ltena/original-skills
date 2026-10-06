---
metadata:
  author: "4ltena"
  version: "1.1"
name: mutation-check
description: Use when checking whether a test detects a specific defect. Apply one deliberate mutation, observe the expected failure, and restore the original file exactly.
---

# Check tests with a deliberate mutation

A passing test shows that the current implementation passes; it does not show that the test would catch a defect. A rejection-only test may also pass when the implementation rejects everything. Choose a plausible defect and check the test against it.

## Protect the starting state

Identify the smallest file and change needed for one mutation. Run the mutation in a disposable worktree or fixture that includes the starting changes; leave the user's original tree untouched. Record the target's starting bytes or hash and its worktree diff. If the test cannot run in an isolated tree, stop unless you can save a byte-for-byte backup outside the target and run mutation, test, and restoration in one guarded process (`finally` or a shell `trap`). The guard must restore on normal exit, test failure, and ordinary interruption. Keep the backup until a byte comparison and worktree-diff comparison pass. If a hard abort prevents the guard from running or restoration fails, keep the backup and report its location and the exact remaining change before further work. Do not use `git reset --hard`, `git clean`, or another operation that could discard unrelated work.

## Run one mutation

1. Make the deliberate defect and verify that the intended bytes actually changed on disk.
2. Confirm that the relevant build or test runs against the changed source, rather than an old artifact.
3. Run the focused test. Confirm it fails for the expected assertion, not merely because compilation or setup failed.
4. Restore the original bytes before attempting another mutation. Confirm that the target hash and worktree diff match the recorded starting state. If restoration fails, stop and report the exact remaining change.

An unapplied mutation is indistinguishable from an undetected defect unless step 1 is checked. A test that exits successfully while doing nothing is a useful mutation when it represents a plausible implementation error.

## Check both directions

Pair an input that must be rejected with one that must be accepted. A rejection test alone cannot distinguish correct validation from an implementation that rejects everything.

Test doubles can be easier to start than the real program under its normal constraints. Keep at least one path that executes the real program with those constraints when that difference matters to the claim.
