# Machine-qualified performance envelope

Date: 13 October 2026

Status: **consolidated recorded evidence**

## Meaning

This document collects the largest and most relevant checked-in measurements for Parison's released comparison modes. It is evidence about exact synthetic profiles on one arm64 macOS machine, not a universal capacity promise, service-level objective or substitute for measuring representative user data.

Every included run checked semantic accuracy before accepting timing or resource measurements. Configured byte, row, group, distinct-row and temporary-storage limits remain fail-closed processing guards; they do not promise that a machine can process inputs at those limits.

## Recorded envelope

| Mode and engine | Largest recorded profile | Median elapsed | Median peak RSS | Temporary storage | Evidence |
| --- | ---: | ---: | ---: | ---: | --- |
| keyed memory, CSV | 250,000 baseline rows, 61.4 MB combined input | 16.22 s | 636.6 MB | none | [CSV streaming](../../benchmarks/results-2026-10-06-streaming.json) |
| keyed memory, Parquet | 250,000 baseline rows, 0.49 MB encoded input | 10.91 s | 772.6 MB | none | [Parquet streaming](../../benchmarks/results-2026-10-06-parquet-streaming.json) |
| keyed SQLite, CSV | 100,000 matching rows per side | 11.59 s | 26.9 MB | 81.0 MB | [keyed SQLite](../../benchmarks/results-2026-10-13-keyed-spill.json) |
| keyed memory comparison for the same SQLite profile | 100,000 matching rows per side | 3.36 s | 174.8 MB | none | [keyed SQLite](../../benchmarks/results-2026-10-13-keyed-spill.json) |
| aggregate memory, CSV | 100,000 rows and 100,000 groups | 7.33 s | 484.8 MB | none | [aggregate 100k profiles](../../benchmarks/results-2026-10-13-aggregate-100k.json) |
| multiset SQLite, CSV | 100,000 distinct rows per side | 16.55 s | 35.7 MB | 34.7 MB | [multiset SQLite](../../benchmarks/results-2026-10-11-spill.json) |
| multiset memory comparison for the same SQLite profile | 100,000 distinct rows per side | 5.44 s | 275.3 MB | none | [multiset SQLite](../../benchmarks/results-2026-10-11-spill.json) |
| mixed-mode local suite, four workers | nine cases of 100,000 rows per input | 6.38 s | 1.05 GB process tree | none | [suite concurrency](../../benchmarks/results-2026-10-10-suite-concurrency-mixed-100k.json) |
| suite-v2 orchestration | 100 tiny cases, four sequential shards | 0.21 s shard execution; 0.19 s assembly | not recorded | none | [suite-v2 orchestration](../../benchmarks/results-2026-10-10-suite-v2.json) |

All row rates and sizes describe the generated fixtures, not arbitrary rows. Wide-row, long-string, composite-key, null-heavy and high-mismatch CSV profiles were separately accuracy-verified at 10,000 rows. Their median peak RSS ranged from 60.0 MB to 258.9 MB, demonstrating that row shape matters materially ([adversarial CSV profiles](../../benchmarks/results-2026-10-06-adversarial.csv.json)).

## Environment boundaries

The measurements were recorded on arm64 macOS with CPython 3.9.2, 3.12.5 or 3.14.7 as identified in each result file. They span Parison 0.1.0 through the 0.18 development line. Current CI proves functional installed-wheel compatibility on Python 3.11–3.14 and on Linux, macOS and Windows; it does not establish comparable performance on those platforms.

SQLite results show an explicit trade: substantially lower recorded process memory in exchange for roughly threefold keyed or multiset runtime and additional local disk. Users must choose the engine and temporary byte ceiling explicitly. The measurements do not justify automatic engine selection.

## Gaps before 1.0

- Raw-sensitivity performance is not qualified; retained discrepancy evidence can materially change memory and output size.
- Windows and Linux have functional smoke evidence but no recorded performance profiles.
- Input distributions remain synthetic and do not predict storage, cache, virtualization or shared-runner effects.
- The suite concurrency record contains one measured run per worker count, not repeated medians.

These gaps require honest documentation, not invented limits. Add a measurement only when it answers a concrete adoption or release question and records the fixture, environment, accuracy result, time, peak memory and temporary storage.
