---
name: forget
description: Completely deletes a verified growth-loop-created Skill automatically. Use when evidence shows it is obsolete or merged; handles other Skill or profile deletion only within explicit user authorization.
argument-hint: "[what to forget]"
---

Read [runtime](../../RUNTIME.md) first. Use the verified Python and installed
`gl-run`; never depend on shebang, PATH or an unset plugin variable.

## Locate

Resolve `$ARGUMENTS` to one concrete target: a skill directory or a specific
profile line. If the reference is by topic ("that skill about migrations"), run
`<verified-python> -X utf8 -B <plugin-root>/bin/gl-run journey` and match against its listing rather
than guessing from memory.

**For a skill**, get the exact path from the tool, never by reconstructing one:
the listing prints clipped names with no path, and the same name can exist under
more than one root.

```bash
<verified-python> -X utf8 -B <plugin-root>/bin/gl-run journey --locate <name>
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
`<verified-python> -X utf8 -B <plugin-root>/bin/gl-run journey --paths`, read the `profile:` line, and
find the literal line inside that file.

If the scope is ambiguous (several matches, or unclear whether a skill or a
profile line is meant) ask before touching anything. A wrong guess deletes the
wrong thing, and there is no undo.

## Owned automatic deletion

Read [runtime](../../RUNTIME.md). Use the verified Python and installed `gl-run`:

```text
<verified-python> -X utf8 -B <plugin-root>/bin/gl-run owned status <slug>
<verified-python> -X utf8 -B <plugin-root>/bin/gl-run owned delete <slug> --generation <returned-generation> --reason obsolete
```

`duplicate-merged` is allowed only after opening both Skills, completing the fold,
and verifying the keeper retains the loser's useful knowledge. Age and similar
names alone never justify removal. An obsolete verdict needs concrete evidence.
With ownership-only automatic deletion enabled, successful status and deletion
need no additional human confirmation. Delete the entire verified payload, not
just SKILL.md. Report the outcome; a refusal is not deletion.

The helper rejects unowned/modified files, extra files, ambiguous roots, stale
generation, unsafe paths, symlinks/reparse points and ledger/lock failures. Never
fallback to rm/rmtree or register an old Skill to evade rejection. A pending
transaction needs `owned recover <slug> --generation <id>`; recovery validates
its saved intent and does not search for a new same-name generation.

## Other targets

For existing/manual/synced/vendor Skills or a profile line, show the exact path
and full proposed removal and require scoped user authorization. Keep earlier
explicit authorization if it already names this exact target; do not ask twice.
Without it, stop before deletion. The owned helper never removes these targets.
If an owned Skill is modified externally, report refusal for manual review;
automatic maintenance cannot switch to this route to bypass the ownership check.

## Delete, do not soften

No `[deprecated]` markers, no "this may no longer apply", no commented-out
blocks. A tombstone still loads every session and still shapes behaviour, and
costs what the original cost. If a value changed and the change itself is worth
keeping, that is a `/growth-loop:profile` update carrying the old value forward
(`uses pnpm (previously npm)`), not a comment left here. *Forget* means gone.

## Follow the references

A deleted item rarely stands alone: look for profile lines that only made sense
beside it, and other skills that name it or route to it. **Report what you find.
Do not delete it.** The verified ownership or explicit authorization covers one concrete target and nothing else; deleting a second skill on the strength of the first
"yes" defeats the gate this skill exists to be. List the referrers and stop. A
dangling reference is a correction (`/growth-loop:refine` on the referring
skill), not another deletion; anything that should go too comes back through
this skill from the top.
