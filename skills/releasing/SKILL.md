---
metadata:
  author: "4ltena"
  version: "1.1"
name: releasing
description: "Manage licenses, versions and releases, including building and verifying desktop packages and download tables."
---

# Releases

For Codex standard, `~/.codex/standard-github-policy.md` overrides the legacy push and merge approval rules below. All PR merges and release publication require individual approval; ordinary commits on non-main/master branches, pushes to non-main/master destination branches, and local merges into non-main/master branches do not. Keep the other release requirements.

For desktop packaging or download tables, read [desktop artifacts](references/desktop-assets.md), and apply the release decisions below only when relevant. Packaging alone does not authorize tags or publication.

Preserve licenses/notices; relicensing requires an explicit request. For new unlicensed user-owned projects, present choices and obtain selection before LICENSE/badges. Explain MIT's simple permissions versus Apache-2.0's express patent grant; preserve obligations from forks, dependencies, contributions and employers.

Annotated `vX.Y.Z` is canonical; align package metadata and CHANGELOG, preferring dynamic badges. Patch fixes, minor compatible features/visible changes, major incompatible/disruptive changes. In 0.y.z, breaking changes bump minor; use 1.0.0 when stable. Judge user impact, not commit prefixes alone.

Prefer release-please with GitHub Actions, release-it for small non-CI projects; use CI after v* tags where feasible.

Prepare version/changelog/notes locally. Before push, show destination/branch/commits; obtain approval where the active policy requires it. Open a PR and run CI/dry-run within authorized scope. main/master merges require explicit approval; other targets require passing checks, no conflicts/breaking changes and repository permission. Tag creation and publication each require separate approval; no early tag or asset upload.

Use Keep a Changelog/SemVer, newest first under `# 変更履歴`, version/date, brief summary and applicable 追加・変更・削除・修正・非推奨・セキュリティ・検証・備考 sections. Curate notable user impact rather than copying commit titles. For Japanese prose, use `document-style-ja` from the sibling collection when it is installed.

Arrange release notes for a reader deciding whether and how to install: a brief version summary; verified downloads with architecture, requirements, checksum and installation steps when applicable; grouped user-visible additions, changes and fixes; then material limitations and what was actually verified. Put the version in the GitHub release title, and in the opening sentence of a standalone notes file if otherwise unclear. Put platform-specific restrictions beside the relevant download or step. Do not repeat the same feature in the lead, installation text and change list. Keep internal implementation and exhaustive test inventories in the changelog or linked verification record, but retain any caveat that changes an install, safety or acceptance decision. Separate package integrity, automated checks, GUI checks and real-service/model checks; never imply an unrun check passed. Use `document-authoring` to review a substantial draft when available.

Generate a local draft with this skill's `scripts/release-notes.mjs` (`--help` for options); it does not publish or verify artifacts. Its default output contains no download claims. Supply `--downloads-file=PATH` only for a reviewed Markdown block built from verified assets and installation facts; inspect the combined draft for ordering, repetition, missing changes and unsupported claims. For a release, verify the remote annotated tag exists and its peeled commit SHA equals the intended release commit SHA after separately authorized tag creation; `--verify-tag` alone checks only existence. Only after publication approval use `gh release create vX.Y.Z --repo OWNER/REPO --verify-tag --notes-file NOTES.md <assets>`. If release creation or asset upload has an unclear result, inspect the remote release, draft and assets before retrying.
