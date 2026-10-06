# Parison 0.2 blind agent-proxy task

The participant starts without conversation history and may use only the root README, CLI help, generated inputs and its own artifacts. It must not read source, tests, Git history, `docs/` or study answer keys.

1. Generate the `report-filtering-01` synthetic inputs into a fresh temporary directory.
2. Draft a recipe from `baseline.csv` and `candidate-a.csv`.
3. Complete it with the supplied policy: exact string key `id`; the declared synthetic snapshot/cutoff; full, nonempty scope with no filters; equal nulls; scale-2 decimal `amount` with symmetric absolute tolerance `0.10`; exact string `status` and `note`; no exclusions; summary output.
4. Validate, compare, verify and explain the outcome from the self-contained report.
5. Make a reviewed raw-sensitivity copy, rerun and identify both status keys, the note key, baseline-only key, candidate-only key and count of tolerated amount differences.
6. Report every command, exit code, artifact consulted, recovery, confusion, repeat-use intent and a go/fix/stop decision.

Generated data and bundles remain outside the repository.
