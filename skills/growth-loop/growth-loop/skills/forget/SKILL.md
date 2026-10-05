---
name: forget
description: Deletes a skill or a profile entry completely, after showing exactly what will be removed and getting confirmation. Use when the user says "forget that", "delete that skill", or "that is no longer true". Deletion is a human decision, so this skill is never invoked automatically.
argument-hint: "[what to forget]"
disable-model-invocation: true
allowed-tools: Bash("${CLAUDE_PLUGIN_ROOT}"/bin/gl-journey:*)
---

> Under Codex, `${CLAUDE_PLUGIN_ROOT}` is unset: use the plugin root, two
> directories above this SKILL.md. `/growth-loop:<skill>` is `$growth-loop:<skill>` there.

## Locate

Resolve `$ARGUMENTS` to one concrete target: a skill directory or a specific
profile line. If the reference is by topic ("that skill about migrations"), run
`"${CLAUDE_PLUGIN_ROOT}"/bin/gl-journey` and match against its listing rather
than guessing from memory.

**For a skill**, get the exact path from the tool, never by reconstructing one:
the listing prints clipped names with no path, and the same name can exist under
more than one root.

```bash
"${CLAUDE_PLUGIN_ROOT}"/bin/gl-journey --locate <name>
```

`--locate` matches the clipped form too, so paste the name as the listing
printed it. It prints the directory, which is what gets deleted:

- **One line.** That is the target; use it verbatim.
- **More than one line.** The name is ambiguous. Show every path, name what
  distinguishes them, and ask which. Never pick.
- **`no skill named …`, exit 1.** Nothing matched. Say so and stop; do not fall
  back to a path you assembled.

**For a profile line**, `--locate` does not apply: it looks up skills, so a
profile entry always misses. Resolve the file with
`"${CLAUDE_PLUGIN_ROOT}"/bin/gl-journey --paths`, read the `profile:` line, and
find the literal line inside that file.

If the scope is ambiguous (several matches, or unclear whether a skill or a
profile line is meant) ask before touching anything. A wrong guess deletes the
wrong thing, and there is no undo.

## Show

Before asking for confirmation, print exactly what will be removed, not a
summary of it: the full path for a skill directory, the literal line for a
profile entry. The person must see the actual thing that is about to disappear.

## Confirm

Wait for confirmation. Do not proceed on an implied yes: agreeing with the
description of the deletion is not agreeing to the deletion. Deletion is
permanent; asking again is cheap.

## Delete

For a skill, delete the whole `<slug>/` directory, not just `SKILL.md`: orphaned
support files fail silently. For a profile entry, remove that line and leave the
rest of the file untouched.

## Delete, do not soften

No `[deprecated]` markers, no "this may no longer apply", no commented-out
blocks. A tombstone still loads every session and still shapes behaviour, and
costs what the original cost. If a value changed and the change itself is worth
keeping, that is a `/growth-loop:profile` update carrying the old value forward
(`uses pnpm (previously npm)`), not a comment left here. *Forget* means gone.

## Follow the references

A deleted item rarely stands alone: look for profile lines that only made sense
beside it, and other skills that name it or route to it. **Report what you find.
Do not delete it.** The confirmation covers the one target that was located and
shown, and nothing else; deleting a second skill on the strength of the first
"yes" defeats the gate this skill exists to be. List the referrers and stop. A
dangling reference is a correction (`/growth-loop:refine` on the referring
skill), not another deletion; anything that should go too comes back through
this skill from the top.
