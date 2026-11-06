# Draft decision: explicit cooperating-owner recovery profile

Date: 6 November 2026
Status: UNAPPROVED proposal; contract296 remains binding; implementation prohibited
until the owner selects this semantic change and its contract is reviewed

## Why a decision is needed

[Audit314](314-session-mutation-protocol-audit.md) identifies unresolved conditional
namespace mutations under contract296's independent same-owner substitution
threat. No full supported-platform protocol was established. More pathname checks
cannot be presented as atomic preservation. This proposal is one concrete
alternative, not approval to weaken the existing contract or a completed feature.

## Proposed decision, if explicitly selected

Introduce a new opt-in `cooperating-owner-v1` retained-session profile with a
version2 session contract. It supports the same qualified Linux/macOS/Windows
lanes and keeps explicit bounded retention, integrity-only reuse and unchanged
final evidence. The semantic change is the admitted interference model:

- The operator must exclude independent same-user mutation of the workspace,
  its entry in the parent, and every ancestor entry used to resolve/mutate it
  throughout the mutating invocation. Kernel locking excludes cooperating
  Parison owners; it does not enforce this independent-process exclusion.
- The reviewed replacement contract must define and qualify permission/ACL
  admission that excludes other-user mutation of those relevant namespace
  entries. Owner-only root permissions alone do not protect its name in a shared
  writable parent. Reject layouts whose parent/ancestor protection cannot be
  established; do not infer it from root mode0700. The operator's same-user
  exclusion must cover these entries too. No unqualified parent/ACL behavior is
  authorized by this outline.
- Fixed members, non-symlink/reparse admission, pinned ancestors/descriptors,
  expected identity/change stamps and pre-mutation rechecks remain mandatory.
  Observed unexpected changes reject/abort. No best-effort check is described as
  an atomic compare-and-mutate primitive.
- Preservation against an independent same-owner modifier at the unobservable
  final-check/mutation boundary is explicitly outside this new profile. Such
  interference can delete or overwrite a substituted entry; it is not merely
  guaranteed detection. This is the exact guarantee being changed.
- Under the admitted cooperating-owner environment, use the strongest qualified
  existing primitives, atomic journal replace and no-overwrite final publication.
  Keep296's abandonment ordering and full sensitive-content cleanup requirement;
  do not substitute tombstones, empty shells or raw-content retention.

This is a product execution-profile decision, never approval of a user's keys,
tolerances, comparison scope, exclusions, repairs, migration or cutover.

## Explicit admission and compatibility treatment

If selected, write a complete replacement contract and freeze schemas/fixtures
before runtime implementation. The proposed wire/admission changes are:

1. `partition_session_version:2`, a closed `namespace_profile` constant
   `cooperating-owner-v1`, and engine contract `partition-session-engine-v2`.
   Bind this profile into engine/session identity; never silently reinterpret v1.
2. New retained discover/resume require an explicit
   `--session-profile cooperating-owner-v1` in addition to workspace/budget and
   all existing mandatory recipe/plan/source/output arguments. Resume requires
   exact recorded profile equality. Omission does not select a weaker profile.
3. A version2 session invocation response includes the profile. Preview identifies
   the profile without granting reuse; counters/assurance and summary-safe fields
   retain296's distinctions. Fresh comparison never authenticates earlier cache.
4. Existing v1 schemas, fixtures and read-only preview remain readable and
   byte-compatible. V1 sessions gain no discard, migration, abandon or execution
   authority; no automatic rewrite/repair is allowed. State their unsupported
   mutating status honestly.
5. Ordinary discover without retention, both aliases, released recipes/plans,
   policies, four-file evidence, exit codes, exact source replay and other bundles
   retain their existing semantics/bytes. No final-publication guarantee changes.

These are concrete proposed differences, not an approved schema or CLI contract.
The eventual reviewed specification must enumerate every closed field, response,
error, budget and old-reader gate; do not implement from this outline alone.

## Required verification if selected

Retain kernel ownership/exclusion and after-lock recognition tests. Add explicit
profile admission, v1 preservation/refusal and version2 canonical fixtures.
Test source/policy/plan/engine/runtime binding, byte equality with clean runs,
cache forgery's weaker assurance, budgets, every interruption/publication boundary,
all admitted outcomes and safe abandonment. Preserve symlink/reparse rejection
and deterministic observed substitution rejection tests. State that these do
not prove preservation for interference expressly outside the profile.

Independently review the new threat/contract before code, then implementation
Standards/Spec, local preflight and exact-head manual full Python3.11–3.14
Linux/macOS/Windows qualification before integration. Keep all ten train features
and audit307 clarity work before release. The profile must not be enabled merely
because the older isolated native experiments passed.

## Other decision

Retain contract296 unchanged and continue only research for a complete qualified
conditional-mutation protocol. No destructive implementation or feature4 completion
follows until one is established. Do not silently choose a platform exclusion,
privileged helper, weaker profile, logical abandonment or numbered-feature skip.

## Unchanged boundaries

Local inputs, no network/credentials/signing/repair/remote orchestration; explicit
policy, unsigned-cache assurance, exact source-backed replay and deterministic
atomic no-overwrite final evidence remain. No secure-erasure promise is added.
This draft approves no action and changes no released or active runtime behavior.
