# SQLite multiset engineering checkpoint

Date: 11 October 2026

Status: **prototype accepted for cross-platform qualification**

## What was measured

[`benchmarks/results-2026-10-11-spill.json`](../../benchmarks/results-2026-10-11-spill.json) records three fresh-process measurements after one warm-up for each engine on arm64 macOS with Python 3.12.5. Both inputs contain unique synthetic rows in opposite order; every run checked the exact expected PASS counts.

| Rows / distinct rows | Engine | Median elapsed | Median Python peak | Median process peak RSS | SQLite bytes |
| ---: | --- | ---: | ---: | ---: | ---: |
| 10,000 | memory | 0.513 s | 9.1 MiB | 48.8 MiB | 0 |
| 10,000 | SQLite | 1.575 s | 1.5 MiB | 32.5 MiB | 4.6 MiB |
| 100,000 | memory | 5.442 s | 93.3 MiB | 262.5 MiB | 0 |
| 100,000 | SQLite | 16.549 s | 2.1 MiB | 34.1 MiB | 33.1 MiB |

## Decision

Continue qualification. At 100,000 high-cardinality rows, the SQLite engine cut measured process peak RSS by about 87% while taking about three times as long. That is a useful explicit disk-for-memory tradeoff, but not a reason to change the default.

The result is machine-specific engineering evidence, not a supported capacity claim. Tracemalloc changes timing, process peak RSS includes interpreter startup and the inputs are synthetic. Linux and Windows forced-spill, interruption, disk-full and adversarial semantic-equivalence coverage remain release gates.

## Reproduce

```sh
PYTHONPATH=src python3.12 benchmarks/generate_spill_cases.py --rows 10000 100000
PYTHONPATH=src python3.12 benchmarks/run_spill_cases.py --repeats 3 \
  benchmarks/generated/multiset-10000 benchmarks/generated/multiset-100000
```
