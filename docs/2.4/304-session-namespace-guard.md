# Read-ownership namespace guard correction

Date: 1 November 2026
Status: isolated correction before preview integration

Preview PR140's exact-head [native matrix](https://github.com/raghavkandpal/parison/actions/runs/41305399310)
exposed an existing ownership defect on Windows3.13: the test created
session.next inside read ownership, but the final directory-stamp check did not
reject. Preview's own20 tests, including native junction rejection, passed; the
existing read-ownership test failed. Do not rerun away this failure or merge the
preview until this prerequisite and its rebased head both qualify.

The ownership guard previously relied on root/lock identity plus native
metadata-change stamps. The observed directory stamp did not change at the
recheck despite a persistent new member. A local regression on clean develop
holds POSIX directory metadata steady while performing the same real file
creation. It failed in0.002s before the fix, demonstrating that the defect does
not require the preview helper extraction.

Read ownership now captures a bounded root member-name set after acquiring the
lock and compares it during every recheck, alongside the existing native clocks
and root/lock identities. More than the fixed six possible root names rejects
without unbounded enumeration. This guards namespace differences even when a
directory clock does not expose them. It does not authenticate session contents,
recognize journals, validate reuse, or claim detection of every unobserved
transient operation. File/member guards and ownership remain necessary.

No timestamps or member names are emitted, no session bytes are changed, and
released comparison/evidence contracts remain unchanged. Focused ownership
tests, independent Standards/Spec review, full local checks and exact-head
quality/full native built-wheel matrix must pass before integration. Rebase
preview PR140 on that integration, reuse this bounded enumeration helper and
repeat exact-head qualification. Feature4 remains incomplete (3/10 features
integrated); all ten precede a2.4 candidate.

After the current preview gate qualifies, the owner requested a discussion of
CI architecture, repeated full matrices and workflow growth before more feature
implementation. Preserve that sequencing; no CI policy changes are authorized
by this correction itself.
