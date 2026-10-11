# Real-world applications and adoption opportunities for Parison 0.14

Date: 11 October 2026

Status: **research recommendation**

## Question and boundary

This review asks where Parison's released local comparison contracts solve real operational problems, and which small additions could make the tool useful more often. It uses primary sources owned by the systems or projects discussed. It is product-direction evidence, not evidence of market size, user demand or willingness to pay.

The recommendation preserves Parison's current boundary: users materialize local inputs; Parison neither connects to production systems nor stores data remotely. That boundary is useful rather than incidental. Database connectors would make Parison responsible for credentials, pagination, source load and cross-system snapshot consistency, while the applications below can all export bounded snapshots through tools the user already operates.

## Where Parison fits today

### Database migrations and CDC cutovers

AWS DMS validates migrations by matching source and target rows and reporting mismatches. Its documentation also exposes the difficult parts of the workflow: validation adds source, target and network load; tables normally need a primary or unique key; continuously changing records can be suspended; and CDC validation delays and retries comparisons to reduce false positives. AWS explicitly describes a validation-only task used just before or during a production cutover to obtain the current mismatch count ([AWS DMS data validation](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Validating.html)).

Google's migration guidance likewise requires completeness and consistency verification, but warns that directly comparing source and target is insufficient when the migration intentionally filters records unless those exclusions are also accounted for ([Google Cloud database migration principles](https://docs.cloud.google.com/architecture/database-migration-concepts-principles-part-1)).

Parison's keyed mode, declared filters and completeness, policy lock, bounded evidence and suite bundle already fit a **post-extraction cutover gate**. A migration process can export both sides at a reviewed watermark, run a suite, retain the verified bundle and make the cutover decision without granting Parison database credentials. Parison should not claim continuous CDC validation: it cannot prove that independently produced exports share a watermark.

### Data warehouse migrations, refactors and backfills

