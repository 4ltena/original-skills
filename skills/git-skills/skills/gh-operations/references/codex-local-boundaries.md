# Local Codex and shared-preset GitHub boundaries

Read this only in the user's Codex or shared preset environment. Check the current `/home/altena/.codex/AGENTS.md`, `/home/altena/.agents/common.md` if applicable, and effective runtime permissions. Newer user instructions and active policy take precedence. Do not treat Claude-only grants as Codex grants or change Claude configuration.

## Codex standard

Read `/home/altena/.codex/standard-github-policy.md` before GitHub operations. It is the authority for Codex standard and overrides older shared/Skill approval defaults. Within a requested task, ordinary PR and Issue creation/updates do not need another user confirmation. Other-person comments or messages need a named target and operation. Every PR merge, main/master write, remote deletion, release publication, visibility, secret and protection-rule change needs the policy's individual approval unless the exact target and effect were already approved. A user request that explicitly names the required target and effect can satisfy that approval; do not ask for it twice. This Skill does not add a gate or bypass one. Assess `gh api` by endpoint and body, including GraphQL mutations; runtime auto-review is separate from user approval.

Resolve the actual host/repository and PR or Issue number before acting. For PR creation with a push, use `git-operations` to inspect the remote, destination ref and outgoing commits. `gh pr create --dry-run` is not proof that no remote write occurs. Verify the resulting PR, Issue, review, Actions run or setting in GitHub. Do not retry an ambiguous response before checking for a partial effect.

## Other presets

Apply their own, potentially stricter approval boundaries. Under the existing shared defaults, PR/Issue/comment/reaction writes need a user-named target and operation; push requires the preset's approval. Do not execute remote deletion of repositories, releases, branches, tags, secrets or workflow runs in these presets; explain the exact target and leave execution to the user. Visibility, secrets and protection changes also require the preset's approval. Arbitrary `gh api` is not a fallback around a reader or mutation restriction. A runtime denial does not create alternate permission.
