# Feature 3 exact hash discovery execution

Date: 31 October 2026
Status: implemented locally; independent review and exact-head CI pending

The corrected integrity reader integrated through [PR131](https://github.com/raghavkandpal/parison/pull/131)
at `5b5c4133866e816b36bc71a18a67a40e67010e68`. Exact head
`74918499e5b86c44d5804cd8ccae8794534e4d1a` received independent Standards/Spec
clearance and passed [quality](https://github.com/raghavkandpal/parison/actions/runs/41215517267)
and [full built-wheel CI](https://github.com/raghavkandpal/parison/actions/runs/41215514459).
This supersedes checkpoint293's pending integration state.

This slice enables the producer and exact source-backed replay frozen in
[contract291](291-composite-key-discovery-contract.md) through the existing
`parison partitions discover|verify` commands and their released alias. There
is no new project script or dependency. Hashes route typed normalized tuples;
the released exact comparator decides identity and field agreement. PASS remains
agreement under an explicit policy, never extraction truth or cutover approval.

Recipe and CSV handles remain pinned through publication. Source bytes are copied
into a private workspace with streaming digests and shared byte accounting;
semantic reads use those snapshots. The bounded frame reuses the existing typed
encoder. All buckets retain their original rows and use sorted physical columns;
only one side's bucket writers remain open at once. The mechanically derived
recipe changes only expected_empty for local bucket comparison. Original global
empty policy and incomplete-result suppression remain authoritative.

The producer checks source identities, private bytes, stamps and membership,
removes sensitive staging, writes bounded canonical metadata and verifies it
before atomic no-overwrite publication. Exact replay compares the entire private
receipt while evidence handles remain pinned. It requires all three source
arguments and an identical admitted CPython3.11–3.14 runtime descriptor before
opening sources. Integrity-only reading continues to admit well-formed future
context descriptors. Range-v1 bytes and investigation-v1 admission remain intact.

The execution gate covers frozen key/golden bytes, every bucket count2..128,
forced routing collisions, full-engine oracle agreement, null/duplicate/empty
cases, limits, mutations, interruption cleanup and publication races. Full local
checks, cross-Python execution tests, independent Standards/Spec reviews and
exact-head quality/manual full built-wheel CI must pass before integration.
Feature3 remains incomplete until then; features1/2 are integrated (2/10).
All ten features must integrate and qualify before any2.4 candidate.

Independent review found publication redirection through a replaced staging
path and cleanup that trusted the replaced name. The correction anchors metadata
writes and sensitive cleanup to the owned directory descriptor where available,
checks directory identity around path-mode operations and preserves unrelated
replacement directories. Replay now also binds the root directory identity in
path mode, rejecting a substituted root containing identical hardlinked members.
Regressions cover both publication attacks, partial-copy interruption on each
side and a candidate-only final-side failure. Corrected-head review/CI remain
required; earlier head f4b0187 cannot qualify this correction.

Corrected local gate:674 repository tests pass with lint, formatting, generated
command documentation and whitespace checks;34 execution/reader/wire tests pass
on CPython3.11.18,3.12.5,3.13.18 and3.14.7. These local results do not replace
independent corrected-head review or the manual full built-wheel matrix.
