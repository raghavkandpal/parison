# Parison 0.2 autonomous roadmap

Date: 6 October 2026

This roadmap separates work an agent can complete and verify independently from evidence that requires a human. Work proceeds in order on `develop`, one focused commit at a time. Every implementation commit must keep existing bundles readable, preserve keyed-v1 semantics and exit codes, add the smallest relevant regression check, and leave the tree passing.

## Autonomous commits

### Repeatable CI evidence

- [x] Add safe terminal summaries and a copyable GitHub Actions workflow.
- [x] Exercise PASS, FAIL, ERROR and INCONCLUSIVE through the workflow's capture/upload/restore contract; verify every produced bundle.
- [x] Exercise deterministic interruption handling and verify its published bundle.
- [x] Record a CI checkpoint covering artifact retrieval, verification and public-fork safety.

### Recipe generation

- [x] Specify the draft format and unresolved-choice behavior using the existing recipe schema.
- [x] Add a `draft-recipe` command that reads two local inputs, includes exact shared columns and emits reviewable JSON.
- [x] Require explicit keys, snapshot, cutoff, filters, completeness, empty-scope policy, exclusions and tolerances before validation can succeed; do not infer trusted policy.
- [x] Cover mismatched columns, ambiguous types, empty inputs, unsafe paths and deterministic output.
- [x] Document the shortest draft-review-validate-compare workflow.

### Static report filtering

- [x] Add dependency-free controls for field classification and bounded raw-sample field, class and key-text filtering.
- [x] Preserve the complete no-JavaScript report, escaping, keyboard operation and summary-mode privacy.
- [x] Add report-level regression checks for filtering hooks, raw/summary separation and canonical JSON immutability.
- [x] Record a seeded investigation benchmark that can later be repeated by a human.

### Additional local inputs

- [x] Specify JSON Lines mapping and rejection behavior against keyed-v1, including scalar types, missing fields, duplicates, limits and cancellation.
- [x] Implement JSON Lines through the existing comparison result model and add oracle-based mixed-input tests.
- [x] Document JSON Lines use without introducing format-specific recipes.
- [x] Specify a read-only SQLite input locator, type mapping, query/table scope, limits and cancellation without introducing a connector abstraction.
- [x] Implement SQLite with the standard library, read-only connections and the existing comparison result model.
- [x] Add oracle-based CSV/JSONL/SQLite compatibility tests and document local credential/data handling.

### Release integration

- [x] Run the full supported Python/optional-Parquet suite and build artifacts.
- [x] Verify 0.1 example bundles with 0.2 code and record compatibility evidence.
- [x] Update current documentation, changelog/release notes and the GitHub-hosted installation reference.
- [ ] Run a clean-environment release rehearsal and produce a go/fix/stop engineering checkpoint.

## Human-only gates

These cannot be honestly completed by an implementation agent acting as the product's user:

- Two unfamiliar people author recipes and report whether drafting reduces friction versus editing the example JSON.
- A reviewer performs the seeded report investigation; filtering ships only if it measurably helps.
- At least one target user repeats a real comparison.
- A human reviews the produced evidence and makes the final 0.2 release decision.
- Any use of production credentials, private datasets or raw artifacts remains a user-controlled action outside this repository.

Agent-proxy trials may improve instructions and catch mechanical failures, but they are recorded separately and never counted as these human gates.

## Stop conditions

Stop autonomous implementation and request direction if a change would alter PASS semantics, approve inferred policy, require customer data, require a hosted service, or introduce a backend-specific exception into the canonical result model. Reject JSON Lines or SQLite if their semantics cannot map cleanly to keyed-v1.
