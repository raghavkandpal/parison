# Parison 0.12 engineering checkpoint

Date: 11 October 2026

Status: **release candidate verified**

## Implemented

- `run-suite --jobs N` accepts an explicit bound from 1 through 16; 1 remains the default.
- Concurrent execution uses standard-library spawned worker processes for consistent startup semantics across operating systems.
- Each worker receives one resolved case and publishes only its ordinary child bundle.
- The parent restores selected plan order before outcome reduction and atomic suite publication.
- Selection, external shard assignment, per-case limits, policy locks, child verification, and result schemas are unchanged.
- Suite-v2 workspaces resolve reusable children before admission, then checkpoint newly published worker results in the parent.
- Unexpected worker-future failures become generic summary-safe ERROR children; unrelated cases continue and exception text is not disclosed.
- Parent staging cleanup now covers interruption as well as ordinary exceptions.
- Parent SIGINT stops admission and bounds active-worker shutdown to two pool-wide two-second phases. It never publishes the requested output; completed workspace children are verified and checkpointed for resume, while incomplete children and scratch are removed.
- The checked-in GitHub Actions reference includes both a two-worker local suite and the released two-shard external workflow.

## Verification so far

- 184 local tests pass on arm64 macOS; optional Parquet tests are skipped when Polars is absent.
- Tests cover the CLI job bound, mixed PASS/FAIL equivalence, plan-order restoration, recursive verification, concurrent resume without checkpoint rewriting, generic worker-failure evidence, real abrupt process death, bounded interruption, forced kill of workers that ignore termination, no post-interrupt admission, scratch cleanup, and unchanged sequential interruption behavior.
- The existing 0.11 sharding, assembly, resume, reporting, examples, schemas, and benchmark tests pass unchanged.
- GitHub Actions run [38039584289](https://github.com/raghavkandpal/parison/actions/runs/38039584289) passed from commit `ec004868e4e500771ce79b75b582c6e36b611e70`: Linux Python 3.11–3.14 and the macOS and Windows platform-smoke jobs were all green.
- The latest checkpoint run [38058990764](https://github.com/raghavkandpal/parison/actions/runs/38058990764) also passed from commit `1a858e2eae4d8bcbec6ea8e968f6040ca575ccf5` after interruption recovery, mixed-mode performance/memory evidence, the user guide, and the bounded-termination design were added.
- Release-candidate run [38127624460](https://github.com/raghavkandpal/parison/actions/runs/38127624460) passed from commit `c925f9d376ca0ca925d832afb5970c321b5fba0f`: Linux Python 3.11–3.14 plus macOS and Windows all passed the 184-test suite, including bounded termination and forced-kill coverage.
- A locally built universal wheel installed into an empty Python 3.12 environment without the source checkout on `PYTHONPATH`. Its installed `parison` command ran the checked-in three-mode suite with `--jobs 2`, published three PASS children, and recursively verified the suite-v2 bundle. The release-preparation commit advances the package version to 0.12.0.

## First measurement

The checked-in 10-, 25-, and 100-case tiny-fixture measurement verifies equivalent outcomes and bundles for jobs 1, 2, and 4. Concurrency is slower throughout this profile because process startup dominates:

| Cases | Jobs 1 | Jobs 2 | Jobs 4 |
| ---: | ---: | ---: | ---: |
| 10 | 0.019455 s | 0.123636 s | 0.130587 s |
| 25 | 0.044721 s | 0.136280 s | 0.138427 s |
| 100 | 0.166075 s | 0.211975 s | 0.196269 s |

These numbers establish overhead, not throughput. They justify retaining jobs 1 as the default. See [`benchmarks/results-2026-10-10-suite-concurrency.json`](../../benchmarks/results-2026-10-10-suite-concurrency.json).

A second measurement used nine CPU-heavy cases: three each of keyed, aggregate, and multiset comparison, with 100,000 rows per input. Every jobs 1/2/4 bundle recursively verified with the same ordered case outcomes.

| Jobs | Elapsed | Peak sampled process-tree RSS |
| ---: | ---: | ---: |
| 1 | 17.278 s | 276,512,768 bytes |
| 2 | 10.288 s | 599,621,632 bytes |
| 4 | 6.384 s | 1,054,425,088 bytes |

This profile demonstrates useful local throughput, unlike the tiny fixtures, and also shows why Parison does not choose a job count automatically: four workers used roughly 3.8 times the sampled process-tree memory of one. RSS was sampled from the parent and descendants approximately every 20 ms on Darwin, so it remains machine-specific evidence rather than a hard peak guarantee. See [`benchmarks/results-2026-10-10-suite-concurrency-mixed-100k.json`](../../benchmarks/results-2026-10-10-suite-concurrency-mixed-100k.json).

## Release gate result

All implementation gates are green. The versioned release commit, immutable artifacts, checksums and post-upload installation check remain release operations rather than product gates.

The implementation decision and acceptance evidence are recorded in [the bounded interruption design](93-bounded-interruption-design.md).

