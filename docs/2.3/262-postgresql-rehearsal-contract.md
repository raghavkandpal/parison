# PostgreSQL 16→18 rehearsal contract

Date: 29 October 2026
Status: released in 2.3.0; rehearsal remains verification, not cutover approval

## Boundary and reviewed inputs

One offline rehearsal composes verified feature 2 acquisition pairs, feature 3
exact partition discovery and released reconciliation-v1 identity, reference
and grouped conservation checks. No database connection, extraction, migration,
credentials, repair, approval or cutover occurs in this command. Feature 4
investigation remains available against the emitted discovery children.

`postgres-rehearsal-plan-v1` is strict JSON with exactly `rehearsal_plan_version:
1`, `pairs`, `coordination`, `policies`, `partitions`, `reconciliation_sha256`,
and `limits`. The two `pairs` slots are `baseline` and `candidate`, each with
exactly `manifest_sha256`, `pair_plan_sha256`, `snapshot`, `expected_rows`,
and `types`. `expected_rows` and `types` each contain exactly `orders` and
`order_lines`: nonnegative row counts and ordered PostgreSQL type-name arrays.
The manifest pins the exact reviewed acquisition, the plan digest pins the
selection, and the snapshot pins its source-local snapshot token. Baseline
must report PostgreSQL major 16, candidate major 18. Tokens are never compared
across clusters. Expected counts are independently reviewed scope assertions,
not counts automatically inferred by this command. Changes require a new plan.

`coordination` has exactly `mode` (`unestablished` or `source-owned`) and
`claim_sha256` (null for unestablished, SHA-256 for source-owned). A separately
supplied bounded local claim file is required for source-owned mode and its
exact bytes must match that digest. Its contents are opaque upstream evidence;
verification authenticates neither the claim nor the database. The plan binds
that claim to both exact receipts. Timestamps/count agreement never establish
coordination. A missing coordination claim yields INCONCLUSIVE even if every
local comparison passes. An incorrect supplied claim fails closed.

`policies` maps the two table slots to effective recipe SHA-256 values.
`partitions` maps the same slots to unchanged partition-plan-v1 objects.
Recipes obey feature 3's simple summary keyed integer policy, select exactly
the acquisition columns, use the acquired primary key and CSV comma delimiter,
and recognize only the adapter's reserved null marker as null. Type, Unicode,
collation and tolerance semantics remain explicit recipe policy; no database
collation is inferred. Both sides' ordered source types must match the reviewed
plan; differing source types are allowed only as explicitly pinned here.

The separately supplied `postgres-rehearsal-relationships-v1` declaration has
exactly `postgres_rehearsal_relationships_version: 1`, `datasets` and `checks`.
These reuse the released reconciliation-v1 dataset and check shapes and
normalization ordering. Its canonical SHA-256 must match
`reconciliation_sha256`. The existing relationship evaluators are reused via
an internal declaration; no released alignment field gains a new public
meaning and no time-window evaluation is claimed. It must contain
exactly the two table datasets and four checks: each table's non-null primary
key identity, a non-null order-line reference to the order identity, and exact
non-null sum conservation grouped by that same parent key/reference. Each
measure is explicit, and must be integer or decimal under released rules.
Global net sums cannot replace per-order conservation. Existing schema and
semantic validators remain authoritative. No generated policy approval.

`limits` has exactly `max_input_bytes`, `max_rows`, `max_keys`, `max_groups`,
and `max_temp_bytes`, positive integers capped respectively at 4 GiB, 300000,
300000, 300000, and 5 GiB. The combined input-byte limit applies across all four
CSV files; row caps apply per input. SQLite performs relationship checks.
Partition limits remain independently enforced. Empty scope follows explicit
recipe empty semantics and reviewed expected counts.

## Execution, evidence and verification

