# Performance optimization plan

Date: 5 October 2026. This is the handoff for the next implementation session.

## Measured baseline

All cases use two ten-column CSV inputs, reversed candidate order, exact rows, tolerance-only changes, required differences and missing/extra keys. Every run verified the complete expected result before its timing was accepted.

| Baseline rows | Combined input | Median of 3 | Baseline rows/s | Median peak Python allocation | Bytes/baseline row |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 10,000 | 2.46 MB | 0.54 s | 18,492 | 20.9 MB | 2,092 |
| 100,000 | 24.57 MB | 6.19 s | 16,164 | 211.1 MB | 2,111 |
| 250,000 | 61.43 MB | 16.23 s | 15,403 | 519.0 MB | 2,076 |

The near-constant ~2.1 KB per baseline row indicates linear retained-object growth. At the current slope, one million baseline rows would require roughly 2 GB of traced Python allocations before accounting for the interpreter, native libraries and operating-system overhead. Do not claim one-million-row support.

A 10k-row `cProfile` run recorded 1.20 million calls in 0.77 seconds. `compare` took 0.72 seconds cumulatively; its two `_read` calls took 0.53 seconds (74%). `_parse` took 0.10 seconds across 199,950 calls. `_index` took 0.05 seconds. `_classify` took 0.006 seconds. Optimization should therefore start at ingestion and representation, not tolerance arithmetic.

## Current sources of cost

1. CSV ingestion first retains every raw `DictReader` row, then builds a second list of typed dictionaries. Both representations coexist during conversion.
2. Each typed row is a dictionary with repeated column-name hashing and substantial per-object overhead.
3. `_index` walks the typed rows again, builds a temporary key list, then creates another dictionary referencing the rows.
4. `common`, `baseline_only` and `candidate_only` materialize three key sets. Complete common keys are sorted even in summary mode, where output ordering is irrelevant.
5. Input files are read for the pre-read digest, parsing and post-read digest. This costs I/O but currently contributes much less CPU than object construction on cached local files.
6. Parquet is converted from a Polars frame to dictionaries and then to typed dictionaries, briefly retaining multiple full representations.

## Module and seam decision

Keep `compare(recipe_path, baseline_path, candidate_path, ...)` as the external interface. It is already a deep module: callers receive validation, identity checks, comparison, provenance and deterministic results through one function.

Create one internal `InputIndex` module behind an internal seam:

```text
read_index(path, compiled_recipe, limits) -> InputIndex
```

`InputIndex` owns typed row representation, key indexing, null/duplicate preflight, row count and input digest. CSV and Parquet are the two real adapters at this seam. Do not expose parser-specific frames, dictionaries or iterators through the interface. Do not add factories or a public adapter interface.

## Ranked implementation plan

### 1. Stream CSV conversion directly

Replace `raw_rows = list(reader)` plus the typed-list comprehension with one loop that validates and converts each row immediately. This removes one complete dictionary representation without changing the result model.

Acceptance:

- All semantic and artifact tests pass unchanged.
- Generated 10k/100k/250k counts remain exact.
- Median bytes per baseline row improve by at least 20%, to no more than 1,700.
- Median throughput does not regress by more than 10%.

Stop after this change and remeasure before restructuring anything else.

### 2. Build a compact index during parsing

Compile the recipe once into ordered column positions. Store each row as a tuple rather than a dictionary and insert it into the key index while parsing. Reject null or duplicate keys in the same pass. This removes the typed-row list, repeated column-name lookups and the separate `_index` pass.

Acceptance:

- The `compare` external interface and canonical result schema do not change.
- Peak allocation falls below 1,200 bytes per baseline row on the 100k and 250k cases.
- The 250k case stays below 320 MB traced Python allocation.
- Readable typed conversion errors still identify the column and policy without exposing raw values.

### 3. Remove unnecessary key collections in summary mode

Iterate one index and use membership checks in the other to derive common and missing counts. Do not sort all common keys when `sensitivity=summary`. For raw mode, preserve deterministic evidence with a bounded selection strategy sized by `sample_limit`, not a full sort solely for samples.

Acceptance:

- Reordering inputs still produces semantically identical summary results.
- Raw evidence samples remain byte-stable for identical inputs and recipes.
- Missing/extra count conservation invariants remain true.

### 4. Make Parquet avoid dictionary round-trips

Have the Parquet adapter populate the same compact `InputIndex` from ordered Polars rows or columns. Do not call `to_dicts()`. Keep the metadata-first row-limit check.

Acceptance:

- Decimal scale, timestamp, nested-type rejection and row-limit tests pass.
- Measure process RSS as well as Python allocations because Polars uses native memory.

### 5. Consider a vectorized engine only if needed

After steps 1–4, reassess actual user-size requirements. Prototype a Polars-native keyed comparison only if the compact Python implementation still misses a measured target. A second execution engine creates a real seam only when both implementations are needed; do not add an engine abstraction speculatively.

DuckDB, partitioning and spill-backed execution remain later options for demonstrated larger-than-memory demand. They are not the next optimization.

## Benchmark protocol improvements

- Keep exact-count verification inside every measured run.
- Use five fresh subprocess runs for release claims; exclude one warm-up run.
- Record median and range, never only the fastest run.
- Add process peak RSS to `tracemalloc`; Python allocation alone misses Polars/native memory.
- Keep the CI guard memory-based and generous. Do not add wall-clock CI thresholds.
- Record hardware, Python, Parity and optional Polars versions with every result.
- Compare changes against the committed `results-2026-10-05.json` baseline using identical generated inputs.

## Next-session checklist

1. Implement only step 1: direct streaming conversion in `_read`.
2. Run all tests, including installed Polars tests.
3. Run the three generated cases five times and capture memory plus throughput.
4. Commit only if the 20% memory target is met with no semantic drift.
5. If the target is not met, retain the measurements, revert the optimization and proceed to the compact `InputIndex` prototype in a separate commit.

