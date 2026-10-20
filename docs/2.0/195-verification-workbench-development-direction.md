# Verification workbench development direction

Date: 19 October 2026

Status: **proposed post-1.9/2.0 exploration; not scheduled**

Depends on:

- [Verification workbench product research](194-verification-workbench-product-research.md)
- [Accepted product direction](../0.15/104-product-direction-and-release-arc.md)

## Decision proposed

After the active 1.9 structured-selection train is qualified, assess a
local-first **Parison Workbench** as a peer human interface to the CLI. Do not
interrupt 1.9 qualification or implicitly assign the workbench to 2.0. At the
1.9/2.0 train boundary, use the gates below to decide whether it belongs in the
next three-feature train or remains prototype research.

The workbench organizes the existing verification lifecycle:

```text
Define -> Run -> Investigate -> Compare
```

It does not schedule migrations, connect to remote databases, repair data or
authorize cutover.

## Compatibility boundary to establish first

The long-term architecture should make CLI and workbench peer adapters:

```text
CLI ---------+
             +-> shared application services -> verification core
Workbench ---+             |
                           +-> versioned schemas and artifacts
```

The prototype may invoke the CLI as a subprocess to test workflows, but that
must not become the permanent semantic boundary. The UI must not scrape human
terminal output or query undocumented catalog tables.

Before product implementation, inventory each workbench operation against one
stable interface:

- shared application service;
- released JSON schema;
- verified bundle reader;
- summary-safe inspection projection;
- catalog API or explicitly versioned catalog projection;
- structured progress event contract.

Missing interfaces are core design work, not permission for the UI to duplicate
logic.

## Gate 0: complete the active train

Do not begin production workbench development until:

- all three 1.9 structured-selection features are implemented and qualified;
- the combined 1.9 review and exact-commit CI gate passes;
- active documentation and release state are reconciled;
- the next release train is selected as one coherent group of at least three
  substantial, separately reviewable features.

Research prototypes may be maintained outside released package paths and must
not change active CLI, schema or artifact contracts.

## Gate 1: command and task inventory

Create a bounded inventory of the documented commands and classify them by user
task rather than implementation area:

- define and validate policy;
- preflight inputs;
- execute comparisons and suites;
- reconcile related datasets;
- investigate discrepancies;
- verify and publish evidence;
- inspect history and compare rehearsals;
- integrate with CI or external orchestrators.

For each task, record:

- intended user and decision;
- required inputs;
- safe preview;
- mutation and custody behavior;
- output artifacts and schemas;
- safe versus sensitive fields;
- equivalent CLI invocation;
- existing stable programmatic interface;
- missing contract needed by a workbench.

Completion gate: every proposed screen maps to released behavior, and no screen
requires inventing new agreement semantics.

## Gate 2: information-architecture prototype

Build a disposable read-only prototype using synthetic or repository fixture
evidence. Test these tasks:

1. Find the latest FAIL or INCONCLUSIVE run in a workspace.
2. Explain why a suite did not pass without revealing source values.
3. Compare two exact-policy rehearsals and identify changed inputs.
4. Distinguish tampered, missing, stale and unsupported evidence.
5. Locate the explicit operation needed for bounded sensitive drill-down.

The prototype should model:

- workspace home;
- verification-plan detail;
- run and suite history;
- result summary;
- discrepancy groups;
- policy and provenance comparison;
- artifact authenticity state.

It must not connect to real data sources, execute comparisons or store
credentials.

Completion gate: unfamiliar evaluators can complete the five tasks using only
the interface and do not infer that PASS means correctness or approval. Internal
blind-agent task review is valid development evidence; no real-world migration
or policy approval is sought or implied.

## Candidate three-feature train

If the first two gates pass, the smallest coherent release train contains three
substantial features.

### Feature A: verified evidence navigator

Open a local workspace, catalog or bundle and provide:

- mandatory verification before display;
- run and suite browsing;
- outcome, kind, policy and time filters;
- summary-safe result and discrepancy views;
- policy fingerprint, input identity and limit display;
- explicit unsupported, tampered, missing and stale states;
- links to existing immutable artifacts.

Contract questions:

- whether the navigator is generated static output or a loopback application;
- how a workspace discovers bundles without broad filesystem access;
- how catalog projections are versioned;
- whether browser assets are deterministic and vendored;
- which metadata is safe to aggregate across runs.

Completion gate: the same verified inputs produce deterministic safe views;
malformed or tampered evidence never reaches rendering; no source paths, keys,
values or samples enter default views.

