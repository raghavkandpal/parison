# Project initialization guide

Create and enter a starter project:

```sh
parison init migration-check
cd migration-check
parison validate-recipe recipe.json
parison validate-inputs --recipe recipe.json \
  --baseline baseline.csv --candidate candidate.csv --records
parison compare --recipe recipe.json \
  --baseline baseline.csv --candidate candidate.csv --output run
parison verify run
```

The checked-in sample should PASS. It proves that the local installation and workflow run; it does not validate a migration.

Before using real outputs, replace both CSV files and review every policy field. In particular, record the shared extraction snapshot and cutoff, state all filters, confirm full-scope completeness, choose stable unique keys, and declare each compared column's type and comparison. If the real files have different shapes, `draft-recipe` may provide a separate starting point, but its suggestions require the same review.

Keep real data, raw-sensitivity bundles and credentials out of source control. Summary-only bundles omit source values, but their counts, policy and provenance are still operational metadata that should receive appropriate access control.
