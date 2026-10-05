---
name: learn
description: Distils a reusable skill from work that just finished, when a task took real effort to get right and the same problem will come back. Use when the user says "remember how to do this", "write that down", or "make a skill for this"; when a multi-step procedure has just succeeded after several failed attempts; or when the nudge hook reports a heavy session. Takes an optional target - a directory or URL - and otherwise distils this conversation.
argument-hint: "[directory-or-url]"
allowed-tools: Bash("${CLAUDE_PLUGIN_ROOT}"/bin/gl-journey:*)
---

> Under Codex, `${CLAUDE_PLUGIN_ROOT}` is unset: use the plugin root, two
> directories above this SKILL.md. `/growth-loop:<skill>` is `$growth-loop:<skill>` there.

## First: check for overlap

Run `"${CLAUDE_PLUGIN_ROOT}"/bin/gl-journey` and read the SKILLS section. If an
existing skill already covers the same ground, stop and route to
`/growth-loop:refine` instead of writing a second one. Near-duplicates are the
rot vector: whichever fires first gets followed, correct or not.

## The gate

All three must hold, or nothing gets written:

- **It took real work.** A reader could not have reconstructed it from first
  principles: several failed attempts, a non-obvious flag, or a source that
  isn't the official docs.
- **It will recur.** The same situation, or a close variant, will come up in
  other sessions.
- **It is procedural.** A way of doing something, not a fact about one
  repository (that belongs in its `CLAUDE.md`) or about the person (that
  belongs in `/growth-loop:profile`).

## When to write nothing

Most sessions do not deserve a skill. Saying "nothing here is worth keeping"
and stopping is a success. Reject these common false positives:

- Difficulty caused by an outage or a flaky dependency, not by the procedure.
- A one-off migration or cleanup that will not run again in this form.
- Anything already in the project's `CLAUDE.md`.

## Where it goes

Resolve the directory before writing; do not assume a path:

```bash
"${CLAUDE_PLUGIN_ROOT}"/bin/gl-journey --paths
```

Write to `<that directory>/<slug>/SKILL.md` using the `skills-root:` line, with
`<slug>` in kebab-case. That is the first root `gl-journey` reads, so the
overlap check above will find what you write. Do not hardcode `~/.claude/skills`,
and do not resolve it with a shell expansion such as
`${GROWTH_LOOP_SKILL_ROOTS:-...}`: some hook policies refuse any command
containing one, and the skill then falls back to guessing.

**Check the target does not already exist before writing.** If
`<slug>/SKILL.md` is there, stop. Do not overwrite it and do not quietly pick
`<slug>-2`: overwriting destroys a skill as surely as deleting it, with nobody
shown what was lost. Report the collision. If the existing skill covers the
same ground, the answer is `/growth-loop:refine`; if the content is unrelated,
choose a slug that names this situation more precisely.

## The template

```markdown
---
name: <slug>
description: <what it does + the exact situation that should trigger it>
---

## When this applies
## The approach
## What goes wrong
```

**The approach** carries verbatim commands with the flags that mattered:
`alembic upgrade head --sql`, not "run the migration".

**What goes wrong** is the payload: the plausible route that silently failed,
and the symptom that gave it away. A distillation with no dead end is not worth
writing; if you cannot name one, go back to the gate.

## Pending jots

`/growth-loop:jot` queues notes without any check, so the checks happen here.
Resolve the queue with the same `--paths` command and read the `candidates:`
line; each entry is a `## ` heading. For each one apply the overlap check, then
the three-condition gate. A passing entry is promoted through the same template
and existence check; a failing one is dropped. Either way, remove that entry
from `candidates.md`, editing out only that block and leaving every other entry
untouched: a queue that only grows is the failure `learn` exists to prevent.

## Delegating

For a long session, dispatch the `skill-author` subagent if your runtime has it
(Codex does not ship it), otherwise write inline. Hand it the facts (what was attempted, what failed and why, what worked);
it writes the document, so do not draft it first. It cannot resolve
`${CLAUDE_PLUGIN_ROOT}`, so do both write checks yourself and hand over their
results: give it the resolved absolute path and confirm that path is free first.

## Reporting

Report only the path written and its description line. Do not paste the body.

## Handling $ARGUMENTS

- `$ARGUMENTS` empty: distil this conversation, then process pending jots.
- `$ARGUMENTS` a directory: read it and distil the procedure it encodes.
- `$ARGUMENTS` a URL: fetch it and distil the procedure it describes.

The same gate applies to all three.
