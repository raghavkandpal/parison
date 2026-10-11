# Parison 0.12.0 release checklist

Date: 11 October 2026

Status: **candidate verified; publication pending**

## Feature and safety gates

- [x] `run-suite --jobs N` admits at most 1–16 spawned local workers and defaults to the released sequential path.
- [x] Concurrent and sequential runs preserve plan-ordered semantic results and recursively verifiable child evidence.
- [x] Ordinary worker errors and abrupt process death publish generic summary-safe ERROR evidence without exception values.
- [x] Interruption stops admission, bounds terminate/kill shutdown, removes incomplete scratch and never publishes a partial parent suite.
- [x] Verified completed workspace children remain reusable after interruption; terminated and waiting cases do not acquire checkpoints.
- [x] Tiny-fixture and mixed-mode 100,000-row measurements record both latency and process-tree memory cost.

## Candidate evidence

- [x] 184 local tests passed on arm64 macOS; six optional Parquet tests were skipped when Polars was absent.
- [x] GitHub Actions run [38127624460](https://github.com/raghavkandpal/parison/actions/runs/38127624460) passed on Linux Python 3.11–3.14, macOS and Windows from `c925f9d376ca0ca925d832afb5970c321b5fba0f`.
- [x] A clean Python 3.12 environment installed the candidate wheel outside the source tree, ran the checked-in keyed/aggregate/multiset suite with two workers, and recursively verified all three PASS children.

## Publication

- [ ] Merge the versioned candidate to `main` after final CI.
- [ ] Tag the merge commit `0.12.0`.
- [ ] Build the wheel and source archive from the tag and publish both with `SHA256SUMS.txt` on GitHub.
- [ ] Download the immutable release wheel, verify its checksum, install it in an empty environment, rerun the concurrent suite and verify the result.
- [ ] Mark 0.12 released in the README and documentation index.

PyPI publication remains intentionally deferred.
