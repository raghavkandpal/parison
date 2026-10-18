# Parison 1.7 engineering checkpoint

Date: 18 October 2026

Status: **released in 1.7.0**

## Delivered capability

- Aggregate-v1 comparisons can explicitly select the existing private SQLite
  spill engine in direct execution and suite-v2 cases.
- Parsed and normalized group state stays under the released aggregate
  semantics while a hard page ceiling bounds disposable local storage.
- Memory remains the default and semantic oracle. PASS, FAIL, INCONCLUSIVE,
  empty, raw and summary results match after removing only the three documented
  operational fields.
- Controlled failures retain engine and temporary-limit attribution in
  verifiable suite child evidence. Row, group and storage ceilings, invalid
  parents, database-full errors, normal failure and interruption cleanup are
  qualified.
- Deterministic low- and high-cardinality benchmark profiles preserve the
  historical keyed and multiset benchmark interface.

## Qualification

- `make check` passes 363 tests with 11 expected optional-Polars skips.
- Exact implementation checkpoint
  `74a87f48564190f6637a37682dcd55790904bc21` passed
  [built-wheel CI run 39140670513](https://github.com/raghavkandpal/parison/actions/runs/39140670513)
  on Python 3.11--3.14, Linux, macOS and Windows; the separate
  [quality run 39140670525](https://github.com/raghavkandpal/parison/actions/runs/39140670525)
  also passed.
- A clean archive of that checkpoint produced:
  - wheel SHA-256:
    `896d64011813758fccdda5252b91259bc14c3dd669df71eb24d30f7939ff5738`;
  - source SHA-256:
    `913f97ccf0ff6f89cc17fb7b4278dfaa7c4ef72b3a8a9f16044ae7e8abe796e6`.
- A fresh Python 3.14 environment installed the wheel, ran a 1,000-group
  SQLite aggregate comparison, verified the published bundle and inspected a
  PASS result with 2,000 exact measures.
- Independent Standards and Spec reviews found no remaining blockers. The
  exact matrix then caught a benchmark-directory compatibility regression;
  the shared naming rule was corrected with regression coverage before this
  checkpoint.

## Machine-specific benchmark evidence

The recorded Apple arm64/Python 3.12 measurements are engineering evidence,
not capacity claims. At 10,000 rows and 10,000 groups, the SQLite engine used
about 1.57 MB peak traced Python memory and 6.36 MB temporary storage versus
about 19.85 MB peak traced Python memory for the memory engine. The SQLite
median was about 3.97 seconds versus 0.76 seconds in memory. The 17-group case
showed similar traced Python memory for both engines and only 16 KiB of
temporary storage. Full measurements and exact accuracy oracles are in
`benchmarks/results-2026-10-18-aggregate-sqlite.json`.

## Preserved boundaries

SQLite selection is explicit operational policy. No automatic engine choice,
resume database, remote service, new measure, repair or truth claim is added.
Recipe-v2, result-v2, aggregate-v1 semantics, policy fingerprints, canonical
values, CLI JSON, bundle readers and exit codes remain unchanged.

## Publication

[Pull request #48](https://github.com/raghavkandpal/parison/pull/48) merged as
`5da6e08dc97c4bdef3f57c6b71a272b42d7ea171`. Exact-merge test and quality CI
passed, and the annotated `1.7.0` tag identifies that commit. The
[GitHub release](https://github.com/raghavkandpal/parison/releases/tag/1.7.0)
publishes the clean-merge wheel, source archive and checksums. Re-downloaded
assets matched their hashes and the public wheel completed the 1,000-group
SQLite aggregate smoke in a fresh Python 3.14 environment.
