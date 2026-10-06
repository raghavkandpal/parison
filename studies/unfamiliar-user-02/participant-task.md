# Parison unfamiliar-user task 02

You are advising a cold-storage team after a pipeline rewrite. They need to know whether the candidate calibration export is equivalent to the baseline under the supplied policy, and whether it is safe to use for the next compliance report.

Work from this directory and use Parison's CLI. Do not edit the CSV files or recipe. You may inspect all generated artifacts and use `parison --help` whenever useful.

## Initial comparison

1. Validate `recipe.json`.
2. Compare `baseline.csv` with `candidate.csv`, writing the evidence bundle to a new output directory of your choice.
3. Verify the completed bundle.
4. Report the run outcome and make a clear release recommendation.
5. Briefly explain how the recipe treats record identity, blank notes, calibration offsets, and timestamps. Cite concrete evidence from the generated artifacts rather than relying only on the process exit code.

## Follow-up

The migration team sends a replacement export, `candidate-problematic.csv`. Run the same validated recipe against that file in a different output directory, verify its bundle, and update your recommendation. Identify each distinct kind of problem that matters to the decision and explain why the recipe does or does not allow it.

Keep your final response concise enough for an engineer to act on. Do not change policy merely to obtain a preferred outcome.
