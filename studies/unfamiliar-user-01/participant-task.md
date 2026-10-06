# Parison evaluation task

You are reviewing a pipeline migration. Work without facilitator guidance where possible and think aloud. You may use the repository README, `parison --help`, generated files and any normal local tools.

The facilitator will provide a Parison wheel. Install it in a fresh environment, then use the files in this directory.

1. Compare `baseline.csv` with `candidate.csv` using `recipe.json`. Save the output outside this directory. Decide whether the candidate preserves the baseline and explain the evidence.
2. Repeat using `candidate-duplicate.csv`. Explain the outcome and what must happen before the migration can be assessed.
3. Change only the recipe's absolute tolerance from `0.01` to `1.00`, then rerun the original comparison in a new output directory. Explain whether the files are identical and whether the result permits the migration under the edited rule.
4. Verify the final result bundle. Identify which files you would retain in CI and which one you would open first during an investigation.

When finished, tell the facilitator:

- what was confusing or slower than expected;
- whether you would use this for a second comparison;
- what you would otherwise use for this task.
