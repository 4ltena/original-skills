# document-skills

Agent Skills for drafting, revising, reviewing and translating reader-facing documents, checking their sources, and verifying PDF/DOCX artifacts. Choose the Skill for the main task. Use a matching target-language style Skill after drafting or translation; combine other Skills only when the document has another distinct completion condition. Skill instructions are in English, while generated documents follow the user's requested language.

| Skill | Use |
| --- | --- |
| [`document-writing`](skills/document-writing/SKILL.md) | Draft a new document; load repository guidance only for README/docs. |
| [`document-style-ja`](skills/document-style-ja/SKILL.md) | Polish persistent Japanese prose after `document-writing` or Japanese-target `document-translation`, or perform a requested focused style pass. Check [lexical cues](skills/document-style-ja/references/lexical-cues.md) after syntax and flow. |
| [`document-rewriting`](skills/document-rewriting/SKILL.md) | Substantively revise or explicitly summarize an existing document, checking claims against the original. |
| [`document-authoring`](skills/document-authoring/SKILL.md) | Review a draft against its request and supplied sources without rewriting it. |
| [`document-sources`](skills/document-sources/SKILL.md) | Research external sources and verify that citations support claims. |
| [`document-translation`](skills/document-translation/SKILL.md) | Translate for another language or locale while checking meaning and protected syntax. |
| [`document-files`](skills/document-files/SKILL.md) | Extract, convert, generate or verify PDF/DOCX and inspect rendered output. |

Use the Japanese companion after drafting or translating a persistent document into Japanese, not for an English target, a short conversation or an unchanged quotation. Its lexical cues are context checks, not forbidden words or automatic substitutions. Substantive changes belong in `document-rewriting`; review-only requests belong in `document-authoring`. Literary polishing is outside this collection.

Place each `skills/<name>/` directory in a client that supports Agent Skills. Replacing the currently installed Codex Skills is a separate task after other work stops.

## Origins and rights

| Material | Origin | Current notice |
| --- | --- | --- |
| `document-writing/SKILL.md` | Revised from a Polaris Skill. | [Polaris MIT](skills/document-writing/LICENSE). |
| Japanese technical-prose guidance in `document-style-ja/SKILL.md` | Reworked from k16shikano's guidance; see [third-party notice](THIRD_PARTY_NOTICES.md). | Original guidance: Unlicense. This does not set a license for the whole Skill. |
| `document-writing/references/repository-docs.md` | Reorganized from a previously used Codex documentation Skill. | Repository-wide license not set. |
| `document-authoring` | Reorganized from a previously used Codex `docs-authoring` Skill. | Repository-wide license not set. |
| `document-style-ja` and its lexical reference | Revised from a previously used `writing-style-ja` Skill and new research. | Repository-wide license not set, subject to the source notice above. |
| `document-rewriting`, `document-sources`, `document-translation`, `document-files` | Created for this collection. | Repository-wide license not set. |

No repository-wide license has been chosen. Decide rights for the unlicensed material before external publication or distribution. GitHub, note, Qiita and research reports informed the problem analysis; this collection does not reproduce third-party Skill text or code.
