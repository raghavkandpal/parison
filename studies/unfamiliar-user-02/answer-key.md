# Facilitator answer key

## Expected procedure

From the repository root (with Parison installed), the participant can run:

```sh
parison validate-recipe studies/unfamiliar-user-02/recipe.json
parison compare \
  --recipe studies/unfamiliar-user-02/recipe.json \
  --baseline studies/unfamiliar-user-02/baseline.csv \
  --candidate studies/unfamiliar-user-02/candidate.csv \
  --output /tmp/parison-unfamiliar-02-initial
parison verify /tmp/parison-unfamiliar-02-initial
```

They should use a different output directory for the follow-up and substitute `candidate-problematic.csv`.

## Initial comparison

Expected outcome: `PASS` (compare exit code 0; verify exit code 0).

- All six typed composite keys match. `site_code` is a string, so `007` remains distinct from numeric-looking alternatives; `sensor_slot` is an integer. Input row order is irrelevant.
- All timestamps describe the same instants despite using `Z` in the baseline and `+05:30` offsets in the candidate.
- Four rows have calibration offsets within the absolute tolerance of 0.05 C, and two are exact. The boundary is inclusive.
- Blank `technician_note` values parse as null on both sides and compare equal because `nulls_equal` is true.
- Exact text values and all record identities agree.

Expected headline counts: baseline 6, candidate 6, common keys 6, baseline-only 0, candidate-only 0, matched exact 2, matched within tolerance 4, matched with required difference 0. The discrepancy count is 4 because tolerated numerical differences remain visible evidence even though they do not cause failure.

The defensible recommendation is to accept this candidate under the declared recipe and scope. A strong response notes that the scope fields are assertions recorded in the evidence, not independent proof of extraction completeness.

## Follow-up comparison

Expected outcome: `FAIL` (compare exit code 1; bundle verification still succeeds with exit code 0 because integrity verification is not a semantic pass/fail rerun).

The participant should find all of these issue classes:

- Baseline key `(12, 2)` is missing from the candidate.
- Candidate key `(12, 3)` is extra.
- For common key `("007", 1)`, `location_label` differs because `Freezer A ` has trailing whitespace and string comparison is exact.
- The same row's offset changes from 0.10 to 0.17, a delta of 0.07, exceeding the 0.05 allowance.

Expected headline counts: baseline 6, candidate 6, common keys 5, baseline-only 1, candidate-only 1, matched exact 2, matched within tolerance 2, matched with required difference 1. The discrepancy count is 6: two identity discrepancies, two allowed numerical differences, and two violating field differences.

The recommendation should change to reject or hold the replacement export. Numeric tolerance cannot excuse a missing or extra identity, exact text is not trimmed, and one numerical delta exceeds policy.

## What this scenario probes

- Correct use of CLI validation, comparison, separate output directories, and bundle verification.
- Distinguishing semantic outcome from artifact-integrity verification.
- Typed composite identity and completeness invariants.
- Exact text and explicit null equality.
- Timestamp instant equivalence across timezone offsets.
- Decimal tolerance, including the fact that tolerance applies only to its field and not to identity problems.
- Ability to revise a release decision when the input changes without changing the policy.
