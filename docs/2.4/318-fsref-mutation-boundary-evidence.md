# Darwin FSRef: observed mutation-boundary counterexample

Date/access date: 10 November 2026
Status: rejected native lead; contract296 remains unchanged; no runtime change

## Continuation and decision

The owner requested merging the two pending records and resuming the documented
v1 direction. [PR154](https://github.com/raghavkandpal/parison/pull/154) integrated
at `b2e23db` from independently reviewed source `1e7b425`, with
[exact-head quality](https://github.com/raghavkandpal/parison/actions/runs/42222203194).
[PR155](https://github.com/raghavkandpal/parison/pull/155) then integrated at
`3a6ba23` from reconciled, independently reviewed source `40c8607`, with
[exact-head quality](https://github.com/raghavkandpal/parison/actions/runs/42782819084).
The keep-v1 decision and [post-feature engineering gate317](317-post-feature-engineering-release-gate.md)
are both retained. The owner did not select the weaker profile in315.

[Audit314](314-session-mutation-protocol-audit.md) left FSRef deletion unqualified
because declarations and API names did not establish its actual mutation path.
The saved own-process observation was resumed and extended to a deterministic
substitution at the intercepted deletion-call boundary. Both tested FSRef routes
deleted the replacement. Reject these implementations as a way to satisfy
contract296's preservation requirement on this host. Do not infer that every
Linux/macOS primitive or future OS implementation is impossible.

## Method and primary implementation evidence

Host: macOS 27.2 build 26B123, arm64; installed CoreServices and Clang. A disposable
executable and interposer operated only on parent-created synthetic temporary
files. No root, manual signing, debugger, protected-process attachment or system
protection bypass was used. No product runtime, user source or evidence bundle
was involved.

Apple's dyld header documents replacement/replacee tuples in the interpose
section, with an example forwarding to the original function. This mechanism
was applied only to the disposable process. Positive controls verified actual
interception; it was not assumed that every private/direct system call could be
observed this way.
[Apple dyld interposing header](https://github.com/apple-oss-distributions/dyld/blob/main/include/mach-o/dyld-interposing.h).

The actual calls observed after FSRef resolution were:

| Invoked operation | Intercepted implementation boundary | Observed caller |
| --- | --- | --- |
| Plain unlink control | unlink, absolute path | main |
| FSDeleteObject | __carbon_delete, absolute path | FSMount::remove |
| FSUnlinkObject | unlink, absolute path | FSMount::remove |

The private symbol is implementation evidence, not an API proposed for product
use. These observations narrow the uncertainty left in314; they are not inferred
from a third-party implementation or an early pre-API pathname swap.

For each FSRef call, the synthetic original was created, its device/inode and
full bytes captured, its descriptor closed and its FSRef resolved. Inside the
observed deletion wrapper, immediately before forwarding the unchanged pathname
to the original primitive, the probe renamed that original to a saved name,
created an exclusive regular replacement, wrote its marker, extended it to
1,048,577 bytes, captured its fstat identity/size and closed it. No busy-file pin
masked Carbon behavior. The original deletion primitive was then called.

Inspection occurred after the API returned and before cleanup, regardless of
API success/failure. A surviving replacement had to match the captured identity,
exact size and complete marker-plus-zero-tail bytes. The saved original was
checked independently against its original identity and full bytes. A failed API
alone could not count as preservation. Every observation window ended before
harness cleanup, preventing cleanup from being mistaken for the API's effect.

## Actual outcome

| Operation | API result | Observed hooks / injections | Replacement exists before cleanup | Saved original identity and bytes |
| --- | --- | --- | --- | --- |
| Plain unlink control | 0 | 1 / 0 | No, as expected | Not applicable |
| FSDeleteObject | 0 | 1 / 1 | No | Match |
| FSUnlinkObject | 0 | 1 / 1 | No | Match |

Both FSRef calls returned success with errno 0 while the oversized replacement
was absent. Its identity, size and content were therefore not preserved; this
was not merely a missing measurement following an error. The owned original
survived under the saved name. The harness reported complete cleanup for all
three cases and zero residual synthetic entries before parent-root removal.
The parent bounded execution to 20 seconds and reaped the child. No probe or
persistent handle remains running.

A process exit 0 here means the experiment completed and reported its observations,
not that either candidate passed contract296. No product regression or full
native qualification is claimed.

## Reproducibility and limits

The corrected sources, bounded runner, output and source hashes are retained in
ignored `local-research/fsref-native-probe/`. The earlier graceful-exit draft was
compiled but not executed; this run followed review/correction of its result gate
and independent cleanup/reporting paths. The runner can be invoked after rebuilding
its disposable binaries; it is not required to read the public contract.

This counterexample concerns the actual installed routes tested on this named
host. It does not qualify unrelated CoreServices operations, other filesystems,
other OS versions, Linux removal, Windows expected-target journal promotion,
or final lock/root cleanup. API deprecation alone is not the rejection basis:
the observed loss of the substituted file is.

## Parallel Linux research disposition

A bounded primary-source follow-up did not establish a complete Linux candidate.
The inspected upstream unlinkat flag check rejects flags beyond AT_REMOVEDIR;
located expected-fd/AT_EMPTY_PATH proposals were not established as a merged
supported-runtime interface. Delegation documentation and implementation permit
timeout-driven removal, leaving the stopped-process check/mutation gap unresolved.
No examined handle or subvolume operation supplied both regular-child conditional
removal and expected-target journal promotion. These are bounded source findings,
not a native Linux qualification or a claim about every vendor/filesystem API.
[Upstream name lookup/mutation source](https://github.com/torvalds/linux/blob/master/fs/namei.c),
[delegation manual](https://man7.org/linux/man-pages/man2/F_GETDELEG.2const.html),
[lease implementation](https://github.com/torvalds/linux/blob/master/fs/locks.c).

The examined upstream links are moving snapshots, not an exact qualified release
commit. The Darwin host did not establish a Linux runner's kernel/mount admission.
Detailed sources and access limits remain in ignored
`local-research/linux-conditional-mutation-status.md`. Header presence, a proposal,
or a function named by-handle is not runtime availability or a complete protocol.
No privileged/configuration workaround or platform exclusion was adopted.

## Exact next gate

Continue only with a new concrete public conditional-mutation or namespace
exclusion candidate and prove every unresolved row of314, including promotion
source and expected destination, child removal, final lock ordering and owned
empty-root removal. Do not repeat pre-call FSRef swaps as proof or revisit the
unselected weaker profile. Unprivileged filesystem-specific research remains
permitted, but no support restriction or privileged deployment is silently added.

Keep discard, promotion, abandonment and retained execution disabled. Feature4
remains incomplete (3/10 features integrated). The all-ten release boundary,
audit307 clarity and gate317's post-feature engineering work remain required.
No source deletion, credentials, signing, repair, remote orchestration, release
or rate-limit reset is authorized by this checkpoint.

## Checkpoint validation

Documentation3 tests, lint, formatting, generated-reference, local-link and diff
checks pass. Independent WIP Standards/Spec reviews inspected the probe sources,
recorded source hashes and interpretation and found no blocking findings. Host
version/build/architecture were rechecked. Exact committed-head review and
quality remain required before this docs-only checkpoint integrates. No product
code, schema, CLI or canonical evidence bytes changed.
