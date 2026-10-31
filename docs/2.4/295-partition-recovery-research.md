# Recoverable exact discovery sessions: research

Access date: 31 October 2026
Status: design input for feature4; no contract frozen or implementation qualified

## Recommendation

Use a bounded versioned canonical JSON checkpoint journal and verified immutable
partition children, deepening `partition_discovery.py` and the existing suite
recovery pattern. At most128 partitions makes a transactional database optional,
not necessary. Start sequentially; a private mutable session is never evidence or
PASS. Final output must reproduce ordinary discovery's four canonical files.
These are design inferences from the primary facts below, not source guarantees.

## Primary facts and consequences

1. SQLite atomic commit applies to database transactions and depends on filesystem,
OS and storage assumptions. It does not atomically commit arbitrary CSV/result
files beside the database. A journal entry therefore cannot establish that a
partition file completed or still matches its expected bytes. Verify external
files before reuse and keep final evidence publication separate.
[SQLite atomic commit](https://www.sqlite.org/atomiccommit.html).

2. SQLite allows only one simultaneous writer. WAL adds persistent state outside
the database, needs same-host shared memory, and cannot be treated as a lone
portable database file. Avoid WAL for a sequential session. If measurements later
justify SQLite, choose explicit rollback-journal transactions, close the database
before moving/cleaning its directory, and retain any recovery journal until
SQLite resolves it. [Transactions](https://www.sqlite.org/lang_transaction.html),
[WAL](https://www.sqlite.org/wal.html),
[locking](https://www.sqlite.org/lockingv3.html).

3. Python3.11 supports `isolation_level=None` with explicit transaction SQL;
3.12 introduced `Connection.autocommit`, retained in3.13/3.14. Do not depend on a
changing default or call a3.12-only keyword unconditionally on3.11. If SQLite is
selected, one small explicit transaction profile must be tested on all four
minors and actual linked SQLite versions, rather than inferring capability from
Python alone. [3.11](https://docs.python.org/3.11/library/sqlite3.html#transaction-control),
[3.12](https://docs.python.org/3.12/library/sqlite3.html#transaction-control),
[3.13](https://docs.python.org/3.13/library/sqlite3.html#transaction-control),
[3.14](https://docs.python.org/3.14/library/sqlite3.html#transaction-control).

4. SQLite distinguishes consistency from persistence of the last acknowledged
transaction after power loss; rollback-mode `synchronous=FULL` is not an
unconditional durability promise, and `EXTRA` adds directory synchronization.
Corrupt/broken locking and storage remain relevant. Even a durable database
commit cannot make independently written bucket files durable.
[SQLite synchronous](https://www.sqlite.org/pragma.html#pragma_synchronous),
[corruption causes](https://www.sqlite.org/howtocorrupt.html).

5. Python documents flushing buffered files before `os.fsync()`. Successful rename
is atomic on POSIX, but ordinary rename/replace can overwrite targets; the
repository's `rename_no_replace` remains the final publication boundary. Atomic
visibility alone is not a promise that a renamed entry survives power loss.
Define feature4 as verified reuse after process interruption; after arbitrary
storage loss it may reject and require a fresh session. Do not claim universal
crash durability. [Python3.11 OS interfaces](https://docs.python.org/3.11/library/os.html),
[Python3.14 OS interfaces](https://docs.python.org/3.14/library/os.html).

6. Windows deletion of an in-use file differs from Unix unlink semantics. Native
Windows sharing flags also govern rename/delete permissions while handles are
open. Descriptor-relative traversal and symlink-resistant `rmtree` are
platform-dependent. Own a regular workspace, reject symlinks/reparse substitutions,
check directory identities as well as member identities, close writers before
cleanup, and test actual Windows behavior. Never clean a replacement directory
merely because it occupies the old session pathname.
[Windows CreateFile](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew),
[Python shutil](https://docs.python.org/3.14/library/shutil.html).

7. Future cancellation does not undo completed work and does not cancel already
running work. Feature4 needs a single session writer; feature5 can later deliver
worker results to that owner. Do not let workers independently mutate session
state or publish final artifacts.
[Python3.11 futures](https://docs.python.org/3.11/library/concurrent.futures.html#concurrent.futures.Executor.shutdown),
[Python3.14 futures](https://docs.python.org/3.14/library/concurrent.futures.html#concurrent.futures.Executor.shutdown).

8. An exported PostgreSQL snapshot can be imported only while its exporting
transaction remains open. Session resume is entirely local over captured files;
it cannot restart a dead database transaction or assert snapshot continuity.
[PostgreSQL18 snapshot synchronization](https://www.postgresql.org/docs/18/functions-admin.html#FUNCTIONS-SNAPSHOT-SYNCHRONIZATION).

## Existing seams and compatibility constraints

`src/parison/suites.py` already supplies the design vocabulary:
`_checkpoint_data`, `_write_checkpoint`, `_reusable_workspace_child`,
`preview_suite_recovery`, and the `workspace`/`resume` flow. It binds policy,
inputs, limits, version/context and verified child manifests, then copies and
verifies children before assembly. Reuse that admission pattern, not its
unbounded JSON reads or every path-based cleanup operation verbatim.

Discovery currently combines snapshotting, routing and comparison in `_run_hash`;
`_compare_ranges` combines each exact comparison and final aggregation. Deepen
those seams only enough to checkpoint an entirely completed routing generation
and individual complete partition results. A partial routing pass has no
reusable claim: discard its owned partial files and route again. An incomplete
comparison result may be final INCONCLUSIVE evidence but should be recomputed
on resume; only verified complete results qualify for reuse. Aggregate in fixed
plan order with the existing incomplete-result suppression.

Retain range-v1 admission and receipt accounting. In particular, v1 physical CSV
column order follows loaded recipe order, while v2 sorts names. The same effective
policy hash need not encode a v1 staging layout. Bind the ordered physical column
list in the private session identity; do not silently canonicalize/reorder the
recipe and thereby change old bucket digests. Reload the bounded owner-supplied
recipe on resume; preserve v2's rule against retaining a raw recipe copy on disk.
Keep original input descriptors in final receipts, not hashes of re-emitted CSV.
Session storage accounting is a new explicit private bound; it must not redefine
v1 `staged_bytes` or double-count v2 snapshots in published receipts.

## Proposed smallest contract to freeze

- Explicit existing-command options for a new retained workspace and resume;
  new session-version/profile, no new project script. Ordinary discovery keeps
  temporary cleanup behavior. Retention is opt-in and visibly sensitive;
  offer explicit inspect/abandon semantics before freezing the CLI.
- One bounded strict canonical journal, fixed names and at most128 children.
  Suggested phases: initializing, routed, comparing, ready-to-publish. Only a
  complete routing generation can become `routed`; each result checkpoint
  follows closed, hashed, verified child files. Atomically replace private
  journal files; final publication always uses no-overwrite installation.
- Identity binds canonical plan/profile/limits, original effective policy,
  ordered v1 layout, exact input SHA256/bytes, comparator contract and explicit
  recovery-engine revision, package/build identity and runtime. Package version
  alone is insufficient during unreleased source changes. Hash-v2 requires
  contract291's exact CPython/Unicode descriptor before source I/O; freeze an
  equally explicit reuse rule for range-v1 rather than weakening hash-v2.
- Resume pins and rehashes current original inputs and recipe, then verifies all
  eligible snapshot/bucket/result bytes, closed shapes, arithmetic, parent/root
  identities and caps. A source/policy/plan/runtime mismatch rejects the session;
  a missing/truncated uncommitted child can be discarded and recomputed only
  under an explicit recovery rule. Never trust a journal's `complete` flag alone.
- Reject concurrent session ownership without PID-based stale-lock guessing.
  Freeze and test either a scoped OS lock held for the invocation or an explicit
  recoverable ownership protocol; portable lockfiles alone do not prove a prior
  process died. Keep distributed/network filesystems outside the support promise.
- If publication completed before an interruption, an existing output must be
  verified and reported as already published only under an explicit idempotence
  rule; never overwrite or delete it. Final ordinary evidence contains no
  resume counters, timestamps, paths, session IDs or cache provenance that would
  alter clean-run bytes. Session state itself remains nonportable mutable input.

## Threats, non-goals and qualification

Threats: truncated/rehashed journal, changed source bytes under reused names,
policy/layout/runtime drift, replaced children or root directory, hardlinked
member substitution, stale locks, disk-full and late candidate-side failure,
interrupted cleanup and output races. Hashes provide binding, not signatures or
protection from an actor able to forge every local artifact. No repair, source
reacquisition, background monitoring, automatic resizing, parallel workers,
remote orchestration, authentication or approval belongs in this feature.

Gate: clean versus resumed byte equality for both plan versions; terminate a real
child process during each snapshot copy, partial routing, completed routing,
mid/final comparison, journal replacement and pre/post publication. Corrupt and
truncate each journal/child; vary each identity independently; test root/name/
symlink/hardlink substitutions and unrelated replacement preservation. Exercise
all bounds, two competing resumptions, explicit abandonment, wrong-runtime
rejection before sources, PASS/FAIL/INCONCLUSIVE outputs and value-free errors.
Verify reuse with a comparator call-count assertion, not elapsed-time inference.
Run required full local checks, independent reviews and exact-head built-wheel
Python3.11–3.14 Linux/macOS/Windows CI. Machine-specific benchmarks may measure
saved comparisons, elapsed time and retained bytes; make no universal capacity
or power-loss guarantee. No feature4 implementation or integration is claimed.

## Mandatory assurance decision before freezing

A reusable result's hash and canonical bytes cannot prove that the exact engine
previously ran. Constructively, someone able to edit both a result and its unsigned
journal/manifest can replace coherent counts and recompute every digest. Input
SHA bindings identify the claimed inputs; they do not demonstrate that output
was derived from them. Even cached routing can be forged consistently unless the
current invocation reconstructs routing or relies on trusted prior evidence.
This is a design limitation, not a defect SQLite transactions or stricter JSON
can solve.

The existing suite rule verifies child bundle integrity, complete status,
policy/version/resources and current input digests. It does not replay the
comparison and does not authenticate execution. Reuse therefore extends the
existing owner-trusted unsigned-evidence boundary; it must not be described as
fresh exact source-backed replay.

Recommended smallest honest boundary: resume may reuse complete, structurally
verified, source/policy/plan/layout/engine/runtime-bound children, with a new
explicit invocation/session assurance label such as `reused-integrity-checked`.
Preview should distinguish recomputed children from integrity-checked reused
ones and state that reuse does not authenticate prior execution. Keep assurance
outside the released four-file discovery contract unless a new evidence schema
is deliberately versioned. The final ordinary evidence remains unsigned, as
before. Only the existing full source-backed `partitions verify` path may return
`exact-source-backed`; it must recompute the entire derivation without trusting
session caches. Avoid calling the resume operation itself exact replay.

The forgery gate must distinguish two classes: reject truncated, malformed,
arithmetically inconsistent, substituted or identity-mismatched children before
reuse; for a coherent entirely rehashed forged result, require the integrity-only
label and show fresh exact source-backed replay rejects it. Never claim journal
integrity detects this second class. If the intended contract instead demands
rejection of every coherent forgery before final publication, recompute the
relevant routing/comparison work; skipping that work while proving its execution
requires an independently trusted root or authenticator, outside this feature's
no-signing/no-secret boundary. Freeze this choice explicitly before implementation.
