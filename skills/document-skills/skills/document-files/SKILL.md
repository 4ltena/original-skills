---
name: document-files
description: Extract, convert, generate or verify PDF and DOCX documents with evidence from both source and rendered artifacts. Use when file-format behavior is central, not for ordinary prose review.
---

# Work with PDF and DOCX files

Use when extraction, conversion, generation or rendered verification of PDF/DOCX is central. Use `document-authoring` for an ordinary draft review. Read [PDF/DOCX checks](references/pdf-docx.md) for the format-specific work being performed.

## Define the artifact and inspection scope

- Identify the source, version, requested output format, reader and submission requirements. Do not assume extracted or converted text fully represents the original.
- Before extraction or conversion, identify pages, sections, tables, figures, footnotes, links, forms and text inside images where omission or displacement would matter.
- Do not bypass passwords or access restrictions, or run macros, external templates or embedded content without authorization. Do not send private documents to external conversion services without explicit approval.

## Compare input and output

- Compare extracted text with the visible source at multiple pages, headings, tables, figure surroundings and footnotes. Leave unreadable or unextractable parts marked as unchecked instead of reconstructing them.
- Open or render a generated/converted file when possible. Inspect page breaks, table columns, figures, character rendering, links and notes. A text comparison alone does not prove layout success.
- Report only submission format, filename, page count, links and accessibility properties actually checked. Do not declare an uninspected output ready for submission or publication.

## Report evidence

Separate source, generated or extracted artifact, method, compared locations, omissions or differences, and unchecked scope. If a particular tool is unavailable, describe the alternative check and its remaining limit.
