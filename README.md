# Parison

Local-first, deterministic output comparison for data pipeline refactors and migrations.

Parison is an independent data-engineering side project. The proposed product compares baseline and candidate outputs under a reviewed, reusable recipe, then produces machine-readable results and a portable investigation report. It does not require an AI model or upload datasets to a hosted service.

## Project status

**0.13.0 released.** Parison adds genuinely offline editor schema export and an explicit zero-custody local catalog for finding verified runs by outcome, kind, policy fingerprint and live state.

**0.14.0 released.** An explicit SQLite-backed multiset engine targets exact local migration and backfill comparisons that exceed comfortable process memory, while preserving the existing semantic contract and bounded evidence.

**0.15.0 released.** Policy-locked catalog history and safe run-summary diff support repeated migration rehearsals and backfill validation without adding hosted storage or parsing raw evidence.

**0.16.0 released.** Fast project adoption includes a safe, runnable `parison init` workflow, actionable failure guidance and tested external-orchestrator patterns.

**0.17.0 released.** Evidence handoff adds deterministic unsigned in-toto Statements that existing CI identity systems can authenticate, without adding cryptography, credentials or network access to Parison.

**0.19.0 released.** Historical compatibility, the complete migration workflow, consolidated command guidance and machine-qualified performance evidence now form a checkable 1.0-readiness baseline.

**1.0.0 released.** The qualified 0.19 surface advances unchanged as the stable 1.x compatibility baseline; this designation adds no new parser, dependency or runtime semantics.

**1.2.0 released.** Opt-in semantic scalar projection now gives mixed-format comparisons a closed conversion boundary, while local schema-evolution declarations and policy diffs explain reviewed renames and structural changes without reading datasets or granting approval.

**1.3.0 released.** Frozen `time-alignment-v1` and `reconciliation-v1` contracts define one UTC half-open event window, source-owned coordination claims and a closed identity/reference/grouped-sum vocabulary. `parison reconcile` composes alignment, existing per-dataset parity and memory/SQLite relationship checks with conservative outcomes, atomic verified bundles and summary-safe inspection.

**1.5.0 released.** Deterministic discrepancy analysis turns verified keyed, aggregate and multiset counters into summary-safe reason groups, compares exact-policy rehearsal series, and permits bounded drill-down only over raw samples already published in run bundles.

**1.6.0 in development.** The active adoption slice consolidates the complete 1.x workflow into one maintained guide and generates an exhaustive command reference from the real CLI parser.

Parison is an open-source, zero-custody tool. Comparisons run in the user's environment; Parison will not receive or store customer production data. Monetization and commercial packaging are outside the current roadmap.

Development setup, quality gates and compatibility obligations are documented in [CONTRIBUTING.md](CONTRIBUTING.md).

## Try it

Python 3.11 or newer is required.

For the complete reviewed-policy, suite, reconciliation, dataset-evidence, rehearsal-analysis and authenticated-handoff path, follow the [current 1.x user guide](docs/user-guide.md). Every supported option is listed in the [generated command reference](docs/command-reference.md).

For cross-format scalar representation rules, follow the [semantic scalar guide](docs/1.1/140-semantic-scalar-guide.md). For data-free rename, addition, removal, split and merge review, follow the [`schema-evolution-v1` and `policy-diff-v1` contract](docs/1.2/143-schema-evolution-and-policy-diff-contract.md).

For coordinated multi-dataset policy authoring and execution, follow the frozen [`time-alignment-v1` and `reconciliation-v1` contract](docs/1.3/149-time-alignment-and-reconciliation-contract.md).

For a local 1.4 workflow, verify [`examples/1.4/payout-dataset-manifest.json`](examples/1.4/payout-dataset-manifest.json), produce its complete suite or reconciliation result bundle, then use `parison publish-dataset-evidence --manifest ... --root ... --policy-file ... --result-bundle ... --output ...`. Standard `parison verify` and `parison inspect` commands recursively validate and summarize the resulting bundle without exposing source paths or resource IDs.

