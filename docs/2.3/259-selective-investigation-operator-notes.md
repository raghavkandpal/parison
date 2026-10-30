# Selective exact investigation operator notes

Date: 29 October 2026
Status: feature 4 integrated through PR #102

This command starts from a complete, source-backed [feature 3 discovery](255-partition-discovery-operator-notes.md). It scans the original local CSV inputs, stages only chosen suspect integer-key ranges, and publishes bounded raw discrepancy items in a private directory. It cannot approve policy or authorize cutover. A subset or truncated list remains incomplete even when its selected exact comparisons finish.

Create a strict `investigation-plan-v1` JSON object with the discovery manifest SHA-256, ascending zero-based suspect `partition_indices`, and four positive limits: `max_cases_total`, `max_cases_per_partition`, `max_staged_bytes`, and `max_output_bytes`. Validate the shape with `parison schema investigation-plan`. The [frozen contract](258-selective-investigation-contract.md) gives the allowed maxima. The plan contains no local paths or raw values.

```sh
parison-partitions investigate --plan investigation-plan.json --discovery discovery-dir --recipe recipe.json --baseline baseline.csv --candidate candidate.csv --output investigation-dir
parison-partitions verify-investigation investigation-dir --discovery discovery-dir
parison-partitions verify-investigation investigation-dir --discovery discovery-dir --recipe recipe.json --baseline baseline.csv --candidate candidate.csv
```

`investigate` first re-verifies the discovery against the original policy and inputs. Both commands return summary-safe JSON. The first verifier form checks artifact integrity and internal arithmetic only; `verification: "integrity-only"` does not authenticate the raw cases. The second reruns the source-backed discovery and selected comparisons and returns `verification: "exact-source-backed"` on equality. A bad plan, altered source, output collision or unsafe destination exits 2 without publishing partial evidence. The output directory contains `plan.json`, `receipt.json`, `cases.json`, `summary.json`, and `manifest.json`; treat the whole directory as sensitive because `cases.json` contains keys and values. The CLI reveals only digest identities and aggregate counts. `scope_complete`, `enumeration_complete`, and `complete` are separate; there is no PASS/FAIL outcome.

The reference fixture in `tests/fixtures/partition_investigation` pins canonical bytes for all five files and a tolerated numeric difference. The selected raw item is compared with the released full raw comparator; its range counts must match the verified feature 3 receipt. A [machine-specific budget](260-selective-investigation-budget-checkpoint.md) records the selected scan cost. The exact-head CI gate is recorded in the feature handoff after integration.
