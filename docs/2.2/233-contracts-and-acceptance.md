# Six-feature contracts and acceptance gates

Date: 23 October 2026
Status: six contracts implemented and released in 2.2.0

The publication hold recorded below applied to the implementation decision.
The user separately approved the 2.2.0 release on 28 October 2026; see the
[release checklist](243-release-checklist.md) for exact tested assets.

The accepted scope is [232](232-accepted-roadmap.md). These gates bind all six
capabilities before implementation. Wire schemas and canonical fixtures must be
frozen with each feature contract before its runtime changes. A gate listed here
is a requirement, not a claim that a test has passed.

## 1. Modern dataset evidence

Introduce opt-in `dataset-manifest-v2` and dataset-evidence outer schema 2.
Keep manifest v1, diagnostic v1 and released source identity algorithms intact.
One unique physical-file inventory records normalized relative paths, sizes and
digests. Separate logical bindings identify each case/dataset and side, its
effective recipe policy, explicit selector and ordered physical membership.
Multiple logical bindings may reference the same inventoried workbook. Physical
aliases remain rejected; logical reuse must not duplicate inventory entries.

For a partition binding, reconstruct the released source digest from ordered
member basenames, NUL separators and raw SHA-256 bytes. A single-member directory
remains a partition, not a file. Logical selection excludes dot-prefixed children
as released; closed physical scope enumeration does not silently exclude them.
Selectors belong to reviewed policy/input binding, never to file-byte identity.
Verification of preserved evidence must need no source files and must bind the
exact semantic child, selection and policy. Workbench publication is explicit,
local, verified and no-overwrite. Source checking and preserved-evidence checking
must remain distinguishable in output.

Acceptance fixtures: two ranges/tables in one workbook; JSON pointers; XML
namespace selectors; partition reorder, rename, addition and content change;
single-member partition; hidden file under open versus closed scope; selector or
policy substitution with unchanged file digest; source removal after publication;
portable path collisions, symlinks, aliases, size bounds and interrupted staging.
Pin v2 canonical bytes and rerun unchanged v1 byte fixtures.

## 2. Complete suite authoring

Author the existing suite-v2 format using explicit existing recipes and input
references. Support adding/removing/reordering cases, IDs, tags, released limits,
execution settings and policy locks. Validate with the authoritative loader at
the eventual destination directory; export only an unapproved draft to a new
path. Every edit or referenced-content change invalidates prior review. Authoring
does not execute or approve anything. Exported JSON is consumed by existing CLI
validation/list/run commands; no redundant CLI builder is required.

Acceptance fixtures: mixed keyed/aggregate/multiset cases with nondefault limits
and execution settings; explicit lock match/mismatch; relocated destination and
reload with intended identity; duplicate IDs and invalid limits; unavailable
dependencies; workspace escape/symlink rejection; referenced recipe mutation;
proof that validation/export never invokes a runner.

## 3. Recoverable suite execution

Retaining a local execution workspace is an explicit sensitive-data choice.
Expose a preview from the runner's authoritative reuse eligibility rules, then
separate deliberate restart/resume actions. Workbench executes one job and
revalidates eligibility at submission. Reuse requires all released policy,
selection, input and verified checkpoint identities; preview cannot authorize
stale reuse. Cancellation preserves only the explicitly retained workspace and
never advertises an incomplete parent as complete. Abandonment must be explicit
and confined to the owned retained workspace.

Acceptance fixtures: instrument a completed member to prove actual reuse;
mutate inputs, recipe, selection and checkpoint independently to prove non-reuse;
cancel during a later member; restart into a fresh destination; retained-state
collision and unsafe path rejection; explicit abandonment; publication succeeds
but catalog registration fails without losing verified output.

## 4. Policy-change review

Use two explicit recipes and one explicit evolution declaration. Delegate all
assessment to released `diff_policies`; preserve its labels, canonical output
and reason derivation. Present the released summary first; schema-sensitive
details require a separate deliberate view. ACCEPT is a mechanical assessment,
never policy approval and never permission to compare unequal-policy evidence.
No automatic draft generation is needed for this checkpoint.

Acceptance fixtures: declared rename, key change, tolerance change, exclusion,
scope change and incomplete declaration; CLI/service/Workbench result parity;
summary omits names, values, paths and declaration fragments; an accepted rename
does not bypass the existing exact-policy suite comparison gate.

## 5. Verified suite rehearsal series

Add a separately versioned suite-series artifact and independent verifier.
Accept a bounded caller-ordered list of distinct complete verified suite parents;
require exact policy, selection and per-case comparison mode compatibility.
Analyze verified ordinary children with existing discrepancy group semantics.
Scope group identity by case, preserving mixed-mode units rather than summing
unlike counts. Include adjacent input-identity changes and deterministic count
transitions; do not call decreasing counts improvement or infer chronology.
The bound and exact wire shape must be fixed in the feature's byte fixtures.

Acceptance fixtures: recurring/resolved/new failures; two cases sharing a group
descriptor; mixed modes; unchanged counts with changed bytes; caller-order
reversal; duplicate parents, incomplete/sharded/tampered parents and changed
policy/selection rejection; source-free artifact verification and canonical
bytes; summary omits case names, field names, paths, keys and samples.

## 6. Complete reconciliation workflow and typed handoff

First qualify the authoritative verifier's closed count vocabularies, feasible
arithmetic and count-derived component outcomes against released producers.
Preserve valid released bytes and conservative FAIL/INCONCLUSIVE/PASS reduction.
Verification establishes internal evidence consistency, not source re-execution.

Review exact local declarations, recipes, inputs and receipt; bind reviewed bytes
and reject stale submission. Reuse composed execution with cooperative
cancellation and explicit post-publication status. Add verified history/results
and preserved-evidence diagnosis for identity, reference and conservation
failures. Fixed reason text must not contain user names or values. Opaque IDs
are pseudonymous linkage, not a confidentiality guarantee.

Introduce explicitly versioned typed handoff predicates/layouts for
reconciliation and dataset evidence. Existing ordinary/suite Statement and report
bytes stay unchanged. New handoff must bind the actual policy/scope,
coordination claims and verified subject kind; it must not reinterpret a
relationship outcome as ordinary parity. Freeze these layouts before coding.

Acceptance fixtures: parity PASS with orphan/reference and conservation FAIL;
ambiguous parent, forbidden nulls, parent without children, zero counts and
heuristic alignment INCONCLUSIVE; missing/unknown/boolean/negative/impossible
counts and forged outcomes with recomputed file digests; stale receipt/input;
cancel before publication and catalog failure after publication; source-free
diagnosis; typed handoff roundtrip, mismatched subject rejection, old handoff
byte fixtures and summary disclosure assertions.

## Qualification and continuation

Each capability needs narrow regressions, `make check`, independent Standards
and Spec reviews, a green pushed checkpoint and exact-head required built-wheel
qualification before integration. Finish all six before candidate preparation.
No tag, release merge or publication is authorized. Assertions, archives and
reconciliation comparison remain deferred. Continue research/build/review through
at least v5.0 under the accepted cadence; future scopes require researched
contracts rather than speculative implementation in this train.
