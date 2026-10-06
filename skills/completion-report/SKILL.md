---
metadata:
  author: "4ltena"
  version: "1.1"
name: completion-report
description: "Report completion and persist verified project handoffs after checks, on exit or when handoff is requested."
---

# Completion report

For repository completion, exit or a requested handoff, first follow [project handoff](references/handoff.md). Skip persistence for user configuration, disposable work or no project state; state why. A handoff-only request needs only changed paths and unknowns.

Then report in concise Japanese, leading with the outcome. Include changed paths, relevant verification commands and actual results, and material failures or unverified behavior. Use a short paragraph for small changes; use a list or table only when it helps compare several changes. Omit empty risk sections and repeated conclusions.

Check the requested outcome against acceptance criteria before declaring completion. Distinguish installed file changes from behavior observed in a running or new session. Do not repeat successful checks just to populate the report; report remaining work as incomplete when acceptance criteria are unmet.

Add only applicable launch instructions or a concrete required next action. Propose a commit only when requested or naturally next, after consulting `git-operations`. Include SemVer only for release/version work or when asked. Invent no follow-up work.
