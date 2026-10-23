# 2.2 expansion: five additional capabilities

Date: 23 October 2026  
Status: proposed expansion to ten features; contracts and implementation pending

## Recommendation

Retain the [original five](229-five-feature-research-and-plan.md) and add the five below. These extend independent verification decisions, rather than splitting one workflow into screens. Ten is an ambitious scope target; no delivery estimate or feasibility guarantee has been established. Freeze each contract before building, and revise scope explicitly if a gate fails.

The original five remain: Workbench reconciliation, modern dataset evidence, policy-change review, recoverable suites and suite rehearsal series. The additional five are reconciliation comparison, reconciliation investigation, explicit dataset assertions, portable evidence archives and suite-plan authoring.

## 6. Compare reconciliation rehearsals

**Outcome:** determine which declared relationships, conservation checks and dataset outcomes changed between two complete reconciliation runs.

**Gap:** the released suite comparison and ordinary-run catalog diff do not compare reconciliation bundles. The reconciliation verifier already validates component membership and outcome reduction, providing a foundation. Sources: [reconciliation implementation](../../src/parison/reconciliation.py), [suite comparison](../../src/parison/suites.py), [catalog diff](../../src/parison/catalog.py).

**Scope:** a shared CLI/Workbench comparison service verifies both bundles and requires identical reconciliation policy, alignment policy, ordered dataset policies and check scope. Show component outcome/count transitions and changed input/receipt identities. Keep strict alignment matching initially: changing the event window or coordination declaration is an incompatibility, not a trend continuation. This limitation must be visible because repeated real-world snapshots often change that declaration.

**Gate:** fixtures cover a resolved orphan, newly broken conservation, unchanged counts with changed inputs, receipt changes under the same declared coordination binding where valid, changed windows, missing checks and tampered evidence. Exact canonical output and CLI/Workbench parity are required. Reject incompatible policy rather than inventing cross-policy equivalence.

**Threats/non-goals:** changed counts are observations, not causal diagnosis or approval. Default output excludes dataset/check names, paths, tokens, keys and values; use versioned domain-separated opaque component references where needed. No automatic policy alignment or weakening of comparison gates.

## 7. Investigate reconciliation failures

**Outcome:** distinguish an alignment failure from duplicate identities, orphan references and conservation discrepancies, and locate the responsible side and component using verified evidence.

**Gap:** Workbench failed-member investigation targets ordinary children of suites. Reconciliation evidence contains a different component structure, and its summary reduces detail to outcome counts. Sources: [analysis implementation](../../src/parison/analysis.py), [reconciliation summary](../../src/parison/reconciliation.py), [released investigation](../2.1/228-suite-investigation-contract.md).

**Scope:** create a versioned diagnostic projection over one verified reconciliation bundle with exhaustive reason groups, component references, baseline/candidate counts and fixed explanatory text. Offer an explicitly schema-sensitive declaration view separately from default safe summaries. Diagnose only evidence already preserved; never imply access to row-level samples that were not stored.

**Gate:** an operator can distinguish duplicate-parent ambiguity, a missing parent and an unmatched conservation group without reopening source inputs. Tampered declarations, inconsistent counts and unknown result versions fail closed. Default output contains no names, tokens, keys or values; zero-count and blocked dependent checks are represented deterministically.

**Threats/non-goals:** no root-cause inference, new raw sampling or automatic repair. This is a shared diagnostic capability with CLI and artifact verification, not simply expanding a Results panel. It is separate from feature 6: diagnosis explains one failure; comparison describes change across two runs.

## 8. Explicit dataset assertions

**Outcome:** detect agreed-but-invalid data, such as a negative amount or an unsupported status appearing identically in both exports.

**Gap:** released type/key validation and cross-dataset relationships do not provide a general closed vocabulary for per-field domain constraints. Sources: [record validation](../0.6/55-record-validation-contract.md), [policy implementation](../../src/parison/policies.py), [reconciliation contract](../1.3/149-time-alignment-and-reconciliation-contract.md).

**Scope:** an opt-in assertion declaration and separately versioned result/bundle for exact allowed-value membership, explicit non-null requirements and inclusive/exclusive numeric or date bounds. Evaluate baseline and candidate independently using released typed scalar semantics. Bounds, null behavior and empty-input behavior must be explicit. Bind declaration, effective recipe and source identities. Start as an independent CLI/Workbench gate; composing it into suites needs an explicit new contract and is not silently included.

**Gate:** identical invalid exports pass their unchanged parity check but fail the assertion gate; null, empty scope, boundary values, exact decimals and invalid typed values have defined outcomes. Memory use and allowed-value set size are bounded. Canonical fixtures, independent verifier derivation and summary-safe violation counts are required. Any FAIL means only violation of the declared assertion.

