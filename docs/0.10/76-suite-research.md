# Parison 0.10 comparison-suite research

Date: 9 October 2026

Status: **recommended feature slice**

## Recommendation

Make 0.10 a **local comparison-suite** release: a versioned JSON plan runs an ordered set of existing keyed, aggregate and multiset comparisons, then publishes one deterministic, verifiable suite bundle that links every case to its ordinary Parison bundle.

This is broader than another export flag but remains feasible without a runtime dependency, hosted service or new comparison engine. It addresses a migration-level job—proving several related outputs under reviewed policies—while reusing the released recipe loaders, comparison engines, atomic bundle publication, verification and safe inspection paths.

The suite must orchestrate existing comparisons; it must not introduce a fourth proof mode or change PASS, FAIL, INCONCLUSIVE, ERROR or INTERRUPTED at the case level.

## Why this slice fits Parison now

Parison's product thesis targets recurring migration and refactor comparisons, but the current CLI accepts one recipe, baseline and candidate per invocation ([product thesis](../0.1/01-product-thesis.md), [current CLI](../../src/parison/cli.py)). Real migration evidence commonly spans several tables or outputs. Today, users must build their own loop, choose output names, retain every exit code and assemble the overall result. That duplicates orchestration while losing the single integrity boundary Parison already provides for one run.

The released primitives are sufficient:

- recipes already version policy separately for keyed-v1, aggregate-v1 and multiset-v1;
- every case can already publish an immutable run directory and verify it against a manifest;
- `inspect` exposes summary-safe metadata across all three result schemas; and
- comparison errors and interruptions already have canonical outcomes and bundle representations.

The 0.9 roadmap explicitly defers servers, remote inputs and interactive UI, so a local plan and static report stay inside the established product boundary ([0.9 roadmap](../0.9/71-roadmap.md)). A suite also complements CI rather than becoming a scheduler. GitHub Actions already supplies matrices, fail-fast controls and bounded parallelism; Parison's job should be deterministic domain aggregation and portable evidence, not runner orchestration ([GitHub Actions matrix documentation](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/run-job-variations)).

## Proposed suite-v1 contract

### Plan

Add a strict Draft 2020-12 `suite-v1` JSON schema and expose it through the installed schema command. Draft 2020-12 provides the object, array and strict unevaluated-property vocabulary needed for a closed declarative plan ([JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)).

The plan should contain:

```json
{
  "suite_version": 1,
  "cases": [
    {
      "id": "orders",
      "recipe": "recipes/orders.json",
      "baseline": "baseline/orders.csv",
      "candidate": "candidate/orders.parquet",
      "expected_policy_sha256": "..."
    }
  ]
}
```

