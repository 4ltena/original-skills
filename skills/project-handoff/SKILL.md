---
name: project-handoff
description: Resume project work from existing state or persist a requested handoff after meaningful project work.
metadata:
  author: 4ltena
  version: '1.1'
---

# Project handoff

Use the project's existing current-state or handoff document; read only links needed for the current task. Do not repeat repository discovery when recorded state remains valid.

Read the state document once per session and again only after context compaction or an external change to it. Read its top section first; reach older sections, archives and links by targeted search only when the current task needs them. Give delegated workers the relevant facts in their task contract instead of the state document.

When updating a handoff, record the active deliverable, verified results, blockers and exact next task. Link existing specifications and plans instead of copying them. Preserve the project's document layout and task checkboxes; create a state document only when no canonical equivalent exists.

Keep the state document a current snapshot, not a log. Overwrite its fixed sections (current state, active deliverable and next task, blockers and decisions, latest verification, links) instead of adding dated progress entries. Keep it within about 150 lines or 12 KB. Before writing, if it exceeds that budget or holds several dated progress entries, summarize it: keep only facts that still affect upcoming work, move superseded history unchanged to an `archive/` file beside it named by date, and link the archive once. Archives are not read by default.

Update the handoff when a user turn's work completes, on request, or before exit or expected compaction; not after each worker result, commit or intermediate check. Persist project facts, not conversation transcripts or secrets. Mark unrun checks and unknown runtime behavior explicitly. Skip persistence for disposable work or configuration changes with no ongoing project state. Updating the handoff does not recursively trigger another handoff, commit, publication or Japanese style pass.