For the 1.5 rehearsal workflow, compare the three candidates under [`examples/1.5/orders.recipe.json`](examples/1.5/orders.recipe.json), then run `parison analyze RUN_1 RUN_2 RUN_3 --output SERIES`. Verified catalog runs may instead be selected with `--catalog` and an exact `--policy-sha256`. Verify the canonical summary bundle with `parison verify-analysis SERIES`; use `parison drilldown` only for explicitly selected groups from raw-sensitivity bundles and check the raw artifact with `parison verify-drilldown`.

Start a new local migration check with `parison init migration-check`. The command writes a minimal keyed recipe, matching smoke-test inputs and a short workflow guide into a missing or empty directory; it never overwrites an existing project.

```sh
python -m pip install \
  https://github.com/raghavkandpal/parison/releases/download/1.5.0/parison-1.5.0-py3-none-any.whl
parison --version
parison validate-recipe examples/orders.recipe.json
parison validate-inputs --recipe examples/orders.recipe.json \
  --baseline examples/baseline.csv --candidate examples/candidate.csv
parison explain examples/orders.recipe.json
parison compare --recipe examples/orders.recipe.json \
  --baseline examples/baseline.csv --candidate examples/candidate.csv \
  --output runs/orders-example
parison verify runs/orders-example
parison verify runs/orders-example --json
parison inspect runs/orders-example
```

`draft-recipe` inspects both inputs and writes a valid starting recipe with suggested keys, data types, scope metadata and exclusion rationales. Review every suggestion, then use `validate-recipe` as the structural gate. See the [recipe draft contract and workflow](docs/0.2/22-recipe-draft-contract.md).

The [`examples/0.5`](examples/0.5) workflow combines gzip TSV, a custom candidate delimiter, side-specific null tokens, column mappings and normalization in one summary-only comparison.

Recipes can map renamed source columns to one canonical field. Keys, policies, counts and discrepancy evidence continue to use the canonical name. See the [column-mapping contract](docs/0.3/28-column-mapping-contract.md).

A generated PASS bundle is checked in under [`examples/output`](examples/output), containing [`result.json`](examples/output/result.json), [`effective-recipe.json`](examples/output/effective-recipe.json), [`report.html`](examples/output/report.html), and [`manifest.json`](examples/output/manifest.json). It is summary-only and contains no source keys or raw values.

To compare Parquet files, install `"parison[parquet] @ https://github.com/raghavkandpal/parison/releases/download/1.5.0/parison-1.5.0-py3-none-any.whl"`. Local [JSON Lines](docs/0.2/23-json-lines-contract.md) and read-only [SQLite table](docs/0.2/24-sqlite-contract.md) inputs are also supported, including mixed-format comparisons. Recipes are strict JSON; YAML and a local UI are intentionally deferred. Exit codes are `0` PASS, `1` FAIL, `2` ERROR, `3` INCONCLUSIVE and `130` interrupted. A completed run directory contains the effective recipe, canonical result JSON, self-contained HTML report and integrity manifest. Results record the semantic contract plus Python, platform, package and optional Polars versions without recording hostnames.

A baseline or candidate may also be a directory of same-format CSV, TSV, JSON Lines or Parquet files. Parison treats its immediate files as one logical input and enforces limits, schemas and identity across partitions. See the [partitioned-input contract](docs/0.3/30-partitioned-input-contract.md).

Local CSV, TSV and JSON Lines inputs may be gzip-compressed with `.csv.gz`, `.tsv.gz`, `.jsonl.gz` or `.ndjson.gz` extensions, including inside partition directories. The physical-byte guard still applies, and `--max-decoded-bytes` independently limits their combined decoded size. See the [compressed-input contract](docs/0.5/48-compressed-input-contract.md).

Recipes may set independent one-character baseline and candidate delimiters. Omitted delimiter policy preserves comma-separated behavior; drafting suggests tab only for `.tsv` inputs. Effective delimiters are fingerprinted and recorded in preflight and comparison evidence. See the [delimited-text contract](docs/0.5/51-delimited-text-contract.md).

Delimited inputs may also declare independent baseline and candidate null-token lists. Tokens are exact and case-sensitive, empty strings cannot be configured as null tokens, and drafting safely proposes no tokens. See the [null-token contract](docs/0.5/52-null-token-contract.md).

