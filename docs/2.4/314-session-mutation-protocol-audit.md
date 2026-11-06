# Retained sessions: complete mutation protocol audit

Date/access date: 6 November 2026
Status: no complete destructive protocol qualified; contract296 remains binding

## Qualified evidence and its boundary

[Experiment313](313-windows-mapping-and-close-experiment.md) integrated through
[PR152](https://github.com/raghavkandpal/parison/pull/152) at `8b6fcf2`, from exact
head `456eec0`, after independent Standards/Spec reviews,755 local tests,
[quality](https://github.com/raghavkandpal/parison/actions/runs/42218979183),
[ordinary preflight](https://github.com/raghavkandpal/parison/actions/runs/42218979100)
and [manual full Python3.11–3.14 Linux/macOS/Windows qualification](https://github.com/raghavkandpal/parison/actions/runs/42218987122).
Windows preflight ran57 tests with two unrelated POSIX skips: all12 mapping,
four protected-close and prior13 disposition cases executed.

Writable mappings refused admission with32 across all tested handle/view lifetimes
and sharing0/1. Read-only mapped views refused disposition with5 and preserved
bytes/name; unmapped retry succeeded. Protected CloseHandle returned6, retained
exclusion, and allowed tested clear/close retry or process-death cleanup.
These are actual runner observations, not general storage/filter-failure guarantees.
No production deletion helper or complete session transition was implemented.

## Every mutation needs its own primitive and interruption proof

Contract296 requires identity preservation at mutation, not merely checks around
it. A safe source operation does not establish a safe destination operation.

| Mutation | Required binding and interruption state | POSIX status | Windows status |
| --- | --- | --- | --- |
| Discard fixed session.next | Recognized bounded regular child; preserve replacements; primary unchanged before/after interruption | Ordinary unlinkat accepts a name, not expected child identity; rejected last-boundary probe | Handle disposition candidate has qualified isolated namespace/mapping/close observations; full session recognition/ownership composition remains |
| Promote staged journal: source | Move exactly recognized staged identity; never move a substituted next slot | renameat selects current source name; expected-source coupling unresolved | FILE_RENAME_INFO acts on a source handle; a full session protocol remains unqualified |
| Promote staged journal: destination | Replace exactly recognized primary atomically; keep valid sole primary before/after interruption | No expected-target comparison in examined rename interface | RootDirectory, filename and ReplaceIfExists do not supply expected target ID; target-pin/sharing protocol is unqualified |
| Remove routing/results children | Bind each recognized owned child, preserve foreign replacements; retain journal/lock until sensitive contents gone | Same conditional-removal gate for every fixed child, not just next slot | Disposition primitive observations do not establish multi-child recognition, budgets or interruption ordering |
| Remove plan/primary metadata | Remove only expected identities after sensitive content is gone; never infer authority from next | Conditional removal unresolved | Handle candidate possible; protocol/order not qualified |
| Release/remove final lock | Primary gone before release; unlink only owned lock after release; new owner rereads metadata | Final pathname unlink can remove a replacement; flock does not exclude independent modifier | Delete-capable ownership handle/share/byte-lock ordering must be qualified separately |
| Remove empty root | Remove only owned empty directory; preserve even an empty replacement root | rmdir name accepts no expected child identity; descriptor alone does not make it conditional | Existing root/parent read pins are not a qualified delete-capable root protocol |

Deleting primary then installing next without overwrite is not atomic journal
replacement. Interruption leaves a missing primary, and296 forbids recovering
authority from next. Keeping a target pin then assuming own rename can bypass it
is also unqualified. Test native sharing/rename flags rather than asserting how
all variants behave.
[Microsoft FILE_RENAME_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_rename_info),
[Linux rename](https://man7.org/linux/man-pages/man2/rename.2.html),
[Linux unlink](https://man7.org/linux/man-pages/man2/unlink.2.html),
[Linux rmdir](https://man7.org/linux/man-pages/man2/rmdir.2.html).

## Further bounded POSIX evidence

Synthetic last-boundary probes on Darwin27.2.0 arm64, CPython3.14.7 reproduced:
removing a substituted regular lock; removing an empty replacement root while
the owned directory descriptor remained valid; overwriting a substituted primary
target with ordinary replace; and moving a substituted next source over the
previous primary. All probes used temporary synthetic files and the rejected
check-then-mutate sequences, not product runtime. These observations extend the
next-slot counterexample to the whole protocol; they do not prove every API or
filesystem extension impossible. The ignored probe is diagnostic only.

Apple's current legacy /.vol implementation converts a vnode identity into an
ordinary path and releases that vnode before name lookup continues. Apple QA1113
also forbids applications constructing /.vol paths. This does not establish
identity-conditional unlink. FSRef deletion remains unqualified: the actual
CarbonCore implementation was not established, and declarations alone are no
atomicity promise. RENAME_SECLUDE is another filesystem-specific lead, not an
expected-child removal proof or complete final-root protocol.
[XNU lookup](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/vfs/vfs_lookup.c),
[Apple QA1113](https://developer.apple.com/library/archive/qa/qa2001/qa1113.html),
[Apple rename flags](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/stdio.h).

## Architecture alternatives do not silently satisfy296

Descriptor truncation binds content changes to an inode but leaves directory
entries and does not establish atomic variable-length canonical journal updates.
Dual cells, append logs or selected generations require new authority, format,
recovery and budget semantics; final namespace cleanup remains unresolved.
Tombstones/empty shells change abandonment's required end state. Quarantine/swap
can relocate a foreign replacement before inspection and introduce new retry
states. None may be counted as full296 merely because it is easier to implement.

Unprivileged filesystem-specific mechanisms remain within native research
authority if they qualify the supported lanes and full protocol. No complete
candidate was established in this bounded audit. Privileged services, kernel
modules and deployment-boundary changes require a separate explicit decision.
Do not conflate filesystem specificity with an automatic prohibition.

## Decision and next action

Keep destructive discard, promotion, abandonment and retained execution disabled.
No complete contract296 protocol was established by the examined APIs and
independent full-contract audits. This is a qualification gap, not a universal
impossibility claim or permission to exclude Linux/macOS.

The owner explicitly selected keeping the v1 preservation guarantee on6 November2026.
Require a concrete primitive/protocol filling every unresolved table row under296.
[Draft315](315-session-interference-profile-decision-draft.md) was not selected;
no cooperating-owner profile, weaker preservation or silent platform exclusion
is authorized. Continue compatible research without reopening that same decision.
Source-handle deletion success alone is not grounds to ship an unused helper as
if the full protocol were solved. Feature4 stays incomplete (3/10); integrate
remaining numbered features in the roadmap order and retain audit307's separate
pre-release gate. No release, source deletion, credentials, signing, network
custody, repair, policy approval or reset is authorized by this audit.

## Documentation validation

Documentation3 tests, lint, format, generated-reference checks and diff checks
pass. Independent WIP Standards/Spec reviews cleared the bounded audit and the
draft's corrected parent/ancestor admission boundary. This docs-only checkpoint
changes no runtime, schema, CLI or canonical bytes. Exact-head review/quality
remain integration gates; all destructive protocol rows stay unqualified as noted.
