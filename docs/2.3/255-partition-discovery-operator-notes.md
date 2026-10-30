# Exact partition discovery operator notes

Date: 28 October 2026
Status: feature 3 released in 2.3.0 through PR #99

The optional `parison-partitions` command runs the [frozen reviewed-range
contract](254-partition-discovery-contract.md) on two local CSV files. It does
not contact PostgreSQL. Use a released keyed summary recipe with one integer
key, no mappings, field projection, input projection or exclusions. Keep the original recipe
unchanged; the command permits empty individual ranges internally and applies
the original `scope.expected_empty` once to the total inputs.

Prepare a strict plan such as:

```json
{
  "partition_plan_version": 1,
  "ranges": [{"upper": 50001}, {"upper": 100001}, {"upper": null}],
  "limits": {
    "max_input_bytes": 100000000,
    "max_rows_per_input": 250000,
    "max_rows_per_partition_side": 100000,
    "max_staged_bytes": 200000000,
    "max_partition_bytes": 100000000
  }
}
```

Each finite upper is exclusive; the first range starts at negative infinity
and the last ends at positive infinity. Choose and review bounds for the
actual key distribution. A skewed range that exceeds a limit fails rather
than silently spilling past its budget.

Run:

```sh
parison-partitions discover --plan partition-plan.json --recipe recipe.json \
  --baseline baseline.csv --candidate candidate.csv --output discovery
parison-partitions verify discovery --recipe recipe.json \
  --baseline baseline.csv --candidate candidate.csv
```

`discover` exits 0 for PASS, 1 for FAIL, and 2 for INCONCLUSIVE or a rejected
run. `verify` exits 0 when verification succeeds, regardless of recorded
outcome; it exits 2 on a mismatch. Without all three source arguments,
`verify discovery` checks only evidence structure, digests and arithmetic and
returns `verification: "integrity-only"`. With the recipe and both original
inputs it reroutes and rechecks every exact range, returning
`verification: "exact-source-backed"`. The latter is required before feature
4 can investigate a range. The private receipt contains reviewed bounds and
per-range results; `summary.json` and CLI output contain only aggregate
counts and digest identifiers. Treat the output directory as private local
evidence. Temporary partition CSV files are deleted before publication and
on failure or interruption.

The command preserves released comparator outputs and 2.2 bundle bytes. Its
PASS means agreement under the reviewed policy and declared local inputs,
not extraction truth, migration approval or cutover authorization.
