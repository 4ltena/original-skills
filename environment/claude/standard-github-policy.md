# Claude host policy

Applies to Claude on this host using its actual permission mode and permission prompts. Classify each action by its actual target and effect, not its command name. When tiers overlap, the stricter tier wins.

## Run directly

Run read-only work the sandbox permits without requesting escalation: file reads and searches, builds and tests that write only inside workspace roots, Git reads through the pinned validator and GitHub reads through its validator. If the sandbox blocks one, diagnose the cause (path, ownership, network domain) before escalating; do not escalate reads by default.

## Ordinary task work

Use the active Claude permission mode. Follow any permission prompts; do not claim Codex automatic approval review is available. Within the requested task this covers staging and commits, local merges into non-main/master branches, ordinary pushes to non-main/master branches (including `backup/*`), PR and Issue creation or updates on the task's repository, network access or writes beyond the sandbox needed by the task, and any action not listed below. After a denial, take a safer alternative or report it; ask the user only when the action belongs to the next tier.

## User approval

Ask in plain text before acting, showing the exact target and effect (host, owner/repository, visibility, destination branch and outgoing commits for Git):

- Any push or merge to main/master, including a designated direct-push exception repository; reconfirm every push.
- Force pushes including `--force-with-lease`, tag pushes and rewriting published history.
- Release publication; repository visibility, secret, protection-rule and Actions settings changes.
- Global Git configuration and security or approval configuration (Claude config, rules, permission modes, approval rules in AGENTS.md).
- Local operations that lose uncommitted or unpushed work, such as `reset --hard`, `clean -fdx`, deleting branches with unmerged commits or dropping stashes.
- Messages or comments addressed to other people.

A request that already names the exact target and effect is the approval; do not ask twice. Never execute or submit remote deletion of repositories, releases, branches, tags, secrets or workflow runs; explain the target and leave it to the user. Runtime or managed-policy denials grant no fallback.