String columns may opt into ordered `trim`, `casefold` and `unicode_nfc` normalization. Normalization is applied before key identity and field comparison; exact comparison remains the default. See the [normalization contract](docs/0.3/31-normalization-contract.md).

Use `validate-inputs` to check physical schemas, mappings, exclusions and partition layouts before reading and comparing all records. Add `--records` to scan configured types and key identity, returning aggregate invalid-row, invalid-field, null-key and duplicate-key counts without keys or values. Its JSON output contains the effective-policy fingerprint and accepts the same `--expected-policy-sha256 HASH` gate as `compare`. See the [input-preflight contract](docs/0.3/32-input-preflight-contract.md) and [record-validation contract](docs/0.6/55-record-validation-contract.md).

Use `parison explain` to review the fully expanded policy and obtain its `policy_sha256`. CI can pass that value to `compare --expected-policy-sha256 HASH`; Parison rejects a malformed or changed policy before opening either input. The fingerprint checks equality only—it is not a signature or proof of approval. Installed Draft 2020-12 schemas are available through `parison schema recipe|result|manifest|preflight`.

Aggregate-v1 execution uses strict recipe v2 files and supports global or grouped `count`, `sum`, `min` and `max`, exact scaled-decimal accumulation, numeric tolerances, bounded groups and summary-safe evidence. Use `draft-recipe --aggregate` for an explicitly requested starting policy. See the [aggregate-v1 contract](docs/0.7/60-aggregate-contract.md) and [aggregate user guide](docs/0.7/61-user-guide.md).

Multiset-v1 execution uses recipe v3 files for exact keyless comparison where duplicate occurrence counts matter. It uses canonical typed row encoding, bounded distinct-row memory and deterministic evidence. Use `draft-recipe --multiset` to request this mode explicitly. See the [multiset contract](docs/0.8/66-multiset-contract.md) and [multiset user guide](docs/0.8/68-user-guide.md).

`parison inspect RUN_DIRECTORY` returns safe metadata from a verified bundle. `parison export-evidence RUN_DIRECTORY --output evidence.jsonl` exports a bounded projection only from an existing raw-sensitivity sample; classification, kind and exact field/measure filters are available. See the [investigation guide](docs/0.9/72-investigation-guide.md) and [frozen contract](docs/0.9/74-investigation-contract.md).

`parison validate-suite PLAN` validates an ordered migration-level plan, and `parison run-suite --plan PLAN --output DIRECTORY` runs its keyed, aggregate and multiset cases sequentially into one atomic parent bundle. `verify` recursively checks every child; `inspect` reports safe suite metadata. See the [suite user guide](docs/0.10/79-suite-user-guide.md) and [suite-v1 contract](docs/0.10/78-suite-contract.md).

Suite-v2 plans add tags, deterministic case selection and per-case limits. `run-suite` can publish independently verifiable external shards; `assemble-suite` requires exact non-overlapping coverage and restores plan order. Explicit workspaces support digest-validated `--resume`, while `report-ci` exports bounded Markdown or JUnit-style summaries from verified bundles. See the [scalable suite guide](docs/0.11/85-user-guide.md) and [suite-v2 contract](docs/0.11/84-scalable-suite-contract.md).

Parison 0.12 can execute independent local suite cases with `run-suite --jobs N`, where `N` is between 1 and 16. Workers use isolated child destinations and final suite results remain in declared plan order. Existing resource limits apply to each active case, so peak resource use can approach `N` times one case; `--jobs 1` remains the default. Interruption stops new admission, bounds worker shutdown and preserves only verified children for explicit resume. See the [concurrency guide](docs/0.12/92-user-guide.md) and [frozen contract](docs/0.12/90-concurrency-contract.md).

Parison 0.13 adds installed union schemas for offline editor validation and an explicit local SQLite catalog of verified safe run metadata. Use `parison export-editor-schemas --output .parison`, then `parison catalog add|list|show|remove --database PATH` for zero-custody run discovery. See the [0.13 guide](docs/0.13/98-user-guide.md).

