# Structured preflight diagnostics

Date: 7 October 2026

`validate-inputs` returns one JSON object for both matching and mismatched physical schemas. A valid schema exits zero; a schema mismatch exits two and still writes the complete diagnostic object to standard output.

The top-level `schema_version` is `1`, and `policy_sha256` identifies the fully expanded policy used for the check. Pass `--expected-policy-sha256 HASH` to reject a malformed or changed policy before either input is opened. The installed schema is available from `parison schema preflight`.

Each input contains a `schema` object:

```json
{
  "missing": ["legacy_total"],
  "unexpected": ["new_field"],
  "mapped": {"total": "legacy_total"},
  "excluded_present": ["updated_at"]
}
```

- `missing` and `unexpected` are sorted physical column names.
- `mapped` maps canonical fields to side-specific physical names only where they differ.
- `excluded_present` lists reviewed exclusions actually present on that side.

Diagnostics contain schema names but no record values or local paths. Schema metadata may itself be sensitive and should be handled accordingly.

Malformed recipes, unreadable inputs, unsupported formats, invalid partition layouts and resource-limit failures remain operational errors: they exit two on the CLI and are reported on standard error because no trustworthy two-sided schema result exists.
