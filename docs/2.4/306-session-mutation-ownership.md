# Private mutating session ownership

Date: 1 November 2026
Status: feature4 ownership prerequisite; abandonment/execution remain disabled

Under [contract296](296-partition-recovery-contract.md), the private
partition_sessions._write_owner context holds the same existing kernel lock and
root/lock identity guards as read ownership. It yields borrowed directory/native
capabilities and an ownership recheck. It creates no lock, reads no journal,
writes/deletes nothing and grants no cache reuse or execution authority.

The caller may change its validated owned namespace while ownership is held.
A pinned parent directory identity/change stamp also detects root-name replacement
that is later restored, while legitimate writes inside the root remain possible.
Unrelated parent namespace activity conservatively rejects ownership. Spec review
found a missing writer root-name guard; its real rename/restore regression failed
before this correction. Root/lock identities and native lock-file change stamps
still must match at every
recheck and normal exit. The root and lock themselves must remain until context
closure. Recognizing pinned metadata after lock acquisition, binding every file
mutation, storage reservation and atomic journal transitions are separate duties.
The final lock/empty-root removal phase of abandonment is not implemented here.

Read ownership layers its existing post-lock directory stamp and bounded member
snapshot over the shared kernel/identity context. No read-only=False flag or
namespace guard bypass was added. Existing preview remains read-only and retains
all canonical responses and safe error/interrupt behavior. Released discovery,
evidence, CLI, aliases and schemas are unchanged.

Focused tests preserve all read/preview gates and exercise legitimate writer
namespace changes, read/write exclusion both ways, writer exceptions and
interruption release, actual cross-process read/write exclusion and kernel
release after process kill, and root/lock substitution rejection or actual native
pin denial. Tests run through existing discovery-based native suites; no workflow
commands were added. Full local checks, independent Standards/Spec review and
exact-head preflight/manual full native qualification are required before merge.

Next extract the existing bounded reader so a mutating invocation can recognize
pinned metadata under its already-held lock without recursively acquiring it.
Then add bounded atomic journal replacement and safe abandonment, including both
sides of interruption, metadata retention until sensitive content is gone and
replacement-preserving final cleanup. Retained discover/resume and the full
forgery/storage/equality gate follow. Feature4 remains incomplete (3/10 features
integrated); all ten precede a2.4 candidate. No release or usage reset.

## Usage-limited continuation

This scoped branch starts at develop847c371. Full local checks passed742 tests
(five Windows-native skips on macOS);15 ownership tests passed on all four local
Python minors. Independent WIP Standards/Spec re-review cleared the parent-guard
correction. Exact committed-head clearance and new CI preflight/manual full
qualification must be read from the PR before integration. Keep the branch
unmerged until all those gates qualify; do not infer native success from local
checks. The owner297 spacing edit remains excluded and unchanged. Stop near95%
usage without consuming a reset; continue this gate from its pushed branch.
