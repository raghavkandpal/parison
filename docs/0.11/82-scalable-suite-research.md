# Parison 0.11 scalable-suite research

Date: 10 October 2026

Status: **recommended feature-rich slice**

## Recommendation

Make 0.11 the **scalable suite execution and CI exchange** release.

Parison 0.10 established a trustworthy migration-level unit: an ordered suite of ordinary keyed, aggregate and multiset comparisons, published as one atomic and recursively verifiable bundle. The next release should make that unit practical when a migration has dozens of outputs or must run inside a CI matrix:

- discover and select cases without editing the reviewed plan;
- partition a reviewed plan into deterministic shards;
- execute each shard independently into a portable partial suite bundle;
- assemble complete, non-overlapping shard bundles into one ordinary full suite bundle;
- resume local work by reusing only verified, still-current child bundles;
- apply explicit per-case resource limits; and
- render summary-safe Markdown and JUnit-style CI reports from verified bundles.

This is a broad slice, but it has one product story: **run a large reviewed comparison plan efficiently, move its safe proof units through CI, and recover from interruption without weakening what PASS means**.

Do not add a fourth comparison mode, remote data connector, hosted coordinator or in-process scheduler. CI systems already provide bounded parallel jobs, cancellation and artifact transport. GitHub Actions, for example, has matrix `max-parallel`, matrix-wide `fail-fast`, and per-job `continue-on-error` controls ([GitHub workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)). Parison should own deterministic domain partitioning, integrity and assembly, not reproduce a general workflow engine.

## Why this is the right next layer

The released suite-v1 contract deliberately stops at 100 sequential cases and defers parallelism, retries, resume, discovery and per-case limits ([0.10 suite contract](../0.10/78-suite-contract.md), [0.10 engineering checkpoint](../0.10/81-engineering-checkpoint.md)). That was the correct boundary for proving parent/child integrity. It also exposes the next real bottlenecks:

1. A user cannot cheaply answer “which cases will this job run?” without reading the plan.
2. CI cannot split one reviewed plan across workers while retaining a single Parison proof boundary.
3. An interruption discards completed work from the final bundle.
4. One suite-wide resource configuration is a poor fit when a small dimension and a wide fact output coexist.
5. CI logs contain the result, but there is no purpose-built, summary-safe test report.

These are suite lifecycle problems, not comparison semantics problems. Solving them above ordinary child bundles preserves the most valuable 0.10 property: every child remains an independently verifiable result under its existing recipe and result schema.

## Evidence from adjacent tools and standards

### Let the CI runner schedule; let Parison prove coverage

GitHub Actions already exposes deterministic matrix inputs, bounded parallelism and fail-fast behavior. A Parison shard can therefore be an ordinary matrix job, while Parison defines exactly which plan cases belong to each shard and later proves that the collected shards cover the plan exactly once ([GitHub workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)).

GitHub's v4 workflow artifacts are immutable, expose a SHA-256 digest on upload, and validate the digest on download ([GitHub artifact documentation](https://docs.github.com/en/enterprise-cloud@latest/actions/tutorials/store-and-share-data)). This supports portable shard transport, but it does not replace Parison verification: the workflow digest identifies the transported archive, while the Parison manifests bind suite metadata and every child file.

This separation also keeps the feature useful outside GitHub. Any runner that can invoke commands and move directories can execute shards and pass them to `assemble-suite`.

### Keep observed facts separate from orchestration state

Deequ's documented architecture separates analyzers that compute metrics from checks that evaluate them, and its verification result retains the generated metrics alongside constraint results ([Deequ key concepts](https://github.com/awslabs/deequ/blob/master/docs/key-concepts.md), [VerificationSuite source](https://github.com/awslabs/deequ/blob/master/src/main/scala/com/amazon/deequ/VerificationSuite.scala)). Parison should preserve the analogous boundary: a keyed, aggregate or multiset child result remains the observed comparison fact; selection, shard identity and reuse belong to the suite layer.

This avoids reinterpreting child `PASS`, `FAIL`, `INCONCLUSIVE`, `ERROR` or `INTERRUPTED` outcomes merely because a case ran in a shard or was reused.

### CI presentation should be derived and bounded

