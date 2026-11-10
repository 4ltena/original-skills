---
name: homework-glowup
description: Review and prepare assignment deliverables, checking content, submission filenames against assignment instructions and saved private rules, monochrome formatting and captions, required AI-use disclosures and references, author metadata, image properties and selected provenance metadata removal, and timestamps with an approximate initial-creation offset. Record results, evidence and unverified items in the included checklist. Use for assignment preparation and pre-submission review.
---

# Homework Glowup

Identify the assignment, questions and submission requirements, and the user's preferred name. Do not ask again for information already established in the conversation or document. Do not infer the user's name from OS accounts or Git configuration. If information is missing, continue independent work such as reviewing the content.

For each assignment creation, resumed preparation or review, copy [the check template](templates/assignment-checklist.md) to a working location outside the submission package. Record each applicable requirement and deliverable, its status and concise evidence. Use `Not applicable` only with a confirmed reason; missing information or an unperformed check is `Unverified`. Duplicate rows as needed for individual files and assignment-specific requirements. Mark the review complete only when all applicable checks are confirmed and every non-applicable item has a reason. Report failures and unconfirmed items while continuing independent work. A completed checklist records the evidence available; it does not itself prove correctness.

## Submission filenames and private user rules

- On every assignment creation or resumed preparation task, read the assignment's current filename instructions and the applicable saved user rules from disk before choosing, creating or renaming deliverable files.
- Use the user's explicitly designated rule file when provided. Otherwise use `$CODEX_HOME/assignment-preferences/filename-rules.md`, falling back to `~/.codex/assignment-preferences/filename-rules.md` when `CODEX_HOME` is unset. An absent file means no saved rules; it does not establish a default naming pattern. If a file cannot be read, report that limit and continue work supported by the available instructions.
- When the user supplies a filename rule, save it in that private location with its exact pattern, applicable course/assignment/file type, source and any explicit exception or replacement. Preserve unrelated rules and update superseded rules within their scope. Record only the identity fields needed to apply the rule. Treat a filename rule as standing only when the user explicitly provided it.
- Follow the assignment's required pattern, numbering, spelling and actual file format. Apply saved user preferences where compatible, or follow a clear user override for that assignment. Resolve a material unresolved conflict with the user while continuing independent work. Do not silently add personal prefixes, dates or review markers to a prescribed submission filename; keep working copies separately.
- Use confirmed, scope-appropriate identity values when a required pattern contains personal fields. Where neither the assignment nor the user specifies a personal prefix, use a descriptive filename without inventing one.
- Keep real names, student/course identifiers and personal filename prefixes out of public skill sources, examples, fixtures and distributable skill packages. Use generic placeholders there. Keep the private rule file outside public repositories and skill source/install trees, and never bundle its contents into generated deliverables or public reports.
- Recheck final basenames and extensions against the applicable instructions before delivery. Stored naming rules do not authorize upload or publication.

## AI-use disclosure and source links

- Do not add a personal AI-use disclosure or research-access date to an assignment deliverable unless the assignment or the user explicitly requires it. When revising an output, remove unsolicited optional AI-use disclosures added by an agent unless required or explicitly retained at the user’s request. Provide collected research-source links or a bibliography only when the assignment explicitly requires references or citations, or the user explicitly requests them. Continue verifying claims even when links are not included. These instructions govern assignment deliverables; higher-priority citation requirements for chat responses still apply.
- If an assignment asks how AI was used, describe the actual, supported use truthfully. State that AI was not used for the assignment's core work only when that is known to be true; if AI was used for core work, describe that use accurately. Give multiple specific examples of supplementary use when multiple such uses actually occurred. Do not invent uses, conceal known core use, or present uncertainty as non-use; if the facts are unclear, seek the needed information while continuing independent work.

## Visual formatting and captions

- Use pure white (`#FFF`) backgrounds and pure black (`#000`) text by default, with neutral gray for table shading and other neutral elements. Avoid chromatic colors; if an accent is needed, use only pure red (`#F00`). Red may identify filled-in answers in a table. Follow explicit assignment or user formatting requirements, and preserve source images when recoloring would alter required instructional content.
- For long reports, especially experiment reports, check that each applicable table and figure has a suitably numbered caption such as `Table x.x` or `Figure x.x`, placed above the corresponding item and centered. Follow the assignment's numbering and caption-language requirements when specified. Verify caption placement and alignment in the rendered document; do not impose an exhaustive caption audit on lightweight assignments.
- Align ordinary text and headings to the left by default. Follow explicit assignment or user requirements for other alignments.

## Review and correct content