Verify both pairs before reading their sources. Check all reviewed bindings,
policy/selection/key/type/null rules, mandatory relationship structure and limits
before execution. Run exact partition discovery for each table, then identity,
reference and grouped conservation checks on each side. Reverify pair identities
and all policy/claim inputs after execution to reject mutation. The outcome
reduces FAIL before INCONCLUSIVE before PASS. A scope-count mismatch or
unestablished coordination is INCONCLUSIVE unless another check fails. Duplicate
keys and malformed conversion may be controlled errors with no artifact.

Publish atomically, no overwrite, under private staging, removing all staging
on any failure or interruption. Output contains exactly `plan.json`,
`receipt.json`, `summary.json`, `manifest.json`, and `discovery/` with exactly
`orders/` and `order_lines/` unchanged feature 3 artifacts. The receipt has
exactly `postgres_rehearsal_receipt_version: 1`, `plan_sha256`, `pairs` (manifest
digests), `parity` (the two discovery summaries), `relationships`, `conservation`
(released check results), `coverage` (`PASS` or `INCONCLUSIVE`), `coordination`
(`source-owned` or `unestablished`), `outcome`, and `complete: true`.

The summary has exactly `postgres_rehearsal_summary_version: 1`, `outcome`,
`complete`, `coverage`, `coordination`, `parity` (two outcomes), `relationships`
and `conservation` (each aggregate outcome), and `receipt_sha256`. It excludes
paths, source names, snapshot/claim contents, column names, keys and values.
`complete` means completed local evaluation, not proven scope or approval.

The manifest has exactly `postgres_rehearsal_manifest_version: 1` and `files`,
binding the three JSON members and both discovery child manifests by SHA-256
under names `plan.json`, `receipt.json`, `summary.json`, `orders`, `order_lines`.
JSON bytes use existing compact sorted-key UTF-8 plus newline; object identity
hashes omit the newline. Verifier requires the original local pairs, recipes,
reconciliation and claim, reruns all checks and compares canonical evidence.
It offers no integrity-only PASS. It needs no PostgreSQL or optional driver.
This is source-backed local reproducibility, not extraction authentication.

`parison-rehearsal run --plan FILE --baseline DIR --candidate DIR
--orders-recipe FILE --lines-recipe FILE --reconciliation FILE [--claim FILE]
--output DIR` and the corresponding `verify DIR` with the same input options
except plan/output print only summary JSON. Exit 0 for PASS, 1 for FAIL, 3 for
INCONCLUSIVE, 2 for controlled invalid input/verification/publication failure;
errors use a fixed summary-safe message. Released commands remain unchanged.

## Adversarial and end-to-end completion gate

Pin complete canonical output bytes. Exercise golden agreement; matching
omissions against independent counts and absent coordination; stale snapshot,
selector, source, policy and type substitution; absent/changed claim; wrong
major versions; duplicate keys; orphan lines; equal global totals with per-order
offsetting errors; partial backfill/tombstone; equal-count ID swap; conversion,
null/empty, Unicode and timezone drift; wrong mandatory relationship shape;
missing/tampered/digest-recomputed evidence; source removal; limits; symlinks;
no overwrite; interruption cleanup; and summary/CLI leakage. Every parity
result must match the released full comparator. Prove selective investigation
can consume emitted suspect discovery children.

Run a disposable real PostgreSQL 16→18 dump/restore rehearsal outside core,
using independently acquired order/line pairs after an explicitly stopped-write
fixture migration; record upstream coordination as a claim. Test mutation
cases on those instances and source-free local verification after shutdown.
Measure three cold-process complete rehearsals at 100k and 250k total rows per
side: median/max elapsed, peak process-tree RSS, temporary disk, bytes and
source load on a named machine. Do not substitute a synthetic receipt test for
this live gate or claim universal capacity. Full local checks, independent
Standards/Spec review and exact-head quality and Python 3.11–3.14
Linux/macOS/Windows built-wheel CI precede integration. All six features remain
one release train; feature 6 and release qualification are separate.
