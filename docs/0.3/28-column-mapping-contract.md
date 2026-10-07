# Explicit column-mapping contract

Date: 7 October 2026

## Purpose

Column mappings let one canonical recipe compare fields whose physical names differ between baseline and candidate outputs. Mapping changes names only; parsing, keys, nulls, tolerances, outcomes and evidence retain keyed-v1 semantics.

## Recipe shape

Mappings are optional. Unmapped canonical fields use their canonical name on both sides.

```json
"keys": ["order_id"],
"columns": {
  "order_id": {"type": "string", "comparison": "exact"},
  "amount": {"type": "decimal", "scale": 2, "comparison": "exact"}
},
"column_mappings": {
  "order_id": {"baseline": "legacy_order_id", "candidate": "order_id"},
  "amount": {"baseline": "total_amount", "candidate": "amount"}
}
```

Keys and column policies always reference canonical names. Results, field counts and raw discrepancy evidence also use canonical names. The HTML report shows canonical, baseline and candidate names together.

## Validation

- Every mapping names an existing canonical `columns` entry.
- Every mapping contains exactly one nonempty baseline and candidate source name.
- A physical source column can feed at most one canonical field on each side.
- A mapped physical source column cannot also be excluded.
- Each input must contain its mapped physical columns; unmapped or unexpected columns remain schema errors unless explicitly excluded.

## Draft workflow

Drafting maps exact shared names implicitly. Rename candidates are not guessed. To review a rename, remove the two physical names from `excluded_columns`, add or retain one canonical column policy, then add an explicit mapping and run `validate-recipe`.

## Non-goals

This slice does not add fuzzy matching, automatic rename approval, expressions, joins, casting beyond existing type policies, normalization, or one source column feeding multiple canonical fields.
