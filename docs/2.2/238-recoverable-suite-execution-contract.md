# Recoverable suite execution contract

Date: 26 October 2026  
Status: frozen before implementation

Implementation checkpoint: the runner shares its exact checkpoint eligibility
rule with read-only preview. Workbench exposes explicit temporary, restart and
resume modes, retained-state preview, cooperative cancellation and guarded
abandonment. Owned Workbench checkpoints also bind the reviewed selection;
released CLI checkpoints and bundle bytes remain unchanged. Host operations
serialize validation and execution under the run lock. Verified publication is
preserved and reported separately when History registration fails.

Focused fixtures cover actual reuse, cancellation during a later member, changed
input/selection/policy, tampered checkpoints, new-workspace restart, path overlap,
unsafe ownership and active abandonment. Independent review and exact-head CI
remain required before integration.

## Deliberate lifecycle

Workbench exposes a retained local execution workspace only after an explicit
operator choice. The workspace may hold sensitive partial evidence. A new run
with retention uses the released suite-v2 `run_suite(..., workspace=PATH)`
path and one job. A cancelled run leaves only this deliberately retained
workspace; no incomplete parent bundle is added to History or shown as PASS.
Without retention, released temporary cleanup remains unchanged.

Restart and resume are separate actions. Restart uses a new output and a new
workspace, with no reuse. Resume requires an existing, structurally safe
retained workspace and a new output. A read-only preview lists selected cases
in their declared order as reusable or pending. It delegates eligibility to
the runner's `_reusable_workspace_child` rule, including complete verified
checkpoint, suite/case policy, effective limits, sample limit, runtime version,
current baseline/candidate source digests and resource limits. Preview never
authorizes a later resume; submission rechecks every case under the run lock.
Recipe, selection, input or checkpoint changes prevent stale reuse. The UI
labels retained work as sensitive local state and makes the chosen mode and
workspace explicit before execution.

Abandonment requires an explicit owned workspace path and an explicit action.
The host checks workspace confinement and ownership marker, rejects symlinks,
active use and output paths, and removes only that retained workspace. An
unmarked directory is never inferred to be disposable. The marker is created
only by the Workbench retention path and binds the owning workspace root; it
is local operational state, not evidence or approval.

## Acceptance fixtures

- Complete first member, cancel during a later member, then preview and resume
  with an instrumented first member to prove actual reuse.
- Change input, recipe, selection and checkpoint independently; each must
  report non-reuse and recompute. A changed preview cannot grant reuse.
- Restart to a fresh destination without reuse. Reject retained-state
  collisions, traversal, symlinks, unmarked directories and active abandonment.
- If final bundle publication succeeds but History registration fails, retain
  the verified output and report the registration failure separately.
- Existing CLI JSON/exit codes, released suite bundles and no-retention cleanup
  remain unchanged. Narrow suite/Workbench tests, `make check`, independent
  Standards/Spec review and exact-head full built-wheel CI gate integration.

This is feature checkpoint 3 of 6. Policy-change review, suite series and the
complete reconciliation workflow follow before candidate preparation.
