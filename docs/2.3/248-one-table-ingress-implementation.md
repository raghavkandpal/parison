# One-table PostgreSQL ingress implementation

Date: 28 October 2026
Status: feature 1 integrated through PR #93

The optional `parison-postgres` entry point reads a strict version 1 plan and
connects using standard libpq environment or service settings. The plan has
no connection field. Install with `pip install 'parison[postgres]'`; this
adds the pinned Psycopg adapter without changing the offline comparison
engine. The command reports only a summary-safe JSON object. Database errors
are deliberately reduced to a generic acquisition failure.

Example plan:

```json
{"plan_version":1,"source_id":"reviewed-source-label","schema":"public","table":"orders","columns":["id","amount"],"primary_key":["id"],"limits":{"max_rows":300000,"max_output_bytes":1073741824,"statement_timeout_ms":300000,"wall_timeout_ms":600000}}
```

Run `parison-postgres --plan plan.json --output local-export`, then
`parison verify-postgres-export local-export`. The reader creates only a new
output directory. Keep `data.csv` and `receipt.json` private; only
`summary.json` is safe for the summary handoff described in the
[contract](247-postgresql-one-table-ingress-contract.md). A comparison recipe
must separately review the exported columns, key, and `\\N` null token.
Verification checks local consistency and does not authenticate PostgreSQL.

The explicit controlled gate is `PYTHONPATH=src python
scripts/check_postgres_ingress_live.py` with an isolated PostgreSQL database
and libpq environment pointing to a role permitted to create a disposable
schema and login role. It creates then removes a uniquely named fixture. The
gate forces a concurrent insert after the snapshot is acquired and checks
that the export still has the original two rows. It checks that a relation
rename cannot pass the acquired lock. It also checks RLS rejection,
reserved null-marker rejection, a mid-COPY byte limit, no-overwrite, staging cleanup, and offline
verification after source removal. Local development ran this gate against
PostgreSQL 18.6 on macOS; that is an environment-specific result, not a
PostgreSQL 16 or production capacity claim.

The producer caps one table at 300,000 rows and 1 GiB, with bounded statement,
connection and wall time. A failed acquisition publishes no complete bundle.
The separate offline verifier needs neither PostgreSQL nor Psycopg. The
schema names are `postgres-export-plan`, `postgres-source-receipt`,
`postgres-source-summary` and `postgres-source-manifest` under `parison schema`.