- Check each question for a corresponding answer, omissions, unmet conditions, word or character limits, units, and required formats. If the questions are unavailable, distinguish what was reviewed from requirements that could not be checked.
- Independently recalculate results, checking values, signs, units, and rounding. Where code can be run, check representative inputs and boundary conditions. Verify facts, quotations, and references against relevant primary sources; do not invent unverified citations.
- Check inconsistencies between tables, figures, and text, cross-references, typos, and gaps in reasoning. Correct clear errors; for uncertain changes affecting conclusions or claims, provide the evidence and proposed correction. Do not fabricate experimental results or personal experiences.
- Preserve the user's approach, writing style, and required template; avoid unnecessary wholesale rewrites. Retain any course requirements for AI-use disclosure or citations.
- Use currently available format-specific skills when reading, editing, or rendering PDF/DOCX and similar files. Reviewing body text alone does not verify text within figures or equations.

## Author metadata

Set the document author to the name specified by the user. If the name is unknown, wait for clarification on that part while continuing other work.

Personal author, coauthor and last-modifier metadata must not contain AI agent or model names, such as Codex or Claude, including within mixed or multi-valued entries. Replace or remove AI-attributed content while preserving confirmed human author values. Preserve any required AI-use disclosures in the document body. After saving, reopen and verify the affected author, coauthor and last-modifier fields; if a tool cannot remove or verify them, report the limitation.

- For DOCX/XLSX/PPTX, target the core properties `creator` and `lastModifiedBy`. For PDF, keep the document information `Author` consistent with XMP `dc:creator` when present. Choose libraries that handle the relevant namespaces and multiple values.
- Distinguish application information such as `Creator` / `Producer` from personal author fields. Names in the body, comments, revision history and signatures are separate targets; do not remove or change them without a request. Preserve confirmed human coauthors while excluding AI agent names from author or coauthor attribution metadata. Editing signed files invalidates their signatures: explain the effect and, where possible, export from the original editable source.
- For HTML and similar formats, use existing author fields. Do not add custom fields or a name in the body to formats with no author metadata.
- Normally preserve the original and create an adjusted copy. Reopen the file after editing metadata to verify the saved values. Do not claim that hidden earlier PDF revisions have also been removed.

## Image metadata and watermark inspection

For image deliverables, read [the image workflow](references/image-metadata.md). Inspect the actual format, dimensions, bit depth, color/transparency properties, and available metadata. Distinguish ordinary attribution fields, C2PA/Content Credentials, visible marks and pixel-domain invisible watermarks. Agent names alone and image statistics do not establish who created an image or whether it has a watermark.

When the user requests removal, remove only identified, selected metadata on a separate copy, preserving confirmed human attribution and required disclosures. The included [helper](scripts/image_metadata.py) inspects raster files with Pillow and can remove PNG `caBX` provenance or exact text-key entries without re-encoding image data. Removing a C2PA manifest also removes its embedded signature and history from that copy; explain that effect. The helper does not validate signatures, edit non-PNG metadata, or remove pixel-domain watermarks.

Reopen the saved copy and compare decoded pixels, retained chunks, color profile, orientation, transparency and dimensions. Inspect the original and output visually. Record original/output hashes, selected removals, actual checks and remaining limits in the checklist. Treat missing metadata as a limited observation, not evidence of human authorship or absence of invisible watermarks. Do not substitute lossy recompression, screenshots, blur, cropping or generative repainting for a metadata operation.

## Document timestamps

At final processing, set the document's internal last-modified timestamp to the final save time and align it with the output file's filesystem modification time, to the precision supported by the format. Capture one actual current instant for both values; after the final metadata save, align the filesystem modification time if needed and read both values back. Use the user's timezone for reporting and the representation required by each file format.

Only when an assignment document is first created, set its internal creation timestamp to approximately 30 minutes before that final modification instant, with a small deviation from an exact 30-minute interval. Preserve the existing document creation timestamp on later reviews or edits, including when making an adjusted copy; creating a copy does not make the assignment a new document. If the document is known to be pre-existing but its creation timestamp is missing, do not invent one. If initial creation cannot be determined, preserve the available value and report the uncertainty. The approximate offset is a metadata convention, not evidence of actual work history.

Determine this approximate value within the document-writing operation in use, accounting for date rollover and timezone offsets.

Distinguish document-internal creation/modification timestamps from filesystem creation/modification timestamps. Do not change filesystem creation time unless the user specifically requests it; do not confuse status-change time, `ctime`, with creation time. Do not add custom timestamp fields to formats that lack them. If a field cannot be updated, preserved or verified, report the limitation rather than claiming success.

## Final verification and report

Reopen the adjusted file and verify its content, saved author, coauthor and last-modifier fields, including the absence of AI agent names. Compare each timestamp attribute read back from the file with its intended value and check the internal and filesystem modification times agree at supported precision. For DOCX/PDF and similar formats, also inspect rendering according to the format-specific skill, checking whether metadata edits affected pages, equations, figures, or tables.

Briefly report the output file, corrected errors, remaining unchecked items, author, and timestamp attributes actually changed or preserved. For images, name the metadata actually removed and the image-preservation evidence, without claiming unknown watermarks were removed. Identify any initial-creation offset as a metadata convention rather than a measured work history. This skill alone does not submit or publish assignments.
