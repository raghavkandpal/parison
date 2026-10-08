# Parison

Local-first, deterministic output comparison for data pipeline refactors and migrations.

Parison is an independent data-engineering side project. The proposed product compares baseline and candidate outputs under a reviewed, reusable recipe, then produces machine-readable results and a portable investigation report. It does not require an AI model or upload datasets to a hosted service.

## Project status

**0.4 development.** The released 0.3.0 CLI provides strict keyed comparison, reviewable recipe generation, explicit column mappings and normalization, partitioned local datasets, schema preflight, JSON/HTML evidence bundles, and CI-oriented exit codes. Development is deepening schema preflight with structured diagnostics.

Parison is an open-source, zero-custody tool. Comparisons run in the user's environment; Parison will not receive or store customer production data. Monetization and commercial packaging are outside the current roadmap.

## Try it

Python 3.11 or newer is required.

```sh
python -m pip install \
  https://github.com/raghavkandpal/parison/releases/download/0.3.0/parison-0.3.0-py3-none-any.whl
parison --version
parison validate-recipe examples/orders.recipe.json
parison validate-inputs --recipe examples/orders.recipe.json \
  --baseline examples/baseline.csv --candidate examples/candidate.csv
parison explain examples/orders.recipe.json
parison compare --recipe examples/orders.recipe.json \
  --baseline examples/baseline.csv --candidate examples/candidate.csv \
  --output runs/orders-example
parison verify runs/orders-example
```

`draft-recipe` inspects both inputs and writes a valid starting recipe with suggested keys, data types, scope metadata and exclusion rationales. Review every suggestion, then use `validate-recipe` as the structural gate. See the [recipe draft contract and workflow](docs/0.2/22-recipe-draft-contract.md).

Recipes can map renamed source columns to one canonical field. Keys, policies, counts and discrepancy evidence continue to use the canonical name. See the [column-mapping contract](docs/0.3/28-column-mapping-contract.md).

A generated PASS bundle is checked in under [`examples/output`](examples/output), containing [`result.json`](examples/output/result.json), [`effective-recipe.json`](examples/output/effective-recipe.json), [`report.html`](examples/output/report.html), and [`manifest.json`](examples/output/manifest.json). It is summary-only and contains no source keys or raw values.

To compare Parquet files, install `"parison[parquet] @ https://github.com/raghavkandpal/parison/releases/download/0.3.0/parison-0.3.0-py3-none-any.whl"`. Local [JSON Lines](docs/0.2/23-json-lines-contract.md) and read-only [SQLite table](docs/0.2/24-sqlite-contract.md) inputs are also supported, including mixed-format comparisons. Recipes are strict JSON in this first slice; YAML and a local UI are intentionally deferred. Exit codes are `0` PASS, `1` FAIL, `2` ERROR, `3` INCONCLUSIVE and `130` interrupted. A completed run directory contains the effective recipe, canonical result JSON, self-contained HTML report and integrity manifest. Results record the semantic contract plus Python, platform, package and optional Polars versions without recording hostnames.

A baseline or candidate may also be a directory of same-format CSV, JSON Lines or Parquet files. Parison treats its immediate files as one logical input and enforces limits, schemas and identity across partitions. See the [partitioned-input contract](docs/0.3/30-partitioned-input-contract.md).

String columns may opt into ordered `trim`, `casefold` and `unicode_nfc` normalization. Normalization is applied before key identity and field comparison; exact comparison remains the default. See the [normalization contract](docs/0.3/31-normalization-contract.md).

Use `validate-inputs` to check physical schemas, mappings, exclusions and partition layouts before reading and comparing all records. Its JSON output contains schema metadata but no record values. See the [input-preflight contract](docs/0.3/32-input-preflight-contract.md).

Use `parison explain` to review the fully expanded policy and obtain its `policy_sha256`. CI can pass that value to `compare --expected-policy-sha256 HASH`; Parison rejects a malformed or changed policy before opening either input. The fingerprint checks equality only—it is not a signature or proof of approval.

`output.sensitivity` defaults to `summary`, which stores no source keys or values. Set it explicitly to `raw` to include a bounded discrepancy sample, and protect that output as sensitive data. `--sample-limit` controls the maximum number of raw field differences written. Comparison errors also publish a summary-only diagnostic bundle when the output destination is available.

Every recipe must declare a source snapshot, extraction cutoff, intended filters, full-scope completeness, whether an empty scope is expected, and whether two non-key null values are equal. These are recorded provenance assertions; Parison cannot independently prove that upstream pipelines honored them.

Combined input size is limited to 1 GB by default and each input to 5 million rows; override these with `--max-input-bytes` and `--max-rows`. These are processing guards, not an operating-system memory sandbox. Ctrl-C returns exit code `130` and publishes a summary-only INTERRUPTED bundle when possible.

The full CSV and Parquet suite runs in CI on Python 3.11 and 3.14.

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

To generate and measure equivalent Parquet inputs:

```sh
PYTHONPATH=src python benchmarks/generate_cases.py --parquet
PYTHONPATH=src python benchmarks/run_cases.py --format parquet \
  benchmarks/generated/rows-10000 benchmarks/generated/rows-100000 \
  benchmarks/generated/rows-250000
```

The first recorded 10k/100k/250k accuracy and performance run is in [`benchmarks/results-2026-10-05.json`](benchmarks/results-2026-10-05.json). Accepted streaming results are recorded for [CSV](benchmarks/results-2026-10-06-streaming.json) and [Parquet](benchmarks/results-2026-10-06-parquet-streaming.json), with the pre-optimization [Parquet baseline](benchmarks/results-2026-10-06-parquet-baseline.json) retained for comparison. These are machine-specific engineering measurements, not supported scale guarantees.

## Documentation

Start with the [documentation index](docs/README.md).

- Step-by-step usage: [user guide](docs/0.2/27-user-guide.md)
- 0.3 workflow: [user guide](docs/0.3/33-user-guide.md)
- Current development: [0.3 roadmap](docs/0.3/29-roadmap.md)
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
