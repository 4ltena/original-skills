# Portable runtime

Install through `original-skills/environment/SETUP.md`. The agent-led questionnaire
selects the host, Skill root and ownership-only deletion setting. It probes Python
3.10+ and writes this installed plugin's `binding.json`; source checkouts have no
machine binding and no active hooks. No Claude/Codex CLI is needed for preparation.

Read the installed host policy to find the stable plugin root. Run all operations
with that binding's absolute `executable`, `-X utf8 -B`, and absolute `bin/gl-run`.
Use argv or the installer-generated command; Windows expansion characters that
cannot be quoted safely are rejected. Never run via `python3` or a shebang on
Windows, and never guess `${CLAUDE_PLUGIN_ROOT}` in a standalone Skill.

`gl-run journey --paths` resolves the configured Skill/profile/candidate paths.
`journey --locate <name>` lists every matching directory. `recall --list-roots`
reports transcript search locations. These operations are offline. `nudge` accepts
the host event on stdin; the generated hook definitions call the verified Python.
Plugin registration/trust and live delivery are separate from source placement.

## Evaluation records

The source checkout's `e2e/run_e2e.py prepare` builds a temporary guided-install
home/work fixture for each case through `environment.install`; `request` prepares
a matching native-host or common-runner handoff; `grade-case` inspects declared
fixture artifacts, while `grade` scores supplied records offline. It does not ship
in this runtime and none of its stages invokes a model, CLI, auth store, or
weakens permissions. A passing record needs an explicit supported check with
artifact or trace evidence and an observed `invoked_skills` array. `null` means
unknown, while `[]` means observed none. Compare only equal fixture/runner/task
conditions across `none`, `current`, and `improved`; source revision identifies a
variant and is not a comparison condition. Missing or unknown metrics are never
zero or a pass.

For managed Skills, `owned create <slug>` accepts a JSON object mapping relative
paths to UTF-8 contents through stdin. Include `SKILL.md` with matching name and
description. `owned status <slug>` returns the generation and verifies contents.
`owned update <slug> --generation <id>` accepts the complete replacement payload.
`owned delete <slug> --generation <id> --reason obsolete|duplicate-merged|explicit-request`
removes all registered files, only when automatic deletion was explicitly enabled.
The caller supplies concrete obsolete evidence or verifies a completed merge;
age/name alone is insufficient. `owned recover <slug> --generation <id>` resumes
only a prepared transaction whose saved identity/digests still match.

The private ledger records roots, generations, directory/file identity and digests.
It does not adopt old Skills. Pending/dirty state blocks deletion; foreign content,
extra files, symlinks, reparse points, hardlinks, stale generation and corrupt state
are refused. Completed deletion retains minimal generation metadata, no content.
POSIX operations use directory FDs and validate after an atomic move; Windows uses
private owner ACLs and pinned handles, including handle-based rename/deletion.
Checks detect observed concurrent replacement. They do not isolate a hostile
process running as the same user with access to that user's files and memory.

If a transaction fails, inspect status and preserve pending payloads. Unprepared
transactions need manual inspection; no raw recursive-deletion fallback is allowed.
Existing/manual/synced/vendor/profile/memory targets keep explicit authorization
requirements. Related references are reported, never cascade-deleted.