### Feature B: schema-driven verification-plan builder

Create and edit transparent JSON plans by user intent:

- choose a released verification workflow;
- select local input locators;
- configure mappings, projections, keys, tolerances and limits;
- validate continuously against released schemas;
- preview the complete effective policy and fingerprint;
- display the equivalent CLI invocation;
- keep generated suggestions visibly unapproved until explicitly accepted.

The builder must not add a second recipe language or hide defaults.

Completion gate: saved plans are canonical inputs accepted unchanged by the
CLI; round trips preserve meaning and bytes where a canonical format applies;
every policy-affecting control has schema and hostile-input coverage.

### Feature C: bounded local runner and rehearsal comparison

Execute one existing plan or suite locally and connect it to history:

- explicit preflight before execution;
- bounded progress from structured events;
- safe cancellation and interruption cleanup;
- exact exit code and artifact preservation;
- atomic registration in the local catalog;
- comparison with a selected same-policy rehearsal;
- clear separation of execution completion from verification outcome.

It is not a scheduler. Runs begin only from an explicit local action or an
external orchestrator using existing automation interfaces.

Completion gate: workbench and CLI execution produce semantically identical
artifacts and outcomes; cancellation cannot leave publishable partial evidence;
history never replaces an earlier run.

## Delivery sequence

Within the candidate train, use these checkpoints:

1. Freeze the workspace, disclosure and application-interface contracts.
2. Implement the evidence navigator against fixtures and released bundles.
3. Fresh blind review of authenticity, path handling, HTML injection,
   disclosure and schema-version behavior.
4. Implement the plan builder only after navigation semantics are stable.
5. Fresh blind review of hidden defaults, canonical round trips and draft
   suggestion behavior.
6. Implement the bounded runner only after shared application interfaces are
   proven by both CLI and navigator.
7. Fresh blind review of cancellation, concurrency, staging cleanup and exact
   artifact parity.
8. Run combined cross-platform built-wheel qualification for the exact commit.
9. Consider one candidate or release only when all three substantial features
   and the combined review are complete.

## Technology decision deferred

Do not choose Electron, Tauri, a Python web framework, a terminal UI or a static
site generator before the information-architecture prototype. Select the
smallest delivery model that passes the contracts.

Evaluation criteria:

- local-only operation and absence of telemetry;
- Windows, macOS and Linux packaging burden;
- deterministic asset delivery;
- browser and filesystem security boundary;
- accessibility and keyboard navigation;
- dependency and supply-chain cost;
- ability to share core services with the CLI;
- testability without fragile screenshot-only assertions;
- upgrade compatibility for workspaces and artifacts.

A generated static navigator is the lowest-custody starting point. A loopback
application becomes justified only when plan editing or live progress requires
it. If a server is used, loopback binding alone is not a security design;
origin, request forgery, file access, lifecycle and port ownership need explicit
contracts and hostile tests.

## Explicit non-goals

- hosted dashboard or multi-tenant service;
- database, warehouse or cloud credentials;
- source extraction or transformation;
- continuous CDC monitoring;
- background scheduling;
- remote workers or distributed execution;
- automatic anomaly policy;
- cross-policy health score;
- incident ownership, chat or ticket workflow;
- data repair, synchronization or deployment;
- migration approval or cutover authorization;
- replacement or deprecation of the CLI.

## Evidence plan

Use development evidence appropriate to the risk:

- primary-source product and platform research;
- fixture-driven task walkthroughs;
- schema and canonical-byte tests;
- bundle authenticity and hostile HTML/content tests;
- disclosure tests asserting absence of paths, keys, values and samples;
- exact CLI/workbench semantic parity tests;
- interruption and atomic-publication tests;
- machine-specific render and responsiveness benchmarks;
- accessibility checks;
- fresh blind-agent review per feature;
- exact-commit built-wheel CI on supported Python, macOS, Windows and Linux.

This evidence supports continued product development only. It does not approve
a user's policies, data, migration, release or cutover.

## Decision at the 1.9/2.0 boundary

Select the workbench train only if all of the following are true:

- command/task inventory shows repeated navigation across multiple command
  families for common verification jobs;
- the read-only prototype materially improves the five target tasks;
- safe and sensitive evidence can remain structurally separated;
- stable shared interfaces can prevent CLI/UI semantic drift;
- the three features are independently reviewable but form one coherent train;
- packaging does not compromise local-first zero-custody execution.

Otherwise retain the research, improve task-oriented CLI navigation and static
reports, and reassess at a later train boundary.
