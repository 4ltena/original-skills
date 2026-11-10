# Original Skills

Personal Agent Skills and plugin sources for assignment preparation, document work and software development.

## Assignment preparation

[Homework Glowup](skills/homework-glowup) prepares and reviews assignment deliverables:

- Check answers against the questions, required formats, length limits and units; recalculate results and check executable code where applicable.
- Read the assignment's naming instructions and saved private filename rules for each task, then check final filenames and extensions. Keep personal identifiers in private rule storage and out of public skill sources.
- Apply white backgrounds, black text and gray table shading, with red accents when needed. Check numbered captions above tables and figures in long reports, centered over their items.
- Include AI-use disclosures and research links when required by the assignment or requested by the user. Describe actual AI use accurately when the assignment asks for it.
- Check human author and last-modifier metadata, excluding AI agent names. Align document and filesystem modification times; for a newly created assignment, set internal creation roughly 30 minutes earlier with a small deviation from an exact interval. Preserve existing creation timestamps on later edits.
- Record results, evidence, unverified items and reasons for non-applicable checks in the included [checklist](skills/homework-glowup/templates/assignment-checklist.md), kept separately from submission files.

Assignment preparation produces local deliverables. Upload or publication requires separate authorization.

## Document work

Choose the [document Skill](skills/document-skills/README.md) that matches the main task:

- [document-writing](skills/document-skills/skills/document-writing/SKILL.md): draft a new document from requirements and sources, including a README or guide.
- [document-rewriting](skills/document-skills/skills/document-rewriting/SKILL.md): revise the structure, explanation or length of an existing document, or summarize it while preserving required claims and evidence.
- [document-authoring](skills/document-skills/skills/document-authoring/SKILL.md): review an existing draft against the request and supplied sources, identifying issues in accuracy and reader usability.
- [document-sources](skills/document-skills/skills/document-sources/SKILL.md): research external sources and check that citations support the associated claims.
- [document-translation](skills/document-skills/skills/document-translation/SKILL.md): translate across languages or locales while checking meaning, omissions and protected syntax.
- [document-style-ja](skills/document-skills/skills/document-style-ja/SKILL.md): polish persistent Japanese prose after drafting or translation into Japanese, or perform a focused Japanese style edit.
- [document-files](skills/document-skills/skills/document-files/SKILL.md): extract, convert, generate or verify PDF/DOCX files using both source content and rendered output.

Combine Skills when a task has distinct requirements, such as translation and file conversion. The Japanese style companion applies to Japanese documents; generated documents otherwise follow the requested language. See the collection's [origins and rights](skills/document-skills/README.md#origins-and-rights) before redistribution.

## Development and supporting tools

- [Workflow](plugins/workflow/skills/workflow), also available as a [plugin](plugins/workflow): implement approved multi-stage changes or resume incomplete milestones with bounded review and verification.
- [Goal checkpoint](plugins/goal-checkpoint): reassess milestone evidence after three hours at the next supported host event. Automatic delivery depends on host setup; no background timer runs while idle.
- [Code inspection](skills/code-inspection): investigate code or review a diff for unnecessary complexity without changing project state.
- [Finite verification](skills/finite-verification): choose complementary checks, assess test adequacy and set a finite verification scope and stopping point.
- [Read evidence](skills/read-evidence): save and reuse non-secret read evidence with its provenance, freshness and history.
- [Project handoff](skills/project-handoff): resume from a project's current state or preserve a requested handoff after work.
- [Web source structure](skills/web-source-structure): organize HTML, styling and behavior using the maintained site's existing conventions.
- [Account catalog and broker](skills/site-account-catalog): look up or maintain account identities and entitlements, or request registered login actions through an isolated broker.
- [Evaluations](evaluations): assess skill selection and compare task results using recorded evidence. Offline grader checks and actual model runs are separate results.

## Set up an agent environment

Start with [environment/README.md](environment/README.md) to set up Codex or Claude Code. The [environment](environment) questionnaire selects the installation scope, Git mode, hooks and configuration changes. Setup supports CLI-free preparation and manual-git. Optional growth-loop auto-deletion is limited to newly created Skills with a valid ownership record.

After a reviewed placement, the installed read-only [doctor](environment/SETUP.md#5-inspect-a-placement-without-changing-it) reports receipt/source drift and configuration evidence. File placement, host registration/trust and live runtime behavior are checked separately.

## Component origins and licenses

The account catalog is imported from `4ltena/site-account-catalog` at `dce5d5ee24c5e902f700c02c9ecdce448154e2d1`. Credentials and personal records are excluded. Separate-account and macOS/Linux deployment verification remains pending; see its [runtime notes](skills/site-account-catalog/references/runtime.md).

License terms remain in each component.
