# Agent environment

Shared global instructions and permission settings for Codex and Claude Code, with no machine-specific paths. To rebuild on another machine, open this repository in Codex or Claude Code and ask it to follow [SETUP.md](SETUP.md).

## Permission model

| Tier | What | How |
| --- | --- | --- |
| Run directly | Reads, builds and tests the sandbox permits | Sandbox profile `standard`; no escalation |
| Automatic review | Ordinary task work: commits, pushes to working branches, PRs and Issues, anything unclassified | Escalation reviewed by `auto_review`; the user is not asked |
| User approval | main/master pushes and merges, force pushes, releases, visibility/secret/protection settings, global or security configuration, work-losing local operations, messages to others | The agent asks first; Claude Code `ask` rules enforce the Git subset |
| Never | Remote deletion of repositories, releases, branches, tags, secrets, workflow runs | Left to the user; Claude Code `deny` rules |

## Layout

| Path | Installed as |
| --- | --- |
| [codex/AGENTS.md](codex/AGENTS.md) | `~/.codex/AGENTS.md`, shared by Codex and Claude Code |
| [codex/standard-github-policy.md](codex/standard-github-policy.md) | `~/.codex/standard-github-policy.md`, the tier definitions |
| [codex/host-read-policy.md](codex/host-read-policy.md) | `~/.codex/host-read-policy.md`, Git/GitHub read validators per OS (template) |
| [codex/local-policy.example.md](codex/local-policy.example.md) | `~/.codex/local-policy.md`, language and personal exceptions (template) |
| [codex/marketplace.example.json](codex/marketplace.example.json) | `~/.agents/plugins/marketplace.json` (Codex plugin registry) |
| [codex/config.standard.toml](codex/config.standard.toml) | merged into `~/.codex/config.toml` by [codex/apply_config.py](codex/apply_config.py) |
| [claude/CLAUDE.md](claude/CLAUDE.md) | `~/.claude/CLAUDE.md` |
| [claude/settings.template.json](claude/settings.template.json) | merged into `~/.claude/settings.json` (permissions, hook, plugins) |
| [claude/hooks/git-push-guard.sh](claude/hooks/git-push-guard.sh) | `~/.claude/hooks/git-push-guard.sh` |

Skills come from [../skills](../skills) and plugins from [../plugins](../plugins); SETUP.md installs both.
