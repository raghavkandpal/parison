# 0.2 human-results checklist

Use synthetic or user-controlled data only. Do not commit production data, credentials or raw-sensitive reports.

- [ ] **Recipe authoring — person 1:** have an unfamiliar user run `draft-recipe`, complete every review choice, validate the recipe and run a comparison. Record completion, elapsed time, help needed, mistakes and whether drafting was easier than editing the example JSON.
- [ ] **Recipe authoring — person 2:** repeat independently with a second unfamiliar user and record the same results.
- [ ] **Report investigation:** run the counterbalanced [filtering protocol](../../studies/report-filtering-01/protocol.md) with an unfamiliar human. Record both timings, answers, corrections, controls used and confusion. Keep filtering only if answers are correct and the filtered condition is faster without help.
- [ ] **Real repeat use:** have one target user run the same reviewed recipe on a later candidate. Record whether the run and bundle verification completed, what help was needed and whether they would use it again.
- [ ] **Release decision:** review all four records and write a dated **GO**, **FIX** or **STOP** decision. A GO must confirm that no policy was inferred or self-approved and that the evidence bundle was understandable.
- [ ] **After GO only:** rebuild from the chosen commit in a clean environment, inspect the wheel and source archive, repeat the installed-wheel smoke test, then tag and publish `0.2.0`.

Store only consented, non-sensitive observations in `studies/`; keep private datasets and raw artifacts outside the repository.

## Release-owner decision

On 7 October 2026, the project owner explicitly chose to publish 0.2.0 with the current capabilities and waived the four unfinished direct-human validation gates above. Those studies remain unchecked and must not be represented as completed evidence.

## Code runbook

Run each participant in a fresh temporary directory. On `develop`, use the checkout explicitly so an installed 0.1 release cannot be selected by accident:

```sh
PYTHONPATH=src python -m parison --version
PYTHONPATH=src python -m parison draft-recipe \
  --baseline BASELINE --candidate CANDIDATE --output DRAFT.json
# The participant reviews and edits DRAFT.json here.
PYTHONPATH=src python -m parison validate-recipe DRAFT.json
PYTHONPATH=src python -m parison compare \
  --recipe DRAFT.json --baseline BASELINE --candidate CANDIDATE --output RUN
PYTHONPATH=src python -m parison verify RUN
```

For the filtering study, prepare and verify both intentionally failing bundles before handing only the reports and participant task to the reviewer. Exit `1` is expected from both comparisons.

```sh
python studies/report-filtering-01/generate.py /tmp/parison-filter-study
PYTHONPATH=src python -m parison compare --recipe /tmp/parison-filter-study/recipe.json \
  --baseline /tmp/parison-filter-study/baseline.csv --candidate /tmp/parison-filter-study/candidate-a.csv \
  --output /tmp/parison-filter-study/run-a
PYTHONPATH=src python -m parison compare --recipe /tmp/parison-filter-study/recipe.json \
  --baseline /tmp/parison-filter-study/baseline.csv --candidate /tmp/parison-filter-study/candidate-b.csv \
  --output /tmp/parison-filter-study/run-b
PYTHONPATH=src python -m parison verify /tmp/parison-filter-study/run-a
PYTHONPATH=src python -m parison verify /tmp/parison-filter-study/run-b
```

For repeat use, rerun the first command sequence with the already reviewed recipe, a later candidate and a new output directory; do not edit the recipe during that observation.

After a human GO, run the full suite and build the candidate. Continue with [`RELEASING.md`](../../RELEASING.md) for archive inspection, clean-environment installation, tagging and GitHub publication.

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
python -m build
```
