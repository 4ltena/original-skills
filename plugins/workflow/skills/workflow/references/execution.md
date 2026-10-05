# Execution details

## Delegation

Inspect actual starting changes and preserve existing edits. Give each worker the expected behavior, owned paths, dependencies, permitted side effects and acceptance checks. Shared generated files, indexes and plans count as shared writes. Isolate work only when it prevents a concrete conflict; retain recovery options until verification.

Collect actual changed paths, relevant starting/ending revisions, executed checks, unresolved concerns and remaining work. Review the integrated result rather than relying on a worker's summary.

## Debugging

Reproduce the symptom where possible, inspect the complete error and trace the affected state through callers. Test one plausible cause at a time; distinguish environment failures from product defects and state reproduction limits. Where a regression check is appropriate, confirm failure for the intended reason before relying on its later pass. Stop speculative patching when no new evidence supports it.

## Retry and recovery

An interrupted operation may have changed state. Inspect receipts, affected files or the remote destination before retrying a write. Investigate unchanged failures; retry only with new evidence or changed conditions. Preserve existing authorization and recovery requirements.
