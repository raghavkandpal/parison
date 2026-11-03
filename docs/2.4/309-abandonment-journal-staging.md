# Bounded abandonment journal staging

Date: 3 November 2026
Status: private staging prerequisite; atomic promotion and abandonment disabled

The new private `_stage_abandoning` borrows existing mutating ownership and
recognizes the bounded retained session before preparing an abandonment journal.
It preserves every recognized field except the proposed state. `_recognize_owned`
now also returns observed retained file bytes, including lock, primary metadata,
committed and uncommitted contents, so staging reserves the additional canonical
replacement bytes before creating or writing the fixed `session.next` slot.

Creation is exclusive with private permissions, descriptor-relative on POSIX
and under the existing native root pin on Windows. An existing slot is never
overwritten or discarded. Primary name/metadata identity is checked throughout;
written bytes are flushed, fsynced and read back through their owned handle.
Named/handle identity, all retained members and total storage are rechecked
before returning the staged identity. Child handles close before return.

The primary journal stays authoritative and unchanged. Interruptions or storage
errors may retain only a bounded empty, partial or complete uncommitted next
slot. Preview continues to report the primary state; it never promotes the
replacement or grants reuse. No CLI, schema, response, final evidence or source
handling changes are enabled. fsync does not establish a cross-platform power-loss
durability promise. The caller must retain ownership throughout this helper.

Tests cover all five fixture profiles and six persisted states, unchanged
existing files, byte equality with the frozen abandoning fixtures from ready,
exact storage reservation and one-byte-short rejection before creation,
non-overwrite of partial/complete next slots, interruption before writes and at
fsync, storage errors, malformed primary metadata, symlink preservation,
primary changes during staging and same-size staged-byte corruption.

Full local `make check` passes752 tests (five Windows-native skips on macOS).
Independent WIP Standards/Spec reviews are clear;55 focused tests pass with
one native skip. Exact committed-head review and native CI remain required.

## Integration and continuation

Recognition PR #147 integrated at `a8cbca9` from exact source head `2774ee5`,
after independent exact-head Standards/Spec clearance, quality and
[manual full qualification41599096957](https://github.com/raghavkandpal/parison/actions/runs/41599096957).
The earlier full source head `3c0bb43` also passed; the later head carried only
the clarity release-gate merge and was separately requalified before integration.

Next qualify staging at its exact committed head, then implement verified
fixed-slot discard and atomic primary replacement under contract296. Every
mutation must preserve substituted identities and interruption semantics.
Safe abandonment, final lock/root removal and retained discover/resume remain
separate unfinished gates. Feature4 is incomplete; only3/10 train features are
integrated. Complete audit307's bounded clarity work before releasing2.4.
Preserve the unrelated continuation297 edit. The owner explicitly requested
continuation toward weekly exhaustion on3November; do not consume a reset.
Read the PR's actual native results before claiming integration qualification.
