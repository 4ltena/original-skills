---
name: git-writing
description: Draft clear commit messages, pull request descriptions, and review comments for a known change; not for Git mutations or read-only repository inspection.
---

# Git writing

Write from the actual diff, request, checks, and repository conventions. Follow the repository's `CONTRIBUTING.md`, commit history, templates, DCO, and signing requirements when present. If no convention exists, use `type(scope): description` or `type: description` with a concise English active-verb subject. Choose the type by the resulting change: `feat` adds behavior, `fix` repairs behavior, `docs` changes documentation, `test` changes tests, `refactor` changes code without a feature or bug fix, and `perf` improves measured performance. Use `style` only when the repository defines it for source formatting or other non-behavioral code style; a visible UI appearance change is not `style` merely because it concerns visual design. Other types such as `build`, `ci`, or `chore` depend on the repository's convention. Name the affected component in the optional scope, rather than forcing a platform or folder name.

For example, a new adjustable macOS pane could be `feat(macos): add adjustable workspace panes`; repairing a misplaced pane could be `fix(macos): preserve workspace pane positions`; formatting-only Swift changes could be `style(macos): format Swift source` *if that repository uses `style`*. Avoid vague subjects such as `update UI` or `improve code`; say what changed. Use a blank-line-separated body when the reason, prior behavior, migration, or limitation would otherwise be unclear. A body may be English or Japanese. If the repository uses Conventional Commits, indicate an incompatible change with its supported `!` or `BREAKING CHANGE:` form and explain the migration. Keep each message understandable without the conversation; links supplement context.

For a commit, describe its own meaningful change, not every trial or repair step. Do not invent an author, email, co-author, or certification. Add AI co-authorship only if the user explicitly requests it and the repository permits it; add `Signed-off-by` only when the required certification can be made truthfully. Git identity configuration and staging belong to `git-operations`.

For a PR, Issue or change report, lead with the purpose and resulting behavior. Group distinct user-visible changes into short bullets, then include relevant implementation detail, limitations, and checks actually run. State failed or unrun checks accurately; do not promote a build or automated test to an unperformed end-to-end check. Match the final diff and repository template; omit empty sections, repeated facts, and a work diary. For a release note, use `releasing` instead of copying commit titles or the entire PR inventory.

For review comments, name the triggering condition, consequence, and requested outcome. Separate required fixes, optional suggestions, questions, observations, and uncertainty. Reply to feedback with what changed and how it was checked. Scale detail to the change. For persistent Japanese prose, use `document-style-ja` when available.

Drafting a message does not authorize posting, staging, committing, pushing, or merging. Use the active Git/GitHub policy and `git-operations` for local Git writes or pushes, and `gh-operations` for GitHub-side posting or other remote mutations.
