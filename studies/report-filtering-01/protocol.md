# Static-report filtering study 01

This benchmark measures investigation help, not comparison correctness. Use one human reviewer who has not read `answer-key.md`. Generated inputs and bundles stay outside the repository.

## Setup

```sh
python studies/report-filtering-01/generate.py /tmp/parison-filter-study
parison compare --recipe /tmp/parison-filter-study/recipe.json --baseline /tmp/parison-filter-study/baseline.csv --candidate /tmp/parison-filter-study/candidate-a.csv --output /tmp/parison-filter-study/run-a
parison compare --recipe /tmp/parison-filter-study/recipe.json --baseline /tmp/parison-filter-study/baseline.csv --candidate /tmp/parison-filter-study/candidate-b.csv --output /tmp/parison-filter-study/run-b
```

Both comparisons intentionally return FAIL. Verify both bundles, then give the reviewer only the two `report.html` files and `participant-task.md`.

## Counterbalancing and measurement

For odd-numbered participants, investigate A without using report filters, then B using filters. Reverse the conditions for even-numbered participants. Browser Find is allowed in the no-filter condition; the report's filter controls are not. Start timing when the report opens and stop when all answers are submitted.

Record elapsed seconds, answers, corrections, controls used and unsolicited confusion separately for each report. Filtering demonstrates benefit only if the reviewer is correct in both conditions and the filtered investigation is faster without requiring facilitator help. One result is directional evidence, not a universal usability claim.
