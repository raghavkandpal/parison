# Dataset evidence v2 contract

Date: 24 October 2026
Status: wire-contract draft; freeze requires acceptance fixtures and review

## Physical and logical identity

An opt-in manifest contains exactly `manifest_version: 2`, `collection_id`,
`policy`, `closed_scopes`, `files` and `bindings`. Policy retains the v1 closed
kind/digest shape. Existing v1 readers, bytes and fingerprint domains stay fixed.

`files` contains 1–10000 closed objects with `path`, `bytes`, `sha256`.
Paths use the released normalized relative POSIX grammar, portable collision
checks and descriptor-based symlink/alias/mutation safeguards. Sizes are exact
nonnegative integers, never booleans. Inventory sorts by UTF-8 path bytes.
One physical path is inventoried once even when selected by many bindings.

`bindings` contains 1–10000 objects. Each has `id`, `role`, `source`,
`members`, `source_sha256` and `policy_sha256`. IDs use the released identifier
grammar; roles are baseline/candidate. The pair `(id, role)` is unique. `source`
is a portable explicit released locator or partition-directory reference,
resolved relative to the physical root. `members` is the exact nonempty ordered
array of inventoried physical paths selected by that source. Bindings sort by
ID then baseline/candidate role. The normalized source retains selector kind,
case-sensitive selector values and namespace bindings; normalization cannot
resolve a different selection or infer a selector. Policy SHA binds the effective
recipe, including field selection. Physical digest alone never binds a selector.

A file binding contains one member and its source digest equals that file's
SHA-256. A partition binding reconstructs the released ordered basename/NUL/raw
SHA-256 algorithm, including a single-member directory. Explicit directory/file
kind must therefore be preserved during normalization. Released dot-child
selection is distinct from closed physical scope enumeration. Every selected
member must be inventoried; supporting files may be inventoried without a logical
binding. Closed scopes enumerate all physical files, including hidden files.

Canonical JSON uses compact separators, sorted object keys, UTF-8, no trailing
newline and domain `parison:dataset-manifest-v2\0`. Creation and source checking
reuse stable-file reads and closed-scope checks. Invalid declarations/unsafe
objects produce controlled errors; missing or mismatched resources produce
FAIL. Source checks expose only closed aggregate summaries by default.

## Preserved semantic evidence

Outer dataset-evidence schema 2 carries canonical manifest, verification result,
effective policy, diagnostic and recursively verified semantic child. Each new
member shape and outer metadata must be versioned; diagnostic v1 is not silently
extended. Source-free verification reconstructs logical digest membership and
compares policy, selector, side and source identities to preserved semantic
execution evidence. It derives aggregate counts and outcome, rejects extras and
verifies all cross-member identities before returning a summary-safe projection.

Ordinary suite children preserve some selector metadata, but summary XLSX may
omit table/defined-name details. Reconciliation v1 preserves input digests without
selectors. Those omissions cannot be filled by trusting a new caller declaration.
Fresh execution must produce an explicitly versioned input-binding record bound
into semantic evidence; dataset evidence v2 requires the new semantic bundle versions described below.
Old semantic evidence remains supported through dataset evidence schema 1. Define that record's schema and producer
boundary before implementing publication. Do not claim reconstruction from
file digests or reopen source files during preserved-evidence verification.

## Workbench and publication

Workbench reviews the explicit root, policy, physical inventory and logical
bindings; changes invalidate review. Publication rechecks selected bytes and
semantic evidence, stages privately, verifies staged evidence and atomically
installs without replacement. Cancellation/failure cleans sensitive staging;
post-publication catalog failure preserves the verified bundle and reports it.
Default derived summaries omit paths, resource/case IDs, selectors and values.

## Freeze gate

Freeze canonical fixtures for a shared workbook with two selections, JSON/XML
selectors and a one-member partition, plus hostile policy/selector/membership
substitutions. Specify semantic binding-record schema, outer/result/diagnostic
versions and command surface. Qualify source-free verification, hidden closed
scope members, aliases/symlinks, collisions, bounds and interrupted publication.
Old v1 byte fixtures must remain identical. No implementation is claimed here.

## Explicit source kind and semantic binding record

Each logical binding additionally requires `source_kind`, either `file` or
`partition`. A structured locator always selects one physical file. A partition
source is a plain directory reference; every member is an immediate child and
members sort by basename UTF-8 bytes. File bindings contain exactly one member.
This field prevents source-free verification from confusing a one-member
partition with a file. Receipt/supporting inventory is physical-only; a
reconciliation receipt must match the one declared receipt digest exactly.

