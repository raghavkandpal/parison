# JSON field projection contract

Status: **implementation contract**

## Versioned recipe policy

Recipe versions 4, 5 and 6 are the field-projection keyed, aggregate and
multiset recipes. Their comparison semantics are exactly recipe versions 1, 2
and 3 respectively, but they require `input_projection` to be
`semantic-scalar-v1`, prohibit `column_mappings`, and require:

```json
{
  "field_projection": {
    "version": 1,
    "baseline": {
      "kind": "json-pointer-v1",
      "fields": {"id": "/identity/id", "amount": "/totals/net"}
    },
    "candidate": {
      "kind": "direct-v1",
      "fields": {"id": "id", "amount": "amount"}
    }
  }
}
```

Each side uses one closed kind. `fields` has exactly the configured logical
column names, with at most 256 entries and unique selector values. There is no
implicit fallback. `direct-v1` selects one exact nonempty flat source-field
name. `json-pointer-v1` selects one nonempty RFC 6901 pointer relative to each
record chosen by the released `json:path#record-pointer` locator. A JSON side
must use `json-pointer-v1`; that kind is invalid for every other input format.

The whole declaration is part of the normalized effective policy and policy
fingerprint. Recipe versions 1--3, their schemas and their fingerprints remain
unchanged.

## Pointer evaluation and record shape

The released document pointer first selects one array. Every item remains a
JSON object, duplicate member names are rejected throughout the document, and
field pointers are then evaluated from that object. Pointer tokens use exact
code-point member matching, `~0` and `~1` escaping and canonical array indices.
Pointers are limited to 32 tokens and 1,024 UTF-8 bytes.

Every field pointer must resolve for every record to one JSON scalar: string,
number token, boolean or null. Missing paths, invalid escapes or indices,
containers and recursion failure are controlled input errors. Numbers retain
their source spelling; booleans project as `true` or `false`. Different
pointers may traverse shared containers, but may not select the same value by
using duplicate selector text.

Source members outside the declared pointers are intentionally outside the
comparison scope. This is an explicit projection, not a completeness claim.
The recipe's reviewed scope and exact selector mapping make that exclusion
visible; Parison never infers, suggests or approves it.

## Workflows and evidence

Versions 4--6 work in direct comparisons and portable suite-v2 cases under all
existing memory/SQLite engine combinations. Validation emits strict preflight
schemas v16--v18. Full preflight records the declared per-side projection;
summary-sensitivity comparison results do not expose selector paths or source
field names. Raw effective recipes retain the reviewed declaration as policy.

`draft-recipe` does not invent field pointers. It continues to draft flat
records and fails closed on nested JSON until a human supplies a versioned
selector policy. Schema export and CLI schema lookup include the new recipe
and preflight schemas.

## Limits, compatibility and non-goals

Physical input bytes, selected rows and the JSON parser's existing recursion
handling remain authoritative. The selector-count, depth and byte limits bound
per-record traversal. Comparison contracts, canonical scalar/row bytes,
outcome reduction, result schemas, bundle readers, CLI JSON and exit codes are
unchanged.

JSONPath, Relative JSON Pointer, wildcards, recursive descent, container
serialization, missing-value defaults, inferred flattening, selector
suggestions, repair and approval are out of scope. PASS means only that the
declared projections agree under the explicit recipe policy.
