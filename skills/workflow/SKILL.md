---
name: workflow
description: Coordinate approved multi-stage software changes or resume unfinished implementation.
metadata:
  author: 4ltena
  version: '1.3'
---

# Development workflow

Resume from current project state and approved decisions. For substantial work without an approved specification, use the available specification skill first; ordinary reversible edits need only focused checks.

Implement in dependency order and preserve existing work. Parallel bundles need non-overlapping owned paths, no shared command side effects, satisfied dependencies and bounded requirements/checks supplied to each isolated worker; otherwise run sequentially. The parent owns integration and milestone gates. Load a specialist skill only when its capability is needed.

Treat a push, progress or status request as its own short task: do it, report, and stop. Do not begin new implementation inside it unless asked. "After the current work" means finishing the work already in progress, not starting the next task.

Review the integrated change against requirements and likely regressions. Resolve supported blockers, run required focused checks, and report actual results and remaining work. Preserve valid earlier evidence; repeat checks only when a change or unresolved risk requires it.

Read the relevant section of [execution details](references/execution.md) when diagnosing an uncertain failure, preparing delegated work, handling large output or retrying an interrupted write. Persist a project handoff when continuity is needed; use available completion-report when delivering completed work. This workflow grants no additional permissions.
