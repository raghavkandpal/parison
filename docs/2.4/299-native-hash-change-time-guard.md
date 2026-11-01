# Native metadata change-time guard

Date: 1 November 2026
Status: regression correction; independent review and exact-head CI pending

The feature4 wire gate [PR135](https://github.com/raghavkandpal/parison/pull/135)
is paused at corrected head89322ec. Manual matrix41283158036 passed every job
except the existing hash mutation test on Windows3.14: replacing and restoring
a source/snapshot name sometimes did not raise the expected controlled error.
This is a feature3 prerequisite defect, isolated from the new session schemas.
Do not qualify the wire gate by rerunning away this failure.

A focused local regression masks reported ctime as stable creation time while
performing a real source rename/substitute/restore. It failed in0.027s before
the correction. Python's Windows timestamp APIs have reported creation/change
semantics differences; see the [CPython report](https://github.com/python/cpython/issues/157671).
Metadata identity and matching file bytes alone do not detect this namespace ABA.

The hash-only file guard now obtains native metadata change time on Windows
through GetFileInformationByHandleEx(FileBasicInfo), retaining dev/inode/size/
mtime and comparing held/reopened regular-file handles in one representation.
Microsoft's [FILE_BASIC_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_basic_info)
explicitly distinguishes metadata changes, including renames, from data writes;
[GetFileInformationByHandleEx](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getfileinformationbyhandleex)
defines the handle query and failure result (accessed1November2026). Unsupported
or zero native change time fails closed. POSIX uses its metadata ctime directly.
The new guard applies to original pinned hash sources, private staged files and
hash evidence members. Windows hash evidence roots also retain the existing
non-delete-sharing directory pin during reads. No native time is serialized.

The focused regression now passes. A mocked ABI probe verifies FileBasicInfo
layout and that ChangeTime, not CreationTime, is selected; a native Windows test
requires rename denial or changed native metadata time. The existing source and
snapshot mutation cases are independently labelled, with no sleeps or weakened
assertion. Full positive/negative hash tests, all supported Python minors and
actual native Windows CI must qualify this correction before integration.

Released range-v1 contracts/helpers, recipes, typed key grammar, policy hashes,
canonical output, CLI JSON/exit semantics and local-first boundaries are
unchanged. No dependency, script entry point, network operation or authenticator
is added. After this fix qualifies, rebase the wire branch onto updated develop,
repeat its exact-head reviews/CI and integrate it only when qualified. Feature4
remains incomplete;3/10 features are integrated and all ten precede a candidate.

Local gate:686 repository tests pass with `make check`;46 hash execution/reader/
wire tests pass on CPython3.11.18,3.12.5,3.13.18 and3.14.7. Four native Windows
checks skip on this macOS host. Actual Windows change-time/rename behavior and
all four supported Python minors must pass the exact-head manual matrix.
