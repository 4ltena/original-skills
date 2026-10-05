---
name: refine
description: Corrects a stored skill against evidence in front of you - a step that failed, an assumption that no longer holds, a better route found, a description that fired at the wrong time, or a duplicate whose content has to be folded into the skill that supersedes it. Use when following a skill produced an error, when a documented command no longer exists, when the right skill did not fire for an obviously matching task, or when a review puts two overlapping skills side by side. Correct on evidence, never on a hunch.
---

## When this fires

The hard rule: **refine on evidence in front of you, never on a hunch.** That is
usually something that happened this session, with the failing command, its
output and the fix still in view, or a review that has the files open side by
side. Never a half-remembered past failure or a guess. Fire when:

- A step produced an error when followed, or a documented command or flag no
  longer exists.
- A better route was found while following the documented one.
- The right skill did not fire for a task it obviously matched, or a wrong one
  fired instead.
- A review found two descriptions that both plausibly claim the same task, so
  whichever fires first wins regardless of which is right.
- A review puts two skills side by side and one has to absorb what the other
  documents. `/growth-loop:journey` routes merges here.

## The procedure

Read the whole file first: a targeted edit to a file you have not read
contradicts sections you did not see. Then make the smallest correct edit,
verified against the evidence that brought you here. Then append a dated entry
under `## Revisions` saying what changed **and why**:

```markdown
## Revisions
- 2026-08-04: replaced `--force` with `--yes` — the flag was renamed
  upstream; `--force` now exits 2 with "unrecognized argument".
```

The why stops the next reader reinstating the old step because it looked
reasonable.

## Fixing the description

For two descriptions that claim the same task, **narrow one of them** so it
stops claiming what the other owns; do not broaden either. Decide which skill
genuinely owns the task, edit the other, and put the `## Revisions` entry in the
file you edited. Nothing fired wrongly yet, so there is no situation to name:
record which skill now owns the overlap, and why.

If the failure was targeting (the skill did not fire when it should have, or
fired on a task it does not cover) the body is fine and the description is the
bug. Rewrite it to name the exact situation that occurred, concretely enough to
trigger next time.

## What not to do

Never soften a wrong step into a hedge. "This may not work on newer versions" is
the original wrong step with a disclaimer taped to it. State the condition
precisely ("on v2 and later, use `--yes` instead of `--force`") or delete the
step.

## When it is beyond repair

If more than half the skill is wrong, or it is patched so often the throughline
is gone, stop editing and route to `/growth-loop:forget`. You cannot invoke it:
present the skill and why it is beyond repair, then stop and let the person run
it. Do not delete the directory yourself. A heavily patched skill built on a
dead assumption still reads as authoritative, which is worse than none.

## When to write nothing

A skill that was merely unhelpful (vague, slower than it needed to be) but not
wrong needs no edit: refine corrects errors, it does not polish prose. Missing
and overlapping are not merely unhelpful. A keeper that lacks the dead end its
duplicate documents is wrong for the reader who follows it into that dead end,
and two descriptions that claim one task are wrong for the reader whose task
fires the wrong one. Folding in a dead end and narrowing an overlapping
description are corrections, not polish; this rule declines neither route that
`/growth-loop:journey` sends here.
