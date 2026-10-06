---
metadata:
  author: "4ltena"
  version: "1.1"
name: document-translation
description: Translate documents across languages or locales while checking meaning, omissions, protected syntax and locale-sensitive wording. Use when translation itself is the task.
---

# Translate and localize a document

Use when rendering a source document for another language or locale. Do not use for new writing, ordinary revision in the same language or a general review after translation.

## Identify the target and protected content

- Establish the audience, target language and locale, purpose, source version, and terminology that must be kept. An explicit target language overrides the language of the user's request. If no target is named, infer it from the request language only when that differs from the source and the intent is clear; otherwise ask when the choice affects the translation. If an unspecified use would change another important choice, ask or present bounded options with reasons instead of guessing.
- Separate translatable prose from code, commands, identifiers, variables, URLs, paths, anchors and filenames. Preserve Markdown, HTML, template and placeholder syntax.
- Do not mechanically preserve every proper name. Check official local forms, reading or display needs, and audience convention. If these cannot be verified, keep the original or mark the choice as open.

## Compare translation with source

- Map headings, paragraphs, notes, tables, lists and link targets to the source. Check for omissions, duplication and accidental source-language text.
- Compare the meaning of numbers, units, dates, conditions, negation, comparisons, causality, caveats and warnings. The test is whether the reader receives the same action and constraint, not one-to-one word correspondence.
- Check whether link targets, anchors, code examples and UI labels work for the target locale and context. Do not call an unopened link or unrun example verified.

## Finish in the target language

After drafting a persistent translated document, use the matching `document-style-<language>` Skill once if it is discoverable. Here `<language>` is the lowercase primary language code of the target locale (for example, Japanese or `ja-JP` maps to `ja`). This collection currently provides only `document-style-ja`: use it after translation **into Japanese**, whether the target was explicit or clearly inferred, and do not use it for an English or other non-Japanese target. If no matching style Skill is available, finish the translation without one. The style pass changes fluency and register, not claims or protected syntax. Compare the styled result against the source again before delivery.

## Report the result

State the target language and locale, compared scope, intentionally retained original forms and unresolved terminology or display issues. Follow a supplied glossary or official form; do not present a newly chosen term as an established official name.
