# Read-ownership prerequisite for private sessions

Date: 1 November 2026
Status: implementation gate; independent review and exact-head CI pending

The [wire gate298](298-partition-session-wire-checkpoint.md) integrated through
PR135 at `07b71b2ab41ea23da67ae0a153ae17fb3335a10a`. Exact headaaa9d43 passed695
local tests, independent Standards/Spec review, [quality](https://github.com/raghavkandpal/parison/actions/runs/41285167137)
and [full built-wheel CI](https://github.com/raghavkandpal/parison/actions/runs/41285164896)
on Python3.11–3.14 Linux/macOS/Windows. Before that, the native metadata-change
correction [299](299-native-hash-change-time-guard.md) qualified at head5c8fa2f
([quality](https://github.com/raghavkandpal/parison/actions/runs/41284318063),
[full native matrix](https://github.com/raghavkandpal/parison/actions/runs/41284315785))
and integrated through PR136 at661374e. Earlier failed wire heads are superseded.

This adds one private read-ownership context in partition_sessions.py, under
frozen [contract296](296-partition-recovery-contract.md). It opens an existing
regular one-byte .lock containing exactly NUL, obtains nonblocking exclusive
kernel ownership and retains root/lock identity guards. It never creates,
unlinks, rewrites or repairs the lock and never guesses liveness from a PID,
timestamp or stale flag. The context returns a directory capability and recheck
callback; callers must read/revalidate pinned metadata only after entry.

POSIX uses [flock LOCK_EX|LOCK_NB](https://docs.python.org/3.11/library/fcntl.html#fcntl.flock).
Windows uses [msvcrt LK_NBLCK](https://docs.python.org/3.11/library/msvcrt.html#msvcrt.locking)
on the first byte and the existing non-delete-sharing directory pin (primary
sources accessed1November2026). Both release kernel ownership on exit; tests
also kill a real fixture child process and require kernel release without
rewriting its lock. The native metadata-time helper is shared for files and
Windows directories; device/inode/size/mtime/change checks remain in memory,
with no serialized timestamp or canonical-byte change.

This is explicitly read ownership. Root namespace changes are rejected, so it
cannot be used as a mutating-session or abandonment context. It verifies only
the root/lock capability: acquiring it does not recognize a session, validate
journal/cache contents, grant reuse eligibility, authenticate prior execution,
perform comparisons or create a PASS artifact. Bounded pinned semantic reading,
preview, mutation/abandonment and retained execution remain separate gates.
No session command, execution flag, project script or dependency is added.

The gate covers same-process exclusion, real competing-process rejection,
ordinary/exception/interruption release, kernel release after process kill,
missing/wrong-size/wrong-content/nonregular locks, symlink roots/locks,
permanent/transient root or lock replacement, preserved unrelated directories,
read-only namespace enforcement and unchanged data bytes. Actual macOS/Windows
ownership tests run from the built wheel on each supported Python minor; Linux
full suites cover them too. No network/distributed filesystem or unconditional
power-loss guarantee is made.

Run `make test TEST=tests.test_partition_session_ownership`, full local checks,
independent reviews and exact-head quality/manual full matrix before integration.
Feature4 remains incomplete;3/10 features are integrated. All ten must integrate
and qualify before any2.4 candidate. Released range-v1/hash-v2 contracts, aliases,
local-first boundaries and the through-v5.0 direction remain intact.

Local gate:703 repository tests pass under `make check`; all eight ownership
checks pass on CPython3.11.18,3.12.5,3.13.18 and3.14.7. The native Windows lock,
directory-clock and kill-release paths still require exact-head platform CI.
