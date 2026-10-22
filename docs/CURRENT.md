# Current development state

- Version: **2.1 release train in development after 2.0.0**
- Branch: `develop`
- Theme: local-first verification — the Workbench suite workflow is complete;
  further substantial capabilities are being selected for the 2.1 train
- Released: explicit JSON Pointer, bounded QName XML, exact XLSX named-table
  record projection and the 1.9 JSON/XML/XLSX structured field-selection train
  across all comparison modes
- Verified: exact 1.8 merge `511b1bbc9c68a581760939b72690255ec545dbbb` passed the full [built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39230867633) and [quality gate](https://github.com/raghavkandpal/parison/actions/runs/39230867642); public assets were checksum-verified and all three projection workflows passed fresh
- Verified: combined parser-train checkpoint `defb65fac85ac0bc8eac48b2f6f70af3ebb07bcc` passed the full [built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39201282230), [quality gate](https://github.com/raghavkandpal/parison/actions/runs/39201282259), independent Standards and Spec review, and a fresh Python 3.14 named-table wheel smoke
- Implemented and reviewed: JSON field projection under recipe versions 4--6
  passed fresh blind Standards and Spec review after correcting preflight
  source pairing, XML schema coverage and controlled surrogate rejection
- Verified: exact JSON field-projection checkpoint
  `c657fb2c3afefa6e2fb495cab59020a0b60bf3b7` passed the full
  [built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39233529242)
  and [quality gate](https://github.com/raghavkandpal/parison/actions/runs/39233529210)
- Implemented: XML field projection selects exact record attributes or bounded
  unique child-element paths under policy-owned namespace bindings and a
  closed record shape; fresh Spec review is clear and the Standards tail-text
  finding is corrected and independently cleared
- Verified: exact XML field-projection checkpoint
  `94078a4ffb6bcc68127f663359f7346e97870b86` passed the full
  [built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39272848506)
  and [quality gate](https://github.com/raghavkandpal/parison/actions/runs/39272848633)
- Implemented and reviewed: XLSX defined-name projection resolves one exact
  non-reserved workbook-scoped static name to one local bounded rectangle,
  with raw metadata auditing, portable suites, summary-safe evidence and
  strict preflight schemas v19--v24
- Verified: exact XLSX defined-name checkpoint
  `5a0f8009681ffef327985d9439ffafb84fc1c236` passed the full
  [built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39275323739)
  and [quality gate](https://github.com/raghavkandpal/parison/actions/runs/39275323852)
- Verified: combined Standards review passed; combined Spec review found one
  preflight source/projection pairing gap, corrected in all six structured
  schemas and independently cleared. Full `make check` passes 400 tests with
  11 optional skips at exact combined checkpoint `75e5ea0`.
- Verified: exact 1.9.0 candidate
  `6876da905bc795fa49568b80ccf13866cc80f31d` passed complete
  [built-wheel CI](https://github.com/raghavkandpal/parison/actions/runs/39369300738),
  [quality CI](https://github.com/raghavkandpal/parison/actions/runs/39369300726),
  clean-archive artifact inspection and a fresh Python 3.14 wheel smoke
- Released: exact merge `703e5b9daa39e9165f7bced933354061af0d5f89`
  passed [built-wheel CI](https://github.com/raghavkandpal/parison/actions/runs/39369665801)
  and [quality CI](https://github.com/raghavkandpal/parison/actions/runs/39369665788);
  annotated tag and [GitHub release 1.9.0](https://github.com/raghavkandpal/parison/releases/tag/1.9.0)
  publish checksum-verified artifacts whose public wheel passed all 20 fresh
  JSON, XML and XLSX structured-selection workflow tests
- Implemented: first 2.0 slice adds `parison workbench`, a Python-native
  launcher for a deterministic script-free local application. It verifies an
  existing bundle before rendering, applies a closed summary-safe projection,
  and publishes atomically without overwrite or network access.
- Verified: exact Workbench checkpoint
  `fbb6ea5675fee8bd5ed787aafe4291e6349d441c` passed the complete
  [built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39370931644)
  on Python 3.11--3.14 with direct macOS and Windows Workbench smoke coverage,
  plus the [quality gate](https://github.com/raghavkandpal/parison/actions/runs/39370931604)
- Implemented locally: the first plan-builder slice adds an explicit
  `workbench plan` activity with authoritative initial validation, exact JSON
  import, policy identity, local draft export and equivalent CLI commands;
  drafts remain visibly unapproved and execute nothing
- Verified: exact plan-builder checkpoint
  `c9628d250ab112e830f1ce613678806453205b3f` passed the
  [quality gate](https://github.com/raghavkandpal/parison/actions/runs/39371521497)
  and complete [built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39371521251)
  on Python 3.11--3.14, including direct evidence and plan application smoke
  checks across every macOS and Windows entry
- Decided: 2.0 exposes one `parison workbench` application with Plans, Run,
  Results, History, Investigate and Compare activities. The current `evidence`
  and `plan` commands are prototypes, not the release interface. See the
  [unified interface decision](2.0/201-unified-workbench-interface-decision.md).
- Implemented: `parison workbench --workspace DIRECTORY` starts one
  numeric-loopback Python host on an ephemeral port with a per-launch
  capability, closed routes, strict Host validation, restrictive browser
  headers and no filesystem or execution endpoint
- Implemented locally: the unified Results activity accepts one explicit
  workspace-relative, non-symlink bundle path and returns the existing closed
  summary-safe projection only after integrity verification, with exact Origin,
  Host, capability, content-type and request-size enforcement
- Implemented locally: Results can invoke a fixed native macOS or Windows
  directory chooser constrained to the workspace, and users can clear the
  rendered result without changing the verified bundle
- Implemented locally: unified Plans opens an existing workspace recipe through
  authoritative validation, shows exact source and effective policy identity,
  supports constrained native file selection, clears browser state on request,
  and downloads edits only as explicitly unapproved local drafts
- Verified: exact unified Plans checkpoint
  `462eeac3b9e21b641df2070a4cdff8bfbde91c94` passed the complete
  [built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39398735075)
  on Python 3.11--3.14 with macOS and Windows smoke, plus the
  [quality gate](https://github.com/raghavkandpal/parison/actions/runs/39398735044)
- Implemented locally: every Plans edit invalidates its displayed policy
  identity and disables download until a closed, bounded, non-persisting route
  validates the exact current text through the authoritative Python loader
- Verified: exact edited-plan validation checkpoint
  `4233c8542b80dbc07546a63dd7697607ac29bfa2` passed the complete
  [built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39400756824)
  on Python 3.11--3.14 with macOS and Windows smoke, plus the
  [quality gate](https://github.com/raghavkandpal/parison/actions/runs/39400756800)
- Recorded: the first reproducible Impeccable source and rendered-browser audit
  scored the current Workbench 13/20 and identified a bounded responsive,
  touch-target, contrast, token and hierarchy refinement slice. See the
  [Workbench Impeccable UI audit](2.0/206-workbench-impeccable-audit.md).
- Implemented locally: the desktop Workbench now uses semantic color and
  spacing tokens, higher-contrast planned states, direct heading hierarchy and
  overflow-safe loaded-plan controls. Dedicated mobile navigation and touch
  interaction remain explicitly out of scope; narrow layouts only protect
  resized desktop windows and zoom use. See the
  [Workbench UI refinement checkpoint](2.0/207-workbench-ui-refinement-checkpoint.md).
- Verified: exact Workbench UI refinement checkpoint
  `66bdc427bf489eb290c387c5e7aa3885002ec856` passed the complete
  [built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39433950485)
  on Python 3.11--3.14 with macOS and Windows smoke, plus the
  [quality gate](https://github.com/raghavkandpal/parison/actions/runs/39433950126)
- Implemented locally: the unified host limits concurrent request handlers,
  exposes one capability- and origin-guarded shutdown route, clears its launch
  capability before stopping and gives the browser an explicit Stop workbench
  action. See the [host lifecycle checkpoint](2.0/208-workbench-host-lifecycle-checkpoint.md).
- Implemented locally: Run performs authoritative record preflight, in-process
  comparison, atomic publication, bundle verification and safe catalog
  registration for one explicit recipe and input pair. It exposes bounded
  structured phases and cooperative cancellation at the shared input-row
  boundary; cancellation before publication leaves no bundle or catalog entry.
- Implemented locally: History preserves catalog insertion order, Compare
  enforces the existing exact-policy gate, and Investigate returns a stricter
  Workbench projection of verified discrepancy groups without paths, field
  names, policy values, record keys or samples. See the
  [run/history contract](2.0/209-workbench-run-history-contract.md).
- Reviewed: the unified Workbench code checkpoint `d1ba0a4` passed the complete
  [built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39440174683);
  the later reviewed head `a37a15d` passed the
  [quality gate](https://github.com/raghavkandpal/parison/actions/runs/39440995964).
  The [2.0 state review and next plan](2.0/210-workbench-state-review-and-next-plan.md)
  records the Run locator mismatch, remaining Plans gate and current-guide
  drift without treating this evidence as release qualification.
- Implemented locally: Workbench Run resolves released structured input
  locators inside the workspace while retaining format selectors; focused host
  tests cover path rejection and a JSON run. Exact-head qualification remains.
- Verified: Run locator fix merged through PR #56 at `a5f2b90`; the exact
  merge passed the full [built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39564064545).
- Implemented locally: schema-derived Plans controls for recipe versions 1--6,
  explicit omitted settings and effective policy display, exact field edits and
  workspace-constrained input handoff. See the
  [Plans controls checkpoint](2.0/212-workbench-plan-controls-checkpoint.md).
- Reviewed: Plans passed independent Standards/Spec source review and a
  labeled unfamiliar-agent proxy trial with informed in-app browser followup.
- Verified: exact Plans implementation `77b05ab` passed the full
  [built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39570203040)
  and [quality gate](https://github.com/raghavkandpal/parison/actions/runs/39570191438).
  [PR #57](https://github.com/raghavkandpal/parison/pull/57) was integrated at
  `be1b872`; its exact merge passed the full
  [built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39605729250)
  and [quality gate](https://github.com/raghavkandpal/parison/actions/runs/39605728982).
- Verified: README now separates the released 1.9 wheel quickstart from the
  unreleased source-checkout Workbench, merged through PR #58 at `af16cd5`.
- Verified: Run now reports post-publication and catalog failures honestly,
  preserving any verified output for explicit Results inspection. The fix
  merged through PR #59 at `8d9272e` after exact head `57224cb` passed the
  complete [built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39607547089).
- Combined local `make check` passes 422 tests; fresh rendered inspection
  covered rejected Run inputs, validated Plans controls and explicit shutdown.
  See the [integration checkpoint](2.0/215-workbench-integration-checkpoint.md).
- Reviewed: an informed participant completed the synthetic Plans usability
  task, reported no confusing or misleading steps, and confirmed that
  validation/download do not approve a policy and input handoff does not run
  it. See the [trial record](../studies/workbench-plans-01/human-trial-01-report.md).
- Reviewed: independent combined Standards and Spec reviews each found one
  defect. Compare now rejects modified or missing cataloged bundles (PR #61,
  merged at `caf1e6d`), and stalled Workbench clients cannot block the accept
  loop (PR #62, merged at `5bcedf7`). Both reviewers cleared their findings
  after regression fixes. See the [combined review](2.0/218-workbench-combined-review.md).
- Verified: exact PR #62 head `2d4b788` passed the complete
  [built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39611398493)
  on Linux, macOS and Windows with Python 3.11--3.14; combined local
  `make check` passed 424 tests.
- Released: exact 2.0.0 merge `9f4846a45bac5f0c5e8e20e8cb4d56d7de725edc`
  passed [quality CI](https://github.com/raghavkandpal/parison/actions/runs/39733155869)
  and the [full built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39733155795).
  The [public release](https://github.com/raghavkandpal/parison/releases/tag/2.0.0)
  was checksum-verified and its wheel passed a fresh local Workbench smoke;
  see the [release checklist](2.0/219-release-checklist.md).
- Implemented: 2.1 Workbench suite plan review, bounded local suite rehearsal
  and verified unsigned handoff merged through [PR #68](https://github.com/raghavkandpal/parison/pull/68)
  at `40288e4`. Its exact merge passed [quality CI](https://github.com/raghavkandpal/parison/actions/runs/39737204435)
  and the [full built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39737204420).
- Corrected: Workbench accepts released partitioned suite inputs and binds
  reviewed plans to their selected bytes. [PR #69](https://github.com/raghavkandpal/parison/pull/69)
  merged at `b3c5c69` after its exact head passed the
  [full built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39780279353).
- Next gate: implement and qualify [repeated suite comparison](2.1/227-suite-comparison-contract.md),
  then [failed-member investigation](2.1/228-suite-investigation-contract.md)
  as distinct 2.1 capabilities before restarting candidate qualification.

## Recorded next steps

- Development resumed by explicit user direction after the verified 1.9.0
  release. Follow the active 2.0 research, contract and checkpoint documents;
  internal review and test evidence never establishes operational policy or
  cutover approval.

- When an autonomous session stops near its usage limit, return a copy-ready
  next-session goal prompt. Include the exact branch and commits, green CI and
  review evidence, completed train features, open findings, next gate,
  compatibility constraints, release cadence and the through-v5.0 direction
  so work resumes without repeating discovery.

- Every release after 1.7.0 must contain at least three separately reviewable,
  substantial feature additions. Push and record green feature checkpoints,
  but do not open a candidate, tag or publish until all three are complete.
  Refactors, fixes, documentation reconciliation and test hardening do not
  count unless they independently add material user capability. Follow
  [RELEASING.md](../RELEASING.md) and the accepted
  [product direction](0.15/104-product-direction-and-release-arc.md).

- Preserve the released [1.8 roadmap](1.8/177-roadmap.md) and projection
  contracts. Release 1.8.0 is complete at exact merge
  `511b1bbc9c68a581760939b72690255ec545dbbb`; the public wheel, source and
  checksums were re-downloaded and all three parser workflows passed fresh.

- Follow the active [1.9 roadmap](1.9/188-roadmap.md) and
  [structured field-selection research](1.9/187-structured-field-selection-research.md).
  Keep record/range locators separate from logical-field policy, preserve
  recipe versions 1--3, and do not begin candidate work until JSON, XML and
  XLSX feature checkpoints are independently qualified.

- Preserve the released [1.7 roadmap](1.7/172-roadmap.md) and [SQLite aggregate contract](1.7/173-aggregate-sqlite-contract.md). Cross-engine equivalence, controlled failures, cleanup and dual-cardinality benchmarks are qualified; keep engine selection explicit and preserve aggregate-v1 semantics and evidence bytes.

- Release 1.7.0 is complete at exact merge `5da6e08dc97c4bdef3f57c6b71a272b42d7ea171`; public wheel, source and checksums were re-downloaded and the public wheel passed the primary SQLite aggregate smoke.

- Follow the active [1.6 roadmap](1.6/166-roadmap.md), accepted [current-workflow research](1.6/165-current-workflow-research.md) and approved [XLSX values research](1.6/169-xlsx-values-projection-research.md). Keep task guidance hand-written, require explicit worksheet/range selection and preserve every released contract as history.

- The [pre-1.5 repository quality and layout plan](157-repository-quality-and-layout-plan.md) is complete at exact commit `35fe2d0`; see the [maintenance checkpoint](158-repository-maintenance-checkpoint.md). Ruff is mandatory, contributor standards are documented, `core.py` is a compatibility facade and atomic no-replace publication is consolidated in `_safe_fs.py`.
- Exact maintenance commit `35fe2d0578ac54956c58bd4501aba8ae03fb8de2` passed the full built-wheel matrix on Python 3.11–3.14 across Linux, macOS and Windows in [CI run 39015498650](https://github.com/raghavkandpal/parison/actions/runs/39015498650). No product release was created for internal maintenance.
- Per-run reason groups, exact-policy direct/catalog series, bounded raw-sample drill-down, strict installed summary/raw schemas, canonical atomic artifacts and CLI workflows are implemented. Review corrections pass 342 local tests, independent Standards/Spec re-review and exact corrected cross-platform CI.

- Follow the active [1.4 roadmap](1.4/153-roadmap.md) and frozen [manifest/reproducibility contract](1.4/154-dataset-manifest-and-reproducibility-contract.md). Keep exact byte identity, semantic agreement and runtime explanation as separate claims.
- Strict schemas, canonical identities, descriptor-relative named-file verification, reviewed closed scopes, summary-safe results and informational diagnostic comparison are implemented. The opt-in `dataset-evidence` bundle carries the canonical manifest, full verification result, effective policy, diagnostic and recursively verified semantic result as semantically bound members without changing released bundle readers.
- Reject implicit discovery, remote resources, live SQLite state, path traversal, symlinks, aliases and environment inventories. Do not let diagnostic differences alter verification outcomes in v1.

- Follow the active [1.3 roadmap](1.3/148-roadmap.md) and frozen [contract](1.3/149-time-alignment-and-reconciliation-contract.md) as one coherent capability: existing per-dataset parity plus a fixed UTC half-open event window and per-side identity, reference and grouped-sum conservation checks.
- `time-alignment-v1` and `reconciliation-v1` now have strict installed schemas, semantic cross-reference validation, canonical bytes and fingerprints. Alignment preflight binds the receipt and policies, scans both sides under explicit resource limits, and emits strict PASS/FAIL/INCONCLUSIVE JSON without changing released comparison execution.
- Identity and reference checks execute independently on baseline and candidate with deterministic aggregate-only diagnostics and byte-identical memory/SQLite evidence.
- Grouped-sum conservation executes independently on both sides with exact or symmetric tolerance comparison over matching integer/scaled-decimal domains and byte-identical bounded memory/SQLite evidence.
- `parison reconcile` composes alignment, existing keyed/aggregate/multiset parity and all declared relationships under one input-change guard, with conservative FAIL-before-INCONCLUSIVE reduction and a summary-safe projection.
- Reconciliation bundles publish atomically with no overwrite, bind normalized declarations plus every input/receipt identity, verify semantic membership and outcome reduction, and support summary-safe standard inspection.
- Three end-to-end scenarios cover payout reconciliation, relationship failure despite parity, and an alignment-INCONCLUSIVE partitioned backfill; local compatibility, atomic no-replace publication, semantic verification binding and the full 303-test gate pass. Independent review reports no blockers, and exact candidate `b25db99` passed the complete built-wheel matrix plus a fresh Python 3.14 wheel smoke. Merge and publication evidence remain. See the [engineering checkpoint](1.3/150-engineering-checkpoint.md) and active [release checklist](1.3/151-release-checklist.md).
- Preserve extraction ownership upstream. Snapshot tokens and watermarks remain source-owned claims bound by local evidence; a declared cutoff cannot establish coordination and therefore remains `INCONCLUSIVE`.
- Deepen the existing suite, keyed/SQLite and aggregate seams. Do not add connectors, a query language, a graph planner or a second orchestration framework.

- The [`semantic-scalar-v1` contract](1.1/139-semantic-scalar-contract.md) and reader seam passed exact built-wheel CI across Python 3.11–3.14, macOS and Windows at `a12e1783418889cc58718360d25a9a819ce86162`.
- The released [1.2 roadmap](1.2/142-roadmap.md) delivered one larger capability: explicit schema evolution, meaningful policy diffs and qualified semantic-scalar projection.
- `schema-evolution-v1` validation, canonical identity, safe mapping compilation, `policy-diff-v1` classification and summary-safe rendering are qualified and published in 1.2.0.
- The semantic-scalar promotion corpus covers every scalar type, null/empty boundaries, numeric and temporal boundaries, row-order permutations, every supported format and comparison mode, admitted Parquet dtype families, unsupported Parquet families and pinned canonical row bytes. Exact commit `0b07f1cd1705020e7fe039089ea8f8f1e98ac47b` passed the complete built-wheel matrix; see the [1.1 engineering checkpoint](1.1/144-engineering-checkpoint.md).
- Preserve recipe versions 1–3 unchanged. New coercion or rejection semantics require an explicit versioned policy boundary.
- Use `1.x.0` for the next release line, advancing the minor component through `1.20.0`; reserve patch releases for compatible fixes.
- Treat the completed [cross-format projection research](1.1/137-cross-format-semantic-projection-research.md) as the design input: recipe-directed scalar conversion is safe only through a closed source-type allowlist; lossy or inferred conversion stays explicit or upstream.
- Prefer coherent capabilities that materially improve how Parison is developed or used over release-filling collections of small improvements. Features must still preserve the 1.x compatibility contract and explicit local-first boundaries.
- Audit documentation for duplication, stale guidance and deprecated paths. Design a consolidated current guide and clearer topic-based navigation across versions; preserve historical contracts and release evidence, using redirects or archive labeling before deleting anything still needed for compatibility or provenance.

## Feature research inventory

- Explainable failures that connect discrepancies to explicit policy, scope and normalization without suggesting repair.
- Versioned schema-evolution comparison for renamed, added, removed, split and merged fields.
- Explicit time-window alignment using cutoff, watermark and lateness policies.
- Referential and reconciliation checks across related datasets without becoming a database.
- Distribution and drift contracts for reviewed histograms, quantiles, categories and null rates, distinct from exact equality.
- Cross-format semantic projection across CSV, JSONL, SQLite and Parquet first, with workbook semantics researched separately.
- Deterministic discrepancy grouping and bounded drill-down across rehearsal runs.
- Meaningful policy diffs and compatibility impact around approval-ready fingerprints, without implementing approval.
- Dataset manifests covering declared file, partition and table collections.
- Reproducibility diagnostics for environment, parser, dependency, input-identity and policy differences.
- A strict local extraction manifest or receipt contract for unsupported upstream formats.
- Additional evidence interoperability without adding signing, credentials or network custody.
- Streaming, external-sort and other bounded execution improvements only where benchmarks show a real ceiling.
- Contributor tooling for contract fixtures, golden bundles and compatibility testing.
- One task-oriented current guide, generated command reference, concept pages and clearly archived historical contracts.

## Recommended order

1. Specify and qualify `semantic-scalar-v1` because it turns existing mixed-format behavior into a narrow compatibility promise without changing comparison modes.
2. Implement the researched `schema-evolution-v1` and `policy-diff-v1` pair because mappings and reviewability must share one explicit contract.
3. [In progress] Specify time alignment and multi-dataset reconciliation because they unlock broader cutover workflows but introduce the most policy-sensitive semantics.

Adopt a feature only when the research produces a narrow versioned contract, a realistic workflow, explicit non-goals and a checkable compatibility gate. Keep the remaining inventory as options rather than promises.

Authoritative detail: [1.3 research](1.3/147-time-alignment-and-multi-dataset-reconciliation-research.md), [1.3 roadmap](1.3/148-roadmap.md), [1.2 release checklist](1.2/146-release-checklist.md), [semantic scalar contract](1.1/139-semantic-scalar-contract.md), [compatibility contract](0.19/126-compatibility-contract.md) and [post-1.0 direction research](0.20/134-post-1.0-direction-research.md).

Update this page when the active version, completion state, or next gate changes. Keep historical evidence in the version folder.