GitHub job summaries accept GitHub-flavored Markdown through `GITHUB_STEP_SUMMARY`, cap a step summary at 1 MiB, and present the result on the workflow-run page ([GitHub workflow commands](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/workflow-commands-for-github-actions#adding-a-job-summary)). Pytest likewise emits “JUnit XML style” report files for CI consumers ([pytest documentation](https://docs.pytest.org/en/stable/how-to/output.html#creating-junitxml-format-files)).

Parison should generate these as bounded projections from an already verified suite bundle. They must never become authoritative evidence, include raw discrepancy samples or be covered by the immutable suite manifest. The verified JSON and manifests remain canonical.

### Avoid an internal process scheduler in 0.11

Python's `ProcessPoolExecutor` can bypass the GIL, but submitted values must be picklable, `__main__` must be importable by workers, and worker behavior has platform-specific constraints ([Python `concurrent.futures`](https://docs.python.org/3/library/concurrent.futures.html#processpoolexecutor)). Thread pools avoid process serialization but cannot safely stop an already running comparison; Python's documentation also warns about deadlocks and shutdown behavior for thread executors ([Python `ThreadPoolExecutor`](https://docs.python.org/3/library/concurrent.futures.html#threadpoolexecutor)).

Parison already promises cross-platform interruption and deterministic bundle publication. Shipping an internal `--jobs` implementation before solving cancellation, multiplied memory bounds and worker failure would trade a known sequential proof for fragile convenience. Deterministic external shards deliver parallel throughput with a much clearer failure boundary.

## Proposed suite-v2 contract

Preserve suite-v1 exactly. Introduce `suite_version: 2` only for the new metadata; do not silently widen v1.

### Plan additions

Each case keeps the v1 fields and may additionally declare:

- `tags`: a sorted, unique list of portable identifiers used only for selection;
- `limits`: explicit overrides for `max_input_bytes`, `max_decoded_bytes`, `max_rows`, and the mode-specific `max_groups` or `max_distinct_rows`;
- `description`: bounded human context for listings and reports, never interpreted as policy.

The plan may declare `defaults.limits`. Effective per-case limits are the defaults overlaid by the case overrides and are included in the effective suite and suite fingerprint. Recipe policy remains authoritative for comparison meaning; suite limits only bound execution.

Do not add globs, recursive discovery, environment interpolation, arbitrary commands, inline recipes, implicit tags from paths or conditional expressions. A reviewed plan must enumerate its proof scope.

### Stable plan identity

Define `suite_policy_sha256` over a canonical effective plan containing:

- ordered case IDs;
- resolved recipe, baseline and candidate references represented by portable plan-relative strings;
- every expected recipe-policy fingerprint;
- tags and effective resource limits; and
- the selection and sharding contract version.

Absolute host paths must not enter this fingerprint. The digest identifies the reviewed plan, not the current input bytes. Each child result already records input digests; reuse validates both identities.

### Listing and selection

Add:

```text
parison list-suite PLAN [--case ID ...] [--tag TAG ...] [--json]
```

Selection rules must be small and conjunctive:

- repeated `--case` values form an explicit union;
- repeated `--tag` values select cases containing every requested tag;
- when both are present, a case must satisfy both filters;
- zero selected cases is an error; and
- output order is always plan order.

`list-suite --json` reports the plan fingerprint, total and selected counts, ordered IDs, modes, tags and effective limits. It performs the same reference and policy-lock validation as `validate-suite`, without scanning input records.

### Deterministic shards

Add `--shard-index I --shard-count N` to `list-suite` and `run-suite`, with zero-based `I`, positive bounded `N`, and `I < N`.

After ordinary case/tag selection, selected case at zero-based position `p` belongs to shard `p mod N`. This rule is intentionally plain, portable and independent of timing, file size and machine count. It balances case count, not predicted runtime; a future weighted scheme would require a new named sharding contract.

Every partial bundle records:

- full plan fingerprint and declared case count;
- selection specification and selected ordered IDs;
- shard contract, index and count;
- completed IDs and outcome counts; and
- ordinary child bundle locations and digests.

A partial bundle can be complete for its shard but **cannot claim that the full suite passed**. Its top-level kind and terminal language must say `suite-shard`, not `suite`.

### Assembly

Add:

```text
parison assemble-suite --plan PLAN --input SHARD ... --output DIRECTORY
```

Assembly:

1. validates the current plan and expected plan fingerprint;
2. recursively verifies every shard and child;
3. requires the same selection specification and shard count;
4. rejects duplicate case IDs, duplicate shard indexes, missing indexes, extra cases and gaps;
5. requires exact selected-case coverage in plan order;
6. copies verified child bundles into a fresh staging directory rather than linking mutable paths;
7. recomputes child manifest digests and suite outcome; and
8. atomically publishes an ordinary full suite bundle that existing `verify` and `inspect` can read.

Assembly must not trust a shard's claimed aggregate counts when the child bundles can be checked. It is a structural operation: it never opens source inputs or reruns comparisons.

### Resumable local execution

Add an explicit workspace distinct from the immutable destination:

```text
parison run-suite --plan PLAN --workspace WORK --output DIRECTORY
parison run-suite --plan PLAN --workspace WORK --output DIRECTORY --resume
```

The workspace is not a valid result bundle. After each child completes, Parison atomically writes a small checkpoint that binds case ID, plan fingerprint, effective limits, engine version, recipe-policy fingerprint, input digests and verified child-manifest digest. Python documents that a successful same-filesystem rename is atomic; cross-filesystem rename may fail, so the checkpoint temporary file must be created beside its destination ([Python `os.replace`](https://docs.python.org/3/library/os.html#os.replace)).

On resume, a child is reusable only when:

- its bundle verifies recursively;
- its case ID and policy fingerprint match the current effective plan;
- its recorded resource limits match;
- the installed Parison version is reuse-compatible under an explicit contract; and
- freshly computed source digests equal the child result's digests.

Digesting current inputs means resume is not a zero-I/O cache. It saves parsing, indexing, comparison and report generation while refusing stale evidence. A mismatch reruns that case; it never silently adopts the old result. Final publication copies verified children into a new staging tree and retains the 0.10 no-overwrite rule.

The implementation may use atomically replaced JSON checkpoints. SQLite is unnecessary at this scale; Python's SQLite transaction API is capable of commit and rollback, but introducing a mutable database would add schema and recovery behavior without solving child-bundle validity ([Python `sqlite3`](https://docs.python.org/3/library/sqlite3.html#transaction-control)).

### CI projections

Add derived exports from verified ordinary suite or shard bundles:

```text
parison report-ci BUNDLE --format markdown --output FILE
parison report-ci BUNDLE --format junit --output FILE
```

The Markdown projection contains bounded outcome counts, failed/non-passing case IDs and safe links or relative paths. The JUnit-style projection maps one case to one testcase and records the Parison outcome explicitly as a property; `FAIL`, `INCONCLUSIVE`, `ERROR` and `INTERRUPTED` must not collapse into indistinguishable text. Because JUnit XML dialects vary, document the exact emitted subset and test it against at least GitHub's common report consumers rather than claiming universal JUnit compatibility.

Both formats are summary-only, deterministic, atomic, size-bounded and derived after verification. Raw evidence remains available only through an explicitly targeted raw child bundle.

## Outcome and completeness rules

Keep the released precedence for every complete selected scope:

```text
INTERRUPTED > ERROR > INCONCLUSIVE > FAIL > PASS
```

Add scope language rather than weakening the word PASS:

- **full suite PASS**: every declared plan case completed and passed;
- **selection PASS**: every explicitly selected case completed and passed, with the omitted count visible;
- **shard PASS**: every case assigned to that shard completed and passed, never a full-suite assertion;
- **assembled suite PASS**: every selected case is present exactly once across verified shards and passed.

Machine-readable results need separate `scope_complete` and `execution_complete` booleans. A shard can be execution-complete and scope-incomplete relative to the full plan. Human reports must lead with the scope, for example “PASS for shard 2/4: 18 of 73 plan cases,” not simply “PASS.”

## Security and privacy requirements

- Treat plan descriptions, IDs and tags as untrusted text in HTML, Markdown and XML; escape them for each output format.
- Reject path traversal, symlinks and shard contents outside the verified bundle boundary.
- Never execute commands found in plans or imported bundles.
- Never merge raw evidence into a parent report or CI projection.
- Recompute digests instead of trusting filenames, checkpoint claims or transport-level artifact digests.
- Bound plan cases, tag count and length, shard count, report size and input bundle count before expensive work.
- Do not call shard assembly an attestation of authorship. Existing SHA-256 manifests establish integrity relative to supplied manifests, not identity or approval.

## Ordered roadmap

### 1. Freeze scope and identity

- Write normative suite-v2, selection, sharding and assembly contracts.
- Define canonical effective-plan encoding and `suite_policy_sha256` golden vectors.
- Add adversarial examples for empty selection, duplicate tags, changed limits and relocated plan trees.

Acceptance: two independent implementations choose the same ordered cases and fingerprint for every golden plan.

### 2. Listing, tags and resource limits

- Add suite-v2 schema and strict loader while retaining suite-v1 behavior.
- Implement `list-suite` text/JSON output and shared selector evaluation.
- Thread effective per-case limits through existing comparison calls and record them in parent metadata.

Acceptance: listing and execution share one selector implementation; no listed case can execute with different effective limits.

### 3. Shard bundles

- Implement the fixed modulo sharding contract.
- Publish atomic `suite-shard` bundles with distinct result and manifest kinds.
- Extend `verify` and `inspect` with summary-safe shard dispatch.

Acceptance: union of all shards is exact and disjoint for generated plans across reorderings, filters and shard counts.

### 4. Verified assembly

- Implement recursive verification, exact-coverage reconciliation and atomic full-suite publication.
- Preserve plan order regardless of shard arrival or completion order.
- Add tampering, duplicate, gap, mixed-plan, mixed-selection and interrupted-shard tests.

Acceptance: assembly cannot publish when any selected case is absent, duplicated, stale or bound to another plan.

### 5. Resume workspace

- Add atomic checkpoints and conservative child reuse.
- Recompute input digests and verify child bundles before reuse.
- Specify version compatibility as exact Parison version initially; widen only with evidence.
- Exercise Ctrl-C and injected failure at every checkpoint/publication boundary.

Acceptance: resumed and clean runs produce semantically identical final bundles apart from documented volatile runtime fields; stale input or policy changes force rerun.

### 6. CI reports and reference workflow

- Add bounded Markdown and documented JUnit-style projections.
- Check in a GitHub Actions matrix example that runs shards, uploads immutable artifacts, downloads them and assembles the final suite.
- Test shell quoting and paths on Linux, macOS and Windows.

Acceptance: the reference workflow surfaces non-passing case IDs without exposing raw values, and its assembled bundle verifies after artifact transport.

### 7. Release evidence

- Benchmark 10, 25 and 100-case suites for sequential, sharded and resumed execution.
- Measure orchestration overhead separately from comparison time and artifact transport.
- Run Python 3.11–3.14 plus macOS and Windows installed-wheel workflows.
- Repeat the existing mixed-mode suite to prove suite-v1 and ordinary bundle compatibility.

Acceptance: publish measured speedup and overhead without claiming that case-count balancing guarantees equal shard duration.

## Features to defer beyond 0.11

- in-process thread/process pools and automatic worker sizing;
- dynamic work stealing or runtime-weighted sharding;
- retries that obscure deterministic first outcomes;
- network/object-store transport built into Parison;
- remote input connectors or a hosted coordinator;
- cross-run trend databases and anomaly detection;
- fuzzy matching, tolerant row assignment or automatic deduplication;
- arbitrary selector expressions, globs or recursive case discovery;
- hard links or symlinks as a substitute for copying verified children; and
- signing or organizational approval claims.

## Stop conditions

Pause or narrow the release if implementation would:

- let a partial selection or shard present itself as a full-suite PASS;
- reuse a child without verifying its bundle and current input digests;
- make results depend on shard completion order;
- modify keyed, aggregate or multiset comparison semantics;
- require GitHub Actions specifically rather than any file-moving runner;
- expose raw child evidence in parent or CI summaries;
- overwrite an existing result destination; or
- add an internal parallel scheduler before cancellation and aggregate resource bounds are proven cross-platform.

## Bottom line

Parison has enough comparison breadth for the next release. Its larger opportunity is to make a reviewed, mixed-mode suite operationally credible: inspectable before execution, divisible without ambiguity, portable through CI, exactly reassembled, and safely resumable. That is feature-rich user value built from the product's strongest existing primitives rather than a collection of unrelated flags.
