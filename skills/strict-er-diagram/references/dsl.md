# DSL reference (schema_version 1)

A confirmed DSL is canonical UTF-8 JSON: keys sorted, no whitespace, one trailing LF, entities and relationships sorted by ID. `er.py canonicalize` produces it. Duplicate keys, unknown keys, wrong types and floats are rejected.

```json
{
  "schema_version": 1,
  "notation": "crows_foot",
  "line_semantics": "identifying",
  "entities": [
    {"id": "E001", "name": "顧客", "attributes": [
      {"id": "A001", "name": "顧客ID", "type": "int", "keys": ["PK"], "note": null}
    ]}
  ],
  "relationships": [
    {"id": "R001", "src": "E001", "dst": "E002",
     "src_multiplicity": "exactly_one", "dst_multiplicity": "zero_or_more",
     "line_style": "dashed", "identifying": false, "label": "発注する"}
  ],
  "unresolved": [
    {"target": "R002", "field": "dst_multiplicity", "views": ["conceptual", "logical"],
     "question": "最小値が図にない。0か1か"}
  ]
}
```

## Fields

- `notation`: `crows_foot`, `chen`, `ratio` or `unknown`.
- `line_semantics`: `identifying` (solid means identifying, dashed means non-identifying), `none` (line style carries no meaning) or `unknown`. Decide it from a legend or the user's answer.
- `identifying`: `true` or `false` only when `line_semantics` is `identifying`, matching `line_style`. Otherwise `null`.
- IDs are fixed width: `E001`, `A001`, `R001`. Number entities by observed rectangle `(y_min, x_min, y_max, x_max)`, ties by name in UTF-8 order. Number relationships by their endpoints, label, multiplicities, line style and observed path. IDs do not change after confirmation.
- `attributes` keep the image's order. `type` is the written type, or `null` when none is written. `keys` is an ordered subset of `PK`, `FK`, `UK`.
- The identifier of an entity is its set of `PK` attributes. A marked identifier such as an underline becomes `PK`, with its evidence kept in the observation record.
- `src` and `dst` keep the reading direction of `label`. Never swap them to sort.
- A multiplicity at an end states how many instances of that end's entity correspond to one instance on the other side. Values: `zero_or_one`, `exactly_one`, `zero_or_more`, `one_or_more`, `unknown`. `unknown` needs an `unresolved` entry listing both views.
- `label`: `null` when the relationship has no label.
- `unresolved.target`: an entity, attribute or relationship ID, or `diagram`.

Keep display text as drawn: do not change case, Unicode form or spaces.

## Reading by notation

| Notation | Drawn | Value |
|---|---|---|
| crow's foot | bar + bar | `exactly_one` |
| crow's foot | circle + bar | `zero_or_one` |
| crow's foot | circle + foot | `zero_or_more` |
| crow's foot | bar + foot | `one_or_more` |
| ratio, Chen | `1` | `unknown` until the minimum is settled, then `exactly_one` or `zero_or_one` |
| ratio, Chen | `N`, `M` | `unknown` until the minimum is settled, then `zero_or_more` or `one_or_more` |

Chen: a rectangle is an entity, a diamond is a relationship whose text becomes `label`, an ellipse is an attribute of the entity it connects to with `type: null`. An underlined attribute becomes `PK`.

## Mermaid limits

Mermaid output is refused, with the items listed, when an attribute name has a character outside letters, digits, `_`, `-` and non-ASCII, or starts with a digit or `-`; when a type also fails this with `()[],` allowed, or is literally `unknown`; or when a display name, label or note contains `"`, `#`, `<`, `>`, `&` or a control character. SVG has none of these limits.

## Limits

DSL 256 KiB, 50 entities, 500 attributes, 100 relationships. Output 256 KiB per file, 4,096 lines, 1,024 bytes per line. Lean: 120 s per proof file.
