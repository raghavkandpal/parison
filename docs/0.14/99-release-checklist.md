# Parison 0.14.0 release checklist

Date: 11 October 2026

Status: **released**

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
- [x] Exact candidate `52fc1ad` passed [GitHub Actions run 38153162904](https://github.com/raghavkandpal/parison/actions/runs/38153162904) on Linux Python 3.11–3.14, macOS and Windows, including cross-platform installed-wheel spill benchmarks.

## Publication

- [x] Pull request [#22](https://github.com/raghavkandpal/parison/pull/22) merged to `main` as `d1bde9774de5cfece8f14c99140d977efc95a866`; annotated tag `0.14.0` and the [GitHub release](https://github.com/raghavkandpal/parison/releases/tag/0.14.0) publish the wheel, source archive and checksums.
- [x] Downloaded archives matched their published checksums: wheel `061837e01d6ee6ef89d644e95ccb6c5f166d94016b21b76d852eef309d6076e7`; source archive `639c9b7f11e616a940fa640c6762ee747f3ee252501e063288e8e019b8eebce5`.
- [x] A clean Python 3.12 install from the downloaded wheel reported `parison 0.14.0`, ran the aggregate plus SQLite-multiset backfill suite to PASS and recursively verified the published bundle.
- [x] The README and documentation index mark 0.14 released.

PyPI publication remains intentionally deferred.
