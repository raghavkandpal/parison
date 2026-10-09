# Comparison suite user guide

Comparison suites run several reviewed Parison recipes as one local job and publish one portable integrity boundary. Each case still uses its existing keyed, aggregate or multiset contract.

## Create and validate a plan

Paths are resolved relative to the suite file:

```json
{
  "suite_version": 1,
  "cases": [
    {
      "id": "orders",
      "recipe": "recipes/orders.json",
      "baseline": "baseline/orders.csv",
      "candidate": "candidate/orders.jsonl",
      "expected_policy_sha256": "64-lowercase-hex-characters"
    }
  ]
}
```

Case IDs are unique lowercase letters, digits and single hyphens. Plans contain at most 100 cases. The optional policy fingerprint locks each case to a reviewed effective recipe.

```sh
parison schema suite
parison validate-suite migration-suite.json
```

Validation checks the strict plan shape, references, recipes and policy locks without scanning input records.

## Run and inspect

```sh
parison run-suite --plan migration-suite.json --output runs/migration
parison verify runs/migration
parison inspect runs/migration
```

Cases run sequentially in plan order. FAIL, INCONCLUSIVE and ERROR cases do not prevent later cases from running. Ctrl-C publishes an INTERRUPTED child when possible and stops the remaining cases.

Suite exit codes use the existing Parison outcome mapping. Overall outcome precedence is `INTERRUPTED`, `ERROR`, `INCONCLUSIVE`, `FAIL`, then `PASS`. A suite PASS therefore means every case completed and passed.

The parent contains `suite-result.json`, `effective-suite.json`, `report.html`, `manifest.json` and ordinary child bundles under `cases/<id>/`. Verification checks the parent files, recursively verifies every published child, and reconciles child metadata, order, counts, outcome and completeness with the effective plan.

## Investigate a case

Suite inspection is summary-safe and does not copy child discrepancy samples. Inspect or export one child explicitly:

```sh
parison inspect runs/migration/cases/orders
parison export-evidence runs/migration/cases/orders \
  --classification different \
  --kind field \
  --output orders-differences.jsonl
```

Evidence export still requires that case's recipe to have requested raw sensitivity. The suite parent is never a raw-evidence export target.

## Example

[`examples/0.10/mixed-suite.json`](../../examples/0.10/mixed-suite.json) runs one keyed, one aggregate and one multiset comparison with locked policies. It is exercised on every supported Python version plus macOS and Windows.