`cases` is an ordered, nonempty array with a conservative maximum such as 100. JSON arrays are ordered while JSON objects are unordered, so case execution and report order must come from this array, never object-member or filesystem order ([RFC 8259](https://www.rfc-editor.org/rfc/rfc8259)). Each `id` is unique and restricted to a portable filename-safe subset such as lowercase ASCII letters, digits and hyphens. The case owns only references and an optional policy lock; its recipe continues to own comparison mode, scope, tolerance, normalization and sensitivity.

Resolve relative references against the suite file's directory. Normalize them before use and record value-free source metadata in the case bundle, as Parison does today. Python's supported `Path.resolve()` behavior eliminates `..` components and resolves symlinks, which gives the implementation one explicit normalization point ([Python `pathlib`](https://docs.python.org/3.11/library/pathlib.html#pathlib.Path.resolve)). Resolution is not confinement: suite-v1 should accept explicit paths outside the suite directory because the existing CLI does, while continuing to reject unsafe source types through the existing readers.

Do not add globbing, recursive discovery, environment interpolation, inline recipes, per-case semantic overrides or arbitrary commands. Those features make the plan less reviewable and expand the security boundary without improving comparison semantics.

### Execution

Add two user operations:

- `validate-suite PLAN` validates the suite and every referenced recipe, resolves paths and checks duplicate IDs without reading input records;
- `run-suite --plan PLAN --output DIRECTORY` executes cases sequentially in declared order and publishes the suite bundle.

Sequential execution is the correct v1 default. It bounds peak memory to one comparison, makes Ctrl-C and publication behavior straightforward, and produces deterministic progress without building a worker scheduler. External CI may still parallelize separate plans. A later version can add concurrency only after specifying resource sharing and deterministic cancellation.

Run every case after ordinary FAIL, INCONCLUSIVE or ERROR outcomes so a single invocation yields complete investigation coverage. Stop only on user interruption or a suite-level failure that prevents safe execution or publication. Do not add fail-fast in v1.

Resource limits remain explicit command arguments and apply independently to each case. Add a suite-level case-count limit, but no hidden aggregate byte or row claim: sources may overlap, and summing declared physical sizes is not a memory bound.

### Outcome reduction

Preserve each case outcome verbatim. Reduce the suite outcome with a documented precedence:

```text
INTERRUPTED > ERROR > INCONCLUSIVE > FAIL > PASS
```

`PASS` therefore means every declared case completed and passed. `FAIL` means every case reached a conclusive comparison and at least one found required differences. Higher-precedence outcomes prevent a partial or untrustworthy suite from being described as a completed failure comparison.

The suite result must also record `total_cases`, `completed_cases` and counts by outcome. A case entry records its ID, outcome, completeness, result schema version, comparison contract, policy fingerprint, child manifest digest and relative child-bundle location. It must not copy raw discrepancy samples or source values into the suite summary.

### Bundle and integrity

Publish one parent directory containing a suite result, effective suite plan, self-contained HTML summary, parent manifest and `cases/<id>/` ordinary child bundles. Keep child bundles byte-compatible with 0.9 so all existing inspection and evidence-export behavior remains available per case.

Introduce a distinct suite-manifest schema rather than silently broadening run manifest v1. The parent manifest should digest its top-level files and bind each case ID to the SHA-256 digest of the child's verified manifest. Suite verification recursively verifies every child bundle, recomputes those manifest digests and checks that child outcome, policy fingerprint and schema metadata agree with the suite result. As with existing bundles, this proves integrity relative to the supplied parent manifest, not authorship.

Stage the complete suite beside its destination and publish it with one same-filesystem rename. Python documents that `os.replace` may fail across filesystems, while `tempfile.mkdtemp(dir=...)` can create a race-free private staging directory in the chosen parent; together they support the existing atomic publication pattern ([Python `os.replace`](https://docs.python.org/3.11/library/os.html#os.replace), [Python `tempfile`](https://docs.python.org/3.11/library/tempfile.html#tempfile.mkdtemp)). Existing destinations remain no-overwrite errors.

Extend `verify` and `inspect` by manifest-kind dispatch rather than inventing parallel commands. Run-bundle behavior stays unchanged. Suite inspection returns only aggregate counts and per-case safe metadata. Raw evidence still requires an explicit `export-evidence` against a raw child bundle; the parent never creates a new disclosure path.

## Vertical implementation slice

1. Freeze suite-v1 plan, result and manifest contracts with PASS/FAIL/INCONCLUSIVE/ERROR/INTERRUPTED reduction examples.
2. Add strict installed schemas, plan loading, path resolution, unique-ID checks and `validate-suite`.
3. Extract a small internal case runner from the existing CLI path so `run-suite` invokes the same comparison and publication behavior without subprocesses.
4. Stage sequential child bundles, then publish the parent result, report and recursive integrity bindings atomically.
5. Dispatch `verify` and `inspect` across ordinary and suite bundles while preserving all 0.9 output contracts for ordinary runs.
6. Add a checked-in mixed-mode example with one keyed, one aggregate and one multiset case.
7. Test outcome precedence, continued execution, interruption, path resolution, duplicate IDs, policy-lock failure, raw/summary separation, tampered children, parent/child metadata disagreement and no-overwrite races.
8. Run installed-wheel smoke on Linux, macOS and Windows and record a release checkpoint.

This is a coherent release rather than a collection of flags: it adds a versioned input contract, orchestration path, result contract, portable report, recursive verification, safe inspection, example workflow and release evidence.

## Explicitly defer

- Parallel workers, retries, resume and incremental cache reuse.
- Cross-suite trend storage or comparison; that is temporal analysis, which the product thesis treats as a separate job.
- Glob or directory discovery, generated cases and parameter matrices.
- Per-case resource-limit overrides until the shared-limit contract is proven insufficient.
- A suite-wide raw evidence export, because combining samples would require new ordering, quota and privacy semantics.
- Remote inputs, hosted history, signing and authenticated provenance.

## Alternatives considered

### Spill-backed execution

Standard-library SQLite could eventually reduce memory pressure, and the repository has already identified it as an evidence-driven option. It is not the best 0.10 focus: a correct spill engine must preserve three different identity and aggregation contracts, deterministic evidence order, cancellation, mutation detection and cross-platform performance. The current research contains no measured user demand or benchmark showing that this complexity is the next product bottleneck ([tested support envelope](../0.1/13-tested-support-envelope.md), [0.8 roadmap](../0.8/65-roadmap.md)). Keep it as a separate scale project.

### Subset comparison or tolerant row assignment

Both change what PASS proves and need new semantic contracts. They should not be coupled to workflow expansion, and tolerant assignment in particular introduces ambiguity that the exact keyed and multiset modes intentionally avoid ([comparison semantics](../0.1/05-comparison-semantics.md), [0.9 roadmap](../0.9/71-roadmap.md)).

### CSV or JUnit export

Additional presentation formats are useful adapters but too narrow for a major slice. CSV also carries spreadsheet-formula handling obligations already called out by the security model ([security and data handling](../0.1/07-security-and-data-handling.md)). They can follow once a concrete consumer requires them.

## Go/no-go criteria

Proceed if a mixed three-case suite can be calculated by hand, produces the same child bundles as standalone runs, publishes atomically, verifies recursively, leaks no new values in summary mode and has invariant bytes under repeated execution apart from already-declared runtime metadata.

Narrow or stop if implementation requires changing any case result schema, reinterpreting a recipe, copying source data, retaining unfinished output as a valid bundle, adding a scheduler abstraction or weakening manifest path restrictions.
