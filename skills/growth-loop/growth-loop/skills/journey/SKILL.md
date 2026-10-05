---
name: journey
description: Reviews everything the learning loop has accumulated - skills, memory files, the nudge ledger - and forces a verdict on every stale skill. Run this weekly - either the person invokes it directly, or a schedule they set up in advance fires it for them; either way it is never a call the model decides to make mid-conversation. Deletion stays a human decision no matter which of those triggered the run.
disable-model-invocation: true
allowed-tools: Bash("${CLAUDE_PLUGIN_ROOT}"/bin/gl-journey:*)
---

> Under Codex, `${CLAUDE_PLUGIN_ROOT}` is unset: use the plugin root, two
> directories above this SKILL.md. `/growth-loop:<skill>` is `$growth-loop:<skill>` there.

## Gather

Run all three and read them before deciding anything:

- `"${CLAUDE_PLUGIN_ROOT}"/bin/gl-journey`: the full inventory of skills, memory
  files and the nudge ledger.
- `"${CLAUDE_PLUGIN_ROOT}"/bin/gl-journey --stale 60`: what is due, skills older
  than 60 days, before the 90-day STALE flag. It narrows the SKILLS section
  only; MEMORY and LEDGER print in full, so a memory file in this pass is not a
  stale item.
- `"${CLAUDE_PLUGIN_ROOT}"/bin/gl-journey --duplicates`: skill pairs ranked by
  description similarity, or `(none)`. Each pair is a candidate to open, not a
  verdict: it compares description text only, so it surfaces some unrelated
  pairs and cannot see an overlap phrased in dissimilar words.

## The verdict

Every **skill** `gl-journey --stale 60` surfaces gets exactly one verdict; no
undecided leftovers.

- **Delete**: it no longer applies, or should never have been written. Name it
  and why; this is a recommendation in the report, not an action you take.
  `/growth-loop:forget` is user-invoked only and you cannot invoke it, so let
  the person run it. Do not delete the directory yourself.
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

A merge has two halves and you perform only the first. Fold what the loser has
that the keeper lacks into the keeper through `/growth-loop:refine`. Then
recommend the loser for deletion and stop. Do not delete it here: it would be a
skill never located, shown or confirmed, which is what `forget` exists to
prevent, and you cannot call it. Name the directory and let the person act.
Until they do the merge is incomplete and the duplication is worse than before;
say so in the report.

## Audit the description set

Read descriptions from the files, not the listing: it clips each at 90
characters, which cuts the "use when …" clause the question below turns on. The
listing also prints clipped names and no paths, so resolve each one:

```bash
"${CLAUDE_PLUGIN_ROOT}"/bin/gl-journey --locate <name as the listing prints it>
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
the decisions: what is recommended for deletion and why, what got corrected,
what got kept and why, duplicates folded together with the loser named for
deletion, and descriptions routed to refine for mis-targeting.

## When a schedule triggers this run

A run fired by a schedule the person set up follows every section above
exactly, including performing a confirmed merge's fold through
`/growth-loop:refine` without pausing: they approved that when they set up the
schedule. `forget` is still unreachable, so every deletion lands in the report
as a named recommendation, never as a directory removed. Because nobody is
watching, send the report through rather than only printing it, so a wrong fold
is caught from the notification and reverted.
