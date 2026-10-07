# Goal Checkpoint

Reassess milestone progress after three hours, on the next supported Codex hook event. Requires Python 3.9+ and local Codex command hooks on Windows, macOS or Linux.

Successful native goal creation automatically registers the current session through the trusted PostToolUse hook. Failed or ambiguous results do not register; duplicate events preserve the deadline. The initial baseline stays unconfirmed until checked against the current goal and plan. Goal text is not saved.

Use `goal-checkpoint enable`, `status`, `review`, `baseline`, `disable` or `resume` for manual operations. Installation does not create goals or monitor chats without goals. Explicit manual monitoring is available when native goal tools are unavailable. Hosts without goal-tool hook delivery require skill-driven setup after goal creation; verify registration before claiming success.

Windows hooks use `python` on PATH; verify it resolves to a real Python installation. macOS/Linux use `python3`. Runtime-provided `PLUGIN_ROOT` and `PLUGIN_DATA` identify the installed source and writable data. Review and trust the installed hook definition through `/hooks` before expecting delivery.

The interval is 10,800 seconds from enable or acknowledgement. Idle time and a long running tool do not trigger a background timer. Pending reviews survive interruptions; a Stop hook continues a turn at most once. Terminal goals and budget exhaustion never restart development.

State uses private files, nonblocking process locks and atomic replacement. Windows validates owner-only DACLs and rejects reparse points/hardlinks; POSIX retains ownership, mode and no-follow checks. Hook notices contain fixed instructions and a checkpoint ID, never goal text or tool output.

## Verification

From the repository root:

```sh
python -X utf8 -B -m unittest discover -s plugins/goal-checkpoint/tests -v
```

Tests simulate the time boundary and hook envelopes in isolated directories. Distinguish passing tests, installation, hook trust, live delivery and active monitoring. See the [skill](skills/goal-checkpoint/SKILL.md) for operations and recovery.

Official references: [Hooks](https://learn.chatgpt.com/docs/hooks), [Plugin packaging](https://developers.openai.com/plugins/build/plugins).
