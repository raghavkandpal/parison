# Parison research and proposed product design

Research date: 4 October 2026. Implementation evidence reviewed 6 October 2026: the CLI vertical slice, semantic corpus, benchmark matrix, release packaging and cross-platform CI now exist; customer interviews and independent workflow trials remain incomplete.

Parison would help data engineers evaluate whether a pipeline refactor or migration preserves intended output. The recommended starting point is a local CLI with a portable investigation report, not a hosted data platform. Its engine is deterministic and does not require AI.

The research supports a **bounded discovery and prototype**, not an unconditional business launch. Basic comparison is already well served. The potential opening is reducing the effort between configuring a trustworthy comparison, understanding its exceptions and rerunning the same procedure in CI. That opening must be demonstrated against existing tools and AI-generated scripts.

## Reading guide

| Document | Main question |
| --- | --- |
| [Product thesis](01-product-thesis.md) | Who is this for, and what should we deliberately not build? |
| [Competitors and existing tools](02-competitors.md) | What already solves this problem, and where might Parison fit? |
| [Market and monetization](03-market-and-monetization.md) | How could it attract users and sustain an independent business? |
| [Workflows and usability](04-workflows-and-usability.md) | How do configuration, execution, investigation and CI connect? |
| [Comparison semantics](05-comparison-semantics.md) | Exactly what does a result mean, including difficult data cases? |
| [Proposed architecture](06-proposed-architecture.md) | What is the smallest credible implementation and how can it grow? |
| [Security and data handling](07-security-and-data-handling.md) | What can leak or be corrupted even in a local application? |
| [AI development and optional AI research](08-ai-development-and-optional-ai.md) | Can the product survive AI-generated alternatives without using AI itself? |
| [Validation and delivery plan](09-validation-and-delivery.md) | What evidence should determine whether we proceed? |
| [Sources and evidence gaps](10-sources-and-evidence.md) | Which claims have primary sources, and what remains unverified? |
| [Engine compatibility spike](11-engine-compatibility-spike.md) | Can DataComPy implement Parison's pinned comparison contract? |
| [Performance optimization plan](12-performance-optimization-plan.md) | Which measured costs should the next implementation session remove first? |
| [Tested support envelope](13-tested-support-envelope.md) | Which input shapes and sizes have actually been measured? |
| [Built evidence review](14-built-evidence-review.md) | Which earlier questions can the current implementation answer, and which still require humans or external evidence? |
| [Unfamiliar-user test 01](15-unfamiliar-user-test.md) | Can a new user install Parison and correctly interpret failure, ambiguous identity and tolerance behavior? |

## Recommended initial decisions

The eight Mermaid diagrams have been parsed, rendered and visually checked. [PNG versions](diagrams/README.md) are included for readers whose Markdown viewer does not support Mermaid.

- Target engineers comparing exported outputs for the same input snapshot and scope.
- Support local CSV and Parquet first; no database credentials or cloud storage connectors.
- Start with keyed record comparison; reject ambiguous identity rather than guessing.
- Produce machine-readable results and self-contained HTML from one result model.
- Keep recipes in Git and datasets outside Git. Freeze the recipe used by each run.
- Keep the contract-specific engine after the DataComPy compatibility spike; use external engines only as differential references where semantics overlap.
- Keep the engine, evidence format and test corpus usable without any model subscription.
- Do not build hosted collaboration until recurring team demand and security requirements are established.

## How to read the evidence

“Observed” means documented by the linked maintainer/vendor at research time, not independently verified by execution. “Proposed” means our design. “Hypothesis” means a market or usability assumption. Prices and commercial scenarios in this dossier are experiments, not forecasts or competitor quotes. Public marketing does not establish adoption, profitability, accuracy or comparative performance.

No employer data, code, configurations or internal requirements are used. No actuarial positioning, personal-workout-app reference or enterprise workflow analogy is part of the design. Parison has passed a preliminary package, domain and trademark screen; formal trademark clearance has not been performed.
