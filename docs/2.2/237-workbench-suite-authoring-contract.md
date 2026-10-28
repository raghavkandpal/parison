# Workbench suite-v2 authoring contract

Date: 26 October 2026  
Status: released in 2.2.0

Implementation checkpoint: the Workbench Plans activity now composes ordered
cases with explicit references, tags, descriptions, limits, SQLite execution
settings and policy locks. It reviews the complete draft at the intended
destination through the released suite loader, binds source identities to a
review token and exports one unapproved local file without replacement.
Focused mixed-mode, relocation, lock, stale-reference, traversal, symlink,
hostile UTF-8, staging-failure and loopback route fixtures pass. Independent
Standards and Spec reviews found controlled-error and unapplied-editor gaps;
both were corrected and independently cleared. A rendered Workbench check
confirmed that unapplied case edits block review. Exact-head platform
qualification remains pending.

## Scope and trust boundary

Workbench composes the released suite-v2 JSON shape. The operator chooses an
ordered, nonempty list of at most 100 cases and supplies each case ID, existing
recipe, baseline and candidate reference, sorted unique tags, optional
description, released limits, optional SQLite execution settings and an
explicit expected policy SHA-256 lock. Suite defaults may contain only released
limits. No choice of comparison key, tolerance, source or approval is inferred.
Authoring does not invoke a runner or create evidence. Export is visibly an
unapproved draft; existing CLI validation, listing and execution consume it.

The draft destination is an explicit new workspace-relative JSON path under an
existing directory. Input
references are interpreted relative to that destination's directory, including
the released structured locator forms. Every referenced path and component must
stay in the active workspace, avoid symlinks and exist before review. The host
normalizes the draft with the authoritative `load_suite` at a private temporary
file in the destination directory, then compares the effective suite identity,
case order and recipe policies. It removes that private file on success or
failure. A destination outside the workspace, an existing destination or an
unsafe parent is rejected. No export overwrites or follows a symlink.

Review returns the exact authored fields, effective suite policy digest and a
short lived review identity bound to the draft bytes, destination and current
referenced contents. Any edit to the draft, destination, recipe or input source
invalidates it. Export revalidates under the host's one-job lock, compares the
review identity, writes canonical draft bytes privately, and installs them
atomically without replacement. The UI clears review state on every edit and
shows explicit case order, effective policy and unapproved status.

## Acceptance fixtures

- Mixed keyed, aggregate and multiset cases, reordered from initial selection,
  with nondefault defaults/case limits, sorted tags, SQLite execution controls,
  and matching policy locks; export to a relocated destination and reload with
  the intended case order and policy digest.
- Wrong policy lock, duplicate ID, invalid limits and unavailable recipe or
  input reject in authoritative review; no draft or evidence is published.
- Traversal, absolute escape, symlinked reference/parent and existing output
  reject before export; a changed recipe or source rejects stale review.
- Instrument runners to prove review/export never executes a suite or case.
  Existing suite-v1 bytes, APIs, CLI JSON and exit codes remain unchanged.

## Qualification

Narrow Workbench and suite tests, `make check`, independent Standards/Spec
review, exact-head PR CI and the full built-wheel platform matrix must pass
before integration. This capability is feature checkpoint 2 of 6; no candidate
preparation follows until every feature checkpoint is complete.
