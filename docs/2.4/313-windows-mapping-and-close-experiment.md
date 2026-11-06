# Windows mapped-file and close-refusal experiments

Date/access date: 6 November 2026
Status: isolated native experiment; qualification pending

## Integrated prerequisite and next gate

[Prototype312](312-windows-disposition-prototype.md) integrated through
[PR151](https://github.com/raghavkandpal/parison/pull/151) at `753ccda` from exact
head `64ae9c8`. It passed independent Standards/Spec reviews,754 local tests,
[quality](https://github.com/raghavkandpal/parison/actions/runs/42217629047),
[ordinary preflight](https://github.com/raghavkandpal/parison/actions/runs/42217629089)
and [manual full qualification](https://github.com/raghavkandpal/parison/actions/runs/42217647767)
on Python3.11–3.14 Linux/macOS/Windows. Windows preflight ran13 synthetic
native disposition cases including file-symlink refusal; its two skips were
unrelated POSIX-only cases. The earlier failed native heads remain documented
in312; neither qualified integration.

That prerequisite established bounded namespace/content interference and
close/kill/retry observations, not all requirements for a production helper.
Deepen the same test module with12 mapping combinations and four real protected
close cases. There is no new runtime helper, session operation, schema, command,
source access, evidence output or retained-execution authority. The supported
POSIX identity-removal gate remains unresolved; feature4 remains incomplete.

## Source-backed hypotheses and experimental controls

Microsoft CreateFileW documents that omitting FILE_SHARE_WRITE fails admission
when a file has a writable file mapping. Test that hypothesis with direct native
CreateFileMappingW/MapViewOfFile, rather than assuming Python mmap object lifetime
matches the native section/view distinction. Cover writable/read-only mappings,
original handle kept/closed and section handle closed while its view remains,
under both read-only sharing and sharing0. Demonstrate a same-size mapped backing
write and restoration after selecting each handle lifetime. Writable mappings
must refuse admission with bytes/name preserved. A failure of that assertion
requires investigation; do not silently permit a write-capable mapped competitor.
[CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew),
[CreateFileMappingW](https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-createfilemappingw),
[MapViewOfFile](https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-mapviewoffile).

Read-only mapping outcomes are observations: record admission, disposition
refusal/success, name visibility before unmapping and final cleanup/retry.
No permitted observation authorizes a helper to report deletion before its
postcondition. Preserve synthetic primary bytes in every case.

Microsoft documents HANDLE_FLAG_PROTECT_FROM_CLOSE as preventing CloseHandle
from closing a valid protected handle. Exercise real refusal before/after marking
disposition; prove the handle still excludes another opener, then clear protection
and close or kill the isolated process. Require expected retained/deleted state
and retry after release. This qualifies protected-handle refusal only, not all
storage/filter faults or ambiguous close outcomes. Never use fabricated handles
or mock returns as native clearance.
[SetHandleInformation](https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-sethandleinformation),
[CloseHandle](https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle).

## Completion and limits

Use bounded synthetic subprocesses, temporary files, actual section/view cleanup
and explicit non-Windows skips. Keep the module in existing native preflight/full
suite discovery. Require local preflight, independent Standards/Spec clearance,
quality/ordinary checks and exact-head manual full Python3.11–3.14 native matrix
before integration. Record outcomes rather than claiming an unrun hypothesis.

Only afterward select a minimal private handle-bound helper with its own complete
identity/content recognition, storage, borrowed-ownership and interruption gate.
These tests neither relax contract296 nor solve final POSIX unlink/root removal.
No elevated service, kernel module, filesystem exclusion, raw source deletion,
network custody, release or usage reset is introduced. All ten train features
and audit307 clarity work remain prerequisites to2.4 release.

## Local checkpoint

Full local `make check` passes755 tests with seven native skips on macOS under
CPython3.14.7 with declared dependencies including Polars. Focused native preflight
passes53 tests with five native skips; documentation3 tests pass. Independent
WIP Standards/Spec reviews are clear. This establishes no mapping or close-refusal
behavior on Windows; exact-head review and full native qualification remain open.
