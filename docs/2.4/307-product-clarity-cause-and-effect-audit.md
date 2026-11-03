# Product clarity: feasibility and cause-and-effect audit

Date: 3 November 2026
Status: audit complete; owner requires bounded clarity work before 2.4 release; implementation pending

## Verdict

The proposed direction fits Parison strongly when applied to task structure,
onboarding and state-specific guidance. It is a refinement of the accepted
Workbench direction, not a reason to replace the interface or reduce the
verification model. The highest-value opportunity is fewer competing tasks
and clearer transitions, rather than fewer words everywhere.

Treat “Linear’s website or Apple Notes” as the user's shorthand for focus,
obvious interactions and restraint. This audit does not claim visual parity,
benchmark either product, or recommend copying their navigation. A marketing
website, a notes editor and a verification application have different decisions
and failure consequences.

Parison's focused purpose remains: compare baseline and candidate outputs
under an explicit policy and produce portable, independently verifiable evidence.
The human lifecycle is prepare policy, execute explicitly, inspect verified
results, investigate differences, and hand off evidence. PASS means agreement
under that policy; it cannot become a generic success or approval signal.

## Method and evidence limits

This is a repository-based product feasibility assessment, not a rendered UI,
accessibility conformance or usability qualification. Findings below separate
observed structure from predicted user effects. No browser session, user study,
performance benchmark or affected-flow execution was performed. Actual task-time,
visual density and keyboard improvements need validation in a later implementation.
No external product facts are needed or asserted; sources were read locally on
3 November 2026.

Inspected primary repository sources:

- [Product direction and release arc](../0.15/104-product-direction-and-release-arc.md),
  interpreted alongside the later [unified Workbench decision](../2.0/201-unified-workbench-interface-decision.md).
  The older desktop-UI non-goal does not negate the subsequently released local Workbench.
- [Prior UI refinement](../2.0/207-workbench-ui-refinement-checkpoint.md):
  task headings, removed redundant eyebrows, semantic tokens, desktop/zoom scope.
- [README](../../README.md), [maintained guide](../user-guide.md),
  [CLI operator notes](../2.3/274-cli-consolidation-operator-notes.md)
  and [alias contract](../2.3/273-cli-command-alias-contract.md).
- [Embedded Workbench page](../../src/parison/workbench_page.py):
  navigation, forms, status messages, review gates, event handlers and responsive CSS.
- [2.4 roadmap](275-ten-feature-research-and-roadmap.md),
  [recovery contract](296-partition-recovery-contract.md),
  [preview checkpoint](303-partition-session-preview.md),
  ownership checkpoint `306-session-mutation-ownership.md` (read on the
  existing `feature/2.4-session-mutation-owner` branch before creating this
  documentation branch; not yet present on its develop base) and
  [qualification gates](305-tiered-ci-qualification.md).

The existing `tests/test_workbench*.py`, `tests/test_documentation.py` and
`tests/test_cli_consolidation.py` identify verification seams, not evidence that
any proposed refinement already passes. The audit makes no capability or
qualification claim for the unfinished 2.4 train.

## Observed causes and predicted effects

