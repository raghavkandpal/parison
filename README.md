# Parity

Local-first, deterministic output comparison for data pipeline refactors and migrations.

Parity is an independent data-engineering side project. The proposed product compares baseline and candidate outputs under a reviewed, reusable recipe, then produces machine-readable results and a portable investigation report. It does not require an AI model or upload datasets to a hosted service.

## Project status

**Early vertical slice.** The repository now includes an installable Python CLI for strict keyed CSV comparison, JSON/HTML evidence bundles and CI-oriented exit codes. Parquet input is available through the optional `polars` dependency. Interviews, competitor trials, usability studies and performance benchmarks remain planned work.

## Try it

Python 3.11 or newer is required.

```sh
python -m pip install -e .
parity validate-recipe examples/orders.recipe.json
parity compare --recipe examples/orders.recipe.json \
  --baseline baseline.csv --candidate candidate.csv --output run
parity verify run
```

Install `.[parquet]` to compare Parquet files. Recipes are strict JSON in this first slice; YAML and a local UI are intentionally deferred. Exit codes are `0` PASS, `1` FAIL, `2` ERROR, `3` INCONCLUSIVE and `130` interrupted. A completed run directory contains the effective recipe, canonical result JSON, self-contained HTML report and integrity manifest.

`output.sensitivity` defaults to `summary`, which stores no source keys or values. Set it explicitly to `raw` to include a bounded discrepancy sample, and protect that output as sensitive data. `--sample-limit` controls the maximum number of raw field differences written. Comparison errors also publish a summary-only diagnostic bundle when the output destination is available.

Combined input size is limited to 1 GB by default and each input to 5 million rows; override these with `--max-input-bytes` and `--max-rows`. These are processing guards, not an operating-system memory sandbox. Ctrl-C returns exit code `130` and publishes a summary-only INTERRUPTED bundle when possible.

The full CSV and Parquet suite runs in CI on Python 3.11 and 3.14.

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

Mermaid diagrams are included in the documents. [PNG alternatives](docs/diagrams/README.md) are available for viewers without Mermaid support.

## Build direction

1. Establish a synthetic test corpus and an explicit comparison contract.
2. Evaluate a pinned DataComPy adapter before writing a custom Polars kernel.
3. Build a vertical slice: local CSV/Parquet inputs, strict recipe validation, keyed comparison, JSON results and self-contained HTML reports.
4. Verify correctness, privacy, resource limits and CI exit-code behavior before distributing a packaged alpha.
5. Add a localhost visual interface only if usability evidence justifies it.

The initial application would execute on a user's laptop or customer-owned CI runner. Hosted collaboration, database connectors and optional AI features are deferred. Market demand and differentiation must be tested against existing tools and AI-generated scripts.

## Security and evidence

Do not commit real datasets, credentials or sensitive comparison artifacts. Local execution alone is not a security guarantee; proposed controls and acceptance criteria are detailed in the security document.

Research was assembled on 4 October 2026. Vendor documentation is not an independent product evaluation. Proposed pricing and adoption targets are hypotheses, not forecasts. The Parity name and distribution license have not yet been cleared or selected.
