# Tested support envelope

Date: 6 October 2026. This document defines what the current alpha candidate has actually exercised. It is not a claim that larger or differently shaped inputs fail.

## Environment

Performance evidence was collected on arm64 macOS with Python 3.14.7 and Parison 0.1.0. Every reported value is the median of five fresh subprocesses after one discarded warm-up. Each repetition verified the complete expected result before its measurements were accepted.

Use at least 2 GB of available process memory for the largest standard-profile case below. Parison's `--max-input-bytes` and `--max-rows` options are processing guards, not memory reservations or proof that inputs below those limits will fit.

## Tested summary-mode envelope

| Shape | Largest tested row count | Columns | Largest field | Formats | Highest observed peak RSS |
| --- | ---: | ---: | ---: | --- | ---: |
| Standard | 250,000 | 10 | short synthetic strings | CSV, Parquet | 772.6 MB |
| Wide | 10,000 | 100 | short synthetic strings | CSV, Parquet | 355.3 MB |
| Long strings | 10,000 | 4 | 4 KB | CSV, Parquet | 162.7 MB |
| Composite identity | 10,000 | 11 | short synthetic strings | CSV, Parquet | 121.9 MB |
| Null-heavy | 10,000 | 17 | short synthetic strings | CSV, Parquet | 122.7 MB |
| High mismatch | 10,000 | 10 | short synthetic strings | CSV, Parquet | 117.3 MB |

CSV-to-Parquet mixed comparison is covered by the semantic suite. The large performance matrix measures same-format pairs so format costs remain interpretable.

## Important boundaries

- The performance envelope applies to `summary` sensitivity. Raw evidence is semantically tested but has not been performance-qualified at these sizes and retains both complete inputs.
- The 250,000-row result applies to the ten-column standard profile. Do not extrapolate it to 100-column or 4 KB-field inputs.
- Input compression is not a memory predictor. The 250k Parquet pair occupies only about 489 KB on disk but peaks at about 773 MB RSS after decoding and comparison.
- Timing and RSS have not yet been characterized on Linux, Windows, Python 3.11, Intel hardware or deliberately memory-constrained processes.
- Nested Parquet values are rejected by the current scalar recipe model. Database connectors, partitioned execution and spill-to-disk are not implemented.

## Evidence

- [`results-2026-10-06-streaming.json`](../benchmarks/results-2026-10-06-streaming.json): standard CSV.
- [`results-2026-10-06-parquet-streaming.json`](../benchmarks/results-2026-10-06-parquet-streaming.json): standard Parquet.
- [`results-2026-10-06-adversarial.csv.json`](../benchmarks/results-2026-10-06-adversarial.csv.json): adversarial CSV matrix.
- [`results-2026-10-06-adversarial.parquet.json`](../benchmarks/results-2026-10-06-adversarial.parquet.json): adversarial Parquet matrix.

Clean wheel installation and the CLI now pass CI on Python 3.11–3.14 under Ubuntu, with Python 3.14 smoke coverage on macOS and Windows. That establishes functional compatibility, not a performance envelope on those platforms. Expand this envelope only from recorded measurements, not from configured resource limits.
