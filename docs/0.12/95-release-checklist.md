# Parison 0.12.0 release checklist

Date: 11 October 2026

Status: **released**

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

- [x] Merged release pull request [#18](https://github.com/raghavkandpal/parison/pull/18) to `main` at `c96ee7027ac0750200aedf974738056abda40f56` after all checks passed.
- [x] Tagged the merge commit `0.12.0`.
- [x] Published the wheel, source archive and `SHA256SUMS.txt` on the [GitHub release](https://github.com/raghavkandpal/parison/releases/tag/0.12.0).
- [x] Downloaded both immutable archives, verified their checksums, installed the wheel in an empty Python 3.12 environment, confirmed `parison 0.12.0`, reran the concurrent three-mode suite and recursively verified the PASS bundle.
- [x] Marked 0.12 released in the README and documentation index.

PyPI publication remains intentionally deferred.
