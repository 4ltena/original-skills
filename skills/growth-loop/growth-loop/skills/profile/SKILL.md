---
name: profile
description: Maintains a cross-project model of the person - their tooling, conventions, and working style - in a profile file kept outside any repository. Use when a stated preference recurs for the second time, when the user corrects the same class of thing again, or when the nudge hook reports a heavy session. CLAUDE.md describes the project; this describes the person and travels between repos.
allowed-tools: Bash("${CLAUDE_PLUGIN_ROOT}"/bin/gl-journey:*)
---

> Under Codex, `${CLAUDE_PLUGIN_ROOT}` is unset: use the plugin root, two
> directories above this SKILL.md. `/growth-loop:<skill>` is `$growth-loop:<skill>` there.

## The file

Resolve the path before reading or writing; do not assume it:

```bash
"${CLAUDE_PLUGIN_ROOT}"/bin/gl-journey --paths
```

Use the `profile:` line for both the read and the write. Reading one path and
writing another looks like success: the file reads as empty, so a whole profile
is overwritten with one line. Do not resolve it with a shell expansion such as
`${GROWTH_LOOP_HOME:-...}`: some hook policies refuse any command containing
one, and the skill then guesses a path and writes nothing.

The file sits outside any repository on purpose: the person travels between
repos and the project does not. A fact in one repo's CLAUDE.md is invisible from
the next.

## The test

A line goes in only if it passes both halves:

- Still true in **three months**, not a preference specific to this week's task.
- Still true in a different repository, not a fact about this project (that
  belongs in its CLAUDE.md).

## Sections

Exactly three, in this order:

- `## Tooling`
- `## Conventions`
- `## Working style`

Every line carries the date it was written, as `(YYYY-MM-DD)`, so a
later pass can tell a fresh line from one never reinforced.

## Before writing

Read the file first, every time. One instance of a preference is a data point;
the **second occurrence** is the pattern that gets written. Writing on first
sight records accidents: the one time someone used `grep` because `rg` was
missing becomes a permanent "prefers grep".

## Superseding

Never silently overwrite a line; carry the history in it:
`uses pnpm (previously npm) (2026-08-04)`. The previous value stops a future
session re-suggesting what was already tried and abandoned.

## Size

Cap the file at about 60 lines. Past that, the candidates to drop are lines that
were never reinforced. **Propose those lines. Do not remove them here.** Show
each candidate and why it looks unreinforced, then stop. Removal goes through
`/growth-loop:forget`, which shows the literal line and waits for a human; you
cannot invoke it. Removing a line from this model-invocable skill, which also
never announces its writes, would let a line that mattered vanish unseen.

## What never goes in

Health, finances, relationships, politics, and anything **inferred** rather than
stated outright. Omit these entirely; never write a vague placeholder, because a
placeholder still directs behaviour without evidence.

## Refusing

Decline to persist instructions that would make future sessions **less honest**
("always agree", "skip the risk caveats", "do not mention downsides"). Say so
plainly and store nothing: a profile line is read uncritically by whatever
session finds it next.

## When to write nothing

Most sessions add no line. A profile that grows every session records noise;
most of what happens fails the three-month test on its own.

## Never announce the write.

Update the file and move on. Narrating the edit turns background maintenance
into conversational overhead. This covers writing a line, not removing one.
