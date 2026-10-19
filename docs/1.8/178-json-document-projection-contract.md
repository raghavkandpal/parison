# JSON document projection contract

Status: **implementation contract**

## Locator

```text
json:path/to/export.json#/records
```

The `json:` prefix, local `.json` regular file and `#` separator are mandatory.
The suffix is an RFC 6901 JSON Pointer in string form; an empty pointer selects
the root. URI-fragment encoding, parameters, symlinks, compression and
partition directories are rejected.

## Records and values

The selected value must be an array. Every array item must be a flat object
with non-empty string field names and the same field set. Duplicate JSON member
names, nested record values and non-finite numbers fail closed. Decimal and
integer tokens retain their source spelling rather than passing through binary
floating point; booleans map to `true` and `false` as JSON Lines already does.

JSON document inputs require `input_projection: semantic-scalar-v1`. Existing
recipe column types remain authoritative. The selector only establishes which
objects are records.

## Limits and evidence

`--max-input-bytes` bounds the document and `--max-rows` bounds selected array
items. Full evidence records `format: json`, the JSON `pointer`, byte size and
whole-file SHA-256 without exposing the source path. Keyed, aggregate and
multiset preflights use new strict schema versions; released schemas remain
unchanged.

## Compatibility boundary

Comparison modes, recipes, policy fingerprints, canonical encodings, results,
bundles and CLI exit codes are unchanged. Generic recursive JSON comparison,
JSONPath, implicit array discovery, mutation and repair are out of scope.
