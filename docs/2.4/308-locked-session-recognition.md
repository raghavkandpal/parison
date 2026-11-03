# Recognition under existing session ownership

Date: 3 November 2026
Status: private prerequisite; no retained execution or abandonment

Extract `_recognize_owned` from the existing preview reader. It borrows the
caller's already-held root/lock ownership, validates bounded primary metadata,
routing, child results and file/namespace identities, then closes child handles
and returns recognized journal/plan metadata. It acquires no second kernel lock,
performs no mutation, and grants no cache reuse or execution authority.

A root namespace/change-stamp snapshot spans recognition even under mutating
ownership. Callers must retain ownership throughout the call. Preview continues
to use immutable read ownership and preserves its response, error and byte
contracts. Native Windows callers pass their borrowed root pin; preview's
existing read-owner callback retains its native checks.

New tests exercise recognition with `_acquire` forbidden inside an already-held
writer, exact metadata across all five fixture profiles, release of child pins
before mutation, and rejection of root changes while writer ownership remains
valid. Existing preview hostile-input and canonical-response tests remain gates.

Ownership PR #145 integrated at `37efb1e` from exact head `1be1f81`, with fresh
independent Standards/Spec clearance and successful quality, preflight and
manual full qualification [run41310841173](https://github.com/raghavkandpal/parison/actions/runs/41310841173).

Next: qualify this extraction at its exact head, then implement bounded atomic
journal transitions and safe abandonment under contract296. Retained execution
remains a separate subsequent gate; feature4 and the all-ten2.4 train remain
incomplete. Complete the bounded clarity work in audit307 before release.
Stop near95% weekly usage, never consume a reset automatically. Preserve the
unrelated continuation297 edit. Full exact-head review/CI evidence must be read
from the PR; local success alone does not qualify native integration.
