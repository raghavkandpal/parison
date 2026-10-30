# PostgreSQL snapshot collection acquisition

Date: 30 October 2026
Status: feature 1 implementation candidate; independent review and final CI pending

```text
parison postgres collection --plan collection-plan.json --output collection
parison verify-postgres-collection collection
```

The [frozen plan](277-postgresql-collection-contract.md) declares 1–16 distinct
ordinary base tables, private IDs, ordered columns/keys and shared limits.
The optional `postgres` extra supplies Psycopg; libpq service/environment
configuration stays outside the plan and offline verifier. No new installed
script is introduced; shipped table/pair commands retain their contracts.

The adapter validates the entire bounded regular-file plan before connecting,
locks every relation before any snapshot query, pins `search_path=pg_catalog`, qualifies every member before
COPY and exports ID order under one read-only repeatable-read transaction.
Qualification also counts each table to force row-security planning before any
COPY. Acquisition counts again; this intentional extra source scan is measured.
Shared row/byte allowances tighten execution without changing reviewed child-plan bytes.
Commit, child publication, offline replay and deadline admission must succeed
before one atomic no-overwrite installation. Failures/interruption clean staging;
a failed cleanup is surfaced rather than reported as success.

The SELECT-only profile rejects owner membership, effective write privileges,
superuser/BYPASSRLS, role/database creation and replication administration.
On PostgreSQL17/18 it also rejects MAINTAIN. This privilege is documented by
[PostgreSQL17 GRANT](https://www.postgresql.org/docs/17/sql-grant.html), while
[PostgreSQL16 privileges](https://www.postgresql.org/docs/16/ddl-priv.html) lack it
(accessed 30 October 2026). These checks narrow the new collection adapter;
released source/pair formats and readers remain unchanged. Built-in namespace
identity is checked so a custom type named `text` cannot impersonate a built-in.
Inheritance, partitioned/unlogged/temp/foreign relations and views remain excluded.

Use `scripts/check_postgres_collection_live.py --bin POSTGRES_BIN --report REPORT`
for disposable local qualification. It initializes/stops a temporary cluster,
uses a SELECT-only role and never connects to an existing service. `--measure`
adds three cold worker processes at 100k and 250k total six-table rows. Reports
record actual server facts, source statement/scan counts, elapsed time, process
RSS and staged content/allocated bytes. The worker has no children; server RSS
is excluded. Measurements are machine-specific and do not establish capacity.

All three exact live rows in [matrix 278](278-postgresql-capability-matrix.md),
independent Standards/Spec review, full local checks and exact-head built-wheel
CI must pass before feature 1 integration. This acquisition is adapter evidence;
source truth, cross-instance coordination and migration/cutover approval remain
upstream. All ten 2.4 features stay together before a release candidate.

## Review correction: truthful base-only child receipts

Independent review reproduced function shadowing through a hostile libpq search
path and concurrent inheritance attachment under ACCESS SHARE. The adapter now
pins built-in resolution and uses ONLY for prequalification counts, acquisition
counts, collision scans and COPY. New collection children use source-receipt-v2
and derived export-plan-v2 with exact ONLY SQL; source summary/manifest-v1
layouts remain unchanged and bind the new receipt bytes. The new profile is
`postgresql-base-table-only-csv-v1`. Both old and new canonical collection
fixtures remain readable; profile/child-version mixing and false ONLY relabeling
are rejected. Released pair-v1 still requires source-v1 children.

See the contract-277 review amendment for the privilege/locking rationale.
The live corpus includes hostile search-path server/MAINTAIN facts and a child
attached after qualification containing an otherwise forbidden null-marker value.
New base-only export excludes that undeclared row while retaining correct counts.
