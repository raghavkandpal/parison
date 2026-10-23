# Failed suite member investigation contract

Date: 22 October 2026  
Status: implementation on `feature/suite-member-investigation`; qualification pending

The Workbench implementation accepts the exact case ID from the verified case
list. Raw export uses a global limit of 1–100 and a per-run limit of 1–25.
Only already-published samples from a raw-sensitivity child are eligible.

Open a verified failed suite, select one exact member ID from its verified
case list, and inspect that member's existing discrepancy reason groups. The
default view stays summary-safe and is derived from fresh recursive suite and
child verification. It contains no paths, record keys, field names, values or
samples. Unknown IDs, PASS-only members, missing children and changed suite
contents fail closed.

An explicit second action may export the released bounded raw drill-down for
one selected discrepancy group to a new workspace-relative path. It must
reverify the suite and child, use the released `drill_down` and
`export_drilldown` semantics, enforce documented global and per-run limits,
avoid overwrite and mark the output as sensitive before export. The browser
does not receive raw samples. A user decides whether to open or share that
local artifact; the tool never suggests repair or policy approval.

Completion requires tests with multiple failed members, empty groups,
unknown or changed IDs, tampered children, traversal and symlink attempts,
limit enforcement, destination collision and cleanup after failure. Existing
CLI analysis and drill-down bytes and schemas remain readable and unchanged.

No automatic repair, fuzzy matching, unlimited browsing, extraction-truth
claim or cutover decision is part of this capability. [Expansion research](226-release-train-expansion-research.md),
[analysis contract](../1.5/161-discrepancy-analysis-contract.md), [agent contract](../../AGENTS.md).
