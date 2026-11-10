# Verification scope

## What the Lean kernel checks

Each output has fixed propositions, checked with `decide +kernel` on the bytes read back from disk:

| Proposition | Meaning |
|---|---|
| `wellFormed model` | IDs unique and valid, references exist, identifying flags agree with line semantics, unknown multiplicities are declared |
| `encodeDsl model = savedDsl` | the Lean value re-encodes to the saved DSL byte for byte, so the conversion from JSON lost nothing |
| `encodeClassified (classifyView v model) = savedStatus` | the reported design state and missing items are the computed ones |
| `mermaidProblems` | the reported Mermaid refusal reasons are the computed ones |
| `renderMermaid`, `renderSvg (layout …) = saved` | the file is exactly what the generator yields |
| `decodeMermaidSubset`, `decodeSvgSubset saved = some (project v model)` | a separate reader, which never calls the generator, recovers the view's meaning from the saved text. For SVG it reads coordinates, line style, and symbol shapes and positions |
| `layoutOk` | boxes do not overlap, routes are orthogonal and avoid boxes, ends lie on the right boundaries, nothing leaves the canvas, estimated text fits |
| `observationConsistent` | every DSL item links to an existing observation, and each decided end symbol agrees with the multiplicity |

`#print axioms` must show only `propext`, `Classical.choice` and `Quot.sound`. These are per-artifact checks, not a proof for all inputs.

## Trusted, not proved

The kernel proves statements about the definitions in `lean/Er.lean`. It does not cover:

- that the image was read correctly. OCR, geometry and VLM evidence are observations; Lean only checks that they are consistent with the DSL
- the Python runner that loads files into Lean
- that the Mermaid subset is accepted by every Mermaid renderer. Fixtures were checked against the parser of Mermaid 12.3.0 during development
- rendered appearance. Text widths in `layoutOk` are estimates; check overlaps and clipping in a browser
- whether the schema is good design, or meets a normal form or business requirement
- saved encoder coverage: mutation tests in `tests/` show each DSL field reaches `encodeDsl`

## Reading the image check

`matched` means the check used agreed. `conflict` means it disagreed. `insufficient_evidence` means it could not tell, for example lines merged by a crossing. `not_checked` means it was not run. All `matched` does not prove completeness, because OCR and geometry can both miss elements.