Parison 0.15 extends that catalog with `history --policy-sha256 HASH` and `diff LEFT RIGHT`. History uses catalog insertion order and reports same-policy outcome transitions; diff refuses policy mismatch and compares only stored safe projections. See the [rehearsal history guide](docs/0.15/102-user-guide.md).

The synthetic [payout reconciliation starter suite](examples/0.15) layers category-level count and exact-decimal conservation with transaction-level diagnosis. It includes an intentionally failing ledger fixture and states the settlement and extraction guarantees that remain upstream responsibilities.

The [feature-pipeline parity starter suite](examples/0.15/features) combines keyed feature tolerances with exact duplicate-aware checking for a keyless batch, while explicitly excluding statistical drift and model-quality claims.

The [orchestrator integration guide](docs/0.16/110-orchestrator-integration-guide.md) and [tested references](examples/integrations) show how generic CI, dbt, Airflow and Dagster can invoke Parison after coordinated user-owned extraction without giving Parison warehouse credentials.

The [evidence handoff guide](docs/0.17/116-evidence-handoff-guide.md) shows how to export a deterministic in-toto Statement, authenticate its exact bytes with an external signer such as Cosign, and bind that authenticated claim back to a recursively verified local bundle. Parison does not create or verify signatures; identity and issuer policy remain external.

In a 0.18 release checkout:

```sh
parison statement runs/orders-example --output parison-statement.json
parison verify-statement runs/orders-example parison-statement.json
parison report-cutover runs/orders-example --output cutover.md
```

Parison 0.14 can run multiset-v1 comparison through a bounded disposable SQLite workspace: add `--engine sqlite --max-temp-bytes BYTES`, and optionally select a protected parent with `--temp-directory DIR`. Suite-v2 cases can record the same choice under `execution`. See the [released contract](docs/0.14/96-spill-engine-contract.md); benchmark measurements remain evidence, not a universal scale guarantee.

The first [SQLite-engine benchmark](benchmarks/results-2026-10-11-spill.json) compares fresh processes at 10k and 100k high-cardinality rows. On the recorded 100k case, SQLite traded roughly 3× runtime and 33 MiB of temporary disk for an approximately 87% lower process peak RSS. This is machine-specific evidence, not a supported capacity claim.

`output.sensitivity` defaults to `summary`, which stores no source keys or values. Set it explicitly to `raw` to include a bounded discrepancy sample, and protect that output as sensitive data. `--sample-limit` controls the maximum number of raw field differences written. Comparison errors also publish a summary-only diagnostic bundle when the output destination is available.

Every recipe must declare a source snapshot, extraction cutoff, intended filters, full-scope completeness, whether an empty scope is expected, and whether two non-key null values are equal. These are recorded provenance assertions; Parison cannot independently prove that upstream pipelines honored them.

Combined physical input size and combined decoded gzip size are each limited to 1 GB by default, and each input is limited to 5 million rows; override these with `--max-input-bytes`, `--max-decoded-bytes` and `--max-rows`. These are processing guards, not an operating-system memory sandbox. Ctrl-C returns exit code `130` and publishes a summary-only INTERRUPTED bundle when possible.

The built-wheel suite runs in CI on Python 3.11--3.14 across Linux, macOS and Windows; optional Parquet coverage runs when Polars is installed.

For repeatable local measurements, run `PYTHONPATH=src python benchmarks/run.py`. The seeded harness reports elapsed time and Python allocation without claiming a supported scale envelope.

Generate larger accuracy/performance inputs with:

```sh
PYTHONPATH=src python benchmarks/generate_cases.py
PYTHONPATH=src python benchmarks/run_cases.py \
  --repeats 3 --max-memory-per-row 3000 \
  benchmarks/generated/rows-10000 benchmarks/generated/rows-100000 \
  benchmarks/generated/rows-250000
```

Each generated case includes baseline and candidate CSV files, a recipe, and exact expected counts. Generated data is ignored by Git and can be recreated at larger sizes with `--rows`.

Generate and measure global, low-cardinality and high-cardinality aggregate profiles with:

```sh
PYTHONPATH=src python benchmarks/generate_aggregate_cases.py --rows 10000 100000
PYTHONPATH=src python benchmarks/run_cases.py --repeats 3 \
  benchmarks/generated/aggregate-global-10000 \
  benchmarks/generated/aggregate-low-10000 \
  benchmarks/generated/aggregate-high-10000
```

