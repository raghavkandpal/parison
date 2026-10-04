# Parity product thesis

## Recommendation

Explore Parity as a developer tool for **repeatable output-parity testing and difference investigation**. Do not market it as a novel diff algorithm, a universal data-quality platform or a certificate that a migration is correct.

The starting promise is: “Define how two outputs should agree, run the comparison locally, and inspect reproducible evidence of where they do not.” A user should be able to bring two files without adopting a warehouse, orchestration framework or subscription.

## The actual job

A transformation changes from implementation A to implementation B. Both run on the same controlled input snapshot. The engineer needs to establish which output differences are expected, which require investigation and which cannot be evaluated because the matching assumptions are invalid.

This is distinct from tracking yesterday versus today, when real-world changes may explain differences. It is also distinct from checking whether an individual table satisfies an expectation. Parity can complement those checks, but should not absorb them all.

Illustrative use cases include a pandas-to-Polars refactor, an SQL rewrite, a new parser replacing a legacy parser, an export-format change and a batch pipeline migration. The tool compares outputs; it does not execute untrusted transformation code or prove equivalence for every possible input.

## Initial customer hypothesis

The initial user is an individual data engineer or a small engineering team with recurring CSV/Parquet output comparisons. They already understand keys, schemas and reporting scope. Their friction is repeated configuration and exception investigation, not an inability to write Python.

The buyer, if one emerges, might be an engineering lead funding shared recipes, review history or supported distribution. Independent consultants could purchase a polished local workbench for repeated client engagements. Both hypotheses need validation; developer enthusiasm does not automatically produce budget.

Avoid targeting large enterprise warehouse migrations initially. They often involve network access, procurement, platform-specific connectors, data volumes and support commitments beyond a solo side project's capacity.

## Product boundary

| In the first credible product | Explicitly deferred |
| --- | --- |
| Local CSV and Parquet | Warehouse and object-store connectors |
| Composite unique keys | Fuzzy entity resolution and automatic deduplication |
| Declared mappings and typed rules | Arbitrary Python, SQL or plugin execution from a recipe |
| Missing/extra records and field differences | ETL generation or automated repairs |
| Full counts with bounded evidence samples | General-purpose observability and anomaly detection |
| Recipe, engine and input provenance | Enterprise attestations or compliance certification |
| Local HTML and JSON reports | Hosted data uploads and shared identity systems |

## Why the product might matter

The proposed value is a consistent procedure rather than a script for one dataset: explicit parse decisions, visible identity assumptions, inspectable rules, stable results and evidence that can be rerun. These are design goals, not unique capabilities demonstrated by this research.

The closest competition already covers substantial functionality. See [the competitor assessment](02-competitors.md). The market question is whether Parity reduces total work enough to justify its installation and continued use. A beautiful report over an existing library may be useful, but should not be confused with a durable business.

## What a user should understand after a run

1. Were the inputs and scope comparable?
2. Did the declared keys uniquely identify every evaluated record?
3. Which fields were compared, transformed, excluded or unsupported?
4. How many records were missing, additional, different or within tolerance?
5. What rule explains each classification?
6. Was the run complete, sampled, interrupted or resource-limited?
7. Which recipe and software version produced it?

The headline should be “PASS under recipe v3 across the declared scope,” never “the data is correct.” An all-green report over the wrong snapshot remains misleading. A matching baseline can itself contain bugs.

## Evidence of usefulness

Before growing scope, demonstrate that unfamiliar engineers can diagnose known injected defects and explain the outcome faster or more reliably than with their current method. Measure setup, investigation, rerun and evidence-sharing time separately. Then check whether users return for a second real comparison without founder assistance.

Proceed if the workflow saves meaningful repeated effort. Narrow toward an evidence/reporting layer if the comparison engine adds no incremental value. Stop commercialization if existing tools or generated scripts meet the same need with less maintenance.
