# Claude / Codex Skill entrypoints

This inventory covers all 46 unique source Skill names. System Skills and plugin caches
are outside this repository. Installation does not prove live tool/hook availability.

Read the installed host-policy.md and binding.json. Use the current host catalog to
invoke a Skill by name, or open its installed SKILL.md in the conversation when no
slash-command UI exists. Portable Skills use their existing procedures and available
file/terminal/browser tools; neither Claude Code CLI nor Codex CLI is mandatory.
Missing external tools/data remain prerequisites to that operation, not successful execution.

Adapted Git/release Skills use the active host policy and its fixed reader bindings.
Claude has no Codex auto_review; its own permission mode and prompts apply. A manual-git
profile requires the user to explicitly request writes. The installed copies retain
existing safety gates. Without terminal tools, request the bounded validator evidence
from the operator and review it in the conversation; do not silently run direct reads.

Watchdog manual mode evaluates explicit failure evidence with scripts/recovery.py,
then the recovery owner resumes only missing work and records attempts. It does not
claim CLI process supervision. goal-checkpoint uses host_adapter.py --host claude and
an explicit objective/plan; without hooks, use explicit manual review rather than
claiming scheduled delivery. Growth-loop uses RUNTIME.md and the installed gl-run
binding for every script, never shebang/PATH guesses. Catalog uses explicit --catalog
and --client paths; unavailable broker actions are reported, never fabricated.

| Skill | Classification | Claude entrypoint |
| --- | --- | --- |
| agent-watchdog | manual-equivalent | scripts/recovery.py: explicit failure evidence -> bounded continuation decision |
| agentic-development-audit | portable | conversation Skill: agentic-development-audit; bundled references/scripts and available host tools |
| apple-design-principles | portable | conversation Skill: apple-design-principles; bundled references/scripts and available host tools |
| code-inspection | portable | conversation Skill: code-inspection; bundled references/scripts and available host tools |
| completion-report | portable | conversation Skill: completion-report; bundled references/scripts and available host tools |
| design-generation | portable | conversation Skill: design-generation; bundled references/scripts and available host tools |
| document-authoring | portable | conversation Skill: document-authoring; bundled references/scripts and available host tools |
| document-files | portable | conversation Skill: document-files; bundled references/scripts and available host tools |
| document-rewriting | portable | conversation Skill: document-rewriting; bundled references/scripts and available host tools |
| document-sources | portable | conversation Skill: document-sources; bundled references/scripts and available host tools |
| document-style-ja | portable | conversation Skill: document-style-ja; bundled references/scripts and available host tools |
| document-translation | portable | conversation Skill: document-translation; bundled references/scripts and available host tools |
| document-writing | portable | conversation Skill: document-writing; bundled references/scripts and available host tools |
| finish-line | portable | conversation Skill: finish-line; bundled references/scripts and available host tools |
| forget | adapted | verified Python + growth-loop/bin/gl-run; local binding, ownership helper for managed writes |
| frontend-design | portable | conversation Skill: frontend-design; bundled references/scripts and available host tools |
| frontend-optimize-apple | portable | conversation Skill: frontend-optimize-apple; bundled references/scripts and available host tools |
| frontend-optimize-linux | portable | conversation Skill: frontend-optimize-linux; bundled references/scripts and available host tools |
| frontend-optimize-webapp | portable | conversation Skill: frontend-optimize-webapp; bundled references/scripts and available host tools |
| frontend-optimize-windows | portable | conversation Skill: frontend-optimize-windows; bundled references/scripts and available host tools |
| gh-operations | adapted | Claude host policy + explicit GitHub request when manual-git; verified provider/CLI |
| gh-read-inspection | adapted | active Claude host-read-policy.md fixed GitHub validator; no CLI substitution |
| git-operations | adapted | Claude host policy + explicit Git request when manual-git; available Git tool |
| git-read-inspection | adapted | active Claude host-read-policy.md fixed Git validator; no CLI substitution |
| git-writing | portable | conversation Skill: git-writing; bundled references/scripts and available host tools |
| goal-checkpoint | adapted | host_adapter.py --host claude: explicit objective baseline and confirmed session |
| grilling | portable | conversation Skill: grilling; bundled references/scripts and available host tools |
| japanese-writing-refine | portable | conversation Skill: japanese-writing-refine; bundled references/scripts and available host tools |
| jot | adapted | verified Python + growth-loop/bin/gl-run; local binding, ownership helper for managed writes |
| journey | adapted | verified Python + growth-loop/bin/gl-run; local binding, ownership helper for managed writes |
| learn | adapted | verified Python + growth-loop/bin/gl-run; local binding, ownership helper for managed writes |
| mutation-check | portable | conversation Skill: mutation-check; bundled references/scripts and available host tools |
| plan-review-loop | portable | conversation Skill: plan-review-loop; bundled references/scripts and available host tools |
| profile | adapted | verified Python + growth-loop/bin/gl-run; local binding, ownership helper for managed writes |
| project-handoff | portable | conversation Skill: project-handoff; bundled references/scripts and available host tools |
| read-evidence | portable | conversation Skill: read-evidence; bundled references/scripts and available host tools |
| recall | adapted | verified Python + growth-loop/bin/gl-run; local binding, ownership helper for managed writes |
| refine | adapted | verified Python + growth-loop/bin/gl-run; local binding, ownership helper for managed writes |
| releasing | adapted | Claude host policy + portable packaging commands; explicit release approval |
| site-account-catalog | adapted | accountctl.py --catalog <explicit root>: find/identity/license; registered broker only |
| smallest-change | portable | conversation Skill: smallest-change; bundled references/scripts and available host tools |
| spec-first-development | portable | conversation Skill: spec-first-development; bundled references/scripts and available host tools |
| task-relay | portable | conversation Skill: task-relay; bundled references/scripts and available host tools |
| ux-spike | portable | conversation Skill: ux-spike; bundled references/scripts and available host tools |
| web-source-structure | portable | conversation Skill: web-source-structure; bundled references/scripts and available host tools |
| workflow | portable | conversation Skill: workflow; bundled references/scripts and available host tools |
