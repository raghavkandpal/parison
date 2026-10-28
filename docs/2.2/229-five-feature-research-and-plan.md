# 2.2 research: five substantial verification capabilities

Date and source access: 23 October 2026  
Status: proposed scope; not an implementation contract or release approval  
Repository baseline: `97d9bb0d72aeb6d4967a497d05b166126b540d38` on `develop`, after 2.1.0 release reconciliation

The user subsequently requested five more features. The [expansion proposal](230-additional-five-feature-research.md) retains these five and adds five more, for ten total. Its expanded scope supersedes the five-feature target below.

## Recommendation

Build 2.2 around **reviewing, recovering and explaining a complete local migration rehearsal**. Select five independently useful capabilities: cross-dataset reconciliation in Workbench, modern dataset-evidence binding, policy-change review, recoverable suite execution, and suite rehearsal series. Two extend core evidence capabilities; three complete substantial human workflows over released engines. Do not count individual screens, routes, bug fixes or exports as additional features.

This is a research recommendation based on repository gaps and primary-source design evidence, not measured customer demand. The user requested five significant features; the accepted direction requires at least three, so five is compatible with that minimum. No implementation, new schema or release is authorized by this document itself. [Direction](../0.15/104-product-direction-and-release-arc.md), [2.1 feature-counting lesson](../2.1/226-release-train-expansion-research.md).

## What already exists through 2.1

| Layer | Released capability | Implication for 2.2 |
| --- | --- | --- |
| Comparison | Keyed, duplicate-aware multiset and aggregate comparison; explicit scalar policy, mappings, normalization and SQLite execution | More generic diff modes are not the clearest next need. |
| Inputs | Delimited files, JSONL, Parquet, SQLite, bounded JSON/XML projections and XLSX rectangles, tables and defined names | Evidence packaging should catch up with these readers. |
| Coordinated checks | Time alignment, identity/reference checks and exact-decimal conservation; composed reconciliation execution | The engine exists; a complete Workbench workflow is missing. |
| Policy and provenance | Schema-evolution declarations, policy diff, dataset manifests and dataset-evidence bundles | Avoid announcing these existing CLI features as new core semantics. |
| Rehearsals | Suite selection, shards, assembly, bounded parallel CLI execution and digest-validated CLI resume; ordinary-run discrepancy series | Workbench recovery and suite-wide series remain separate gaps. |
| Workbench 2.0–2.1 | Recipe editing, ordinary runs, suite review/run/handoff, pairwise suite comparison and failed-member investigation | The next train should extend decisions users can make, not repeat this train's steps. |

Sources: [current guide](../user-guide.md), [README](../../README.md), [2.1 plan](../2.1/220-workbench-release-train-research-and-plan.md), and the contracts linked below. Some old contract headers still describe implementation as pending; current implementation and release records take precedence when identifying what exists. In particular, `run_reconciliation` is implemented in [reconciliation.py](../../src/parison/reconciliation.py).

## 1. Cross-dataset reconciliation in Workbench

**User outcome:** review and run a gate that checks orders, lines and payments together, distinguishing row parity from orphan references, broken conservation and insufficient time coordination. A pair of exports can agree while both violate a declared relationship; parity and reconciliation answer different questions.

**Existing base and gap:** the CLI already composes alignment, per-dataset parity, identity/reference and conservation checks. Workbench execution currently dispatches ordinary comparisons and suites; its history filter does not include reconciliation bundles. This feature is the complete review → run → inspect → handoff workflow, counted once. [Reconciliation contract](../1.3/149-time-alignment-and-reconciliation-contract.md), [Workbench services](../../src/parison/workbench.py).

**Smallest coherent scope:** load existing alignment/reconciliation declarations, explicitly bind each local recipe and input pair plus receipt, display policy identities and coordination claim, invalidate review on changes, run the shared service, and present verified component outcomes with a concise handoff. Start with existing declarations rather than a general graph editor. Keep sensitive authoring metadata separate from summary-safe results.