| Surface and observed cause | Smallest plausible improvement | Expected effect | Cost or regression risk; required boundary |
| --- | --- | --- | --- |
| README places a long sequence of release descriptions before “Try it”; the opening still calls the product “proposed.” | Lead with current purpose, released status, one runnable start and a Workbench alternative; link release history and advanced workflows. | New readers reach a first action sooner and encounter less conflicting maturity language. | Moving information can break existing anchors or hide optional formats. Retain destinations and clear links; do not edit historical release records. |
| Results repeats readiness across a lede, field help, status and empty-state paragraph. | Make the empty state carry the single instruction; keep “Bundle folder,” “Verify and open,” and folder-versus-file guidance. | Less scanning before opening evidence; verification remains visible in the action. | Over-cutting can make users select `result.json` or mistake open for an unchecked viewer. Preserve folder semantics and live status. |
| Plans presents recipe opening, suite review and suite-v2 authoring before the loaded recipe editor. | Offer explicit “Edit recipe,” “Review suite,” and “Create suite” task selection; show the selected existing section. | The next action and relevant controls become easier to locate. | Hidden forms can lose edits, validity state or focus. Preserve drafts and exact selection; no default policy or automatic execution. |
| Run shows direct-run and suite-rehearsal forms together; a suite depends on preparation in Plans. | Use the prepared context to emphasize its matching form, with an explicit way to switch. | Fewer dead ends and competing submit actions. | Context must not silently choose inputs, mode or output; switching must invalidate stale authority and disclose retained state. |
| Nine navigation activities mix lifecycle stages and specialized evidence tasks. | First clarify local sections and transitions; evaluate grouped navigation only if task checks still find confusion. | Better recognition without immediately renaming the application. | Hiding destinations adds recall and clicks. Keep all activities reachable; do not infer that nine items alone proves failure. |
| Compare contains both exact-policy rehearsal comparison and policy-change review. | Visually distinguish “Compare rehearsals” from “Review policy changes,” with the existing rejection guidance linking them. | Users understand which question each operation answers. | Combining these operations into a permissive comparison would weaken the exact-policy boundary. Keep their requests and claims separate. |
| Investigate displays raw-export fields before a verified group is selected. | Reveal the existing export section only after eligible verified evidence exists, with explicit sensitive-export action. | Summary inspection stays focused; raw handling becomes a deliberate next step. | Keep sensitivity, limits and destination visible before export. Never display raw values in the browser or auto-select a group. |
| Many ready-state sentences describe implementation, while labels and actions already describe the task. | Remove duplication within each state; prefer task language such as “Validate before editing” over Python implementation detail. | Less explanatory scaffolding, easier comprehension. | Retain actual operation semantics. Labels must distinguish validation, execution, verification and publication. |
| Run/cancellation handlers warn that publication may have occurred and direct users to Results. | Preserve this guidance; only shorten surrounding repetition. | Users can recover without overwriting a possibly completed result. | A generic “Cancelled” or “Try again” would misstate completion and risk evidence loss. |
| The page already uses semantic color tokens, system fonts, native forms, details elements and explicit status roles. | Reuse these primitives for any hierarchy/disclosure changes. | Restrained continuity with small code changes and no asset or dependency pipeline. | Moving or hiding live regions can suppress announcements; native disclosure alone does not prove focus behavior is correct. |

Predicted effects are hypotheses. Fewer visible controls may reduce scanning but
increase navigation; shorter copy may improve readability but reduce decision
quality. Validate both sides rather than equating a smaller screen with better UX.

## Copy removal rules and concrete examples

Classify text by its job in the current state, not by its length.

| Treatment | Example | Reason and consequence |
| --- | --- | --- |
| Candidate for removal | “Ready for a local bundle” beside the empty Results instruction | Repeats the same idle state; remove only the redundant initial sentence, preserving the status region for later progress and errors. |
| Candidate for rewriting | “The Python engine validates it before the editor displays its exact source” | Implementation detail obscures the task; “Validate a recipe to edit it” is a candidate, not approved replacement copy. |
| Consolidate near the decision | Repeated unapproved-draft explanations | Retain an explicit unapproved-draft export label and policy boundary where export/review occurs; avoid making users remember a notice from another screen. |
| Keep visible before action | Raw export sensitivity, item limits and new destination | Users need these facts before creating a sensitive artifact. |
| Keep available at the field | Structured locator syntax, shard pairing, inherited limits and exact tag matching | These change the input's meaning; contextual disclosure is possible, omission is not. |
| Preserve state-specific recovery | Connection failed; check the output in Results before reusing the path | Failure does not establish that publication never happened. |
| Preserve as evidence | Outcome, completeness, effective policy and integrity distinctions | A clean PASS badge alone cannot express the supported claim. |

Do not replace visible labels with placeholders, rely on color alone, delete
accessible names or strip `role="status"`/live announcements to reduce DOM size.
A universal word-count target would reward removing necessary meaning.

## Implementation feasibility and developer consequences

The current embedded HTML/CSS/JavaScript can support the first refinements.
Native sections, `hidden`, buttons and `details` are sufficient. No frontend
framework, router, component registry, generic workflow engine, remote font,
analytics service or dependency is justified by this prompt.

The page also contains tightly connected event handlers and explicit revision,
selection and invalidation state. Moving markup without understanding those
connections is not automatically low risk. Keep existing IDs and handler
bindings where possible; inspect every caller of an affected helper and preserve
review-before-execute and reverify-before-export transitions. A task selector
must manage visibility and focus, not become a second policy/state engine.

