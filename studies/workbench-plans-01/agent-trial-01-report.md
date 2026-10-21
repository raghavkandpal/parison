# Workbench Plans agent proxy trial

Date: 21 October 2026

Participant: independent Spec-review agent with fresh context.

This was an agent proxy trial, not a human participant study. The participant
read only the task and used the local interface before inspecting source,
tests, Git or feature contracts. All fixtures were synthetic.

## Initial trial at `0fd2503`

The participant opened `study.json`, found comma delimiters on both sides and
empty normalization lists in the effective policy, then changed the snapshot
and amount tolerance through controls. Python validation passed and the draft
was downloaded. The participant correctly reported that validation and
download do not approve policy.

An outside-workspace baseline was rejected. After recovery, baseline and
candidate locations transferred to Run; its recipe and output remained empty,
the status remained Ready, and no comparison was submitted. Clear restored the
empty Plans view. The participant did not claim that the UI alone proved
original-file preservation or download persistence.

The initial decision was **FIX**: repeated Add/expand actions made tolerance
editing cumbersome; refresh on field blur swallowed a subsequent click; the
footer's “until you review and validate it” wording could suggest validation
ends unapproved status; and Clear did not explain disk lifecycle.

## Corrections and review

The corrected interaction stages scalar field edits until Apply field edits.
Add/remove actions first apply pending changes atomically. Newly added groups
open automatically, and mixed string/number controls explain JSON quoting.
The approval notice explicitly says validation and download never approve
policy. Clear explains that it only clears the page.

Source review separately found a native-picker response that could reopen a
cleared or newer plan. Revision and typed-path checks now guard both response
and body completion. A runnable JavaScript regression exercises both delay
points across clear, newer import and typed-path changes. The importer also
binds policy identity to one exact source read.

Standards and Spec source re-review found no remaining actionable issues.
The Spec agent's informed UI followup was blocked by browser availability;
the primary agent completed it in the Codex in-app browser instead. Pending
field edits enabled Apply and disabled Validate/Download; applying updated the
source and enabled validation. Clicking Add immediately after a text edit
preserved both changes on the first click. Validation enabled the unapproved
download, and Clear displayed the explicit disk-lifecycle notice. At 390 x 844
there was no horizontal overflow and all policy buttons were at least 44px.
This informed followup was not a new blind trial. The record does not establish
human usability or operational approval.
