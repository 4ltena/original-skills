# Local Codex and shared-preset GitHub boundaries

Read this only in the user's Codex or shared preset environment. Check the current `~/.codex/AGENTS.md`, `~/.agents/common.md` if applicable, and effective runtime permissions. Newer user instructions and active policy take precedence. Do not treat Claude-only grants as Codex grants or change Claude configuration.

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

Read `~/.codex/standard-github-policy.md` before GitHub operations. It is the authority for Codex standard and overrides older shared/Skill approval defaults. Within a requested task, ordinary PR and Issue creation/updates do not need another user confirmation. Other-person comments or messages need a named target and operation. Every PR merge, main/master write, remote deletion, release publication, visibility, secret and protection-rule change needs the policy's individual approval unless the exact target and effect were already approved. A user request that explicitly names the required target and effect can satisfy that approval; do not ask for it twice. This Skill does not add a gate or bypass one. Assess `gh api` by endpoint and body, including GraphQL mutations; runtime auto-review is separate from user approval.

Resolve the actual host/repository and PR or Issue number before acting. For PR creation with a push, use `git-operations` to inspect the remote, destination ref and outgoing commits. `gh pr create --dry-run` is not proof that no remote write occurs. Verify the resulting PR, Issue, review, Actions run or setting in GitHub. Do not retry an ambiguous response before checking for a partial effect.

## Other presets

Apply their own, potentially stricter approval boundaries. Under the existing shared defaults, PR/Issue/comment/reaction writes need a user-named target and operation; push requires the preset's approval. Do not execute remote deletion of repositories, releases, branches, tags, secrets or workflow runs in these presets; explain the exact target and leave execution to the user. Visibility, secrets and protection changes also require the preset's approval. Arbitrary `gh api` is not a fallback around a reader or mutation restriction. A runtime denial does not create alternate permission.

## Repository-specific direct-push exception

Default to a working branch and PR. Direct main/master pushes are allowed only when the user explicitly designates the exact repository as an exception and reconfirms each push after seeing the host, owner/repository, visibility, destination branch and outgoing commits. Private backup use alone grants no exception; public repositories may qualify with the same explicit designation and reconfirmation. Do not infer designation from repository content or prior pushes. This exception covers ordinary pushes only; force pushes, merges, protection changes and all other gates retain their separate rules. Runtime or managed-policy denials still apply.