**Completion gate:** a synthetic order/line/payment task exposes an orphan and a conservation mismatch even when row parity passes; heuristic coordination remains INCONCLUSIVE; a changed receipt or input blocks stale execution. Equivalent CLI and Workbench inputs yield equivalent canonical evidence. Cancellation and post-publication failure are represented honestly, and complete reconciliation evidence is discoverable and inspectable without leaking names, tokens or values.

**Threats/non-goals:** a receipt digest does not authenticate extraction or establish a shared database snapshot. No connectors, credentials, inferred relationships, implicit timestamp selection or cutover action. Preserve the released conservative outcome reduction.

## 2. Dataset evidence for structured and partitioned inputs

**User outcome:** bind the actual JSON, XML, XLSX or partitioned export used in a rehearsal to portable, independently verifiable evidence, with an explicit Workbench publication path.

**Existing base and gap:** manifest v1 allows only CSV/TSV/JSONL/Parquet/SQLite comparison resources; JSON is receipt/supporting-only and XML/XLSX are absent. It requires one regular file per unique `(id, role)`. Meanwhile partition input identity hashes ordered member names and digests, rather than one file's bytes. Simply adding extensions would not bind these inputs correctly. [Manifest contract](../1.4/154-dataset-manifest-and-reproducibility-contract.md), [manifest validation and semantic binding](../../src/parison/manifesting.py), [source identity](../../src/parison/inputs.py).

**Smallest coherent scope:** design an opt-in manifest v2 that distinguishes physical files from logical input bindings. Explicit bindings cover the released structured selectors and supported partition sets, carry the existing semantic source digest, and bind the effective policy that owns field projection. Enumerate only explicitly selected roots; never infer scope. Deduplicate physical files when multiple logical selections use one workbook, while preserving strict alias and path rules. Add Workbench review, verification and publication as parts of this one capability.

**Completion gate:** fixtures cover JSON arrays, namespaced XML, XLSX table/defined-name selectors, two selections of one physical workbook, and a multi-file input. Added/removed/renamed partitions, altered selectors or policies, missing receipts and tampered children cannot produce a matching evidence binding. Canonical v2 fixtures and old v1 byte fixtures pass; preserved evidence verifies without reopening sources. Publication remains atomic, no-overwrite and symlink-safe across platforms.

**Threats/non-goals:** physical byte identity is not logical equality, and closed local membership is not upstream completeness. Do not change source-digest algorithms or admit new parser semantics. Freeze limits on member counts and total manifest size. Determine whether the outer dataset-evidence kind also needs a new version before implementation; do not widen its v1 reader silently.

## 3. Explicit policy-change review

**User outcome:** understand why two rehearsals cannot be compared after a key, tolerance, exclusion, field mapping or scope change, and inspect that policy change without weakening the comparison gate.

**Existing base and gap:** `diff-policy` and schema-evolution declarations already provide deterministic compatibility assessments and summary/full disclosure modes. Workbench Plans edits one recipe, while Compare correctly refuses unequal policies. There is no integrated two-policy review workflow. [Policy diff contract](../1.2/143-schema-evolution-and-policy-diff-contract.md), [Plans controls](../2.0/212-workbench-plan-controls-checkpoint.md), [suite comparison](../2.1/227-suite-comparison-contract.md).

**Smallest coherent scope:** select two recipes and an explicit evolution declaration, validate exact bytes, show the shared service's reason codes and assessment, and offer separately requested schema-sensitive detail and an unapproved draft export. Explain incompatible rehearsal comparisons by directing users to this review. Begin with recipe pairs; do not claim suite-wide policy alignment.

**Completion gate:** demonstrate a declared physical rename, a changed key, relaxed tolerance, new exclusion and changed scope. Summary output contains no policy fragments or field names. Every edit invalidates the displayed identities. CLI/Workbench assessments agree, and even an ACCEPT assessment cannot bypass exact-policy run/suite comparison.

**Threats/non-goals:** mechanical ACCEPT must never read as business approval. No inferred renames, automatic tolerance tuning, automatic exclusions, policy migration or cross-policy trend continuity. This is one review capability, not three features for editor, diff and export.

## 4. Explicitly recoverable suite execution

**User outcome:** interrupt a long rehearsal, reopen Workbench and deliberately continue eligible work without silently reusing stale results or rerunning all completed cases.