Google recommends staged, iterative warehouse migration and points users to its Data Validation Tool after transfer. The documented validation examples include `count`, `sum` and `average` across selected columns ([BigQuery schema and data transfer](https://docs.cloud.google.com/bigquery/docs/migration/schema-data-overview)). Google also says pipeline migrations must validate historic and new reports because both schemas and queries may change ([BigQuery pipeline migration](https://docs.cloud.google.com/bigquery/docs/migration/pipelines)). For cross-region moves, where the original and copy cannot be joined directly, Google recommends comparing summaries or hashes computed independently on each side ([Google Cloud cross-region workload migration](https://docs.cloud.google.com/architecture/migrate-across-regions/prepare-data-and-batch-workloads)).

dbt's model is complementary: data tests are reusable assertions over models and sources, return failing records, and are intended to run while code is written and after production transformations. dbt specifically recommends primary-key uniqueness/non-null checks and recurring source-assumption tests ([dbt data tests](https://docs.getdbt.com/docs/build/data-tests)). Its freshness checks can fail a pipeline when a source misses an SLA, and dbt recommends retaining longitudinal results to understand trends ([dbt source freshness](https://docs.getdbt.com/reference/commands/source)).

Parison already covers the missing **old-output versus new-output equivalence** layer: aggregate mode provides count/sum/min/max invariants, keyed mode diagnoses changed records, multiset mode handles keyless outputs, and suites combine all three. This is directly usable for SQL rewrites, warehouse moves, historical backfills, materialization changes and dual-run pipeline deployments.

### Financial and payout reconciliation

Stripe recommends balance transactions as the starting point for reporting because every movement into or out of an account balance creates one. Those records have a related source identifier, status and reporting category; Stripe recommends `reporting_category` rather than raw transaction `type` for accounting classification ([Stripe balance transaction types](https://docs.stripe.com/reports/balance-transaction-types), [Stripe reporting categories](https://docs.stripe.com/reports/reporting-categories)). An automatic payout can combine many charges, refunds and fees. Stripe's reconciliation workflow identifies the payout, lists the associated balance transactions and follows each transaction's source object; for manual payouts Stripe says the user is responsible for reconciling the payout against transaction history ([Stripe payout reconciliation](https://docs.stripe.com/payouts/reconciliation)).

Parison can therefore verify exported processor records against a ledger or warehouse using exact identifiers, scaled decimals, category groups and count/sum conservation. The appropriate claim is **reconciliation evidence for supplied snapshots**, not that Parison establishes accounting correctness: settlement state, currency conversion, reversals and the extraction period remain upstream responsibilities.

### ML and feature-pipeline parity

TensorFlow Data Validation distinguishes schema skew, feature skew and distribution skew. It attributes feature skew to different data sources or different feature-generation logic between training and serving, and compares consecutive spans for drift ([TensorFlow Data Validation tutorial](https://www.tensorflow.org/tfx/tutorials/data_validation/tfdv_basic)). TFX also recommends using the same transformation implementation for training and inference to avoid training-serving skew, and describes gating a candidate model against baseline metrics ([TFX user guide](https://www.tensorflow.org/tfx/guide)).

Parison's credible near-term role is narrower: compare **materialized feature rows produced by two implementations** during a feature-pipeline rewrite, using keyed exact/tolerant columns and aggregate or multiset cases. Statistical distribution metrics such as Jensen-Shannon divergence are a distinct contract with approximation and threshold semantics; TFDV already owns that problem, and Parison should not add a superficial imitation merely to claim ML support.

### CI gates and audit handoff

GitHub describes artifact attestations as signed claims that bind an artifact to build provenance, while stressing that an attestation has value only when verified and does not prove that the artifact is secure ([GitHub artifact attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations)). dbt similarly emits JSON artifacts and uses its manifest for documentation and state comparison ([dbt manifest artifact](https://docs.getdbt.com/reference/artifacts/manifest-json)).

Parison's deterministic JSON, integrity manifest, recursive suite verification, JUnit/Markdown reports and policy fingerprints already make it suitable for CI and review handoff. Its manifest proves internal integrity, not authorship. External signing should remain an explicit integration around a stable signing payload rather than an embedded identity or network service.

## Repeated pain points

Across these domains, five needs recur:

1. **Scale without surrendering exactness.** Warehouse transfers, historical backfills, ledgers and full-load validation can all exceed process memory. Vendor guidance responds with grouping, range queries, summaries or distributed execution. Parison currently has explicit row and byte guards but no disk-backed exact engine.
2. **A defensible comparison window.** CDC latency, changing records, settlement states and successive ML spans all make timing part of correctness. Parison records a user assertion for snapshot and cutoff, but cannot prove two exports were coordinated.
3. **Layered verification.** Teams commonly want cheap aggregate coverage followed by row-level diagnosis. Parison already supports both modes in one suite; it needs examples and scale more than a new semantic mode.
4. **Repeated-run interpretation.** Migration rehearsals, scheduled backfills, source-freshness checks and feature spans generate a sequence of runs. Parison's local catalog can find runs but cannot yet summarize how a policy's safe outcome changed over time.
5. **Evidence that travels.** CI, audit and cutover review require a bounded result that another party can verify independently. Parison largely has this; signer authentication is the remaining optional integration point.

## Ranked feature opportunities

### 1. Prototype explicit spill-backed exact comparison

This is the strongest cross-domain capability gap. Add an opt-in backend that stores canonical typed keys/rows and counters in a private run workspace, initially using standard-library SQLite. Start with one mode—prefer multiset because its contract is canonical row occurrence counting and therefore has the smallest join surface—then prove byte-equivalent semantic results against the in-memory engine before extending it.

The backend must not silently activate. A recipe or CLI choice should name it; result metadata should record it; resource limits should bound temporary bytes; and interruption, disk-full and cleanup behavior should be contractual. Temporary state may contain derived sensitive identifiers or values and must receive the same protection as raw evidence.

Acceptance gates:

1. semantic result content matches the existing engine for golden and adversarial corpora, independent of insertion order;
2. a test forces disk use under a deliberately small memory threshold on Linux, macOS and Windows;
3. deterministic discrepancy order and current PASS/FAIL/ERROR/INCONCLUSIVE meanings do not change;
4. a bounded temporary-storage limit fails closed, and success, error and interruption leave no orphaned workspace;
5. benchmarks publish rows, distinct rows, elapsed time, peak RSS and peak temporary bytes without claiming a universal scale limit.

Why first: it improves migration, backfill, finance and feature-parity workflows without expanding trust boundaries or inventing new comparison semantics.

### 2. Add safe catalog history comparison

Extend the explicit local catalog with a read-only command such as `parison catalog history --policy-sha256 HASH` that returns ordered safe metadata and state transitions for one exact policy. A later `catalog diff RUN_A RUN_B` may compare verified summary projections only: outcome, completeness, input digests, discrepancy/count summaries and runtime/backend metadata. It must never treat two different policy fingerprints as a trend and must not read raw evidence.

This would support migration rehearsals, repeated backfills and span-based pipeline checks using storage Parison already owns. Keep timestamps as display metadata, not identity or ordering proof; deterministic ordering can use catalog insertion identity plus resolved path as a tie-breaker.

Acceptance gates:

1. policy mismatch is explicit, never silently compared;
2. missing and modified bundles retain their existing catalog states;
3. output is bounded, JSON-capable and contains no values unavailable from verified `inspect` projections;
4. deleting the catalog still affects no evidence bundle.

### 3. Ship reviewed real-world starter suites

Add synthetic, value-safe examples—not connectors—for three workflows:

- warehouse refactor: aggregate count/sum coverage plus keyed diagnosis;
- payout reconciliation: exact transaction IDs, scaled-decimal sums and category grouping;
- feature-pipeline parity: keyed feature values with explicit numeric tolerances and a keyless multiset case.

Each example should state what Parison proves, what the extractor must guarantee, and which outcome blocks promotion. A small `examples/real-world/` collection and copyable CI snippets are more useful than a template engine: users can edit strict JSON with the already shipped editor schemas.

Acceptance gates:

1. all examples are synthetic and mechanically checked in CI;
2. expected results can be calculated by hand and contain at least one intentionally failing fixture;
3. extraction watermark, exclusions, currency/decimal policy and sensitivity choices are visible;
4. documentation never implies that a local example is a certified accounting, migration or ML control.

### 4. Define a detached signing payload

Add a network-free command that emits a canonical, domain-separated statement binding bundle kind, manifest digest and schema version. Users can sign that file with their existing CI identity system. Verification of Parison's internal manifest remains separate from verification of signer identity.

This is useful for regulated handoff, but it ranks below scale and repeatability: GitHub's own guidance notes that attestations help only when consumers verify them and apply a trust policy. Parison should not embed Sigstore credentials, OIDC or transparency-log policy.

### 5. Strengthen extraction-window guidance before adding semantics

Document side-specific extraction receipts—a tiny user-owned JSON record containing source label, logical watermark, extraction completion time and exported file digest—and show how CI can compare those receipts before invoking Parison. Do not initially make this another Parison schema. Real CDC watermark equivalence is source-specific, and a generic required field would turn unverifiable text into false assurance.

Only promote receipts into a product contract after concrete users demonstrate a shared, machine-checkable invariant across at least two extraction systems.

## Features not justified by this evidence

- **Remote database or SaaS connectors:** official sources show that source load, credentials, pagination, latency and snapshot coordination are central rather than incidental. Keep extraction outside Parison.
- **Continuous CDC monitoring:** retry timing and watermark behavior belong to the replication system. Parison can gate stable exported checkpoints.
- **Automatic repair:** AWS separates validation from resynchronization, and repair changes production state. Parison should remain evidence-producing and read-only.
- **Statistical drift detection:** TFDV has purpose-built schema, distribution and divergence semantics. Exact/tolerant feature-output parity is Parison's credible ML slice.
- **A new YAML dialect, hosted dashboard or broad UI:** none addresses the recurring correctness and scale gaps. Offline schemas, static reports and the local catalog already cover authoring and review with much less surface area.
- **Averages as a new aggregate primitive:** exact sum plus count already determines an average while preserving more diagnostic information. A new primitive would add rounding semantics without increasing proof power.

## Recommended 0.14 slice

Make 0.14 a **large local comparison** release:

1. freeze a spill-backend contract and threat model;
2. implement a SQLite-backed multiset prototype behind an explicit opt-in;
3. prove semantic equivalence, deterministic evidence and workspace cleanup;
4. add one warehouse/backfill starter suite that runs both aggregate coverage and spill-backed multiset diagnosis;
5. publish honest resource benchmarks.

If the prototype cannot demonstrate materially lower peak memory without unacceptable time or temporary-storage cost, do not ship it as supported execution. In that case, ship the real-world starter suites and safe catalog history as the smaller 0.14 workflow release, and retain spill execution as an experiment.
