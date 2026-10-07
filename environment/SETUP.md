# Agent-led environment setup

Open this repository with the Claude or Codex agent you already use. Ask it to
install original-skills on this machine using this procedure. The agent asks the
predefined questions one at a time; neither agent CLI is required for preparation.
Do not run the apply command until the user has approved the concrete generated
plan and configuration diff. Preserve existing files and fixed host reader bindings.
Never copy authentication material or install missing tools without authorization.

## 1. Ask the questions

Read [questions.json](questions.json). Keep answers by stable question ID in the
conversation. Ask only applicable questions and show the Skill names included in
each set. Use the host's question UI if available, otherwise normal conversation.
The shared helper prints the next question plus available names and sets:

```text
<verified-Python-3.10+> -X utf8 -B <repository>/environment/install.py questions
```

Pass the answer object through stdin; start with `{}`. Host, Claude surface,
user/project scope, Skill set or individual names, plugin functions, Git mode,
owned deletion, checkpoint mode and settings scope are asked in order. New
installations show manual-git as recommended, but unanswered questions never
become implicit consent. `project_path` is required for project scope;
`skill_names` is required for custom selection. Explain additional dependencies
and return to selection when the user does not want them.

For example, completed answers for a minimal Claude setup are:

```json
{"host":"claude","surface":"desktop","scope":"user","skills":"basic",
 "plugins":[],"git_mode":"manual-git","settings":"candidates"}
```

For growth-loop include `"growth-loop"` in plugins, confirm the displayed generated
Skill roots with `growth_root: "selected-skills"`, and set `auto_delete: "yes"` or
`"no"`. For goal-checkpoint include `"goal-checkpoint"` and `checkpoint:
"enabled"` or `"manual"`. Explain that three hours means the next supported
session event after the deadline, not a timer running while idle. Chat without
terminal/hooks uses explicit manual procedures; local preparation does not upload
Skills into a remote chat or prove their activation there.

The agent handles back/change by revising answers and discarding inapplicable
ones. Cancel before applying leaves the destination unchanged. Keep answers in
conversation unless the user asks to save a non-secret plan for reuse/resume.
Saved answers require fresh path, Python, capability and conflict checks on each
machine. Do not persist credentials, prompts or transcript content.

## 2. Diagnose and build a plan

Identify a real Python 3.10+ executable. On Windows, inspect installed interpreter
paths (or the Python launcher's interpreter listing), then probe the absolute
executable; do not launch the WindowsApps python3 alias. The helper itself uses
only Python's standard library. Explicit invalid interpreters fail without fallback.
Git/GitHub binaries and pinned reader versions are required only for the Skills
that use them; absent readers block those operations rather than all placement.
Agent CLI, LSP, authentication and third-party plugins are optional host features.

```text
<verified-python> -X utf8 -B <repository>/environment/install.py plan --home <target-home> --python <absolute-python>
```

Pass the completed answers on stdin. Inspect selected Skills, added dependencies,
all create/change paths and exact diffs, preserved files and remaining host
registration/trust. The helper diagnoses existing files rather than overwriting
Skills; frontend-design is installed only from the personal source and an existing
same-name Skill always wins. superpowers, external frontend-design, commit-commands,
LSP and other third-party plugins are not automatically installed/enabled.

`skills-only` places Skills and bound runtime helpers. `candidates` additionally
prepares settings/instruction candidates. `apply-selected` merges selected Claude
permissions/hooks and appends the selected host-policy reference to instructions,
with backups; unrelated model/plugin settings remain intact. Existing policy and
reader files are preserved. Resolve any policy conflict explicitly; do not claim a
new profile is effective while an existing policy prevents it. The Codex full
sandbox TOML and global Git identity/config are separate operations and are not
modified by this helper.

Skill files live once in the selected host's skills directory. Runtime packages in
`<host-home>/original-skills/` contain hooks/helpers, with no duplicate Skill tree.
Bindings record the probed executable and explicit state/Skill roots. Generated
Claude hooks use an executable plus an argument array, bypassing shell quoting on
every platform. Codex Windows shell-form commands quote spaces/Unicode and reject
expansion characters that cannot be represented. Source hook templates are inert
until generated. Verify the host supports the generated schema before registration;
the [Claude hook reference](https://code.claude.com/docs/en/hooks#exec-form-and-shell-form)
documents the required exec form. Older unsupported hosts need manual operation
or an explicitly reviewed update, without a guessed shell fallback.

## 3. Apply only the reviewed plan

After the user approves its exact effects, pass the generated plan on stdin:

```text
<verified-python> -X utf8 -B <repository>/environment/install.py apply --approve-plan <reviewed-plan_id>
```

The plan ID is a freshness check, not a substitute for human approval. The helper
recomputes against this machine and refuses changed destinations or dependencies
before writing. Replaced files get unique sibling backups. If a filesystem error
interrupts application, inspect the reported/remaining paths, preserve backups and
build a fresh plan; do not retry a stale plan or erase partial files indiscriminately.

For manual-git, explicit user requests are required for stage/commit/push/merge/tag,
PR creation/update and GitHub writes. Claude gets ask rules and a conservative
PreToolUse guard; the exact bound owned helper is allowed without broad rm grants.
Codex gets host policy plus direct Git/GitHub prompt rules. Wrappers/APIs are not
an absolute sandbox boundary: host permissions and existing stricter gates apply.
Switching an existing automatic profile requires a reviewed change rather than
keeping conflicting automatic hooks/rules active.

## 4. Register and verify supported host features

Placement and preparation are complete independently of CLI availability. Invoke
installed Skills from the actual host catalog or read their SKILL.md in conversation.
[HOSTS.md](HOSTS.md) lists all 46 entrypoints and adapters. Do not claim plugin or
hook activation from a file copy. Use the selected host's supported source/plugin
registration and trust UI only when available and within the approved plan. Claude
settings hooks can use the prepared runtime directly; do not also register the same
hook package and double-fire it. On Codex register the generated hooks-only runtime
through its supported local marketplace/plugin flow, then trust the actual hooks.
Use the installed directory as the source and a reviewed marketplace entry. Never
edit plugin caches. Workflow procedures are already standalone Skills and need no
additional plugin registration in this route.

For goal-checkpoint, native Codex creation hooks can auto-register after successful
create_goal. Claude requires explicit enable from the user's objective/plan and a
confirmed session_id; without session hooks use manual review. No native goal is
invented. For growth-loop, all commands use verified Python + installed bin/gl-run.
Only newly created Skills with a valid ownership ledger may be auto-deleted;
manual/synced/vendor/profile/memory and externally changed Skills are excluded.
See [growth-loop runtime](../skills/growth-loop/growth-loop/RUNTIME.md).

Verify metadata/references, JSON/TOML parsing where changed, selected command
smokes, host registration/trust and live delivery separately. Missing runtime
capabilities remain unverified. Windows real-machine, paid model E2E, three-hour
live notification and multi-day development evidence must never be inferred from
an offline fixture. Optional full Codex config merging remains in
[codex/apply_config.py](codex/apply_config.py); review its exact diff separately.
