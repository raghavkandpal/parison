# Workbench suite plan review

Date: 22 October 2026  
Status: implemented on the first 2.1 feature branch; qualification pending

The Plans activity can review an existing suite version 1 or 2. The operator
enters a workspace-relative suite file and optional exact case IDs, tags and
shard index/count. The local Python host validates the suite with the released
`list_suite` path, including every referenced recipe and input, and returns
the ordered selected case IDs, comparison modes, tags, counts and suite policy
digest when version 2 supplies one. The browser shows no reference paths,
recipe keys, values or case descriptions. Validation executes no inputs and
does not approve a policy.

Before invoking the released suite loader, the host rejects absolute,
traversing or symlinked plan and reference paths outside the active workspace.
Invalid selections, missing references and invalid suite plans fail closed.
Changing a UI field hides the previous selection until it is validated again.
The subsequent execution feature must revalidate the suite and selection at
submission; this preview never authorizes a later run.

Completion gate: focused Workbench host tests cover valid v2 selection,
summary-safe output, rejected unknown case IDs and rejected traversal. The
full `make check` gate and exact-head CI must pass before integration.

No new suite format, comparison semantics, bundle bytes, CLI JSON or approvals
are introduced. Suite execution and handoff remain separate 2.1 slices.
