# Workbench policy-change review contract

Date: 26 October 2026
Status: released in 2.2.0

Feature 4 of the accepted six-feature train deepens Compare with a read-only
recipe-pair review. The operator explicitly selects two workspace-relative
recipe files and one evolution declaration. The host confines every path and
uses the shared released `diff_policies` assessment and `summarize_policy_diff` without reinterpreting
labels, reason codes or canonical identity. No records execute and no files are
written. Draft generation and suite-wide policy alignment are out of scope.

The initial response contains only the released summary and an opaque review
identity bound to the exact three input byte sequences. Input paths remain in
the local form, never in returned summary metadata. ACCEPT is labeled a
mechanical assessment, never approval or permission to compare unequal-policy
evidence. Existing ordinary and suite comparison gates remain unchanged.

Full policy details contain schema-sensitive names and fragments and require
a separate explicit button and request. The host rereads all three files,
recomputes the assessment, and rejects changed bytes or a mismatched review
identity. Assessment uses captured bytes, so transient filesystem edits cannot change the
reviewed assessment. Persistent changes during assessment are rejected. Browser edits clear summary,
identities and details immediately; delayed responses cannot restore stale
state. Clear/hide details removes their rendered content.

Acceptance fixtures cover declared rename, key/tolerance/exclusion/scope
changes and incomplete declaration; summary/service/CLI parity; absence of
paths, names, values and declaration fragments in summary; stale detail requests,
unsafe paths, authentication and late responses; and proof that ACCEPT cannot
bypass exact-policy suite comparison. Existing byte fixtures remain unchanged.
Narrow tests, `make check`, independent Standards/Spec review, rendered UI
inspection and exact-head built-wheel matrix gate integration.

Implementation checkpoint: the shared Workbench service and two guarded routes
now expose byte-bound summary/detail review, with Compare controls that clear
stale state and separately reveal/hide schema-sensitive details. Local
`make check` passes 490 tests. Fixtures cover service/CLI parity, confidentiality,
byte changes during/between requests, authentication/path rejection, delayed
browser responses and the unchanged suite comparison gate. The rendered summary
and detail workflow was inspected. Independent Standards/Spec review identified
a transient-edit identity race, corrected by hashing and assessing the same
captured bytes through the shared released logic. Both reviewers cleared the
fix, including a transient-edit regression. Exact-head CI remains before merge.
