# Recoverable local partition sessions

Date: 31 October 2026
Status: feature4 contract; frozen on reviewed integration; implementation is a separate gate

This implements feature4 of [roadmap275](275-ten-feature-research-and-roadmap.md)
from [primary-source research295](295-partition-recovery-research.md). Feature3
integrated through PR132 at `95d434de117aed800aabbb775a33ef64f8fa97c2` after
exact head88997d5 passed independent reviews, quality and the full built-wheel
matrix. Features1–3 are integrated (3/10). All ten must integrate and qualify
before a2.4 candidate. Released range-v1/hash-v2 plans, receipts, bytes, aliases
and ordinary discover/verify behavior remain unchanged.

## 1. Authority and honest reuse

A session is private, mutable, nonportable recovery state, never evidence,
PASS, approval or a live PostgreSQL snapshot. Retention is explicit and sensitive:
raw source snapshots and routed rows remain until explicit abandonment. Resume
works only over local CSVs and a caller-supplied recipe/plan. It neither contacts
PostgreSQL nor revives an exported snapshot or a dead source transaction.

Hashes bind claimed identities and detect inconsistency; unsigned checkpoints
cannot authenticate previous execution. Resume may reuse a complete routing
checkpoint and complete partition results only after structural, integrity and
current source/policy/plan/engine/runtime validation. This is reuse of prior
unsigned evidence, not fresh exact replay. A coherently forged/rehashed cache
can remain integrity-valid. Do not silently promote it to source-backed truth.

The new session invocation response must say `reused-integrity-checked` whenever
any routing or result work was reused, even if all comparisons were recomputed.
It says `fresh-exact` only when routing and every comparison were performed in
that invocation. Neither label authenticates earlier execution or source truth.
The existing `partitions verify DIRECTORY --recipe ... --baseline ... --candidate ...`
always reconstructs the entire derivation without consulting sessions before
returning `exact-source-backed`. No cached comparison substitutes for that gate.
The final ordinary four-file discovery artifact remains unsigned and unchanged;
its integrity-only reader does not acquire execution-authentication authority.

## 2. CLI and bounded admission

Add only optional arguments to existing `parison partitions discover` and its
legacy alias: `--workspace DIRECTORY`, `--resume`, `--max-session-bytes INTEGER`.
No options means the released command and JSON response, including temporary
cleanup, remain unchanged. `--resume` requires `--workspace`. A fresh workspace
must not exist; an existing one requires explicit resume. Plan, recipe, baseline,
candidate and output stay mandatory on every invocation. Existing output is
never overwritten. One invocation owns one session and runs sequentially.

Fresh retained sessions require an explicit positive exact integer
max-session-bytes<=2,100,000,000. Resume uses the recorded bound; an explicitly
supplied different bound rejects reuse. The bound includes every retained file
and transient replacement/checkpoint/publication copy under the session, including
source snapshots, derived recipe, all bucket files, result records and journal.
Reserve/check bytes before writes, with released per-source/row/partition/staged
limits also enforced. Final output metadata has its existing independent caps;
no source staging is copied to the output directory.

Both range-v1 and hash-v2 discovery are admitted with their original key/profile
rules. Retained-session recipe JSON and derived recipe each have a256KiB cap;
plan has the existing256KiB cap. This tighter opt-in profile does not constrain
ordinary released range-v1 discovery. Both session profiles require admitted
CPython3.11–3.14 and exact Python/Unicode descriptor equality on resume before
opening source inputs. Plain range-v1 discovery/verification keeps its contract.

Add `parison partitions session preview DIRECTORY` and `session abandon DIRECTORY`,
with the same legacy alias parser. Preview pins/verifies bounded session metadata
and cache structure but does not read original sources, claim eligibility for
reuse, execute comparisons or expose paths/keys/values/samples. Abandon requires
an unlocked, recognized owned session and deletes only that verified owned
identity. Malformed/unrecognized roots are rejected, not recursively deleted.
No PID-based lock breaking, background recovery or new project script.

Completed session commands return a new closed `partition_session_result_version:1` JSON
object with exactly `action`, `state`, `execution_assurance`, `reused_routing`,
`reused_partitions`, `computed_partitions`, `sensitive_retained` and `summary`.
Action is `discover|resume|preview|abandon`; state is
`initializing|routed|comparing|ready|published|abandoning|abandoned`.
Assurance is `fresh-exact|reused-integrity-checked|not-executed`.
Counts are exact nonnegative integers<=128; booleans are exact JSON booleans.
Summary is the released safe discovery summary only for successful publication
(or recognized already-published output), otherwise null. No source/workspace
path, policy field name or raw content enters this response. Exit discover/resume
0/1/2 follows its final summary outcome PASS/FAIL/INCONCLUSIVE; invalid commands
or state return2 with fixed value-free text. Preview/abandon return0 on valid
completion; interruption returns130 with fixed value-free text and explicitly
retained partial state. Errors/interruption emit no JSON on stdout. Preview/abandon use
not-executed assurance, zero counters, reused_routing:false and summary:null;
abandon sets sensitive_retained:false. Preview cannot establish that an output
still exists. No incomplete session response implies a comparison PASS.

