# SQLite keyed-engine engineering checkpoint

Date: 13 October 2026

Status: **released**

## Semantic and lifecycle gate

The SQLite keyed engine passed the same keyed-v1 oracle as memory execution for
PASS, missing keys, exact and tolerance differences, null values, column
mappings and duplicate-key rejection. Canonical result JSON matched after
removing only the documented engine, temporary-byte and temporary-limit fields.

Private workspaces were empty after success, a forced database-size failure and
Ctrl-C. Suite-v2 cases can select SQLite explicitly; aggregate-v1 remains
memory-only. Candidate-review hardening added raw pre-normalization evidence,
suite failure-metadata and full oracle regressions; the full local check passed
236 tests with six optional-Polars skips.

## Machine-specific benchmark

[`results-2026-10-13-keyed-spill.json`](../../benchmarks/results-2026-10-13-keyed-spill.json)
records three fresh-process measurements after one warm-up for each engine on
arm64 macOS with Python 3.9.2. Both inputs contain unique synthetic rows in
opposite order, and every run checked the exact expected PASS counts.

| Rows | Engine | Median elapsed | Median Python peak | Median process peak RSS | SQLite bytes |
| ---: | --- | ---: | ---: | ---: | ---: |
| 10,000 | Memory | 0.328 s | 7.5 MiB | 34.6 MiB | 0 |
| 10,000 | SQLite | 1.160 s | 2.4 MiB | 25.3 MiB | 6.8 MiB |
| 100,000 | Memory | 3.361 s | 68.8 MiB | 166.7 MiB | 0 |
| 100,000 | SQLite | 11.591 s | 2.4 MiB | 25.7 MiB | 77.2 MiB |

At 100,000 rows SQLite reduced measured process peak RSS by about 85% while
taking about 3.4 times as long and using 77.2 MiB of scratch storage. This is a
useful explicit disk-for-memory tradeoff, not a universal capacity claim and not
a reason to change the default engine.

## Reproduction

```console
python benchmarks/generate_spill_cases.py \
  --output /tmp/parison-keyed-bench --mode keyed --rows 10000 100000
PYTHONPATH=src python benchmarks/run_spill_cases.py --repeats 3 \
  --json-output /tmp/parison-keyed-results.json \
  /tmp/parison-keyed-bench/keyed-10000 \
  /tmp/parison-keyed-bench/keyed-100000
```

Exact implementation commit `12610d5` passed [GitHub Actions run
38363720890](https://github.com/raghavkandpal/parison/actions/runs/38363720890):
Python 3.11–3.14 on Linux plus built-wheel macOS and Windows jobs, including
the 1,000-row keyed SQLite accuracy smoke. This completes the 0.18 engineering
qualification gate.

Release merge `1f43d1724625b508e9c81cae01f454d659b3925a` passed [GitHub Actions run
38398474070](https://github.com/raghavkandpal/parison/actions/runs/38398474070).
The published wheel was downloaded again, checksum-verified, installed in fresh
Python 3.12, and passed direct and suite-v2 SQLite-keyed workflows with
recursive bundle verification.
