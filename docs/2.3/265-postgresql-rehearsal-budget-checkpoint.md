# PostgreSQL 16→18 rehearsal budget checkpoint

Date: 29 October 2026
Status: corrected feature 5 local qualification, machine-specific

Three fresh worker processes per size ran sequentially after disposable
PostgreSQL 16.15→18.6 dump/restore on an Apple M1 MacBook Pro with 16 GB RAM,
macOS 27.0.1 and Python 3.14.7. Storage type could not be read through the
host's DiskManagement framework; the measurement is not a universal capacity
claim. Each worker acquired both two-table pairs, ran exact parity and SQLite
relationships/conservation, then verified the rehearsal locally. The 100k
run additionally passed five live mutations (orphan, offsetting per-order sums,
timestamp, Unicode and partial backfill); both sizes verified offline after
both servers stopped. The fixture used `orders` and `order_lines` with half the
rows in each table per side, and no production workload.

| Total rows per side | Median / max elapsed | Median / max worker peak RSS | Sampled peak temporary disk | Sampled peak output disk | Retained bytes |
| --- | --- | --- | --- | --- | --- |
| 100,000 | 15.921 / 17.709 s | 71.24 / 73.50 MB | 14.44 MB | 19.97 MB | 5.54 MB |
| 250,000 | 41.068 / 42.015 s | 94.99 / 95.85 MB | 36.49 MB | 50.53 MB | 14.06 MB |

The worker spawned no children, so its peak RSS is also its process-tree peak.
Disk was sampled every 10 ms; sampled peaks are observations, not upper bounds.
Each 100k-side acquisition reported 2,756,728 output bytes and 100,000 rows;
each 250k side reported 7,016,731 bytes and 250,000 rows. The source adapter
issued two table count scans and two COPY scans per pair. Acquisition `elapsed_ms`
was 152/164 for PostgreSQL 16/18 at 100k and 356/362 at 250k in the first
sample. The full measured elapsed includes startup, both acquisitions, local
comparison and replay verification; it excludes cluster initialization and
dump/restore, which are upstream fixture preparation. The provisional ten-minute
operator target is met on this named machine for 250k rows, without establishing
production source load or cross-instance snapshot coordination.

Raw reproducible records: [100k](../../benchmarks/results-2026-10-29-postgresql-rehearsal-100k-final.json)
and [250k](../../benchmarks/results-2026-10-29-postgresql-rehearsal-250k-final.json).
The earlier `*-pre-review.json` reports measured the first implementation before
private input staging and must not be used for the final budget claim.
