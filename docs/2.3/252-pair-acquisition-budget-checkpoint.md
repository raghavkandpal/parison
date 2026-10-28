# Pair acquisition budget checkpoint

Date: 28 October 2026
Status: machine-specific synthetic acquisition measurement after feature 2 integration

## Setup and workload

Apple M1, 8 logical CPUs, 16 GiB RAM, macOS 27.0.1; local Homebrew
PostgreSQL 18.6 over a private Unix socket; Python 3.14.7 and Psycopg 3.3.6.
The reader used a non-owner SELECT-only role and the feature 2 defaults of
300,000 total rows, 1 GiB output, five-minute statement and ten-minute wall
limits. No TCP or production source was involved.

The 100,000-row pair had 40,000 `orders` and 60,000 `order_lines`; the
250,000-row pair had 100,000 and 150,000. Each table had an integer primary
key and deterministic numeric, text and (for orders) timestamp fields. Text
payloads used 64 hexadecimal characters per row. Each run launched a fresh
Python process, acquired both tables, verified the pair and removed the local
bundle. The server and OS caches were not cleared between runs. Elapsed time
is external process wall time, including startup and local verification.
`/usr/bin/time -l` measured peak adapter RSS; the adapter spawned no children.
PostgreSQL backend memory was not included.

| Total rows | Three elapsed runs (s) | Median / max (s) | Max adapter RSS | Data bytes | Final bundle logical bytes |
| ---: | --- | ---: | ---: | ---: | ---: |
| 100,000 | 0.626, 0.543, 0.566 | 0.566 / 0.626 | 48,922,624 B | 10,610,006 | 10,615,190 |
| 250,000 | 1.115, 1.129, 1.127 | 1.127 / 1.129 | 48,742,400 B | 26,662,755 | 26,667,949 |

The producer writes only monotonically growing files in one staging directory
before atomic rename, so final bundle logical bytes are also the inferred
peak staged logical bytes. Allocated filesystem blocks and PostgreSQL backend
memory were not sampled. The six-run database-level `pg_stat_database`
checkpoint recorded 19 blocks read, 58,341 blocks hit and zero temporary
files/bytes; it includes catalog and monitoring work. After resetting stats
immediately before these six runs, each source table recorded six sequential
scans (count and reserved-marker probe on each run) and three index scans
(ordered COPY). `seq_tup_read`/`idx_tup_fetch` per table were 240,000/120,000
for the 40k orders table, 360,000/180,000 for 60k lines,
600,000/300,000 for 100k orders and 900,000/450,000 for 150k lines.
These counters describe this fixture and do not predict production source
load.

The controlled [adversarial gate](251-postgresql-pair-operator-notes.md)
separately passed concurrent writers, DDL lock order, aggregate row/byte
limits, partial second-table interruption, backend termination before commit,
RLS rejection, empty/quoted UTF-8 child, no-overwrite and source removal.
[PR #96](https://github.com/raghavkandpal/parison/pull/96) integrated at
`032069f436518036b391c6e206e02c3e06c8262a`; exact head
`fecaa454513d36cb666e1b27ff073132aa2323ba` passed 520 local tests,
independent Standards/Spec review and the [full built-wheel
matrix](https://github.com/raghavkandpal/parison/actions/runs/40689314201)
on Python 3.11–3.14 Linux/macOS/Windows.

This is an acquisition-only, cache-warm synthetic checkpoint. It does not
measure PostgreSQL 16, a target database, parity, reconciliation, source/target
coordination, peak backend RSS, allocated temporary disk, or an operator's
complete ten-minute rehearsal. Feature 5 must measure those combined steps
before making a migration-pair performance claim.
