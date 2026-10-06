# Parison

Local-first, deterministic output comparison for data pipeline refactors and migrations.

Parison is an independent data-engineering side project. The proposed product compares baseline and candidate outputs under a reviewed, reusable recipe, then produces machine-readable results and a portable investigation report. It does not require an AI model or upload datasets to a hosted service.

## Project status

**Early vertical slice.** The repository now includes an installable Python CLI for strict keyed CSV comparison, JSON/HTML evidence bundles and CI-oriented exit codes. Parquet input is available through the optional `polars` dependency. The semantic corpus, local benchmark harness, adversarial performance matrix and DataComPy compatibility spike are complete. Two blinded agent-execution trials and one human review of agent-produced evidence are recorded; interviews and direct, unassisted human CLI studies remain planned work.

## Try it

Python 3.11 or newer is required.

```sh
python -m pip install \
  https://github.com/raghavkandpal/parison/releases/download/0.1.0/parison-0.1.0-py3-none-any.whl
parison --version
parison validate-recipe examples/orders.recipe.json
parison compare --recipe examples/orders.recipe.json \
  --baseline examples/baseline.csv --candidate examples/candidate.csv \
  --output runs/orders-example
parison verify runs/orders-example
```

A generated PASS bundle is checked in under [`examples/output`](examples/output), containing [`result.json`](examples/output/result.json), [`effective-recipe.json`](examples/output/effective-recipe.json), [`report.html`](examples/output/report.html), and [`manifest.json`](examples/output/manifest.json). It is summary-only and contains no source keys or raw values.

To compare Parquet files, install `"parison[parquet] @ https://github.com/raghavkandpal/parison/releases/download/0.1.0/parison-0.1.0-py3-none-any.whl"`. Recipes are strict JSON in this first slice; YAML and a local UI are intentionally deferred. Exit codes are `0` PASS, `1` FAIL, `2` ERROR, `3` INCONCLUSIVE and `130` interrupted. A completed run directory contains the effective recipe, canonical result JSON, self-contained HTML report and integrity manifest. Results record the semantic contract plus Python, platform, package and optional Polars versions without recording hostnames.

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

Start with the [research and design index](docs/README.md).

| Document | Contents |
| --- | --- |
| [Product thesis](docs/01-product-thesis.md) | Target users, problem, differentiation and non-goals |
| [Competitors](docs/02-competitors.md) | Existing libraries, developer tools and commercial alternatives |
| [Market and monetization](docs/03-market-and-monetization.md) | Adoption hypotheses, commercial experiments and operating costs |
| [Workflows and usability](docs/04-workflows-and-usability.md) | Recipe lifecycle, comparison, investigation and CI workflows |
| [Comparison semantics](docs/05-comparison-semantics.md) | Keys, types, tolerances, completeness and result meanings |
| [Proposed architecture](docs/06-proposed-architecture.md) | Python CLI, comparison engine, artifacts and optional local UI |
| [Security](docs/07-security-and-data-handling.md) | Threat model, data handling and security release gates |
| [AI resilience and optional AI](docs/08-ai-development-and-optional-ai.md) | Competition from generated scripts; separate optional AI research |
| [Validation and delivery](docs/09-validation-and-delivery.md) | Synthetic fixtures, benchmarks, discovery and build gates |
| [Sources and evidence gaps](docs/10-sources-and-evidence.md) | Primary research sources and outstanding questions |
| [Engine compatibility spike](docs/11-engine-compatibility-spike.md) | Executed DataComPy cases and engine decision |
| [Performance optimization plan](docs/12-performance-optimization-plan.md) | Measured hotspots and next-session implementation sequence |
| [Tested support envelope](docs/13-tested-support-envelope.md) | Measured input shapes, sizes, memory use and explicit boundaries |
| [Built evidence review](docs/14-built-evidence-review.md) | Questions resolved by the implementation versus questions that still require human or external evidence |
| [Unfamiliar-user test 01](docs/15-unfamiliar-user-test.md) | Participant protocol, scoring rubric, rehearsal observations and decision rule |
| [Name-clearance screen](docs/16-name-clearance-screen.md) | Preliminary package, registry and trademark screen for Parison / `parison` |
| [Release candidate verification](docs/17-release-candidate-verification.md) | Clean 0.1.0 build, installation, test, smoke and archive evidence |
| [0.2 product research](docs/18-0.2-product-research.md) | Ranked next-release options, recommended CI theme and evidence gates |
| [0.2 agenda](docs/19-0.2-agenda.md) | Selected workstreams, sequence, acceptance gates and non-goals |

Release preparation is tracked in [`RELEASING.md`](RELEASING.md). The preliminary alpha name screen and release-candidate rehearsal passed; the name screen is not a legal opinion or formal trademark clearance.

The bounded alpha will be distributed as wheel and source-archive assets on a tagged GitHub Release. PyPI publication is intentionally deferred.

Parison is released under the [MIT License](LICENSE).

Mermaid diagrams are included in the documents. [PNG alternatives](docs/diagrams/README.md) are available for viewers without Mermaid support.

## Build direction

1. Continue expanding the synthetic corpus around false-PASS risks.
2. Keep the contract-specific engine; the pinned DataComPy spike found incompatible identity, tolerance and Decimal evidence semantics.
3. Harden packaging and continue direct-human CLI validation while preparing a bounded alpha.
4. Expand performance measurements across row widths, mismatch rates and constrained resources.
5. Add a localhost visual interface only if usability evidence justifies it.

The initial application would execute on a user's laptop or customer-owned CI runner. Hosted collaboration, database connectors and optional AI features are deferred. Market demand and differentiation must be tested against existing tools and AI-generated scripts.

## Security and evidence

Do not commit real datasets, credentials or sensitive comparison artifacts. Local execution alone is not a security guarantee; proposed controls and acceptance criteria are detailed in the security document.

Research was assembled on 4 October 2026. Vendor documentation is not an independent product evaluation. Proposed pricing and adoption targets are hypotheses, not forecasts. Parison has passed only a preliminary name screen; formal trademark clearance remains outstanding. The project uses the MIT License.
