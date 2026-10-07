---
name: goal-checkpoint
description: Automatically register checkpoint monitoring when a native goal is created, then reassess milestone evidence after three hours. Inspect, review, disable or resume monitoring; not goal creation or a general process audit.
---

# Goal checkpoint

Compare evidence of meeting approved completion criteria, rather than edit, commit or test counts. After reviewing progress, return to authorized implementation. Use this skill only when available in the current runtime catalog.

## Runtime and commands

Requires Python 3.9+ and local Codex command hooks on Windows, macOS or Linux. Resolve the installed `../../scripts/checkpoint.py` and the actual runtime `PLUGIN_DATA`; never guess either path. Use a verified Python (`python` on Windows, `python3` on POSIX), `-X utf8 -B`, and quoted absolute paths.

Use runtime `CODEX_THREAD_ID`, or a runtime-confirmed `--session`; never infer it from cwd. Commands are `enable`, `status`, `review`, `baseline`, `ack`, `disable` and `resume`. Enable accepts `--workspace <confirmed absolute workspace>`; resume uses the registered workspace. Pass JSON through protected stdin, not shell interpolation.

Review and trust the exact installed hook definition through `/hooks`. Report installation, trust and live delivery separately. Three hours means the next supported event after 10,800 seconds from enable/ack, not an idle background timer.

## Automatic registration

After a successful native `create_goal`, the trusted PostToolUse hook registers the current session/workspace automatically. It requires an active structured goal result and a tool-call ID; ambiguous or failed results prompt confirmation without registering. Goal text and arbitrary tool output are never saved. Duplicate delivery keeps the deadline and any explicit disable unchanged; a new goal-creation call starts a new generation.

The initial milestone, criteria and implementation evidence are explicitly unconfirmed. Check the latest goal and existing plan, then update them through `baseline` using the active `goal_ref` and `generation`, without resetting the deadline. Never treat the monitor reference as a native goal ID. If this host does not deliver goal-tool hooks, invoke this setup immediately after confirmed goal creation using the available skill; verify registration instead of claiming automatic delivery.

## Enable or resume

Check the latest goal, budget and user stop instructions. Do not enable terminal, paused, blocked or exhausted goals, or create a native goal. If goal tools are unavailable, explicit user-authorized manual monitoring can use an existing objective and plan.

Read the existing canonical CURRENT/handoff and relevant approved criteria. Establish the workspace, milestone and evidence baseline; missing evidence stays unknown. Send:

```json
{"goal_status":"active","budget_exhausted":false,"goal_ref":"confirmed reference","milestone":"M1","criteria":"approved criterion and reference","evidence":"verified evidence reference or unknown"}
```

Each text field is nonempty and at most 2 KiB; JSON is at most 16 KiB. Persist short facts/references, never transcripts or secrets. If native goals lack a durable ID, generate a UUID reference for this monitor and disclose that it is not a native goal ID. A replaced goal requires a new enable; objective similarity does not prove continuity.

Confirm command success and active state, due time in the user's timezone and pending status. Resume only disabled monitoring with a fresh baseline; do not automatically transfer sessions.

## Review and acknowledge

1. Check the latest goal and stop instructions first. For complete, paused, blocked, exhausted or explicitly stopped goals, disable monitoring and do not restart work. If latest goal status is unavailable, do not acknowledge it as active.
2. Read status and confirm workspace, generation and pending ID. Ignore stale notification identities. For an explicitly requested manual review with active monitoring and no pending record, call `review` once. Do not resume disabled monitoring implicitly.
3. Compare current criterion evidence and concrete blockers with the baseline. Mark `progress` when unmet criteria or blockers decrease, including necessary safety/recovery fixes; otherwise mark `stalled`. Do not restart specification or broaden into a general audit.
4. Select the smallest authorized implementation/check addressing an unmet criterion. On repeated stalling for the same criterion, choose a justified alternative or identify the missing user decision. Preserve required validation and safety.
5. Send `ack` with the fresh baseline JSON plus the confirmed `generation`, `checkpoint_id` and `verdict` (`progress` or `stalled`). Goal reference must stay the same. Confirm success and pending clearance; acknowledgement proves review, not completed implementation.

Report latest goal/milestone, changed evidence, verdict/reason, next concrete work and acknowledgement/disable briefly. Update the existing CURRENT only when useful; create no duplicate ledger.

## Status, disable and recovery

`status` distinguishes inactive, pending, unregistered, corrupt and unavailable states. `disable` accepts `{"reason":"confirmed reason"}` and leaves the native goal unchanged. Interrupt suppresses that turn's continuation, preserving monitoring/pending for the next user instruction.

Recover corrupt JSON only through explicit enable after confirming the latest goal and baseline. Never overwrite unsafe files, another owner, reparse points or stale acknowledgements. A backward clock resets the deadline; pending review is not completion. Missing plugin data, Python or trust means incomplete setup, not active monitoring.
