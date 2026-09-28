# git-skills

Five locally maintained Git and GitHub Agent Skills, extracted from the sibling [original-skills collection](../original-skills/README.md). This is the source collection. The currently installed Codex and shared Claude references still use the previous combined Skill until a separate, reviewed migration.

| Skill | Use it for |
| --- | --- |
| [`git-operations`](skills/git-operations/SKILL.md) | Scope, perform and verify a requested local Git write or push; preserve existing work and recovery options |
| [`gh-operations`](skills/gh-operations/SKILL.md) | Scope and verify requested GitHub-side writes, including PRs, issues, reviews, Actions and API mutations |
| [`git-writing`](skills/git-writing/SKILL.md) | Draft commit messages, PR/Issue descriptions and review comments from the actual change |
| [`git-read-inspection`](skills/git-read-inspection/SKILL.md) | Bounded read-only Git inspection through the local pinned validator |
| [`gh-read-inspection`](skills/gh-read-inspection/SKILL.md) | GitHub reads through direct read-only `gh` in Codex standard or the local pinned validator elsewhere |

`git-operations` keeps local Git decisions in its entrypoint. Read its [local boundaries](skills/git-operations/references/codex-local-boundaries.md) only in this user's Codex/shared preset environment, its [recovery guide](skills/git-operations/references/recovery-and-worktrees.md) for rollback or worktree tasks, and its [evidence map](skills/git-operations/references/agent-failure-modes.md) when auditing the rules. `gh-operations` has separate [GitHub local boundaries](skills/gh-operations/references/codex-local-boundaries.md). A PR creation that pushes uses both operation Skills; release publication also uses `releasing`. A Skill never grants Git or remote permissions. The active host policy and repository rules remain authoritative.

The read validators and their tests are preserved from `original-skills`. They contain local absolute Codex paths and pinned Git/gh binaries or versions; copying this collection to another machine without adapting and validating those paths does not make them usable there. The collection is therefore not fully portable. This source update does not commit, install or publish these Skills.

No collection-wide license is asserted for the extracted locally maintained Skills. The MIT license of the two Polaris-derived Skills in `original-skills` does not cover this collection. Check provenance, notices and permissions before any public release.
