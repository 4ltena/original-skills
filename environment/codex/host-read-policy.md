# Host read policy

Read this before Git or GitHub CLI inspection. Use the applicable fixed validator as a standalone command; no shell redirection, substitution, environment assignment, injected configuration, mixed mutations or alternate dispatch. Its accepted argument grammar defines the read boundary. Set the tool's working directory instead of injecting Git global options.

Replace `<python>` with the absolute path of the Python 3.10+ interpreter and `<skills-dir>` with the absolute path of the Codex skills directory (default `~/.agents/skills`), then delete the section that does not apply.

## Windows

- Git: `<python> -I <skills-dir>/git-read-inspection/scripts/git-read-windows.py <arguments>` (binds Git at its default install path).
- GitHub CLI: `<python> -I <skills-dir>/gh-read-inspection/scripts/gh-read-windows.py <arguments>` (binds GitHub CLI at its default install path).

## macOS and Linux

No validator ships for these platforms. Until one is installed, use direct read-only `git` commands (`status`, `log`, `diff`, `show`, `rev-parse`, `ls-files`, `branch --list`, `remote -v`) and read-only `gh` queries (`repo view`, `pr view/list/diff/checks`, `issue view/list`, `run view/list`) with no `-c` configuration, pager, external diff, output file or mutation.

## Boundaries

Git reads disable pagers, external diff/textconv, fsmonitor, optional locks, caller config injection and output files. GitHub reads permit only bounded repo/pr/issue/run/workflow/release/search queries and deny browser/watch/editor, output files, generic API and mutations. Do not treat fetch/pull, auth changes, downloads, checkout, builds, tests or subprocess execution as this read path.

Exclude .env, authentication key files including *.pub, credentials, tokens, keychains, SSH/GnuPG and cloud-auth paths before reading or searching; resolve explicit symlinks and reject traversal or wrapper bypasses. A missing applicable validator blocks the affected command; do not guess a replacement or broaden permissions.