The first aggregate measurement across all three profiles is recorded in [`benchmarks/results-2026-10-09-aggregate.json`](benchmarks/results-2026-10-09-aggregate.json). It is a machine-specific engineering measurement, not a supported scale guarantee.

To generate and measure equivalent Parquet inputs:

```sh
PYTHONPATH=src python benchmarks/generate_cases.py --parquet
PYTHONPATH=src python benchmarks/run_cases.py --format parquet \
  benchmarks/generated/rows-10000 benchmarks/generated/rows-100000 \
  benchmarks/generated/rows-250000
```

The first recorded 10k/100k/250k accuracy and performance run is in [`benchmarks/results-2026-10-05.json`](benchmarks/results-2026-10-05.json). Accepted streaming results are recorded for [CSV](benchmarks/results-2026-10-06-streaming.json) and [Parquet](benchmarks/results-2026-10-06-parquet-streaming.json), with the pre-optimization [Parquet baseline](benchmarks/results-2026-10-06-parquet-baseline.json) retained for comparison. These are machine-specific engineering measurements, not supported scale guarantees.

Suite-v2 orchestration can be measured with `python benchmarks/run_suite_cases.py`. The first accuracy-verified 10-, 25- and 100-case clean, sequential-shard, assembly and resume measurements are recorded in [`benchmarks/results-2026-10-10-suite-v2.json`](benchmarks/results-2026-10-10-suite-v2.json). They measure local orchestration overhead, not external parallel speedup or a supported performance guarantee.

The 0.12 harness also measures local `--jobs 2` and `--jobs 4` execution. The first [accuracy-verified concurrency result](benchmarks/results-2026-10-10-suite-concurrency.json) is intentionally based on tiny fixtures: process startup made both concurrent variants slower than `--jobs 1`. It is overhead evidence, not a throughput claim; representative CPU-heavy measurements are still required before release.

A subsequent [mixed-mode 100k-row measurement](benchmarks/results-2026-10-10-suite-concurrency-mixed-100k.json) ran three keyed, three aggregate, and three multiset cases. All bundles verified with equivalent ordered outcomes. Jobs 1, 2, and 4 took 17.278s, 10.288s, and 6.384s while sampled aggregate process-tree RSS rose from about 264 MiB to 572 MiB and 1.0 GiB respectively. This is machine-specific evidence, not a performance or memory guarantee.

## Documentation

Start with the [documentation index](docs/README.md).

- Current task-oriented usage: [1.x user guide](docs/user-guide.md)
- Exact CLI syntax: [generated command reference](docs/command-reference.md)
- Current development state: [active handoff](docs/CURRENT.md)
- Future direction research: [adoption-led post-1.0 decision](docs/0.20/134-post-1.0-direction-research.md)
- Product direction and release arc: [accepted direction](docs/0.15/104-product-direction-and-release-arc.md)
- Next opportunities: [real-world application research](docs/0.14/94-real-world-application-research.md)
- CI integration: [GitHub Actions reference](docs/0.2/20-github-actions.md)
- Comparison contract: [0.1 semantics](docs/0.1/05-comparison-semantics.md)
- Safety model: [0.1 security and data handling](docs/0.1/07-security-and-data-handling.md)
- Measured limits: [0.1 tested support envelope](docs/0.1/13-tested-support-envelope.md)
- Released evidence: [0.1 release verification](docs/0.1/17-release-candidate-verification.md)

Release preparation is tracked in [`RELEASING.md`](RELEASING.md). The preliminary alpha name screen and release-candidate rehearsal passed; the name screen is not a legal opinion or formal trademark clearance.

The bounded alpha will be distributed as wheel and source-archive assets on a tagged GitHub Release. PyPI publication is intentionally deferred.

Parison is released under the [MIT License](LICENSE).

## Security and evidence

Do not commit real datasets, credentials or sensitive comparison artifacts. Local execution alone is not a security guarantee; proposed controls and acceptance criteria are detailed in the security document.

Parison has passed only a preliminary name screen; formal trademark clearance remains outstanding.
