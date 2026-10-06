# Unfamiliar-user trial 02 recommendation

## Decision

- The initial `candidate.csv` run passed the supplied policy and its bundle verified successfully. On that evidence, I would accept that export for the next compliance report.
- The replacement `candidate-problematic.csv` run failed the same policy. Do not release or use that replacement for the compliance report until it is corrected and rerun.

## Evidence and interpretation

The recipe uses the compound key `site_code` (exact string) plus `sensor_slot` (exact integer) for record identity; null keys and duplicate identities are rejected. Blank `technician_note` values compare equal because `nulls_equal` is `true`. Calibration offsets are scale-2 decimals with symmetric absolute tolerance `0.05` and no relative tolerance. Timestamps require timezone-aware values and compare exactly as instants: the initial bundle reports all six timestamps exact even though equivalent offsets are written differently.

The initial result is `PASS`: all six keys are common, two records are exact, and four have only calibration-offset deltas of `0.04`, within the `0.05` allowance. There are no required differences.

The replacement result is `FAIL` for three decision-relevant reasons:

- baseline key `["12", 2]` is absent and candidate-only key `["12", 3]` is present; full completeness and exact keyed identity do not allow substitution;
- `location_label` for `["007", 1]` changed from `Freezer A` to `Freezer A `; exact string comparison does not ignore trailing whitespace;
- its calibration offset changed from `0.10` to `0.17`, a `0.07` delta exceeding the `0.05` allowance.

The other `0.04` offset changes remain permitted. Both manifests say `complete: true`, and `parison verify` returned `0` for both bundles.

## Execution notes

No wheel was supplied. I used a fresh temporary virtual environment with the repository source via `PYTHONPATH=src`; this is the only packaging deviation. Validation returned `0`; initial compare returned `0`; problematic compare returned `1` (documented comparison failure); both verify commands returned `0`. The CLI was understandable after consulting `--help`. The main point requiring interpretation was that `verify` validates bundle integrity, not whether the comparison passed. Raw sensitivity exposes keys and values in these bundles, so they should be protected as sensitive evidence.

I would use this workflow again: the exit codes, canonical JSON, effective recipe, and independently verifiable manifest make the release decision auditable.

Bundles: `agent-trial-01/initial/` and `agent-trial-01/problematic/`.