## 3. Identity, ownership and fixed storage

Persist exactly `.lock`, `session.json`, `plan.json`, `routing/` and `results/`,
plus at most one recognized `session.next` during atomic journal replacement.
No arbitrary paths, symlinks, Windows reparse points or extra members qualify.
All writes/reads/deletions bind owned directory/file identities, not merely
checked pathnames. Native Windows pins must request directory data access and
deny delete sharing during sensitive operations; POSIX uses verified descriptors.
Deletion preserves replacement directories and removes owned sensitive contents.

Hold one nonblocking kernel ownership lock throughout each mutating invocation:
POSIX flock or Windows byte-range locking on a fixed regular one-byte `.lock` containing exactly b"\x00".
The lock file remains in the session; never unlink/recreate it to obtain ownership.
Recheck its identity and the root identity before mutations. Reject a second
owner and substituted lock/root names. Preview takes the same lock while reading
so it cannot observe a writer's half-transition. Kernel lock release after process
exit permits resume; never infer ownership from a PID, timestamp or stale flag.
Read/revalidate journal and root metadata after acquiring ownership, including
when another invocation just released it; pre-lock data cannot authorize reuse.
Support local filesystems with the qualified identity/locking semantics; no
network/distributed locking or unconditional power-loss durability promise.

Session JSON is strict, canonical LF JSON<=1MiB, duplicate/nonfinite-free and
closed. It has exactly: `partition_session_version:1`, `state`, `identity`,
`max_session_bytes`, `routing`, `results`, `published_manifest_sha256`.
Persist only states initializing/routed/comparing/ready/published/abandoning. A result array
has exactly N slots, ordered by original plan index, each null or a descriptor
with exact `sha256` and `bytes`; no sparse map or caller-selected cache path.
Published manifest hash is null until ready, then a lowercase SHA256 digest.
Initializing requires routing:null and all results:null; routed requires routing
and all results:null; comparing allows partially committed results. Ready/published
require routing and every result slot, including valid incomplete final results.

Only valid session.json is committed authority. If it is missing, malformed or
oversized, reject reuse; never recover authority from session.next. With a valid
primary journal, a bounded regular fixed-slot session.next is uncommitted and
may be discarded under ownership regardless of whether its bytes are partial or
canonical. Never promote it by timestamp, state ordering or apparent completion.
Symlink/reparse/oversized replacement slots reject before deletion. Initializing
permits only missing/partial files at recognized routing names; routed and later
require exact committed routing coverage.

Identity has exactly `plan_sha256`, `policy_sha256`, `derived_recipe_sha256`,
`inputs`, `columns`, `normalization_runtime`, `engine`.
Inputs are the two original SHA256/byte descriptors, not re-emitted CSV hashes;
columns is the ordered physical staging column list. Range-v1 preserves loaded
recipe order; hash-v2 uses its frozen Unicode-sorted columns. Runtime is291's
closed descriptor. Engine has exactly `contract:"partition-session-engine-v1"`,
`parison_version` (nonempty ASCII<=64 bytes), `package_sha256`.
The package fingerprint is SHA256 of canonical JSON mapping every packaged
`.py` and schema `.json` relative resource name to its exact-byte SHA256, in
canonical name order. It excludes pycache, absolute paths and documentation;
version alone cannot admit reuse across unreleased source changes. This is an
identity claim, not attestation of loaded code or authenticated prior execution.

Routing is null until the entire routing generation is committed. Thereafter
it contains exactly `receipt`, `files`. Receipt has exactly `inputs`,
`route_rows`, `staged_bytes`, `partitions`, plus `derived_recipe_bytes` for v2.
Inputs/rows use the released two-side shapes. Partitions are N ordered records
with exactly the released `upper` (v1) or `bucket` (v2) label and baseline/candidate
side row/byte/SHA descriptors, without comparison fields. Identity supplies its
plan/policy bindings. Files is
the exact fixed snapshot/derived/bucket filename-to-SHA/bytes map. Routing files
are two original-byte snapshots, derived-recipe.json and2N side-index CSVs.
Each files-map value has exactly sha256 and bytes. Snapshot names are `snapshot-baseline.csv`/`snapshot-candidate.csv`; bucket names
are `baseline-I.csv`/`candidate-I.csv` with decimal plan index I. No absolute,
parent-relative or user-controlled filename is stored. Validate all counts and
bindings against the admitted plan and source descriptors before reuse.

Each results/I.json is canonical LF JSON<=1MiB with exactly
`partition_checkpoint_version:1`, `index`, `policy_sha256`, `engine_sha256`,
`inputs`, `result`. Policy hash is the mechanically derived comparison policy;
engine hash is SHA256 of canonical engine identity. Inputs bind the two routed
side SHA256/byte/row descriptors. Result has exactly `counts`, `field_counts`,
`discrepancy_count`, `outcome`, `complete`, copied from the unchanged exact engine
with sample_limit0. Validate exact tokens, closed field coverage, row/match/field
arithmetic and outcome as in discovery receipts. Only complete records qualify
for reuse. No signing, repair, approval, discrepancy samples or second comparator.

