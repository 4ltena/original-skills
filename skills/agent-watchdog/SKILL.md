---
name: agent-watchdog
description: "Recover failed or stalled subagents and child Codex runs with bounded safe retries."
---

# Agent recovery

Use one recovery owner per run. Existing hooks keep their persisted retry count and cap; never add competing recovery. Hooks cannot detect every silent stall. For uncovered failures, prefer available in-session controls; a child-process supervisor may inspect exit/completion/idle signals. Verify CLI resume support before using it; otherwise re-dispatch only if safe.

Before continuing, inspect actual files, Git state through its read validator, and verification evidence. Resume only missing work, not an open-ended repetition of completed edits.

Allow one automatic retry, excluding the initial attempt. Additional retries require a positively identified transient failure and safe repeatability. Never auto-retry deterministic input, command, auth, permission, build or test errors; user-paused work; destructive or approval-gated actions; or uncertain external side effects. Escalate with failure and attempt history when the cap is reached, state cannot be recorded, or no supported recovery exists.
