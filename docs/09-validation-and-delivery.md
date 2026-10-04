# Parity validation and delivery plan

## Decision before implementation

Build a bounded proof of usefulness, not an enterprise platform. The first milestone is a small synthetic comparison corpus and a baseline report produced with existing tools. Implementation should follow a written semantics contract and measured gaps.

All targets below are proposed gates. No interviews, task studies, performance tests or paid offers have been conducted.

## Gate-based delivery

| Stage | Deliverable | Evidence required to advance |
| --- | --- | --- |
| 0 — problem validation | Independent interviews and example task inventory | Recurring comparisons and a specific investigation pain not adequately solved today |
| 1 — technical baseline | Synthetic fixtures plus DataComPy/Polars baseline | Documented differences from required semantics; dependency/license decision |
| 2 — vertical slice | CLI, immutable recipe, full counts, JSON and HTML | Known fixtures pass; invalid identity/incomplete runs never return PASS |
| 3 — usability proof | Task comparison against current methods | Unassisted use and better correctness or materially less total effort |
| 4 — repeat adoption | Packaged alpha and safe CI examples | Second real/synthetic-equivalent use; acceptable setup/support burden |
| 5 — commercial test | Narrow paid offer | Real purchases or a credible reason to retain an open-source-only project |

For a side-project planning envelope, reserve several focused sessions for baseline work and several more for the vertical slice, then reassess. These are not delivery dates. Avoid promising macOS, Windows, Linux and every Python version before testing them.

## Synthetic fixture corpus

Start with at least 40 hand-audited cases, then expand through generated/property tests. Use seeded generators with independently computed expected outcomes. Synthetic data should include orders, inventory, event logs and user/account examples so the product does not become industry-specific.

| Category | Minimum cases to include | Expected behavior |
| --- | --- | --- |
| Identity | Composite-key collisions, leading zeros, duplicate keys on one/both sides, null components | Invalid identity stays inconclusive; no join multiplication |
| Schema/parsing | Renames, missing required columns, duplicate names, mixed delimiters, invalid UTF-8, quoted newlines | Explicit mappings or actionable errors; no silent row drop |
| Missing data | Baseline-only/candidate-only rows, empty files, header-only files | Complete counts and clear coverage; empty data is not automatic success |
| Numerical values | Exact boundaries, negative/zero values, high-precision decimals, large integers, NaN/infinity | Contract-compliant classifications with no silent precision loss |
| Null/text semantics | Empty versus null, spaces, Unicode forms, case changes | Differences unless explicitly normalized |
| Time | Naive/aware timestamps, equivalent instants, DST ambiguity, date/timestamp mismatch | Declared policy or blocked comparison |
| Aggregates | Equal totals hiding offsetting errors, missing groups, skew | Row differences remain visible despite matching aggregates |
| Artifacts | Interrupted writes, tampered manifest, missing files, report escaping | No partial-success publication; safe rendering |
| Security | Formula-like CSV cells, traversal, malicious recipes, raw-value canaries | No code execution or accidental export/log disclosure |
| Resources | Cancellation, low disk, constrained RAM, very wide rows | Predictable error/cancel outcome, cleanup and no fallback pass |

## Property and metamorphic tests

Reordering rows must not change keyed semantic results. Changing column order must not matter when mappings are explicit. A one-record mutation must affect the expected counts, not unrelated records. Swapping inputs should exchange missing/extra counts and preserve classifications under the symmetric tolerance rule. Increasing a numerical tolerance must not alter identity validity or schema coverage.

Assert count conservation from the semantics document for every valid run. Assert that within-tolerance differences remain distinguishable from exact matches. Verify that masking changes exported presentation but not underlying comparison outcomes. Rerun from the same pinned inputs/recipe/engine and compare semantic results excluding volatile metadata.

Use small independent reference logic with Python Decimal and explicit typed-key dictionaries, not the same engine algorithm rewritten superficially. Differential tests against existing tools apply only where their semantics actually overlap.

## Performance experiment

Test 10,000, 100,000 and 1,000,000 rows, then extend toward the measured practical envelope. Cross row counts with 10/100/500 columns, short/long string keys, decimal/string-heavy fields and mismatch rates from zero to widespread differences. Add intentionally duplicate keys to confirm cheap preflight failure before an expensive join.

Record input bytes, compression, row widths, hardware, OS, Python/package versions, thread settings, elapsed time, peak memory, scratch usage and report size. Test cold/warm runs separately. Compare equivalent full-check semantics, not a sampled rival against a full Parity run or vice versa.

Do not claim million-row or out-of-core support until full comparison, report generation, cancellation and constrained-resource behavior have been measured. Publish failed runs as well as favorable results. A maximum row count is not a reliable universal size guarantee.

## Usability and demand experiment

Recruit 5–8 unfamiliar engineers for a counterbalanced task comparison, using alternate equivalent fixtures to reduce learning effects. Measure initial setup, correct discrepancy explanation, evidence export and rerun after a recipe/input change. Report assisted versus unassisted use separately.

Exploratory targets: at least 4 of 5 evaluators complete the core task unassisted; at least 3 choose to reuse the tool for a second comparison; materially reduced total task time without more false passes. These small samples guide iteration, not population-level efficacy claims.

For an optional paid test, seek actual purchase/renewal from a handful of independent users at a clearly described offer. A letter of interest or survey response is weaker evidence. Record reasons for non-adoption, especially “existing library is enough” and “generated script is easier.”

## Integration acceptance

Test the same recipe through CLI and Python API; results must agree. Demonstrate a protected CI recipe, secure failure artifact collection and correct handling of exit codes 0/1/2/3/130. CI examples must not inject credentials into public fork jobs or hide nonzero outcomes behind shell defaults.

Database connector work is separately gated by independent demand, snapshot consistency, least-privilege credentials, type mapping and network restrictions. A public API/documented connector does not mean our implementation is safe or correct.

## Side-project operating limits

Keep the maintainer burden visible: supported versions, reproducible bug templates, scheduled dependency checks, migration policies and explicit support hours. Avoid a feature request becoming a production SLA. Build one cross-platform package only after installation tests warrant it.

Publish recipe migrations rather than reinterpreting old files silently. Keep older run bundles readable. A compatibility change to tolerance, parsing or key semantics is behaviorally significant even if package APIs remain unchanged.

## Stop and pivot rules

Stop releases on false PASS, source mutation, unexplained count discrepancies or accidental sensitive-data exposure. Fix and add a regression case before expanding scope.

Narrow to a report/recipe layer if existing engines already satisfy the computation contract. Keep a useful open-source utility if repeated use exists but payment does not. Stop commercial development if differentiation depends mainly on features AI or incumbents can recreate with lower effort, and users do not value maintenance/evidence enough to return.

## Outstanding choices

Decide library adapter versus custom kernel after the spike; choose initial OS/Python support; confirm finite-number/decimal rules; select the distribution license; decide whether a static report is sufficient; clear the working name; then agree the first prototype scope. No hosted service or optional AI integration is needed to answer these questions.
