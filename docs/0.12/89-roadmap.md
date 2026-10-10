# Parison 0.12 roadmap

Date: 10 October 2026

Status: **planned**

## Focus: bounded local suite concurrency

Parison 0.12 will let one `run-suite` invocation execute independent cases concurrently while preserving the exact case results, deterministic suite result, conservative resume rules, and atomic publication guarantees released in 0.11.

This is one feature slice: **finish a reviewed local suite sooner without changing what any case or suite outcome means**.

## Release capabilities

1. **Explicit concurrency** — `run-suite --jobs N`, with `N` validated against a conservative fixed ceiling and `1` retaining the 0.11 path.
2. **Deterministic scheduling contract** — cases are admitted in plan order, each writes only to its assigned workspace, and final artifacts are always reduced in plan order.
3. **Bounded resource semantics** — existing limits remain per case; documentation states that peak resource use may approach `N` times one case. No automatic worker sizing claim.
4. **Cross-platform interruption** — Ctrl-C stops new admission, requests worker shutdown, records unfinished cases as interrupted, and never publishes a complete suite from partial execution.
5. **Concurrent resume** — verified current checkpoints may be reused before workers are admitted; stale cases rerun independently without shared mutable child state.
6. **Failure isolation** — one case's FAIL, INCONCLUSIVE, or ERROR does not cancel unrelated cases; worker crashes become explicit case ERROR evidence. No silent retry.
7. **Measured evidence** — compare `--jobs 1`, `2`, and `4` on representative suites, reporting elapsed time, result equivalence, interruption behavior, and observed peak memory without promising universal speedup.

## Interface and module shape

The CLI adds one option. The suite execution module owns scheduling behind its existing run interface; comparison modules remain unaware of concurrency.

```text
CLI -> suite execution -> isolated case workers -> ordinary child bundles
                       -> plan-ordered reduction -> atomic suite bundle
```

The seam is the ordinary case runner: one case specification enters and one child-bundle result returns. Scheduling, worker lifecycle, cancellation, and ordering stay inside the suite execution module. There is no public scheduler abstraction and no adapter interface with only one implementation.

## Ordered implementation

### 1. Freeze concurrency semantics

- Specify valid `--jobs` values, admission order, completion order, outcome reduction, interruption, worker crash handling, and workspace ownership.
- Add golden scenarios proving that `--jobs 1` and concurrent runs have equivalent semantic results.
- Document that per-case limits are not an aggregate memory sandbox.

Done when every terminal worker state has one deterministic suite representation and no completion-order detail can change result bytes other than already documented runtime metadata.

### 2. Extract one case-execution seam

- Reuse the current case runner for sequential and concurrent execution.
- Pass immutable case inputs to workers; return result metadata rather than mutating parent state.
- Keep bundle verification at the parent seam before reduction and publication.

Done when standalone, sequential-suite, and concurrent-suite paths produce ordinary child bundles accepted by the same verifier.

### 3. Add the bounded worker implementation

- Prefer the Python standard library and a process-based implementation for workload isolation and useful CPU parallelism.
- Admit at most `N` cases and use dedicated case/workspace paths.
- Collect completions independently, then restore declared plan order.
- Reject unsafe output/workspace overlap before starting workers.

Done when randomized worker delays and completion orders produce the same ordered suite semantics.

### 4. Make cancellation and crashes explicit

- Stop admitting cases on interruption.
- Request graceful worker shutdown, then terminate only within a documented bounded cleanup path.
- Convert unexpected worker exits into explicit ERROR case records without retrying them.
- Preserve resumable verified children while refusing to label a partial suite complete.

Done when injected interruption and worker-exit tests leave no complete-looking partial output, orphan publication directory, or corrupted reusable checkpoint.

### 5. Integrate resume, selection, and shards

- Exercise concurrency with case/tag selection and a single external shard.
- Resolve reusable checkpoints before worker admission.
- Prevent two workers from owning the same case path.
- Keep exact external shard assembly unchanged.

Done when clean and resumed concurrent executions are semantically equivalent and every changed input, policy, limit, or version reruns only the affected case.

### 6. Verify portability and performance

- Test Python 3.11–3.14 plus macOS and Windows process startup and interruption behavior.
- Benchmark mixed keyed, aggregate, and multiset suites with `--jobs 1`, `2`, and `4`.
- Record elapsed time, child-result equivalence, final-manifest verification, and peak memory.
- Update the GitHub Actions example with an optional local-concurrency job without replacing external sharding.

Done when the installed wheel passes the same suite under every supported platform and published measurements distinguish throughput gains from multiplied resource use.

## Compatibility commitments

- Existing commands and `--jobs 1` behavior remain compatible.
- Recipe, comparison-result, suite-plan, suite-result, and manifest schemas do not change merely to expose scheduling details.
- PASS, FAIL, INCONCLUSIVE, ERROR, and INTERRUPTED precedence remains unchanged.
- Child bundles remain ordinary independently verifiable Parison bundles.
- External sharding and assembly remain the recommended cross-machine mechanism.

## Explicit non-goals

- Automatic worker sizing, dynamic work stealing, runtime-weighted sharding, or distributed scheduling.
- Hidden retries, retry-until-pass, or fail-fast that discards available evidence.
- Aggregate memory guarantees beyond documented per-case limits and the explicit job bound.
- YAML recipes, remote connectors, hosted coordination/history, or an interactive UI.
- Fuzzy matching, automatic deduplication, data repair, or any new comparison mode.
- A general-purpose public executor or plugin interface.

## Release gates

0.12 is releasable only when:

1. semantic result content is equivalent across `--jobs 1`, `2`, and `4` for the same selected scope;
2. repeated randomized completion orders preserve plan-ordered output;
3. interruption and forced worker death cannot publish a complete-looking partial suite;
4. resume reuses only verified current children under concurrent admission;
5. the installed wheel passes Linux, macOS, and Windows smoke workflows;
6. benchmarks publish both elapsed time and memory cost, including cases where concurrency is slower; and
7. all 0.11 external sharding, assembly, verification, and reporting tests remain green unchanged.

