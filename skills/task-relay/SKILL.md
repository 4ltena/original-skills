---
metadata:
  author: "4ltena"
  version: "1.1"
name: task-relay
description: "Execute a long approved numbered plan across fresh contexts when saved context outweighs rediscovery cost."
---

# Long-plan relay

Use for long/multiday work, degraded context or resuming an ordered plan, only when the next task is reconstructible from durable notes and a fresh context saves more than rereading costs. Keep short/tightly coupled work in context; a checklist alone is not a trigger.

The plan at `.project-notes/plans/YYYY-MM-DD-*.md` must contain:

```markdown
## Tasks
- [ ] P0 / Task1: title
- [x] P1 / Task2: title

## Handoff notes
- Durable facts needed downstream.
```

Task/P prefixes are equivalent. Normalize missing blocks once from task headings. The first unchecked item is next; all checked means complete.

For each task, in the target repository:
1. Read the plan/notes, assigned section and affected files needed for that task.
2. Execute and verify the task against its acceptance checks or actual behavior.
3. Check its box only after success; append durable facts needed downstream, not a transcript. Leave a blocked task unchecked with its reason and next action.
4. Commit only if the executor is authorized, following `git-operations`; no empty commits. Otherwise retain verified uncommitted paths. Push/PR/merge belong to explicitly approved integration.

At a task boundary, use a fresh context only when it saves more than reconstructing the plan and current state. Otherwise continue the approved plan in the current context; a completed checkbox alone is not a reason to stop the user's work. Do not create user-owned conversations without explicit request. Keep one writer for a shared tree and wait for an executor's result before the next writes there. When all boxes are checked, use available `project-handoff` for persistence and available `completion-report` for reporting; integration still requires approval.
