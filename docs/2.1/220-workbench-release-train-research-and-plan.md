# 2.1 Workbench release train: suite rehearsal and evidence handoff

Date and source access: 22 October 2026  
Status: revised 2.1 plan; release candidate deferred

## Decision and evidence

The accepted direction asks each post-1.7 minor release to contain three substantial, separately reviewable features that strengthen local verification. Its verification ladder advances from preflight through parity and repeated rehearsals to portable evidence. The released 2.0 Workbench already covers one recipe, one bounded local run, verified results, catalog history, safe investigation and same-policy comparison. Suite execution and handoff still require CLI use. A coherent next train is therefore **a complete, local, multi-dataset rehearsal in Workbench**, ending with independently verifiable evidence rather than operational approval. [Product direction](../0.15/104-product-direction-and-release-arc.md), [2.0 Workbench contract](../2.0/209-workbench-run-history-contract.md), [2.0 user guide](../user-guide.md).

This selection builds on released semantics. It does not add a new policy engine, alter bundle bytes, or infer extraction truth. PASS continues to mean agreement under an explicit policy. The UI should call shared application services, with the CLI remaining the reproducible automation peer. [Unified interface decision](../2.0/201-unified-workbench-interface-decision.md), [agent contract](../../AGENTS.md).

## Completed integrated capability: suite rehearsal and handoff

The three slices below form one substantial capability for release-cadence
purposes: a single suite plan flows through execution to portable evidence.
They were independently testable steps, but are not three distinct release
features. The [expansion research](226-release-train-expansion-research.md)
records the scope correction and two further capabilities needed before a
2.1.0 candidate.

| Slice | User capability | Completion gate |
| --- | --- | --- |
| **1. Suite plans in Workbench** | Open a released suite plan, validate it authoritatively, inspect its exact ordered members and input bindings, and prepare explicit local inputs and output. Do not silently construct or approve recipes, keys, exclusions, jobs or shards. | A valid suite displays the same selection and validation outcome as CLI `validate-suite` and `list-suite`; invalid or changed members cannot reach Run. Test closed path handling, sensitive fields and each released member format. |
| **2. Bounded suite rehearsal** | Run the selected suite locally, expose bounded per-member and overall progress, cancel cooperatively, verify the immutable suite bundle, and register a safe history entry. Keep jobs explicit and within reviewed limits. | Exact CLI/Workbench semantic and canonical-byte parity for equivalent suite inputs; failure and cancellation leave no partial published bundle or sensitive staging. Cross-platform tests cover concurrency, interrupted children and resume eligibility if resume is exposed. |
| **3. Verified handoff** | From a verified suite result, create the existing deterministic unsigned statement and concise cutover report, show their scope and verification state, and export them through explicit local paths. The receiver workflow must still authenticate any external signature and decide whether policy, outcome and completeness suffice. | Workbench-created statement bytes match CLI output; report matches CLI semantics; tampered or missing bundle members block display/export; no signing, approval or cutover action appears. |

Slices 1 and 2 close the Workbench gap identified in the [2.0 guide](../user-guide.md#start-the-unified-workbench), which directs suite users to the CLI. Slice 3 completes the same rehearsal's portable handoff using the already released [statement and report workflow](../0.17/116-evidence-handoff-guide.md).

## Remaining substantial capabilities

| Feature | User capability | Contract and gate |
| --- | --- | --- |
| **2. Repeated suite comparison** | Compare two recursively verified, same-policy suite rehearsals case by case, including outcome and input-identity changes. | [Comparison contract](227-suite-comparison-contract.md): strict scope and policy gate, summary-safe deterministic projection, tamper rejection and CLI/Workbench parity. |
| **3. Failed-member investigation** | Move from a failed suite to one exact member's verified discrepancy reasons, with an explicit bounded raw-evidence action. | [Investigation contract](228-suite-investigation-contract.md): safe default projection, exact member selection, fresh recursive verification, bounded export and hostile-input tests. |

Each new feature needs its own green pushed checkpoint, independent review,
full `make check` and user-visible documentation. Candidate qualification
starts only after all three capabilities are integrated on `develop`.

## Design consequences

- Keep suite plans and input selections explicit. Reuse the released suite parser, validator, selection and runner rather than interpreting them in browser code. Represent execution as a new immutable run, never an overwrite or silent rerun. [Suite contract](../0.11/84-scalable-suite-contract.md), [Workbench run contract](../2.0/209-workbench-run-history-contract.md).
- Treat every result and handoff view as derived from fresh bundle verification. Default projections remain summary-safe: no source paths, field names, keys, values or samples. Raw evidence, if later exposed, needs its own explicit action and contract. [Workbench run contract](../2.0/209-workbench-run-history-contract.md).
- Retain the hardened numeric-loopback host, per-launch capability, strict routes and body limits, one active execution, cancellation and shutdown semantics. Export uses explicit workspace-relative destinations and the existing atomic, no-overwrite publication rules. [Unified interface decision](../2.0/201-unified-workbench-interface-decision.md), [agent contract](../../AGENTS.md).
- Keep signing and issuer authentication external. The local statement is deterministic and unsigned; a receiver must establish signer identity and assess scope separately. [Evidence handoff guide](../0.17/116-evidence-handoff-guide.md).

## Threats and controls

| Threat | Control and test evidence |
| --- | --- |
| UI shows an incomplete or changed suite as reviewed | Revalidate at execution; display exact member selection and policy identity; test member mutation between preview and Run. |
| Cancellation or child failure leaves partial evidence | Reuse suite publication and cleanup; inject failure at preflight, child execution and final publication boundaries. |
| History or handoff displays tampered evidence | Verify bundle recursively at every entry point; test modified and missing child members before rendering or export. |
| Statement or report is mistaken for approval | Label its claim precisely; omit approval, signing and cutover controls; test user-facing copy and output bytes. |
| Browser route leaks local inputs | Preserve route and capability checks, workspace path confinement and summary-safe output; run hostile request tests. |

## Non-goals and release gates

No hosted dashboard, credentials, remote orchestration, scheduling, automatic repairs, signing keys, cutover authorization, statistical drift or new result semantics. Do not count defect fixes or UI polish as one of the three features. [Product direction](../0.15/104-product-direction-and-release-arc.md), [agent contract](../../AGENTS.md).

For each capability: freeze a small user-visible contract, add narrow behavioral and hostile-input tests, pass `make check`, document the capability, push a green feature checkpoint and obtain independent review. Before 2.1 release integration, qualify the exact candidate head with the required built-wheel Python 3.11–3.14 Linux/macOS/Windows matrix, then follow the release checklist. These internal gates support product development; they do not approve a user's operational policy or migration. [Agent contract](../../AGENTS.md), [release process](../../RELEASING.md).
