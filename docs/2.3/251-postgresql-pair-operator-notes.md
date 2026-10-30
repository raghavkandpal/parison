# Coordinated PostgreSQL pair: operator notes

Date: 28 October 2026
Status: feature 2 integrated through PR #96

Install the optional adapter with `pip install 'parison[postgres]'`. Create a
strict `postgres-pair-plan-v1` JSON file with reviewed `orders` and
`order_lines` slots. Each slot selects one distinct permanent base table and
explicit ordered columns/primary key. The source label is user-declared; it
does not authenticate the server. Connection settings come from libpq service
or environment variables, never the plan. Use a non-owner, non-superuser,
non-`BYPASSRLS`, SELECT-only role with schema usage.

```json
{"pair_plan_version":1,"source_id":"reviewed-source-label","tables":{"orders":{"schema":"public","table":"orders","columns":["id","amount"],"primary_key":["id"]},"order_lines":{"schema":"public","table":"order_lines","columns":["id","order_id","amount"],"primary_key":["id"]}},"limits":{"max_rows":300000,"max_output_bytes":1073741824,"statement_timeout_ms":300000,"wall_timeout_ms":600000}}
```

Run `parison-postgres-pair --plan pair-plan.json --output pair-export`, then
`parison verify-postgres-pair pair-export`. The output directory must not
exist. Each child under `tables/` is independently verifiable with
`parison verify-postgres-export`. Keep the complete pair directory private:
its receipts identify the source, selected relations, role and snapshot. The
pair command and offline verifier emit only the fixed summary-safe projection.
The acquisition claim covers two source-visible selections in one source
snapshot; it is not a parity or cutover decision. Review comparison recipes
separately, including the `\\N` null token.

The controlled gate is `PYTHONPATH=src python
scripts/check_postgres_pair_live.py` with libpq settings for a disposable
PostgreSQL database administrator. It creates a unique schema and read-only
role, then removes them. The test verifies one snapshot despite concurrent
writers, both relation locks before the first read, cleanup when the second
table exceeds the shared byte cap, partial second-table interruption cleanup,
aggregate row cap, connection termination before commit, RLS rejection,
empty child, quoted identifier and UTF-8 output, no-overwrite, and offline
verification after the source schema is removed. It passed locally on
PostgreSQL 18.6 on macOS; this is environment-specific evidence, not a
PostgreSQL 16 or universal capacity claim.

The new schemas exposed by `parison schema` are `postgres-pair-plan`,
`postgres-pair-receipt`, `postgres-pair-summary`, and
`postgres-pair-manifest`. The exact private and summary fields and the
all-or-nothing publication rule are fixed in the [contract](250-postgresql-pair-acquisition-contract.md).