**Threats/non-goals:** this expands policy semantics and deserves the strictest contract review. Do not infer acceptable domains, import arbitrary JSON Schema semantics, use Python/SQL expressions, add regex execution, statistical profiles or repair. Existing recipe versions and PASS meanings remain unchanged.

## 9. Portable verified evidence archives

**Outcome:** transfer one evidence bundle as one deterministic local file, then safely restore and independently verify it on another machine.

**Gap:** existing bundles and unsigned statements are portable directory artifacts, but there is no dedicated safe pack/unpack CLI workflow. This is distinct from feature 2: archives carry existing evidence; dataset manifests bind the source collection. Sources: [evidence handoff](../0.17/116-evidence-handoff-guide.md), [CLI surface](../../src/parison/cli.py), [publication invariants](../../AGENTS.md).

**Scope:** a closed, versioned archive profile over a freshly verified bundle, with fixed member ordering and metadata, explicit sensitivity display and bounded local import. Preserve inner canonical bytes. Reject absolute/traversal paths, portable-name collisions, links, duplicate entries, special files and undeclared members before publication. Use stdlib archive support with explicit entry validation, private staging and atomic no-overwrite installation. Reverify the staged bundle before publication.

**Gate:** repeated exports produce identical archive bytes; round trips of ordinary, suite, reconciliation and dataset-evidence bundles preserve inner digests across Linux/macOS/Windows. Hostile archives test traversal, expansion limits, duplicate names, links, cancellation and cleanup. Raw-sensitivity evidence remains raw and must be identified before export/import.

**Threats/non-goals:** do not trust generic extract-all behavior or filename suffixes. No remote upload/download, encryption, signing, automatic redaction or source-data packaging. Archive integrity does not authenticate its issuer.

## 10. Author complete suite plans in Workbench

**Outcome:** construct and edit an explicit multi-case gate without hand-editing the suite JSON, then export an unapproved validated draft.

**Gap:** v2.1 reviews an existing suite and its selection; it does not author members, ordering, tags or execution limits. Recipe editing and feature 3's two-policy review do not fill this gap. Source: [suite plan review contract](../2.1/221-workbench-suite-plan-contract.md).

**Scope:** create a suite-v2 draft using explicitly selected existing recipes and input references, add/remove/reorder cases, edit tags and released per-case limits, validate through the authoritative suite loader, and export to a new local file. Provide the equivalent CLI workflow. Preserve explicit selections, invalidate displayed identity after every edit and execute nothing during authoring. Existing recipe policies are reviewed separately.

**Gate:** author a keyed/aggregate/multiset suite, export, reload and obtain identical ordered selection and policy identity through CLI. Reject duplicate IDs, invalid limits, unavailable dependencies and escaping/symlinked references. Resolve references relative to the eventual exported plan location, not a temporary validation directory. Changed referenced recipes invalidate review before Run.

**Threats/non-goals:** no automatic key/tolerance selection, discovered directory-to-suite inference, template approval or automatic execution. One complete authoring capability counts once.

## Sequencing and release gates

Implement feature 10 independently of new core formats. Features 6 and 7 reuse feature 1's reconciliation projections but require their own services and tests. Feature 9 should follow feature 2's evidence-version decisions. Feature 8 has the largest new semantic surface and should receive an early fixture-driven feasibility spike; do not hide it inside recipe validation.

All ten require separately checkable completion gates. Keep the original five's gates, preserve old recipes/bundles/canonical bytes, and run independent Standards/Spec review plus exact-head full-matrix qualification for CLI/schema/platform changes. Tests, fixes and UI polish do not count as extra features. No production-demand study or implementation benchmark supports a schedule for this expanded train.

## Primary-source research

Sources accessed 23 October 2026; consequences below are design judgments.

- [dbt data tests](https://docs.getdbt.com/docs/build/data-tests) documents explicit non-null, accepted-value, uniqueness and relationship assertions. [Frictionless Table Schema](https://specs.frictionlessdata.io/table-schema/) distinguishes logical constraints such as required fields and ranges. These support a bounded assertion vocabulary for feature 8, without adopting SQL execution or changing Parison scalar/null semantics.
- [Python archive extraction guidance](https://docs.python.org/3/library/tarfile.html#extraction-filters) warns that filters do not prevent every malicious archive or resource-exhaustion risk. Feature 9 needs explicit member validation and limits across supported Python versions, rather than relying on interpreter defaults.
- [RFC 8493](https://www.rfc-editor.org/rfc/rfc8493.html) distinguishes complete payload membership from checksum validity. Feature 9 must establish both before publishing restored evidence.
- [AWS DMS validation](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Validating.html) documents distinct validation states and revalidation after changes. Features 6 and 7 should preserve completeness and observed component facts; this is not evidence for causal diagnosis or a proposal for live monitoring.

External precedents support engineering fit, not demand, usability or capacity claims. Repository gaps were checked against the current implementation; no new feature was executed in this research.
