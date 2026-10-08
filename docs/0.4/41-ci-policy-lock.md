# CI policy lock

Date: 8 October 2026

`parison explain RECIPE` prints the canonical `policy_sha256` for review. A CI job can pin that exact policy when it compares data:

```sh
parison compare --recipe recipe.json \
  --baseline baseline.csv --candidate candidate.csv \
  --expected-policy-sha256 REVIEWED_HASH \
  --output run
```

The expected value must be 64 lowercase hexadecimal characters. Parison expands and hashes the recipe, then checks the value before opening either input. `validate-inputs` accepts the same option and includes `policy_sha256` in its JSON result. A malformed or mismatched value returns exit code `2`; `compare` also publishes a summary-only error bundle when the output destination is available.

Reformatting or reordering the recipe does not invalidate the lock. Any change to an effective policy decision does. The lock proves equality with the supplied hash; it does not prove who reviewed the policy, authenticate the recipe, or replace repository protections and code review.
