# Workbench suite plan review

Date: 22 October 2026  
Status: released in 2.1.0

The Plans activity can review an existing suite version 1 or 2. The operator
enters a workspace-relative suite file and optional exact case IDs, tags and
shard index/count. The local Python host validates the suite with the released
`list_suite` path, including every referenced recipe and input, and returns
the ordered selected case IDs, comparison modes, tags, counts and suite policy
digest when version 2 supplies one. It also shows each member's exact recipe,
baseline and candidate references for local plan review, and validates an
optional new workspace-relative output path. These references are plan input,
not derived evidence; the browser does not receive record values, recipe
contents or case descriptions. Validation executes no inputs and does not
approve a policy.

Before invoking the released suite loader, the host rejects plan and reference
paths outside the active workspace. Plan-relative `..` references and legacy
absolute member references are accepted only when their normalized target stays
inside the workspace and no target component is a symlink. The plan path and
output stay workspace-relative.
Invalid selections, missing references and invalid suite plans fail closed.
Changing a UI field hides the previous selection until it is validated again.
The subsequent execution feature must revalidate the suite and selection at
submission; this preview never authorizes a later run.

Completion gate: focused Workbench host tests cover valid v2 selection,
summary-safe output, rejected unknown case IDs and rejected traversal. The
full `make check` gate and exact-head CI must pass before integration.

No new suite format, comparison semantics, bundle bytes, CLI JSON or approvals
are introduced. Suite execution and handoff remain separate 2.1 slices.
