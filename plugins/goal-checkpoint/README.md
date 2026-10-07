# Goal Checkpoint

Reassess approved milestone evidence after 10,800 seconds, on the next supported
host event. Requires verified Python 3.10+; no background timer runs while idle.

Follow [agent-led setup](../../environment/SETUP.md) for CLI-free preparation,
selected scope and generated host bindings. Source hook templates are inert.
The installer probes the real interpreter and generates platform-specific commands,
so WindowsApps aliases and unverified python3 do not run the hooks. Skills are
placed once; runtime packages contain the bound helpers and hook definitions.
Source placement, registration/trust, live delivery and active monitoring are
separate results. Never edit installed plugin caches directly.

Codex successful native goal creation can register through the trusted PostToolUse
adapter; initial milestone/criteria/evidence remain unconfirmed. Duplicate events
keep the deadline. Claude instead uses an explicit purpose and approved plan with
a confirmed session_id; it does not fabricate native goal APIs. Without hooks,
explicit manual review remains available without claiming scheduled delivery.

Use the installed Skill and scripts/host_adapter.py with --host claude|codex,
the verified Python and local binding.json. Operations are enable/status/review/
baseline/ack/disable/resume. Pass bounded non-secret JSON on stdin. Pending review
is not milestone completion; stop instructions and terminal goals never restart
work. A Stop hook continues a turn at most once; acknowledgement records a review.

The shared core retains private files, nonblocking locks and atomic replacement.
Windows validates owner DACLs and rejects reparse points/hardlinks; POSIX uses
private mode/owner checks and directory FDs. Hook output retains no prompt/tool
content. See [Skill](skills/goal-checkpoint/SKILL.md) for baseline and recovery.

Offline verification from the repository root:

```text
<python-3.10+> -X utf8 -B -m unittest discover -s plugins/goal-checkpoint/tests -v
```

Tests simulate host envelopes and time in isolated directories; Windows real
execution, Claude live delivery and multi-day effects need separate evidence.
Official references: [Claude hooks](https://code.claude.com/docs/en/hooks),
[Codex plugin packaging](https://developers.openai.com/plugins/build/plugins).
