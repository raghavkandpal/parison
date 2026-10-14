# Cross-format semantic scalar guide

Use `semantic-scalar-v1` when the baseline and candidate use different supported formats and you want source-type changes to fail instead of being hidden by incidental Python coercion.

Add one reviewed field to any keyed, aggregate or multiset recipe:

```json
{
  "recipe_version": 1,
  "comparison_mode": "keyed",
  "input_projection": "semantic-scalar-v1",
  "keys": ["id"],
  "scope": {
    "snapshot": "coordinated-orders-export",
    "cutoff": "2026-10-14T00:00:00Z",
    "filters": [],
    "completeness": "full",
    "expected_empty": false
  },
  "identity": {"null_keys": "reject", "duplicates": "reject"},
  "nulls_equal": true,
  "columns": {
    "id": {"type": "integer", "comparison": "exact"},
    "amount": {"type": "decimal", "scale": 2, "comparison": "exact"},
    "active": {"type": "boolean", "comparison": "exact"},
    "observed_at": {"type": "timestamp", "timezone": "require-aware", "comparison": "exact"}
  },
  "output": {"sensitivity": "summary"}
}
```

Review null tokens, mappings, exclusions and every column type as usual. The projection does not make those choices for you.

Run schema-only preflight first:

```console
parison validate-inputs --recipe recipe.json --baseline baseline.csv --candidate candidate.parquet
```

For Parquet, this checks the complete dtype schema before row materialization. Then validate all records:

```console
parison validate-inputs --recipe recipe.json --baseline baseline.csv --candidate candidate.parquet --records
```

Finally run the unchanged comparison command:

```console
parison compare --recipe recipe.json --baseline baseline.csv --candidate candidate.parquet --output run
```

Typical fixes happen upstream: export booleans as booleans or exact lowercase text, exact decimals as decimal/text rather than binary float, timestamps with explicit offsets and nested values as reviewed scalar columns. Do not weaken the recipe merely to accept an accidental source representation.

Omit `input_projection` only when replaying a released recipe whose legacy coercion behavior is part of the evidence contract. Adding the field changes the policy fingerprint and must be reviewed like any other policy change.

See the [normative contract](139-semantic-scalar-contract.md) for the complete representation table, Parquet rules and compatibility gate.
The checked-in [`examples/1.1` workflow](../../examples/1.1/semantic-scalar.recipe.json) is a runnable CSV-to-JSON-Lines PASS using integer, decimal, boolean and offset-equivalent timestamp representations.
