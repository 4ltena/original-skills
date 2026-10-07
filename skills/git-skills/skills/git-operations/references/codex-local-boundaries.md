# Local Codex and shared-preset boundaries

Read this reference only in the user's Codex or shared preset environment. These are local operating constraints, not portable Git permissions. Check the current `~/.codex/AGENTS.md`, `~/.agents/common.md` if it applies, and the effective runtime permission profile; newer user instructions and active policy take precedence. Do not change Claude configuration or treat a Claude-only grant as a Codex grant.

## Claude host

On Claude, read the active host-home standard-github-policy.md, local-policy.md
and host-read-policy.md, or the explicit installed host binding. Do not import
another host's ~/.codex files, invent auto_review or invoke Codex CLI. Use actual
Claude permission prompts and available tools. A selected manual-git profile
requires an explicit request for every Git/GitHub write; implementation approval
alone is insufficient. All existing main/master, force, release, identity,
secret, deletion and instruction-file restrictions remain. Git/GitHub reads use
that host's fixed validators; missing bindings block those reads. The Codex
section below applies only on Codex.

## Codex standard

Read `~/.codex/standard-github-policy.md` before Git operations. It is the authority for Codex standard and overrides the older shared/Skill approval defaults. Within the requested task, it preauthorizes ordinary staging/commits and local merges on non-main/master destination branches, and ordinary pushes to non-main/master destination branches. Inspect current worktree branch and all push/merge destinations with the pinned Git reader. A merge from main into a feature branch writes the feature branch; a merge into main writes main. Respect any stricter repository gates and preserve existing work.

Do not ask again for a normal operation the policy already authorizes. Main/master writes, force pushes including `--force-with-lease`, remote ref deletions, tags and history rewrites use the policy's specific boundaries. Resolve `HEAD`, upstream and every refspec before applying them; no wildcard, mirror, deletion refspec, leading `+`, argument order or alternate API evades the rule. Use effective `on-request` with `auto_review`; if a task overrides approvals to `never` or automatic review denies an action, report the conflict and do not bypass it. GitHub-side operations, including PR merges, use `gh-operations` and its local boundaries.

## Other presets

Before every push, show the remote identity (redacted if credential-bearing), branch and outgoing commits, then obtain the approval this preset requires. Force push needs separate approval. Use a branch and PR unless the repository-specific exception below applies. Explain exact losses and obtain approval before destructive local operations such as `reset --hard`, `clean -fdx`, or branch deletion. Approval boundaries also cover global Git config and main/master merges.

Do not execute or submit for approval remote ref deletion under these other-preset defaults. Explain reason and exact target; leave execution to the user. Use `gh-operations` for GitHub-side restrictions. Runtime denials do not create fallback permission.

## Identity, index and related data

Use the user's existing Git identity; never hard-code, inject, or change it to satisfy a commit. Commit meaningful units rather than each trial. Squash, amend and rebase are not ordinary-commit operations. Check ignored working documents before push. Explain and obtain approval before index cleanup such as `git rm --cached`.

Never stage or commit `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.cursorrules`, `.github/copilot-instructions.md`, `.claude/`, `.codex/`, `.cursor/`, or `.project-notes/`. A narrow existing exception permits project `.claude/settings.json` only when it contains solely project-discipline hook wiring; prompts, instructions, agent definitions and model settings invalidate it. If those paths are tracked, leave them and ask before changes. No permission rule automatically catches a broad `git add -A`. If a repository rejects a commit, read its relevant guidance and diagnose; do not bypass required hooks with `--no-verify`.

h5i mutations remain subject to their separate approval rule. Only the exact validator-bounded capture named in `AGENTS.md` is preauthorized; raw capture, share, create, apply, repair, restore and removal are writes. h5i stores objects as Git refs, so history destruction can also destroy h5i state. Use `releasing` for version, tag, license and publication sequencing. These related workflows are not permissions granted by this Skill.

## Repository-specific direct-push exception

Default to a working branch and PR. Direct main/master pushes are allowed only when the user explicitly designates the exact repository as an exception and reconfirms each push after seeing the host, owner/repository, visibility, destination branch and outgoing commits. Private backup use alone grants no exception; public repositories may qualify with the same explicit designation and reconfirmation. Do not infer designation from repository content or prior pushes. This exception covers ordinary pushes only; force pushes, merges, protection changes and all other gates retain their separate rules. Runtime or managed-policy denials still apply.
