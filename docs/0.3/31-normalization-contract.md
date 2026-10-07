# String-normalization contract

Date: 7 October 2026

## Purpose

Normalization lets a reviewed recipe declare which representational string differences are irrelevant. It is opt-in per canonical field; an omitted or empty `normalize` list preserves exact 0.2 behavior.

## Recipe shape

Rules are applied in the listed order after type parsing and before key identity or field comparison.

```json
"columns": {
  "customer_id": {
    "type": "string",
    "comparison": "exact",
    "normalize": ["trim", "casefold"]
  },
  "description": {
    "type": "string",
    "comparison": "exact",
    "normalize": ["unicode_nfc"]
  }
}
```

Supported rules are:

- `trim`: remove leading and trailing Unicode whitespace with Python's `str.strip()` semantics.
- `casefold`: apply Unicode-aware `str.casefold()` casing.
- `unicode_nfc`: convert text to Unicode Normalization Form C.

Only string columns may declare normalization. Rules must be supported and may occur at most once in a field's ordered list. Null remains null.

## Identity, comparison and evidence

Normalization applies to keys as well as non-key fields. Consequently, two physical keys that normalize to the same canonical key are the same identity; duplicate-key validation runs on that canonical identity and remains strict.

Every active rule remains visible in the effective recipe and HTML field policy. Summary results contain no source values. With `output.sensitivity` set to `raw`, sampled discrepancies retain the parsed values received before normalization, including original key values for missing-record samples. Evidence is still bounded by `--sample-limit`.

Normalization can make two received values equivalent, so no discrepancy is emitted for that pair. This is intentional and is why every rule requires explicit recipe review.

## Non-goals

This slice does not add regex replacements, locale-specific collation, transliteration, accent removal, fuzzy matching, automatic rule inference or arbitrary expressions.