## 4. Transitions and final publication

Fresh admission pins bounded recipe/plan and both source handles. Snapshot/hash
sources from their pinned handles and preserve name/descriptor stamps through
publication. Retained source paths and raw recipe copies are prohibited: callers
supply original inputs again. Parse only private snapshots for semantic work.
On resume, hash current pinned originals and verify recipe/plan/layout/engine/
runtime before selecting cache work. Changed bindings reject the session without
rewriting its recognized checkpoints or publishing output.

`initializing -> routed` commits only after all snapshots, derived recipe and2N
routed files close, satisfy budgets, reproduce hashes/row counts and pass source/
workspace guards. An interrupted routing generation is wholly discarded under
ownership and rebuilt; no partial row-routing claim is reusable. Session snapshots
count toward session storage, but released range-v1 staged_bytes still excludes
snapshots/derived recipe and hash-v2 retains its own published arithmetic.

`routed -> comparing` processes in plan order. Write/close/hash/validate a child
result before atomically committing its descriptor in the journal. Results
referenced by a valid journal are immutable for that generation. Missing,
malformed, changed or inconsistent committed files reject reuse; uncommitted
partial result files may be discarded only at their fixed known slot and safely
recomputed. Incomplete results are retained for diagnostics but recomputed on
resume. Reject unexpected files instead of treating them as reusable work.

`comparing -> ready` requires N valid current or reused results. Aggregate with
the unchanged exact engine's counts/field suppression and original global empty
policy, in plan order. For legitimate unmodified checkpoints, every ordinary final file must be
byte-identical to a clean run under the same admitted context. Coherently forged
cache has only the weaker unsigned-integrity assurance defined in section1; byte
equality to a fresh run is not asserted for it. Prepare the exact expected manifest hash;
never add resume counters, timestamps, cache provenance or session IDs to those
four released files. The session wrapper carries assurance/counters separately.

`ready -> published` verifies final ordinary metadata and source/session guards,
then publishes through atomic no-overwrite installation. Checkpointing is not
multi-file atomic publication or storage durability. If interruption follows
publication but precedes its journal transition, resume may report already
published only when the supplied output verifies and its manifest hash equals
the ready checkpoint. Other existing outputs reject, without deletion/overwrite.
Report existing output with reused-integrity-checked assurance; do not claim a
fresh comparison because a prior invocation published it.

Abandon first commits state abandoning under ownership. That state cannot
resume comparisons; repeated abandon may safely finish deletion, and preview
reports it without execution authority. Only known owned files may disappear
while abandoning; unexpected members/substitutions still reject. Keep the journal
and lock until all sensitive routing/results content is removed, then remove
non-lock metadata. Close/release the lock only after the primary journal is gone;
a newly admitted owner must reread metadata after its lock acquisition and reject
the missing journal. Finally unlink the owned lock and remove only the empty
owned root, preserving replacement directories. Interruption before metadata
removal leaves a recognized abandoning session; later interruption can leave
only an empty/unrecognized root, never retained raw content behind that state.

## 5. Adversarial completion gate

Freeze schemas/canonical examples/negative vectors before enabling execution.
Prove clean/resumed four-file equality for range-v1 and hash-v2, all outcomes,
empty policy, normalization, null/duplicate/skew cases and both v1 physical
column orders. Show saved comparison invocations and retained bytes on a named
machine; no universal capacity, power-loss or performance promise.

Kill/interruption gates cover partial baseline/candidate snapshots, partial
routing, before/after each child/journal commit, final-side failure and both
sides of publication. Resume either reproduces legitimate clean evidence or
rejects reuse; it never overwrites unrelated output. Cover truncated/oversized/
float-substituted journals, symlinks/junctions, root/member/lock substitution,
changed source/policy/plan/layout/package/runtime, concurrent owner, disk-full,
exact storage boundaries, malformed committed and uncommitted children, and
safe explicit abandonment. Native Windows tests must exercise ownership during
writes and deletion; actual kernel behavior is mandatory, not mocked clearance.

Distinguish forgery classes: malformed, inconsistent or identity-mismatched
children reject; a fully coherent rehashed forged cache is only integrity-checked
prior evidence and must never be labelled exact-source-backed. Demonstrate fresh
source-backed verification rejects forged derivation while legitimate resumed
artifacts pass it. Do not claim unsigned cache validation detects coherent forgery.

Require independent Standards/Spec review, exact-head quality and manual full
built-wheel Python3.11–3.14 Linux/macOS/Windows CI, including session gates on all
platforms, before counting feature4. Feature5 workers, new key semantics, remote
orchestration and source reacquisition remain separate; no release is proposed.
