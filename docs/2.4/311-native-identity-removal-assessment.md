# Native identity removal: bounded qualification assessment

Date/access date: 6 November 2026
Status: research checkpoint; no destructive runtime capability enabled

## Decision

Continue [research310](310-session-discard-identity-research.md) without relaxing
[contract296](296-partition-recovery-contract.md). Windows has a concrete
handle-based prototype candidate. This bounded survey establishes no qualified
Linux/macOS equivalent. It does not establish portable impossibility, authorize
platform exclusion, or complete feature4. Features1–3 remain integrated (3/10).

The next implementable slice is an isolated Windows identity-removal prerequisite,
qualified on actual Windows before composition with session discard. Keep the
POSIX gate open; a Windows prerequisite must expose no platform-specific session
command and must never fall back to pathname deletion. Journal promotion, safe
abandonment and retained execution remain disabled.

## Primary sources and consequences

Microsoft requires DELETE access for SetFileInformationByHandle with
FileDispositionInfo and demonstrates marking the handled file for deletion on
close. CreateFileW documents sharing compatibility: omitting FILE_SHARE_DELETE
blocks subsequent delete-access opens, and delete access includes rename.
OPEN_REPARSE_POINT opens the reparse object itself. The candidate is therefore:
open existing slot with DELETE and no delete sharing; verify the returned regular
non-reparse identity and bounded bytes before recognition; retain ancestor pins;
mark that handle for deletion; close it. This sequence is a design inference,
not native qualification. Existing incompatible handles must cause refusal.
[SetFileInformationByHandle](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-setfileinformationbyhandle),
[CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew).

Apple separates guarded descriptor operations from experimental vnode guards.
GUARD_CLOSE protects descriptor lifecycle, not a name against other processes.
The vnode guard API is private; its policy initialization depends on
PE_i_can_has_debugger. Neither is an established supported normal-user mechanism
for Parison. Apple's unlinkat implementation resolves a name and accepts no
expected child descriptor. These are source observations, not a claim that no
other macOS mechanism could exist.
[guard definitions](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/guarded.h),
[guard implementation](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_guarded.c),
[unlinkat implementation](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/vfs/vfs_syscalls.c).

Linux unlinkat likewise removes a name relative to a directory descriptor,
without an expected child identity argument. Ordinary file leases address
open/truncate and may be forcibly broken; do not infer namespace exclusion.
FreeBSD funlinkat illustrates the desired interface: directory descriptor, name
and expected child descriptor, with refusal on identity mismatch. FreeBSD is
outside the supported matrix and cannot qualify Linux/macOS by analogy.
[Linux unlink](https://man7.org/linux/man-pages/man2/unlink.2.html),
[Linux leases](https://man7.org/linux/man-pages/man2/F_SETLEASE.2const.html),
[FreeBSD manual source](https://github.com/freebsd/freebsd-src/blob/main/lib/libsys/unlink.2).

## Rejected namespace workarounds

RENAME_NOREPLACE/RENAME_EXCL protect destination existence, not expected source
identity. RENAME_EXCHANGE/RENAME_SWAP atomically swap the currently resolved
names, not the previously recognized identities. Moving a replacement into
quarantine and inspecting afterward can preserve its bytes while already
changing its location. Interruption then leaves an unexpected member; restoring
it races another fixed-slot entrant. Swapping through session.json also violates
sole primary authority. None of these sequences qualifies the frozen fixed
layout, interruption and replacement-preservation contract.
[Linux rename](https://man7.org/linux/man-pages/man2/rename.2.html),
[Apple rename](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/man/man2/rename.2).

flock is advisory. Private directory permissions exclude other users but do not
exclude another process running as the owner, which may change those permissions.
Neither binds unlink to the verified child; the session kernel lock only excludes
cooperating owners.
[flock](https://man7.org/linux/man-pages/man2/flock.2.html),
[chmod](https://man7.org/linux/man-pages/man2/chmod.2.html).

## Synthetic local evidence

A diagnostic using only temporary synthetic files ran on Darwin27.2.0 arm64,
CPython3.14.7. After a successful named/open-file identity comparison, it renamed
the owned file away and installed a regular11-byte, oversized1,048,577-byte, or
symlink replacement immediately before pathname unlink. All three replacement
entries were removed while the owned descriptor and saved owned bytes survived.
This demonstrates the rejected sequence's failure; removing the symlink entry
did not delete its target. It is not a product regression or native Windows
qualification.

A separate rename-to-quarantine probe detected the mismatched identity only
after moving the replacement away from its fixed slot and adding an unexpected
member. Byte preservation alone does not qualify that sequence. The ignored
standalone probe is local diagnostic evidence, not a runtime dependency; these
experiments require no source inputs, credentials or network access.

## Next checkable gate

Prototype handle disposition outside product runtime first. Exercise actual
Windows second-process rename/unlink/replacement denial, existing conflicting
handles, regular/oversized/reparse/directory rejection, unchanged primary bytes,
interruption before disposition and after marking it, close failure and retry.
Document exactly when deletion becomes visible and whether other open handles
postpone it. Do not claim a successful delete before the qualified postcondition.
Then consider a minimal private helper using existing native conventions, with
regression tests, independent Standards/Spec review, local preflight and exact-head
manual full Python3.11–3.14 Linux/macOS/Windows qualification before integration.
A helper prerequisite cannot count feature4 or enable destructive commands.

Continue bounded POSIX research in parallel with that prerequisite. A design
changing platform coverage, threat assumptions or storage layout requires a new
explicit versioned contract decision; it cannot be hidden in implementation.
No source deletion, privileged service, kernel module, network custody, repair,
cache authentication, release or rate-limit reset is part of this checkpoint.

## Checkpoint validation

Full local `make check` passes752 tests with five Windows-native skips on macOS,
using a temporary CPython3.14.7 environment with declared test dependencies,
including Polars. The sandbox-only attempt failed14 loopback-bind host tests;
the authorized unsandboxed run passed without code changes. Reader30 tests
(one Windows skip) and documentation3 tests also pass. Independent WIP Standards
and Spec reviews found no blocking findings. Exact committed-head review and
quality CI remain integration requirements; this docs-only checkpoint makes no
new native qualification claim.
