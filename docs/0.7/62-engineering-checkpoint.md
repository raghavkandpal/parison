# Parison 0.7 engineering checkpoint

Date: 9 October 2026

## Implemented head

Aggregate-v1 now has one complete local workflow: explicit drafting, strict recipe v2 validation, policy explanation and fingerprinting, schema and record preflight, deterministic comparison, result v2, terminal and HTML summaries, atomic publication and bundle verification. Keyed-v1 behavior remains covered by the existing regression suite.

## Verified behavior

- Global and typed grouped `count`, `sum`, `min` and `max` execute through the existing local readers and trust boundaries.
- Integer sums use unbounded integers; scaled decimals use unbounded integer coefficients and are independent of row order.
- Group coverage is compared before common-group measures. Missing groups cannot be hidden by offsetting totals.
- Null groups and rejected null measures are inconclusive; ignored nulls conserve separately from contributing values.
- Empty global input produces one group, while empty grouped input produces none.
- Summary results contain no group keys, per-group counts, aggregate values or source values. Raw evidence is deterministic, bounded and labelled sensitive.
- Aggregate result and preflight artifacts validate against installed Draft 2020-12 schemas. ERROR and INTERRUPTED bundles preserve result v2 shape after recipe validation.
- `--max-groups` bounds grouped preflight and execution.

## Local verification

The current local suite passed 143 tests with six optional-dependency skips. The generated aggregate oracle also passed for global, 10-group and 1,000-group profiles.

The checked-in [aggregate measurement](../../benchmarks/results-2026-10-09-aggregate.json) records three fresh-process runs per 1,000-row profile on arm64 macOS with Python 3.12.5. Median elapsed times were 0.056 seconds global, 0.055 seconds low-cardinality and 0.075 seconds high-cardinality. Median Python allocation rose from roughly 1.1 MB global to 3.0 MB at 1,000 groups. These are engineering measurements, not supported scale claims.

CI now installs and prints every v1/v2 schema, runs aggregate preflight/compare/verify smoke commands, measures all three aggregate profiles, and retains the existing Python 3.11–3.14 plus macOS/Windows matrix. Remote CI results are not yet recorded here.

## Local archive rehearsal

A clean PEP 517 build produced `parison-0.7.0.dev0` wheel and source archives. Inspection confirmed that both contain recipe v2, preflight v2 and result v2 schemas. The wheel was installed without dependencies into a fresh Python 3.12 virtual environment; version discovery, aggregate record preflight, aggregate compare/verify and keyed compare/verify all passed.

Rehearsal checksums:

- wheel: `bb299a8833829b1c702c31e9a8e0217c9fc83f6a3871f1339a75967ddd64aab0`
- source archive: `3d2a6cbeb084ce2e7cf5fba278f1fdd8abd840eaa3cfa1a9d3635bd846783d5a`

These identify temporary development archives, not release assets. Final archives must be rebuilt after setting version `0.7.0` on the verified release commit.

## Remaining release gates

- obtain a green remote matrix for the current aggregate implementation;
- run optional Parquet aggregate fixtures in that matrix;
- build clean wheel and source archives and inspect their installed schemas;
- install the wheel in an empty environment and repeat keyed and aggregate smoke workflows;
- finalize version metadata, changelog and the 0.7.0 release checklist before tagging.
