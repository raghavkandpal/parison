# Parison 0.14.0 release checklist

Date: 11 October 2026

Status: **candidate verification in progress**

## Feature and safety gates

- [x] SQLite execution is explicit, multiset-only and does not change canonical equality or deterministic evidence ordering.
- [x] Direct CLI and suite-v2 workflows record execution provenance and recursively verifiable results.
- [x] Database pages are bounded by `max_temp_bytes`; invalid limits, disk-full equivalents, parse failures and distinct-row overflow fail closed.
- [x] Success, handled failure and Ctrl-C close and remove private spill state; suite workers contain spill state within private staging or the explicit workspace.
- [x] Summary output publishes no row values, while raw evidence remains bounded by the existing sample limit.
- [x] A synthetic backfill suite demonstrates aggregate conservation followed by exact disk-backed row occurrence comparison.

## Candidate evidence

- [x] 199 local tests passed after the review fixes on arm64 macOS; six optional Parquet tests were skipped where Polars was absent.
- [x] The 10k/100k Python 3.12 benchmark produced identical expected counts for both engines. At 100k rows, median process peak RSS fell from about 263 MiB to 34 MiB while median runtime rose from 5.44s to 16.55s and SQLite used 33.1 MiB.
- [x] Pre-review GitHub Actions run [38152718904](https://github.com/raghavkandpal/parison/actions/runs/38152718904) passed on Linux Python 3.11–3.14, macOS and Windows.
- [ ] Pass the exact versioned candidate through Linux Python 3.11–3.14, macOS and Windows, including cross-platform installed-wheel spill benchmarks.

## Publication

- [ ] Merge the reviewed candidate to `main`, tag `0.14.0`, and publish wheel, source archive and checksums.
- [ ] Download immutable release assets, verify checksums, install the wheel cleanly and rerun the backfill suite.
- [ ] Mark 0.14 released in the README and documentation index.

PyPI publication remains intentionally deferred.
