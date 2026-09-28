# Execution details

Read this reference when implementation, debugging or coordinated review needs more detail than the main Skill.

## Workspace and tasks

Inspect the actual starting changes with the runtime's authorized reader. Preserve work already in progress. Give each task an expected result, affected paths, dependencies and relevant checks; assign distinct ownership when work is delegated. Shared generated files, indexes and plans are shared writes even if source paths differ. Use isolation when it prevents a concrete conflict, and keep the original worktree available until the result is verified.

Use existing code and conventions before adding a dependency or abstraction. Keep a change small without cutting required validation, recovery, security or accessibility. Record the actual changed paths and outcomes, not only an executor's summary.

## Debugging and checks

Reproduce the symptom where possible. Read the complete error and trace the affected state or value through its callers. Test one plausible cause with a focused experiment; if reproduction is unavailable, name the limit. Add a regression check when it can expose the original failure, and observe that it fails for the intended reason before treating its later pass as evidence. Follow required project checks. Investigate an unchanged failure before retrying; inspect side effects before repeating a write.

## Review, recovery and handoff

Review the final change against the current specification, then check correctness, regressions and coverage. Support actionable findings with a path or condition and impact. Resolve confirmed blockers and recheck the affected behavior. If an independent review is required but unavailable, report that status instead of calling a self-check independent.

An interrupted or uncertain operation may have changed state. Inspect its receipt, files or remote destination before retrying. After an upstream change, revisit only the downstream tasks and evidence it affects. At integration, reconcile the final diff, acceptance criteria and check results. Update the existing project handoff with durable facts, blockers and the next task. Report incomplete work as incomplete; commit and publication follow the project's existing authorization rules.