Splitting the embedded page into a new asset system or refactoring the host is a
separate proposal requiring concrete evidence. Prefer a few local changes to
existing markup and state transitions. Maintain semantic color roles and outcome
contrast; typography consistency and spacing come before decorative motion.
Any report-template change needs its own compatibility assessment because
published artifacts and canonical fixtures differ from ephemeral Workbench chrome.

## Relationship to unfinished 2.4

The owner requires the bounded clarity work below before releasing 2.4. Complete
the README entry path, Results empty-state consolidation, Plans task selection,
and the Run/Investigate disclosure assessment before release qualification.
Implement the latter disclosure changes only where the assessment demonstrates
a clearer flow with preserved authority and recovery; record any no-change
decision and evidence. Navigation redesign and architecture rewrites are not
release requirements. Verify affected flows and document completion against
this audit. Continue the current feature 4 checkpoint first.

This requirement does not add an eleventh feature, replace a train gate, or count
polish toward the all-ten completion requirement. Keep feature 4's ownership,
locked recognition, atomic journal transitions, safe abandonment and retained
execution gates independent of this direction. The current implementation branch
and unrelated continuation edit are not an implementation surface for this audit.

In particular, released suite recovery in Workbench is not proof that the new
partition-session recovery exists. Do not expose resume, reuse or abandon actions
for incomplete partition capabilities; read-only preview is not execution
permission. A retained cache is sensitive, unsigned local state, not final evidence.

Use this direction as a design constraint when later 2.4 human-facing workflows
are implemented: show the next supported action, preserve explicit review, make
unsupported/incomplete states honest, and carry verification and scope forward.
Do not create one new navigation item or form for every backend capability by
reflex. Any consolidation still needs a versioned contract where semantics change.

## Suggested sequence and completion gates

These are bounded pre-release slices. The current instruction is to record
them and continue feature 4 first, not implement them in this documentation change.

1. **README entry path.** Move current purpose/start ahead of chronology, retain
   advanced links and historical anchors, and reconcile maturity language.
   Gate: a clean-environment reader can find CLI and Workbench starts, understand
   the smoke test versus reviewed policy, and follow every retained link.
2. **One Results empty state.** Consolidate idle instructions without changing
   bundle handling. Gate: folder selection, manual path, invalid/tampered bundle,
   valid summary, clear/reopen and keyboard status/focus behavior remain correct.
3. **Plans task selection.** Isolate recipe editing, suite review and authoring
   within the current activity. Gate: each remains reachable; edits survive
   switching; invalid drafts cannot export; changed selections invalidate review;
   suite continuation preserves exact selection and never starts a run.
4. **Only after those checks, evaluate Run and Investigate disclosure.** Gate:
   direct and suite runs, cancellation, partial publication, catalog failure,
   stale review, eligible/ineligible raw export, limits and export failure all
   preserve their previous authority and recovery behavior.

For implementation, run the relevant existing focused suites using
`make test TEST=tests.test_workbench_page`, adding host/plans/authoring/recovery
suites only where behavior changes; use `tests.test_documentation` for guide or
reference changes. Add regression tests for actual defects and canonical byte
fixtures for serialization changes, not tests that merely mirror copy edits.
Manually inspect rendered desktop, narrow desktop and zoom states, keyboard
navigation, accessible names, announcements and focus after disclosure.
Run required `make check` before a feature commit. CLI, packaging, schema or
platform changes additionally require the exact-head full matrix in the CI gate
contract; this prompt is no reason to alter those surfaces.

Compare task completion, wrong turns, missed warnings and recovery success using
fixed local fixtures before and after each slice. An improvement passes only if
users can still identify the policy, supported claim, next action and recovery
path. Do not claim measured gains until these checks are performed.

## Threats and non-goals

The main threats are hidden safety decisions, stale review becoming executable,
raw evidence disclosure, false completion after cancellation, and visual confidence
being mistaken for migration approval. Keep their safeguards at the point of use.

This is not a brand redesign, mobile product, hosted dashboard, command removal,
automatic policy selection, new onboarding wizard, architecture rewrite or
cutover-approval layer. No functionality, public commands, canonical evidence,
source handling or trust boundary changes are proposed as incidental cleanup.

The smallest useful outcome is a clearer entry and one clearer task at a time,
with the same explicit policy and verified evidence underneath.
