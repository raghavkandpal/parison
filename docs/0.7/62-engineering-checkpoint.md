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

CI installs and prints every v1/v2 schema, runs aggregate preflight/compare/verify smoke commands, measures all three aggregate profiles, and retains the existing Python 3.11–3.14 plus macOS/Windows matrix. All six jobs passed from commit `341a930` in [run 37895465310](https://github.com/raghavkandpal/parison/actions/runs/37895465310).

## Local archive rehearsal

A clean PEP 517 build produced `parison-0.7.0.dev0` wheel and source archives. Inspection confirmed that both contain recipe v2, preflight v2 and result v2 schemas. The wheel was installed without dependencies into a fresh Python 3.12 virtual environment; version discovery, aggregate record preflight, aggregate compare/verify and keyed compare/verify all passed.

Rehearsal checksums:

- wheel: `bb299a8833829b1c702c31e9a8e0217c9fc83f6a3871f1339a75967ddd64aab0`
- source archive: `3d2a6cbeb084ce2e7cf5fba278f1fdd8abd840eaa3cfa1a9d3635bd846783d5a`

These identify temporary development archives, not release assets. Final archives must be rebuilt after setting version `0.7.0` on the verified release commit.

## Published release

- Pull request [#13](https://github.com/raghavkandpal/parison/pull/13) merged the verified release candidate as commit `216784530e8dfb1155a89ee5f1fe0433b39fc2dc`.
- All six post-merge jobs passed in [run 37895940636](https://github.com/raghavkandpal/parison/actions/runs/37895940636).
- Tag `0.7.0` points to the verified merge commit and the [0.7.0 GitHub prerelease](https://github.com/raghavkandpal/parison/releases/tag/0.7.0) contains the wheel, source archive and `SHA256SUMS.txt`.
- The final wheel SHA-256 is `385966bf7db923bc05ecdf57c14174df7f85409d8cc1bf56835436dd26032e63`; the source archive SHA-256 is `77993fb77e1e097048167be87298f380402cc3118952aab183620ff0bc114202`.
- Downloaded assets passed checksum verification. The downloaded wheel, installed with Polars 1.44.2 in a fresh Python 3.12 environment, passed version discovery plus keyed and aggregate compare/verify workflows.
