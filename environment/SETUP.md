# Environment setup procedure

Instructions for a Codex or Claude Code agent rebuilding this environment on a new machine. Work through the steps in order. Before writing configuration, settings, global Git config or an existing instruction file, show the user the exact diff and obtain approval; back up any file you replace. Never copy credentials.

## 0. Check requirements

| Tool | Version | Needed for |
| --- | --- | --- |
| Codex CLI | 0.157 or newer (permission profiles are beta) | Codex setup |
| Claude Code | current | Claude Code setup |
| Python | 3.10 or newer | validators, `apply_config.py`, plugin hooks |
| Git | 2.54 or newer; on Windows at the default install path | Git read validator |
| GitHub CLI | 2.93 or newer; on Windows at the default install path | GitHub read validator |
| Bash with `jq` or `python3` | any | Claude Code push-guard hook (on Windows, Git Bash) |

Report missing tools to the user before continuing; do not install them without approval.

## 1. Resolve inputs

Determine and confirm with the user:

| Input | Default |
| --- | --- |
| Agents to configure | Codex and Claude Code |
| `CODEX_HOME` | `~/.codex` |
| Codex skills directory | `~/.agents/skills` |
| Claude Code skills directory | `~/.claude/skills` |
| Python 3.10+ interpreter (absolute path) | from `python --version` / `where python` |
| Workspace root holding repositories | ask |
| Reply language | ask |
| Repositories allowed direct main/master pushes | none |

## 2. Install skills

Every directory under `skills/` that contains `SKILL.md`, including nested `skills/*/skills/*`, is one skill. Copy each into the skills directory of every configured agent under its own name. Skip:

- `h5i-*` (retired Linux tooling) and `site-account-catalog`, unless the user asks for them;
- `skills/growth-loop`, which is a Claude Code plugin installed in step 6;
- for Codex only, `skills/workflow`, `skills/design-generation`, `skills/plan-review-loop` and `skills/ux-spike`, because the workflow plugin (step 3) ships the same skills. Claude Code does not load Codex plugins, so install them as skills there; also copy `frontend-design` and `grilling` from `plugins/workflow/skills/` for Claude Code.

Validate each installed skill with the `quick_validate.py` of the available skill-creator skill (on Windows set `PYTHONUTF8=1`).

## 3. Install Codex plugins

Copy this repository's `plugins/workflow` and `plugins/goal-checkpoint` to `~/.codex/plugins/`. Create `~/.agents/plugins/marketplace.json` from `codex/marketplace.example.json` (paths are relative to the home directory), or add its entries to an existing `personal` marketplace. Then run `codex plugin add workflow@personal` and `codex plugin add goal-checkpoint@personal`, and ask the user to trust the goal-checkpoint hooks through `/hooks` in Codex. Refresh later by updating `~/.codex/plugins/<name>` and re-running `codex plugin add`, never by editing the plugin cache.

## 4. Place Codex instruction files

Copy into `CODEX_HOME`:

- `codex/AGENTS.md` → `AGENTS.md`
- `codex/standard-github-policy.md` → `standard-github-policy.md`
- `codex/host-read-policy.md` → `host-read-policy.md`; fill `<python>` and `<skills-dir>`, keep only the section for this OS.
- `codex/local-policy.example.md` → `local-policy.md`; fill the language and exception list.

`provider-policy.md` belongs to provider plugins; leave any existing one in place. Without it, provider integrations stay blocked as `AGENTS.md` requires.

## 5. Merge Codex configuration

Merge `codex/config.standard.toml` into `CODEX_HOME/config.toml` with `python codex/apply_config.py --workspace-root <workspace-root>` (repeat the option for several roots). On Windows each root must be a directory the user's account owns: the sandbox sets ACLs on it, and a root owned by another or stale account fails with `SetNamedSecurityInfoW failed: 5` in `CODEX_HOME/.sandbox/*.log`. It prints a diff without writing; show it to the user, then re-run with `--apply` (the old file is kept as `config.toml.bak-<timestamp>`). The script sets the template's keys, keeps unrelated settings and entries the user added, removes `sandbox_mode` and `[sandbox_workspace_write]`, and skips `[windows]` on other platforms. Add package domains the user's toolchains need to the template first.

On Windows, the elevated sandbox runs commands as a separate user, so Git refuses repositories owned by the real user ("dubious ownership") and every Git read escalates. With approval, run `git config --global --add safe.directory "<workspace-root>/*"` (forward slashes).

## 6. Configure Claude Code

- Copy `claude/CLAUDE.md` to `~/.claude/CLAUDE.md`, or prepend its two import lines to an existing file.
- Copy `claude/hooks/git-push-guard.sh` to `~/.claude/hooks/` and make it executable (`chmod +x`). It asks before force pushes and pushes to main/master and denies remote deletion, as a second layer behind the permission rules.
- Merge `claude/settings.template.json` into `~/.claude/settings.json`, keeping existing entries: `permissions.ask`/`deny`, the `PreToolUse` hook, `extraKnownMarketplaces` and `enabledPlugins`. Confirm the plugin list with the user; the LSP plugins only help when their language servers are installed. Model and effort settings stay the user's choice.
- Install growth-loop from this repository: in Claude Code run `/plugin marketplace add <repository>/skills/growth-loop`, then `/plugin install growth-loop@growth-loop-local`.

## 7. Verify

Report each result; mark anything not run as unverified.

1. In a repository under the workspace root: `codex sandbox git status --short` succeeds without an ownership error.
2. `codex sandbox <python> -c "print(1)"` succeeds.
3. A new Codex session answers, from its loaded instructions, which operations need user approval; the answer matches the "User approval" list in `standard-github-policy.md`.
4. A new Claude Code session shows the imported `AGENTS.md` in `/memory`, `git push --force` triggers a permission prompt, and `/plugin` lists the enabled plugins.
5. `codex plugin list` shows `workflow` and `goal-checkpoint` from `personal`.
