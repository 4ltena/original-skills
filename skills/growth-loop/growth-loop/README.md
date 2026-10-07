# growth-loop

A learning loop for Claude and Codex: jot a note, learn a reusable procedure,
refine on evidence, recall prior reasoning, maintain explicitly supplied profile
facts and review the accumulated Skills. No agent CLI is mandatory for placement.
All bin scripts are offline Python standard library; URL learning uses the host's
available authorized browsing tool, not this helper.

## Install and run

Follow [original-skills setup](../../../environment/SETUP.md). The agent asks a
shared questionnaire and shows a plan before applying it. It probes a real Python
3.10+ executable and generates local binding.json and host-specific hooks. On
Windows it rejects WindowsApps dummy aliases. Source hooks are inert; no shebang,
chmod or unverified python3 is required to install. See [RUNTIME.md](RUNTIME.md).

Use verified Python, -X utf8 -B, the installed absolute bin/gl-run and an operation
(journey, recall, nudge, owned). Registered plugin caches are never edited directly.
Skill placement, hook registration/trust and live runtime are separate outcomes.
The standalone installer uses /learn, /forget etc. (Codex: $learn, $forget); a host
loading the original plugin Skill package can use its supported namespaced forms.

| Skill | Invoked by | Result |
| --- | --- | --- |
| jot | user/model | Queue one specific note, without claiming a Skill was created |
| learn | user/model | Distil real recurring procedural evidence through owned create |
| refine | user/model | Correct on evidence; owned update preserves ledger identity |
| recall | user/model | Bounded transcript search at the resolved local roots |
| profile | user/model | Maintain non-secret explicitly supplied person facts |
| journey | user or authorized schedule | Evidence-based keep/correct/delete verdicts |
| forget | user/model | Completely delete a verified owned Skill; other targets need explicit authorization |

## Ownership-only automatic deletion

Enable it explicitly during installation. learn/skill-author create only unused
slugs through the ownership helper; manual, synced, vendor/system/plugin and old
Skills are never adopted. The protected ledger records generation, root/directory/
file identity and digests. refine uses owned update rather than editing managed
files directly. External changes, extra files, symlinks, reparse points, hardlinks,
root replacement, stale generation, corrupt ledger and lock contention refuse.

forget can run without another confirmation only for a verified created Skill.
journey/refine can route an obsolete Skill or a loser after verifying its merge
into the keeper. Age or similar names alone is not evidence. A successful delete
removes the whole payload, retaining only minimal generation metadata, no Skill
content/tombstone. Other Skills/profile/memory and references are not cascade-deleted.

Transactions record intent before publication/removal. Prepared interrupted work
can be recovered by matching saved identity/digests. Unprepared or inconsistent
payloads remain for inspection. No raw rm/rmtree fallback or ownership inference
is allowed. POSIX FD operations and Windows private ACL/pinned-handle operations
provide their documented protections; hostile same-user processes are not isolated.

## Verify

Run the offline suite from the growth-loop source directory with verified Python:

```text
<python-3.10+> -B tests/run.py
```

The model E2E harness remains opt-in and can incur cost. Offline tests and source
validation do not prove live Claude/Codex delivery or Windows behavior. The
existing manually planted forget E2E case must retain its unowned Skill until an
explicit deletion authorization is provided.

## Tuning

| Constant | File | Default | Meaning |
|---|---|---|---|
| `MIN_TOOL_CALLS` | `bin/gl-nudge` | 25 | Minimum tool calls before the nudge fires |
| `MIN_EDITS` | `bin/gl-nudge` | 3 | Minimum mutating calls — reading is not doing |
| `COOLDOWN_SECONDS` | `bin/gl-nudge` | 21600 | At most one nudge per 6h, shared by both events |
| `STALE_DAYS` | `bin/gl-journey` | 90 | Age at which a skill is flagged `STALE` in the listing |
| `--stale 60` | `skills/journey/SKILL.md` | 60 | Age at which the monthly review forces a verdict |
| `DEFAULT_MAX` | `bin/gl-recall` | 25 | Matches printed before the search stops — it reads newest first, so this is what decides how far back a search can reach |
| `DEFAULT_DAYS` | `bin/gl-recall` | 90 | How far back the search window extends |
| `SNIPPET_CHARS` | `bin/gl-recall` | 400 | Window around each transcript match |

Those two ages are separate knobs, and only the second one drives the
review: `STALE_DAYS` controls the `STALE` flag in the listing, while the
verdict `journey` forces comes from the `--stale 60` it runs. Raising
`STALE_DAYS` alone changes what the table looks like and nothing about what
gets decided — move both, or move the one you actually mean. Age is the
file's modification time, so copying or syncing a skill resets it.

These defaults are deliberately conservative. **The failure mode of this
whole plugin is a nudge you learn to ignore** — once that happens, lowering
the thresholds back down does not restore your attention to it. Loosen these
only after you notice yourself wishing the nudge had fired and it did not.
Do not tighten them preemptively; tightening after habituation has already
set in does not undo the habituation.
