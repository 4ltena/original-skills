@~/.codex/AGENTS.md
@~/.codex/local-policy.md

# Claude Code-specific instructions

Imported `AGENTS.md` is canonical for rules shared between Claude Code and Codex; don't duplicate them here. Where it names Codex settings (`approval_policy`, sandbox, automatic review), apply the same three tiers through Claude Code permissions: sandbox-safe reads run directly, ordinary task work follows the active permission mode, and the operations listed under "User approval" in `~/.codex/standard-github-policy.md` need the user's confirmation.

## Enforcement

- `~/.claude/settings.json` `permissions.ask`/`deny` additionally enforce the Git rules in `AGENTS.md`. Treat a permission or hook block as prohibited; never bypass, rewrite or disable the mechanism.
- Don't modify `~/.claude/settings.json`, hooks or their scripts unless the user explicitly requests and approves the exact change.
- Follow Claude Code permission prompts even when imported instructions would otherwise permit the action.
