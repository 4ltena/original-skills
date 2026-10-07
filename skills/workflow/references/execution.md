# Execution details

## Delegation

Inspect actual starting changes and preserve existing edits. Give each worker the expected behavior, owned paths, dependencies, permitted side effects and acceptance checks. Shared generated files, indexes and plans count as shared writes. Isolate work only when it prevents a concrete conflict; retain recovery options until verification.

Hand each worker a bounded task contract with the facts it needs; do not make it read the project's state document or reload skills it does not use. Workers do not spawn further workers unless the parent assigns it. Wait for completion notifications instead of polling status repeatedly. Where the runtime selects effort per agent, keep the user's assignment for each task class and use lower effort for orchestration, status, push and scheduled check turns.

Collect actual changed paths, relevant starting/ending revisions, executed checks, unresolved concerns and remaining work. Review the integrated result rather than relying on a worker's summary.

## Context budget

Every token loaded is re-read on each later step and brings compaction closer. Request about 4,000 output tokens or fewer per command. Write large logs, traces, disassembly and generated data to files, then read targeted ranges or matches. Do not print a whole file over a few hundred lines; search it. Pass summaries and file paths between agents instead of raw output.

## Debugging

Reproduce the symptom where possible, inspect the complete error and trace the affected state through callers. Test one plausible cause at a time; distinguish environment failures from product defects and state reproduction limits. Where a regression check is appropriate, confirm failure for the intended reason before relying on its later pass. Stop speculative patching when no new evidence supports it.

## Retry and recovery

An interrupted operation may have changed state. Inspect receipts, affected files or the remote destination before retrying a write. Investigate unchanged failures; retry only with new evidence or changed conditions. Preserve existing authorization and recovery requirements.
