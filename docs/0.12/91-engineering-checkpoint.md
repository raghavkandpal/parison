# Parison 0.12 engineering checkpoint

Date: 10 October 2026

Status: **development checkpoint; not release-complete**

## Implemented

- `run-suite --jobs N` accepts an explicit bound from 1 through 16; 1 remains the default.
- Concurrent execution uses standard-library spawned worker processes for consistent startup semantics across operating systems.
- Each worker receives one resolved case and publishes only its ordinary child bundle.
- The parent restores selected plan order before outcome reduction and atomic suite publication.
- Selection, external shard assignment, per-case limits, policy locks, child verification, and result schemas are unchanged.
- Suite-v2 workspaces resolve reusable children before admission, then checkpoint newly published worker results in the parent.
- Unexpected worker-future failures become generic summary-safe ERROR children; unrelated cases continue and exception text is not disclosed.
- Parent staging cleanup now covers interruption as well as ordinary exceptions.

## Verification so far

- 182 local tests pass on arm64 macOS with Python 3.12 and Polars 1.44.2.
- Tests cover the CLI job bound, mixed PASS/FAIL equivalence, plan-order restoration, recursive verification, concurrent resume without checkpoint rewriting, generic worker-failure evidence, real abrupt process death, and unchanged sequential interruption behavior.
- The existing 0.11 sharding, assembly, resume, reporting, examples, schemas, and benchmark tests pass unchanged.
- GitHub Actions run [38039584289](https://github.com/raghavkandpal/parison/actions/runs/38039584289) passed from commit `ec004868e4e500771ce79b75b582c6e36b611e70`: Linux Python 3.11–3.14 and the macOS and Windows platform-smoke jobs were all green.
- A locally built universal wheel installed into an empty Python 3.12 environment without the source checkout on `PYTHONPATH`. Its installed `parison` command ran the checked-in three-mode suite with `--jobs 2`, published three PASS children, and recursively verified the suite-v2 bundle. The package still reports 0.11.0 because the 0.12 version bump is intentionally a release-preparation step.

## First measurement

The checked-in 10-, 25-, and 100-case tiny-fixture measurement verifies equivalent outcomes and bundles for jobs 1, 2, and 4. Concurrency is slower throughout this profile because process startup dominates:

| Cases | Jobs 1 | Jobs 2 | Jobs 4 |
| ---: | ---: | ---: | ---: |
| 10 | 0.019455 s | 0.123636 s | 0.130587 s |
| 25 | 0.044721 s | 0.136280 s | 0.138427 s |
| 100 | 0.166075 s | 0.211975 s | 0.196269 s |

These numbers establish overhead, not throughput. They justify retaining jobs 1 as the default. See [`benchmarks/results-2026-10-10-suite-concurrency.json`](../../benchmarks/results-2026-10-10-suite-concurrency.json).

## Remaining release gates

1. Inject parent interruption during active concurrent work and prove bounded shutdown, staging cleanup, and safe workspace reuse on the next run.
2. Run representative CPU-heavy keyed, aggregate, and multiset suites; publish elapsed time and peak process-tree memory for jobs 1, 2, and 4, including negative results.
3. Add a checked-in concurrent suite example and update the user guide after the interruption contract is proven.

Do not call 0.12 release-complete until all three gates close.

