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

A second review found a redundant pathname chmod and a remaining path-mode
cleanup check/delete race. Remove the chmod: Python documents that
[mkdtemp creates a private directory](https://docs.python.org/3.11/library/tempfile.html#tempfile.mkdtemp).
Cleanup now reacquires and checks the owned POSIX directory descriptor even
in emulated path mode. Windows pins the directory with CreateFileW while
excluding delete sharing, rejects reparse points and removes only an empty root
after releasing the pin; see Microsoft's [directory handles and sharing rules](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)
(accessed31October2026). Regression tests exercise substitution at capability
reacquisition, unchanged unrelated permissions and native Windows rename denial.
The manual matrix explicitly runs all hash tests from the built wheel on macOS
and Windows for every supported Python version, in addition to Linux tests.
Earlier head3d61067 is superseded and cannot qualify these final corrections.

Publication itself also retains the native Windows ownership pin throughout
workspace/metadata operations and releases it immediately before the final
identity check and atomic rename. POSIX producers reacquire directory capabilities
even when the evidence reader uses its path fallback. This closes redirected
writes between a pathname pre-check and open, rather than merely detecting the
outside write afterward. Native Windows and emulated-reader metadata-open
regressions exercise that boundary. Platform CI retains targeted hash tests;
it does not add full-suite discovery to the macOS/Windows smoke jobs.

The Windows ownership pin also protects the sensitive child workspace throughout
snapshot creation, routing and exact comparison, and replay's private parent.
Workspace ownership closes on success before deletion while original source
handles stay pinned through publication; exception cleanup closes both. Native
Windows tests attempt workspace rename at snapshot and bucket file-open phases.

Final correction local gate:681 repository tests pass under `make check`, and41
hash execution/reader/wire tests pass on each of CPython3.11.18,3.12.5,3.13.18
and3.14.7. Three native Windows tests are skipped on this macOS host and must
run in the exact-head manual Windows matrix. Eight CI contract tests confirm
one shared built wheel, targeted hash coverage and no full-suite discovery in
platform smoke. Corrected-head independent review and CI remain pending.