**Existing base and gap:** CLI suite-v2 workspaces already support digest-validated resume. Workbench passes neither workspace nor resume and fixes `jobs=1`. The runner explicitly rejects cooperative cancellation with multiple jobs, so merely exposing a concurrency selector is unsafe. [Suite runner](../../src/parison/suites.py), [2.1 execution contract](../2.1/222-workbench-suite-rehearsal-contract.md).

**Smallest coherent scope:** explicitly create/select a dedicated execution workspace, inspect bounded checkpoint eligibility, show what can be reused and what must execute again, then resume through the existing runner into a new immutable output. Bind preview to plan, selection, recipes, limits and input identities; revalidate at execution. Keep one job for 2.2. Distinguish retained verified checkpoints from temporary sensitive staging and from a published complete suite.

**Completion gate:** cancel after one completed member, restart the host and resume to the same semantic result as a fresh run. Mutate policy, inputs, limits and checkpoints between preview and execution; never reuse an ineligible child. Test symlinks, corrupt checkpoints, stale previews, an existing output destination, explicit workspace abandonment, and a crash after publication but before catalog registration. Instrument tests to prove eligible work was reused; do not claim speedup from outcome equality alone.

**Threats/non-goals:** retention is explicit because checkpoints can contain raw evidence. No background daemon, scheduled retries, remote workers, automatic resume, distributed execution or new parallel cancellation contract. A helper for read-only eligibility may be necessary; keep it in the suite service so the browser does not duplicate reuse rules.

## 5. Suite rehearsal series and regression analysis

**User outcome:** inspect a selected sequence of several rehearsals and see which cases and discrepancy reasons recur, resolve or regress, together with changed input identities.

**Existing base and gap:** v2.1 `compare_suites` accepts two bundles. The existing `analyze_series` groups ordinary-run discrepancies; it does not accept suite parents. Repeating pairwise screens does not produce a portable, verified suite-series artifact. [Suite comparison implementation](../../src/parison/suites.py), [ordinary-run analysis](../../src/parison/analysis.py), [analysis contract](../1.5/161-discrepancy-analysis-contract.md).

**Smallest coherent scope:** a new shared service and versioned artifact for an explicitly ordered, bounded sequence of distinct complete suite bundles. Require the same suite policy, ordered case set and every member policy. Compose verified child reason groups into case-scoped transitions, retain input-identity changes, and expose CLI and Workbench inspection/export. Start with complete suites; defer shard series. Treat caller order as rehearsal order, never inferred chronology.

**Completion gate:** a four-rehearsal fixture includes resolved, recurring and newly introduced failures, unchanged counts with changed inputs, and different case modes. Reordered/missing cases, changed policies, duplicate bundles, incomplete executions and tampered children fail closed. Verify the exported artifact and canonical bytes independently; preserve all v1 ordinary analysis and v2.1 pairwise output. Bound both run count and the case/group product; fail explicitly rather than silently truncating evidence.

**Threats/non-goals:** a downward count does not establish root cause, improvement under a changed policy or readiness for cutover. Default output must omit paths, field names, keys, values and samples; freeze an explicit identifier disclosure policy rather than blindly exporting full child analyses. No forecasts, statistical drift, automatic reruns or raw-sample aggregation.

## Primary-source findings and design consequences

All external sources below were accessed on **23 October 2026**. Their application to Parison is our design inference, not an endorsement by those projects.

