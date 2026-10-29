# Exact partitioned difference discovery contract

Date: 28 October 2026  
Status: frozen for 2.3 feature 3 implementation; not a release commitment

This is capability 3 in the [six-feature roadmap](246-six-feature-roadmap.md).
It compares two local CSV files under one reviewed keyed recipe. It does not
query a source or authorize migration cutover. Released comparison results,
recipes, bundles, CLI JSON and verification remain byte-compatible.

## Reviewed selection and limits

`partition-plan-v1` is strict JSON with exactly `partition_plan_version: 1`,
`ranges`, and `limits`. The recipe is supplied separately and must be a
released keyed recipe with one integer key, summary sensitivity, no column
mapping, projection, or excluded column. The two inputs must be regular,
non-symlink CSV files. Each side retains its recipe delimiter and null-token
rules. No plan field approves a recipe or changes its scope.

`ranges` is an array of 2–128 objects, each with exactly `upper`. Every
`upper` except the last is a strictly increasing JSON integer; the final
`upper` is `null`. Range zero starts at negative infinity. Each later range
starts at its predecessor's upper bound. Each finite upper is exclusive, so
the ranges cover the entire integer domain without a gap or overlap. The
operator reviews these bounds; generated suggestions are never approval.
The private plan and receipt may reveal bounds; summary-safe output may not.

`limits` contains positive integer `max_input_bytes` (at most 1 GiB),
`max_rows_per_input` (at most 5,000,000), `max_rows_per_partition_side` (at
most 1,000,000), `max_staged_bytes` (at most 2 GiB), and
`max_partition_bytes` (at most 1 GiB, per side).
The producer rejects a breached limit and deletes all sensitive staging.
The per-partition row and byte ceilings are essential under skew. A run is
bounded by these declared caps, not by the mere existence of partitions.

## Exact execution and outcome

Before routing, bind each input's SHA-256 digest and size. Route each parsed
row exactly once by its **normalized** integer key using the released CSV and
policy parser. A null key has no integer range and fails closed with an
explicit unsupported-input error; invalid keys retain the released parse
error. Duplicate normalized keys must remain in the same range and retain
the released duplicate-key INCONCLUSIVE rule. Preserve every raw row field in
private temporary CSV for the exact comparison path. Rehash each source after
routing; changed input fails. Count source rows and routed rows per side and
require equality.

For every range, run the released exact keyed classification under the
original column policies, including zero-row ranges. An internal allowance
for empty *ranges* is mechanical and never changes `scope.expected_empty`.
Apply the original empty-side rule once to the total declared scope. Aggregate
all released count and field-classification fields. Full-scope PASS requires
every range completed, no identity problems, global nonempty eligibility,
and zero required differences. Any missing, failed, capped or interrupted
range makes the run incomplete; it cannot produce PASS. A failing exact
comparison still completes and reports FAIL.

No probabilistic hash filter can turn a partition into PASS. A filter may
only choose the order of exact work. Feature 3 does not expose raw samples.

## Versioned local evidence

Publish a private no-overwrite directory atomically after all ranges finish.
It contains exactly `plan.json`, `receipt.json`, `summary.json` and
`manifest.json`. The canonical private receipt records the version, original
recipe digest, both source digests and sizes, route totals, every range's
bounds, side row/byte/digest totals, exact count and field-classification
totals, completion, and final outcome. The manifest binds canonical bytes of
the other three files. Temporary partition files are removed after the
receipt is committed; the receipt is an integrity and reproducibility record,
not preserved raw input. The summary exposes only version, complete, outcome,
aggregate counts, policy and input digest identifiers, and bounded resource
usage; no source paths, keys, range bounds, values or samples.

Verification with the two original local inputs and recipe must hash them,
reroute under the recorded plan, reproduce every private partition digest and
count, rerun every exact comparison, and match the canonical receipt and
summary. A source-free integrity check can validate structure, digests and
arithmetic, but **cannot** establish that original source rows were routed
exhaustively or that the saved classifications were computed correctly.
The CLI must name that narrower claim and never report it as a fresh exact
verification. Feature 4 may investigate only after input-backed verification
under the same plan, recipe and input identities.

## Adversarial completion gate

- Compare final outcome, completeness, all eight keyed count fields, every
  field classification and discrepancy count to the released SQLite engine
  for low-difference, high-difference, 95%-skewed and all-different cases.
  Include a passing case, empty individual ranges, a globally empty side,
  duplicate keys, quoted CSV, side-specific null tokens and numeric
  normalization at boundaries. A null key must be rejected without PASS.
- Show that plan gaps/overlap, omitted or swapped range records, changed
  recipe/input, altered staged bytes, a skewed range exceeding its cap,
  interrupted work, and output collision cannot yield a complete PASS.
- On a named machine, run fresh processes at 100k and 250k rows. Record
  wall time, peak process RSS, peak and final disk bytes, source bytes/read
  passes, limits and reference-engine results. Report source load only for
  actual source access; local CSV comparison has no PostgreSQL scan claim.
- Pass narrow tests, `make check`, independent Standards and Spec review,
  exact-head PR CI and the built-wheel Python 3.11–3.14 Linux/macOS/Windows
  matrix before integration, because the new command and evidence schema
  affect packaging and CLI.

The [research note](253-partition-discovery-research.md) records primary
sources, design consequences, threats and non-goals.
