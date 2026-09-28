# PDF and DOCX checks

Read only when actually handling or verifying a PDF/DOCX. No single tool or extraction result is authoritative; inspect what matters in the requested format and environment.

## PDF extraction or conversion

- Identify whether pages contain a text layer, scans, rotation, multiple columns, tables, footnotes or figure captions. Extracted order, line breaks, columns and text in images can differ from the rendered page.
- Map page counts to sections. Compare the beginning, middle and end, plus fragile areas such as tables, figures and long paragraphs, with the displayed source. Do not guess missing pages or text in figures.
- If using a table as data, verify column headings against several rows. Even for reading only, check whether crossed columns or misplaced footnotes change meaning.

## DOCX extraction or generation

- Decide from the task whether headings, tables, footnotes and endnotes, headers and footers, comments, tracked changes, text boxes, images and links belong in the comparison.
- For images or OCR, compare image count, position, reading order, duplication and omissions with the source. Check actual output rather than assuming placeholder or bulk-replacement collisions.
- Templates, styles, contents tables, fields, mail merge and macros can change output or safety. Do not execute them without a clear need and permission; report them as unprocessed when relevant.

## Rendered verification

- Use the recipient's specified viewer or format if provided. Otherwise record the available viewer and inspection environment.
- Visually prioritize split tables, orphaned headings, figures, footnotes, long URLs, non-ASCII characters and links instead of assuming every page behaves alike.
- Appearance, extractability, link behavior and accessibility are separate properties. Do not infer an unchecked property from another successful check.