| Primary source and finding | Consequence for this proposal |
| --- | --- |
| [PostgreSQL 18 transaction isolation](https://www.postgresql.org/docs/18/transaction-iso.html): successive Read Committed queries can observe different committed data even within a transaction. [dbt data tests](https://docs.getdbt.com/docs/build/data-tests) documents explicit relationship assertions between models. | Feature 1 must distinguish per-dataset equality, relationship validity and coordinated extraction claims. Local parity alone cannot establish a common source snapshot. |
| [RFC 8493, BagIt](https://www.rfc-editor.org/rfc/rfc8493.html): complete payload membership and checksum validity are distinct requirements; payload manifests enumerate the payload. | Feature 2 needs explicit closed membership and byte validation, with distinct failure reasons. Adopt the integrity distinction, not BagIt's on-disk format or remote-fetch facility. |
| [Canonical XML 1.1](https://www.w3.org/TR/xml-c14n11/) distinguishes physical representation from logical equivalence; [Parquet's file format](https://parquet.apache.org/docs/file-format/) separates data and metadata and describes multi-file arrangements. | Keep file identity, collection identity and selected-record semantics separate. Do not introduce XML canonicalization or reinterpret Parquet containers as part of this feature. |
| [SQLite WAL documentation](https://www.sqlite.org/wal.html) explains that committed changes can reside in the WAL rather than the main database file. | Preserve rejection of ambiguous SQLite sidecar state; expanded manifest coverage must not weaken the existing quiescent-file boundary. |
| [dbt state-comparison caveats](https://docs.getdbt.com/reference/node-selection/state-comparison-caveats) documents limits of change detection and cross-environment relationship testing. | Feature 3 compares expanded policies using Parison's closed vocabulary; source-text differences and external state selection are not proof of semantic compatibility. |
| [dbt retry jobs](https://docs.getdbt.com/docs/deploy/retry-jobs) distinguishes rerunning from the beginning from rerunning failed steps and presents explicit retry choices. | Feature 4 should expose a deliberate recovery decision and reuse preview. Parison still applies its own stricter digest-validated eligibility rules. |
| [AWS DMS data validation](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Validating.html) distinguishes validation states, including pending, failed and suspended, and describes revalidation after changes. | Feature 5 must preserve completeness and input-identity facts instead of reducing selected rehearsals to a success percentage. This is a reporting lesson, not a proposal for live CDC or DMS integration. |

## Priority, dependencies and feasibility gates

| Priority | Capability | Relative effort/risk | First gate |
| --- | --- | --- | --- |
| 1 | Reconciliation Workbench | High: multi-input lifecycle and cancellation | Trace one existing reconciliation fixture through shared services and a safe projection. |
| 2 | Modern dataset evidence | High: new physical/logical binding contract | Prove structured-selector and partition identities without changing existing digest semantics. |
| 3 | Policy-change review | Medium: disclosure and stale review | Demonstrate a rename and a policy denial through the existing diff service. |
| 4 | Recoverable suites | Medium–high: retained state and cleanup | Prove restart/resume with one completed child and one changed input. |
| 5 | Suite series | Medium–high: new artifact and bounded verification | Compose three verified suites without flattening case identity or scope. |

These are relative judgments, not measured delivery estimates. Policy review, recovery and series can proceed independently; dataset-evidence UI can reuse the reconciliation binding workflow, while its core contract does not depend on that UI. No new third-party runtime dependency is justified by this research.

Before implementation, freeze five small contracts and their acceptance fixtures. If a feasibility gate fails, revise the proposed train explicitly; do not replace a substantial feature with cosmetic work. Qualify each feature separately, then the combined train with `make check`, independent Standards/Spec review, and the exact-head built-wheel Python 3.11–3.14 Linux/macOS/Windows matrix for schema/CLI/platform changes. Five features are the target for this proposal; the general minimum release cadence remains unchanged. [Workflow](../../AGENTS.md), [release process](../../RELEASING.md).

## Alternatives deferred

- More formats, fuzzy matching, SQL expressions and automatic repair broaden semantics before completing workflows over current inputs.
- Parallel Workbench jobs need a separately tested cancellation design; they are not a free addition to resume.
- Reconciliation-to-reconciliation comparison is plausible after the reconciliation workflow, but suite series directly extends the newly released 2.1 comparison foundation.
- Hosting, source connectors, built-in signing and scheduling cross explicit custody boundaries. Keep orchestration and signer authentication external.
- UI polish and documentation cleanup are supporting work, not substitutes for these five capabilities.

## Evidence limits

Repository source establishes the gaps above. External specifications and official product documentation provide design precedent, not proof that users want these exact features or that Parison's implementation is correct. No production study, workload benchmark or new feature execution was performed for this research. Fresh task trials should test whether users can distinguish policy validity, evidence integrity, coordination assertions and operational approval before release.
