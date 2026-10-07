---
metadata:
  author: "4ltena"
  version: "1.1"
name: agent-watchdog
description: "Recover failed or stalled agents and child runs with bounded safe retries."
---

# Agent recovery

Use one recovery owner per run. Existing hooks keep their persisted retry count and cap; never add competing recovery. Hooks cannot detect every silent stall. For uncovered failures, prefer available in-session controls; a child-process supervisor may inspect exit/completion/idle signals. Verify CLI resume support before using it; otherwise re-dispatch only if safe.

Before continuing, inspect actual files, Git state through its read validator, and verification evidence. Resume only missing work, not an open-ended repetition of completed edits.

On Claude, prefer its available agent controls; do not invoke the Codex-specific
`codex-exec-watchdog.sh`. Without native recovery controls or either CLI, use
`scripts/recovery.py` with the verified Python and explicit JSON evidence on
stdin: `attempts`, `failure_kind` (`unknown`, `transient`, `deterministic`,
`user-stop`), `repeatable`, `user_stopped`, `uncertain_effects`. The helper only
decides; the recovery owner records attempts and resumes the missing work in
the current conversation. Inspect saved artifacts before every continuation.
Do not claim automatic process supervision or CLI resume in this manual mode.

Allow one automatic retry, excluding the initial attempt. Additional retries require a positively identified transient failure and safe repeatability. Never auto-retry deterministic input, command, auth, permission, build or test errors; user-paused work; destructive or approval-gated actions; or uncertain external side effects. Escalate with failure and attempt history when the cap is reached, state cannot be recorded, or no supported recovery exists.
