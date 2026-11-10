---
name: strict-er-diagram
description: Convert an image of an ER diagram into a deterministic JSON DSL, generate conceptual and logical ER diagrams as Mermaid or SVG, and check them with the Lean 4 kernel and image cross-checks. Use when the user gives an ER diagram image and wants an exact Mermaid/SVG version, or asks to verify a diagram against its DSL. Also for ER図, 概念ER, 論理ER, 図の清書.
---

# Strict ER diagram

Turn an ER diagram image into a confirmed DSL, then generate diagrams from that DSL only. Three checks stay separate and are reported separately: reading the image, the design completeness of each view, and the formal check by Lean.

Read [DSL reference](references/dsl.md) before writing a DSL and [verification scope](references/verification.md) before reporting.

## Steps

### 1. Read the image

View the whole image first, then zoom into every junction and endpoint. Follow each line to both ends; never treat a crossing as a connection. Decide `notation` from the drawing and any legend. Decide `line_semantics` only from a legend or the user's answer; an all-solid diagram does not mean all relationships are identifying.

Never invent what is not drawn: no FK column, data type, label or multiplicity by guessing. "Not stated" and "unreadable" differ: a type not written is `null`; an unreadable value goes to `unresolved`. In `chen` and `ratio` diagrams a minimum is usually not drawn: set the multiplicity to `unknown` and add an `unresolved` entry listing both views.

Write `draft.er.json` following the DSL reference.

### 2. Get an independent reading

Launch one subagent that receives only the image path and the DSL reference, not your draft. Have it write `independent.er.json` in a temporary directory, then compare:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/er.py" compare draft.er.json independent.er.json
```

Re-open the image at each difference and decide from the image. Both readers may share an error, so agreement is not proof.

### 3. Resolve open items

Ask the user only about entries in `unresolved`, naming the image region and the decision. Remove an entry only when the image or the user settles it. Never drop one to reach `ready`.

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/er.py" canonicalize draft.er.json model.er.json
```

The input stays as it was. `model.er.json` is the confirmed DSL; do not rewrite it after this point.

### 4. Check against the image

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/er.py" check-image IMAGE model.er.json --out imagecheck.json --observation-out observation.json
```

This uses macOS Vision OCR and OpenCV geometry, independent of your reading. Without them the affected items are `not_checked`.

- `conflict`: go back to the image and resolve it. Change the DSL only when the image supports it, then rerun step 3 and 4.
- `insufficient_evidence`: check that item by eye and say so in the report.
- `unmatched_image_items`: classify each as diagram content, legend, decoration or a false detection. Never discard one silently.

### 5. Generate and prove

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/er.py" generate model.er.json --outdir OUT --format mermaid|svg|both --view conceptual|logical|both --observation observation.json
```

Defaults: Mermaid, both views. Use `--provenance image_and_supplement` when supplementary requirements added information. The command never overwrites the input image; on failure it keeps existing outputs and reports the working directory.

| Exit | Meaning |
|---|---|
| 0 | every proposition passed |
| 1 | a proposition failed; the output is not verified |
| 2 | the DSL was rejected |
| 4 | not run: Lean missing, wrong version, timeout or size limit |

When `mermaid` is `not_representable`, tell the user which items caused it and offer SVG. Never rename or strip text to fit Mermaid.

To re-check a saved output directory:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/er.py" verify OUT
```

### 6. Compare again and report

Render the result, view it, and compare it with the original image: entity count, attribute names and keys, both ends of each relationship, multiplicities, line styles, labels. For SVG open the file in a browser. Check overlaps, clipped text and label ownership; `label_crossings` in the report counts labels touching a line.

Report these separately, per view:

- design state: `ready`, `draft` or `blocked`, with the missing items
- formal state: `passed`, `failed` or `not_run`
- image check: counts per state, plus your visual comparison
- whether the diagram only reproduces the image or adds supplementary design

Never describe a `draft` logical view as a finished design, and never describe a Lean pass as proof that the image was read correctly.

## Scope

Input: crow's foot and table-style diagrams, binary Chen diagrams without relationship attributes, and ratio notation such as `1:N`. Output is always crow's foot.

Unsupported, returned as unresolved rather than converted: relationships of three or more entities, relationship attributes, weak entities, ISA hierarchies, `(min,max)` notation, arbitrary SQL constraints. Do not infer composite-key groups or FK targets from PK/FK marks.