The new semantic record is `input-bindings.json`, with exactly
`binding_version: 1`, `policy` and `bindings`. Each binding contains exactly
`id`, `role`, `source_kind`, `selection`, `source_sha256`, `policy_sha256`.
Selection is a closed tagged object: `kind` is file, partition, sqlite-table,
json-pointer, xml-record, xlsx-range, xlsx-table or xlsx-defined-name. File and
partition have no extra fields; sqlite-table has `table`; json-pointer has
`pointer`; xml-record has `record_path` and `namespaces`; xlsx-range has `sheet`
and `range`; xlsx-table has `table`; xlsx-defined-name has `name`. Selector
validation reuses released locator rules. Paths never occur in this record.
Field selection remains bound by the effective recipe digest. Sort records by
ID and baseline/candidate role, reject duplicates and require exact selected
semantic scope. Hash compact canonical bytes under
`parison:input-bindings-v1\0`.

Fresh execution captures selectors and input digests before execution and
rechecks them before publication. The new semantic bundle manifest version must
bind this record as an obligatory member. Reconciliation schema 2 preserves v1
result/declaration semantics but additionally requires this record; suite schema
3 similarly retains suite-v2 policy and result semantics with an obligatory
record. No optional record is appended to old closed bundle versions. Verifiers
must derive the record's policy/scope/source identities from preserved results;
selector claims are execution metadata bound at production, not inferred from
digest equality. Dataset evidence schema 2 requires these new semantic bundle
versions for complete selector proof. Old semantic evidence remains readable
through released readers and can still use dataset evidence schema 1.

Manifest bindings retain their portable `source` locator and physical `members`;
normalization derives `selection` and compares it exactly to the semantic
record. A changed selector with unchanged physical digest must therefore fail
cross-member verification. Supporting file inventory does not imply execution.

## Outer and result shapes

The schema-2 outer manifest contains exactly `schema_version`, `kind`, `complete`,
`outcome`, `manifest_sha256`, `diagnostic_sha256`, `semantic_result`, `policy`,
`files`. `kind` is dataset-evidence, `complete` is true and schema_version is 2.
`files` digests exactly dataset-manifest.json, manifest-result.json,
effective-policy.json and reproducibility-diagnostic.json. `semantic-result/` is the only child directory.
`semantic_result` contains exactly kind, outcome, manifest_sha256 and
input_bindings_sha256; all must agree with the recursively verified child.
The semantic policy kind/digest must agree with the dataset declaration.

Manifest result version 2 contains exactly `manifest_result_version`, `complete`,
`outcome`, `manifest_sha256`, `policy`, `files`, `bindings`, `closed_scope_status`,
`reason_codes`, `diagnostic_sha256`, `semantic_result`. Each file observation
contains path, expected_bytes, expected_sha256, observed_bytes, observed_sha256,
status. Missing files have null observed fields; statuses are match, missing,
size-mismatch or digest-mismatch, checked in that order. Each binding observation
contains id, role, source_sha256 and status (match or member-mismatch).
`closed_scope_status` is match or undeclared-members; unknown physical members
are never copied into summary output. Completeness means the declared check
finished, including complete FAIL results; an error aborts publication.
Outcome is PASS iff every file/binding/scope matches, otherwise FAIL. Reason
codes are sorted unique missing-resource, size-mismatch, digest-mismatch,
logical-member-mismatch, undeclared-members as derived from observations.
Only PASS source verification may be paired with semantic evidence for dataset
publication; failed source checks remain standalone results. This prevents an
unmatched inventory from being presented as verified execution evidence.

Diagnostic v2 retains v1's exact runtime and observations vocabulary but uses
`diagnostic_version: 2` and binds the v2 manifest fingerprint. Its domain is
`parison:reproducibility-diagnostic-v2\0`; v1 remains unchanged. Summary output
is a closed projection of versions, outcome, completeness, policy/fingerprints,
file/binding totals, status counts, reason codes and runtime. No source IDs,
selectors or resource-level observations appear in the default projection.

## Explicit command selection

Existing commands keep v1 defaults. Manifest creation selects the new profile
only with `--manifest-version 2`; its declaration input supplies the complete
physical inventory and bindings as strict JSON. Version dispatch for explain,
source verification and dataset publication follows the declared version,
rejecting unknown versions. Existing verify/inspect dispatch follows outer
schema version. Fresh suite/reconciliation execution selects new semantic
bundles only with `--input-bindings`; it captures the obligatory record from
actual runtime locators and policies, never accepts an authored record as proof
of execution. Existing execution defaults and output JSON stay unchanged.
Workbench uses these same services through closed workspace-bound requests.
No network, repair, approval or inferred policy is introduced.

Canonical declaration inputs under `tests/fixtures/2.2/` cover shared workbook,
JSON pointer, XML record locator and single-member partition. Synthetic digest
and byte values make these wire-shape fixtures rather than source-verification
success claims. Hostile fixture transformations must change selectors, recipe
policy, member order/names/content and file/partition kind independently while
preserving unrelated fields. Each must be tested at the authoritative validator
or cross-member verifier boundary before qualification.

Structural checkpoint: the closed Draft 2020-12 manifest-v2 schema accepts all
four canonical declarations and rejects unknown binding fields, missing source
kind, boolean sizes and unknown source kinds. These checks do not prove path
safety, exact membership, canonical normalization or semantic cross-bindings;
those remain authoritative runtime acceptance gates.
