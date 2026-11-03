# Fixed-slot discard: identity-bound deletion research

Date/access date: 3 November 2026
Status: research handoff; destructive discard remains unqualified

## Decision and repository evidence

Preserve [contract296](296-partition-recovery-contract.md): deletion must bind
owned file/directory identities and preserve substitutions. Do not integrate the
current pathname-unlink candidate merely because earlier recognition succeeds.
The integrated [staging prerequisite](309-abandonment-journal-staging.md) remains
separate: it creates an exclusive uncommitted slot, never replaces the primary
and exposes no destructive CLI.

Review reproduced a substituted oversized regular slot being deleted when its
identity was captured after recognition. Binding the slot before recognition
addresses that specific re-baselining defect. A final replacement between the
last identity check and pathname unlink is a separate unresolved gate. A check
after deletion can detect interference but cannot restore a deleted replacement.
A deterministic probe against the corrected local candidate injected replacement
at the `os.unlink` boundary: remove the recognized slot, create a 1,048,577-byte
regular replacement, then execute the original unlink. The candidate returned
`True`; replacement preservation was false. The candidate and probe are retained
only in ignored `local-research/`; runtime/tests were restored to the integrated
HEAD. No destructive candidate shipped. These are repository observations and
reasoning, not upstream API guarantees.

## Primary-source facts and design consequences

Python documents `os.remove(path, *, dir_fd=None)` as equivalent to `unlink`.
Its directory-descriptor support resolves a relative path against that directory;
the documented removal interface accepts no expected child inode or file handle.
Consequently a pinned directory anchors lookup, but does not itself bind removal
to the previously verified child. This consequence is an inference from the
interface, not a Python promise of race prevention.
[Python 3.14 filesystem operations](https://docs.python.org/3.14/library/os.html#os.remove),
[directory descriptors](https://docs.python.org/3.14/library/os.html#files-and-directories).

The Linux man-pages project's `unlink(2)` documentation describes deletion of a
name; `unlinkat` uses a supplied directory descriptor for relative resolution.
Its documented flags provide directory removal, not an expected-file-identity
comparison. Keeping a verified file descriptor open therefore must not be
assumed to turn a subsequent pathname unlink into conditional removal.
[Linux man-pages: unlink/unlinkat](https://man7.org/linux/man-pages/man2/unlink.2.html).
The Open Group Issue 8 and Issue 7 unlink pages both returned HTTP403 during
this access; their normative text was not independently verified here:
[Issue 8 reference](https://pubs.opengroup.org/onlinepubs/9799919799/functions/unlink.html).

Microsoft documents `SetFileInformationByHandle` with `FileDispositionInfo`
and `FILE_DISPOSITION_INFO`. Setting deletion requires a handle opened with
`DELETE` access; its example marks the handled file for deletion on close.
This is a candidate native mechanism to investigate, not a qualified Parison
implementation. Existing read handles/pins cannot be assumed sufficient:
validate access rights, sharing, identity, close behavior and failures on actual
supported Windows filesystems before choosing a design.
[Microsoft API reference](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-setfileinformationbyhandle).

## Rejected shortcut, threats and non-goals

Reject “recognize, stat again, unlink by name, then check.” More checks improve
detection at their observation points; they do not establish atomic coupling
between the final check and mutation. The kernel session lock excludes
cooperating Parison invocations, not an independent namespace modifier.

Threats include slot replacement after validation, same-size modifications,
symlink/reparse substitution, lock/root replacement and interruption around the
mutation. Preservation must cover unrelated replacement bytes, not just avoid
following symlink targets. No contract relaxation, silent platform exclusion,
source deletion, journal promotion or portable-impossibility claim follows from
this bounded research.

## Exact next gate

Research and prototype identity-bound removal separately for supported POSIX
and Windows lanes. Prove preservation with a deterministic substitution at the
last-check/mutation boundary, plus regular/oversized/symlink replacements,
interruption on both sides, unchanged primary authority and retry behavior.
Document the actual primitive's guarantees and residual assumptions; obtain
independent Standards/Spec review and exact-head full native qualification.
If a candidate cannot meet the existing contract, retain it outside product
runtime and leave destructive discard disabled. Only then compose discard,
atomic journal transition and safe abandonment; retained execution remains
unfinished. Bounded product clarity remains required before the 2.4 release.
