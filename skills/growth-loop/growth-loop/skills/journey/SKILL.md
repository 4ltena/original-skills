---
name: journey
description: Reviews everything the learning loop has accumulated - skills, memory files, the nudge ledger - and forces a verdict on every stale skill. Run this weekly - either the person invokes it directly, or a schedule they set up in advance fires it for them; either way it is never a call the model decides to make mid-conversation. Only verified growth-loop-created Skills may be deleted automatically; other targets require explicit authorization.
disable-model-invocation: true
---

Read [runtime](../../RUNTIME.md) first. Use the verified Python and installed
`gl-run`; never depend on shebang, PATH or an unset plugin variable.

## Gather

Run all three and read them before deciding anything:

- `<verified-python> -X utf8 -B <plugin-root>/bin/gl-run journey`: the full inventory of skills, memory
  files and the nudge ledger.
- `<verified-python> -X utf8 -B <plugin-root>/bin/gl-run journey --stale 60`: what is due, skills older
  than 60 days, before the 90-day STALE flag. It narrows the SKILLS section
  only; MEMORY and LEDGER print in full, so a memory file in this pass is not a
  stale item.
- `<verified-python> -X utf8 -B <plugin-root>/bin/gl-run journey --duplicates`: skill pairs ranked by
  description similarity, or `(none)`. Each pair is a candidate to open, not a
  verdict: it compares description text only, so it surfaces some unrelated
  pairs and cannot see an overlap phrased in dissimilar words.

## The verdict

Every **skill** `gl-journey --stale 60` surfaces gets exactly one verdict; no
undecided leftovers.

- **Delete**: it no longer applies, or should never have been written. Name the evidence and invoke `/growth-loop:forget` for a verified owned Skill
  when automatic deletion is enabled. Other targets stay a recommendation.
  Age alone is not deletion evidence. Never delete a directory directly.
- **Verify and correct**: the knowledge might still hold but has not been
  checked lately. Check it against reality now, then route the fix through
  `/growth-loop:refine`.
- **Keep and say so**: still correct despite its age. Say in the report why the
  age does not undermine it.

"I'll look at it later" is not a verdict: an item nobody can decide on is an
item nobody trusts.

## Duplicates

Start from the `--duplicates` shortlist. The same procedure described twice is
worse than once, since whichever fires first is followed. Merge into the skill
with the better **What goes wrong** section, not the newer one: the dead ends it
documents are the irreplaceable part. Open both files with `--locate` (below),
not a path you assembled.

Fold what the loser has that the keeper lacks into the keeper through
`/growth-loop:refine`, then read the keeper and verify the useful knowledge was
retained. Invoke `/growth-loop:forget` for an owned loser with the verified merge
evidence. If the loser is unowned, modified or automatic deletion is disabled,
report it as a recommendation and mark the merge incomplete. Never adopt it or
delete it directly.

## Audit the description set

Read descriptions from the files, not the listing: it clips each at 90
characters, which cuts the "use when …" clause the question below turns on. The
listing also prints clipped names and no paths, so resolve each one:

```bash
<verified-python> -X utf8 -B <plugin-root>/bin/gl-run journey --locate <name as the listing prints it>
```

Paste the name exactly as printed, trailing `...` included: that suffix asks for
a prefix match. It prints the directory across every root. Do not glob the
`skills-root:` from `--paths`: it reports the first root only, so you would
audit a subset of what you listed. Open each `SKILL.md` and read its
frontmatter.

Read them together as a set. The question for each pairing: given a task,
would exactly the right one fire? Two descriptions that plausibly match the same
task mean the wrong one sometimes wins; one vague enough to match nothing means
the task is redone instead of recalled.

An overlap is a targeting error with both files in front of you, and that is
`/growth-loop:refine`. Route it there and say so in the report. A description
merely vague enough that nothing fires is not that: nothing has failed yet, and
`refine` declines speculative polish, so do not send it there. Name it in the
report as a weakness to watch; the next real miss is the evidence for a fix.

## Report

Give a short verdict, not the inventory; the user can see the listing. Report
the decisions: what was deleted or recommended for deletion and why, what got corrected,
what got kept and why, duplicates folded together with the loser named for
deletion, and descriptions routed to refine for mis-targeting.

## When a schedule triggers this run

A run fired by a schedule the person set up follows every section above
exactly, including performing a confirmed merge's fold through
`/growth-loop:refine` without pausing: they approved that when they set up the
schedule. Owned-only deletion uses the same evidence and helper checks. Other targets
stay named recommendations. Deliver a report through an already-authorized
notification channel if available; otherwise report in this conversation.
Scheduling a review does not authorize new messages to other people.
