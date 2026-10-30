# Collection acquisition qualification and machine-specific budget

Date: 30 October 2026
Status: live candidate qualified at source commit `461b2d5ec153f016c6ee3c46adcbff101c9f59b7`; exact-head CI pending

## Reproduced live gates

All clusters were disposable, local, UTF-8/C-locale instances initialized by
`scripts/check_postgres_collection_live.py`; no existing database was used.
Exact PostgreSQL 16.15 passed 33 named gates;17.11 and 18.6 passed 35 each.
The two extra gates check MAINTAIN, which is absent on 16. Evidence:
[16.15](../../benchmarks/results-2026-10-30-postgresql-collection-16.json),
[17.11](../../benchmarks/results-2026-10-30-postgresql-collection-17.json),
[18.6](../../benchmarks/results-2026-10-30-postgresql-collection-18.json).

The corpus covers six-table shared snapshots under concurrent writes and DDL,
all-member prequalification, late RLS/role failures, source-only built-in types,
null-marker rejection, quoted UTF-8/composite keys, inheritance/foreign/temp/
view/unlogged/partitioned rejection, aggregate limits, statement/wall/lock
timeouts, interruption, failed commit/verification/rename, empty and sixteen-table
probes, and offline replay after server shutdown. Independent review additionally
reproduced the concurrent-inheritance bug and confirmed truthful ONLY exclusion
after the contract amendment. Hostile search-path metadata spoofing is regressed.
Unit gates cover connection loss, changed snapshot, publication race, deadlines
after commit, strict semantic negatives, file/directory mutation and safe errors.
These observations qualify the named local configurations, not every deployment.

## Six-table measured workload

Machine: MacBookPro17,1, Apple M1, 8 logical CPUs, 16 GiB RAM, macOS 27.0.1,
Python 3.14.7, Psycopg 3.3.6, PostgreSQL 18.6. Each table has an integer primary
key and a text value. 100k/250k total rows are divided across six tables.
Three fresh Python worker processes perform acquisition plus a separate offline
verification. Database and OS caches are not flushed. No 1m capacity claim is made.

| Total rows | Median seconds | Max seconds | Peak worker-tree RSS bytes | Peak staged content bytes | Staged allocated bytes |
| --- | --- | --- | --- | --- | --- |
| 100,000 | 0.233 | 0.234 | 49,610,752 | 1,679,566 | 1,757,184 |
| 250,000 | 0.543 | 0.543 | 50,593,792 | 4,379,566 | 4,460,544 |

Worker-tree RSS is the worker's RUSAGE_SELF maximum: it has no children and
excludes PostgreSQL server memory. Staged content/allocated blocks are measured
at final stage verification, when this append-only file set is fully materialized.
The allocated-byte observation includes staging directories and filesystem blocks;
it is not a universal disk requirement. CSV bytes and each run are in the raw report.

Each measured run observes 12 COUNT scans (prequalification and acquisition),
6 null-marker checks and 6 COPY scans. Catalog/session statement counts are also
recorded by instrumenting the driver's execute/copy methods. This is source-load
volume evidence; server CPU, physical-read amplification and production contention
were not measured. Medians/maxima are evidence for this machine and workload,
not a general capacity or latency guarantee. Existing 300k-row/1GiB limits remain.

## Integration gate

The corrected source passes599 local tests and independent Standards/Spec re-review.
The final PR head must pass quality CI and the full built-wheel Python 3.11–3.14
Linux/macOS/Windows matrix before integration. Live PostgreSQL qualification and
installed-wheel platform coverage are distinct evidence. All ten 2.4 features
remain together before a release candidate; this checkpoint does not authorize
source extraction truth, cross-instance coordination, migration or cutover.
