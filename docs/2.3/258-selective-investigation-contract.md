# Selective exact difference investigation contract

Date: 29 October 2026
Status: frozen for 2.3 feature 4 implementation; not a release commitment

This is capability 4 in the [six-feature roadmap](246-six-feature-roadmap.md).
It discloses bounded raw discrepancy items from selected suspect ranges of a
[feature 3 discovery](254-partition-discovery-contract.md). It does not
alter the reviewed comparison policy, turn a subset into full-scope parity,
or authorize migration cutover. Released 2.2 and feature 3 bytes remain
readable and unchanged.

## Reviewed selection and prerequisite

`investigation-plan-v1` is strict JSON with exactly
`investigation_plan_version: 1`, `discovery_manifest_sha256`,
`partition_indices`, and `limits`. `partition_indices` is a nonempty,
strictly increasing list of at most 128 zero-based integers. `limits` has
exactly `max_cases_total` (1–10,000), `max_cases_per_partition` (1–1,000),
`max_staged_bytes` (1–1 GiB), and `max_output_bytes` (1–16 MiB).
The operator supplies the existing local feature 3 directory, original
recipe, and both original CSV inputs separately. The plan contains no paths,
credentials, values, tolerance changes or repair instructions.

Before producing any raw item, the command must validate the feature 3
manifest and perform **source-backed exact verification** with the original
recipe and both inputs. `integrity-only` verification is insufficient. It
pins the verified discovery manifest bytes, plan, private receipt, effective
policy SHA-256 and both input SHA-256/size pairs for the rest of the run.
Recheck the discovery bytes before publication; mutation fails.
The discovery receipt must be complete. A suspect range has at least one
baseline-only or candidate-only key, required field difference, or
within-tolerance field difference. Every requested index must identify a
suspect in that verified receipt. No omitted suspect is represented as
investigated, and the output may identify selected bounds only in private
evidence.

## Selective exact work

After the prerequisite, scan both source CSVs under the feature 3 parser and
normalized integer-key routing. Read the full files but materialize only
selected ranges in a private temporary directory. Enforce inherited source
row/byte caps and the investigation staged-byte cap while writing. Recheck
source digests and selected partition row/byte/digest totals against the
verified feature 3 receipt. A changed source or partition fails without
publication. The first version intentionally pays for a full source-backed
feature 3 verification **and** one additional selective source scan; it does
not claim source-side selective reads.

For each selected range, run the released exact keyed comparator with a
mechanically derived raw-sensitivity recipe and empty-range allowance. Only
`output.sensitivity` and range-local `scope.expected_empty` may differ from
the original; record both effective policy digests and the derivation label
`raw-disclosure-v1`. This is an explicit raw disclosure request, not policy
approval. The selected exact counts and field classifications must match the
verified feature 3 private range record. Use the released raw
`discrepancy_sample` shape: a missing-record item identifies a key and side;
it does **not** claim the full missing row. Returned items are bounded first
per range and then globally, in selected range order. Recheck staged bytes
after comparison and remove all staging on success, failure or interruption.

`population_count` is the exact number of discrepancy items in the selected
ranges; `returned_count` is the published sample size. A smaller returned
count means the case list is truncated even though selected exact checks may
have completed. `scope_complete` means every suspect range was selected.
`enumeration_complete` means every selected discrepancy item was returned.
The top-level `complete` is true only when the source-backed prerequisite,
every selected exact check, scope coverage and enumeration all complete.
No investigation result has a PASS/FAIL parity outcome.

## Canonical evidence and verification

Publish one atomic, no-overwrite, symlink-safe private directory containing
exactly `plan.json`, `receipt.json`, `cases.json`, `summary.json`, and
`manifest.json`. Version every payload. The manifest binds the compact,
sorted-key UTF-8 bytes with trailing newline of the other four. The private
receipt records the original discovery manifest digest, plan and effective
policy digests, original input digests and sizes, selected range indices and
bounds, per-range exact counts, population and returned counts, and the raw
derivation digest. `cases.json` contains only the selected existing raw
discrepancy item shapes plus their private range index. The summary and CLI
JSON include only digest identifiers, suspect/selected counts,
population/returned counts, `scope_complete`, `enumeration_complete`, and
`complete`; no source path, range index/bound, key, value or sample.

A source-free verifier requires the discovery directory and checks its
integrity, the investigation's canonical structure and file digests,
selected-index membership and internal arithmetic. It reports only
`verification: "integrity-only"` and cannot authenticate case truth.
Source-backed verification requires the original
discovery, recipe and both inputs; it reruns the feature 3 prerequisite and
selected raw comparisons, reproduces every returned item and count, and
reports `verification: "exact-source-backed"` only on equality. Mutation
of any source or evidence during verification fails. Neither verifier
promotes a selected subset or truncated case list to complete enumeration.

## Adversarial completion gate

- Low/high/skew/all-different and tolerance cases: every returned item must
  match a full released raw-reference run under the same column policy, and
  selected exact counts must match the feature 3 receipt.
- Reject changed recipe/input/discovery, an integrity-only prerequisite,
  missing or swapped range records, nonsuspect indices, altered case values,
  omitted selected ranges, forged completion, over-limit output, symlinked
  destinations, output collision and interruption without raw staging leaks.
- Measure a named 100k/250k local corpus: source bytes/read passes, producer
  wall time, peak RSS, temporary bytes and final evidence bytes. Report
  truncation and selected-versus-total suspect ranges explicitly.
- Pass narrow tests, `make check`, independent Standards/Spec review, exact
  head PR CI and the full built-wheel Python 3.11–3.14 Linux/macOS/Windows
  matrix before integration, because CLI and evidence schemas change.

The [research note](257-selective-investigation-research.md) records source
authority, design consequences, threats and non-goals.
