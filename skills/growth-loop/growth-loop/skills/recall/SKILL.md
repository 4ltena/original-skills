---
name: recall
description: Recovers context from past Claude Code sessions by searching transcripts. Use when the user refers to earlier work without restating it - "how did we fix that", "what was the workaround", "we decided something about this" - or when a task resumes and the reasoning behind the current state is not in context. Searches deterministically outside the model, then summarises.
argument-hint: "[what to search for]"
---

Read [runtime](../../RUNTIME.md) first. Use the verified Python and installed
`gl-run`; never depend on shebang, PATH or an unset plugin variable.

## Search

Run `<verified-python> -X utf8 -B <plugin-root>/bin/gl-run recall "<query>"`. Start with the user's own
words; the phrase they just used is the one most likely in the transcript. If
the memory is old, widen the window **and raise the cap together**:

```bash
<verified-python> -X utf8 -B <plugin-root>/bin/gl-run recall "<query>" --days 365 --max 100
```

`--days` alone will not reach it: the search reads newest first and stops at
`--max` (default 25), so on a recurring topic recent sessions fill the quota.

A line beginning `stopped at the --max limit` means something was left out, and
it names each loss: **older session(s) were not read** and/or **further matches
inside the sessions that were read were not printed**. Raise `--max` and run
again before concluding anything about the history. No such line means the
search was complete; do not re-run it looking for more.

If the first pass is thin, widen with concrete strings that would appear in a
transcript (error text, filenames, command names), not paraphrases. `gl-recall`
matches what was typed, not what was meant.

## Reading the hits

Read **newest session first**, which `gl-recall` already orders; a later session
usually supersedes an earlier one. Prefer the **resolution** over the
discussion: what was **decided** outranks what was merely considered. An
approach discussed at length and then abandoned in one line: that line is the
answer, and it is easy to skim past.

## Answering

Answer the actual question, **conclusion first**, then the supporting detail on
request. Never dump raw `gl-recall` output into the conversation: that spends
the context this tool exists to protect and hands the user your homework.

## When nothing is found

Before reporting a dead end, run
`<verified-python> -X utf8 -B <plugin-root>/bin/gl-run recall --list-roots`. If it reports no root, the
search never ran: say so, set `CLAUDE_TRANSCRIPT_DIR` to the directory holding
the `.jsonl` session files, and search again. Do not report "no history" when no
history was searched.

## Close the loop

A fact that had to be **searched twice** should not need a third search. Route
facts about this project to CLAUDE.md, and facts about the person to
`/growth-loop:profile`.
