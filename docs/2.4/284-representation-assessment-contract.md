# Same-snapshot representation capture and assessment contract

Date and primary-source access: 30 October 2026
Status: frozen feature 2 design; schemas, fixtures and runtime pending

This implements feature 2 of roadmap 275. The assessment scope is
`native-column-representation-v1`: native selected/inventory column facts,
explicit field lineage, primary-key roles and declared representation rules.
ACCEPT is mechanical compatibility within this scope, never data parity,
policy approval, extraction truth or migration/cutover authorization. Preserve
collection-v1, source-v1/source-v2, pair/dossier readers, canonical bytes and CLI
aliases. All ten 2.4 features must integrate and qualify before a candidate.

## 1. Capture envelope and fixed bounds

Add collection-plan-v2 with exactly `collection_plan_version:2`, `source_id`,
`tables`, `limits`. Existing table/ID/selection rules are unchanged. `limits`
contains the four existing fields plus mandatory `max_representation_bytes`
(positive integer, at most 16,777,216). Derive each unchanged source-v2 child
plan using only the four source limits, `plan_version:2`, source_id and the
selection. Remaining execution budgets never change these digest inputs.
New capture requires a UTF-8 database and the exact 16.15/17.11/18.6 live rows
under capability `postgresql-base-table-only-representation-v1`. Collection-v1
admission is unchanged. No implicit capture flag or standalone metadata-only
source reader is introduced.

The new output has exactly receipt.json, summary.json, manifest.json,
representation.json and tables/. Children remain four-file source-v2 ONLY
bundles. All old version1 envelopes retain their exact membership and meaning.
Collection receipt/summary/manifest version2 retain their version1 fields,
using the new profile. Receipt adds `representation_sha256` and observed adds
`representation_bytes`. Limits have the five parent fields. Summary adds only
`representation_bytes`; it exposes no table/column IDs or metadata values.
Manifest files binds receipt.json, summary.json and representation.json;
table_manifests remains a separate mapping. All digests are SHA-256 of exact
canonical member bytes, except reviewed plan digests omit the trailing LF.

Parent/child source, snapshot, session, limits, elapsed and total checks remain.
The four child limits equal the corresponding parent fields. The representation
record binds the parent plan digest and child-manifest map; the parent receipt
binds its digest. Children refer to neither parent nor representation, so there
is no digest cycle. At 16 tables there are68 regular files. Each other JSON
member remains at most 256 KiB; representation has its separate reviewed bound.
Total staged content is at most max_output_bytes + max_representation_bytes +
(3+3*table_count)*262144. No truncated or partial metadata can publish.

## 2. Collection representation record

`representation.json` has exactly `representation_version:1`,
`kind:"postgresql-collection-representation"`, `capability_profile`,
`normalization_profile`, `collection_plan_sha256`, `source`, `transaction`,
`session`, `table_manifests`, `tables` and `not_assessed`.
Source/transaction equal the collection receipt's closed facts; session has
exactly client_encoding:"UTF8", date_style:"ISO, YMD", time_zone:"UTC".
Normalization profile is `pg16-representation-v1`, `pg17-representation-v1` or
`pg18-representation-v1`, matching the recorded server major. Offline readers
validate these profile meanings independently of an evolving live allowlist.
Unknown profiles are controlled unsupported errors, not experimental support.

Tables is the exact ID mapping. Each table has exactly `schema`, `table`,
`selected_columns`, `primary_key`, `columns`. Names/selection/key equal its
verified child receipt. Columns is the complete ordered physical inventory of
non-dropped positive-attnum columns, at most 100 per table. Each column has
exactly `name`, `ordinal`, `selected`, `type`, `numeric`, `characters`,
`datetime`, `nullability`, `materialization`, `collation`. Names are unique;
ordinals strictly increase (positive int16). Selected booleans and ordered key
membership must reconcile with the child. Selected native type names, in
selection order, must equal child source.types with supported:true and pg_catalog
namespace; receipt and metadata cannot disagree about column interpretation. Compare inventory membership with
accessible information_schema columns under table-wide SELECT; absent or extra
rows, incomplete inventory, column-cap overflow or inconsistent facts abort.
Unsupported UNSELECTED types may be recorded, but never broaden COPY admission.

All objects are closed. Integers require exact JSON integer tokens, never
booleans or floating-point equivalents. Text is valid UTF-8; identifiers retain
the existing 63-byte printable bound. Other scalar text is at most512 UTF-8
bytes, except collation rules4096; NUL/surrogates are forbidden. Nested lists
are bounded below; raw SQL default/generated expressions are never captured.
Canonical JSON uses existing _canonical sorted-key UTF-8 plus one LF.

### Column shapes

- Type: exactly `schema`, `name`, `oid`, `typmod`, `display`, `supported`.
  OID is1..4294967295; typmod is signed int32; supported means the exact built-in
  namespace/type allowlist from feature1. OIDs and display text are private
  observations and never cross-instance identity or comparison keys.
- Numeric: exactly `state`, `precision`, `radix`, `scale`, `raw_scale`.
  State is known/unbounded/not-applicable/unsupported. Known integer facts use
  bit precision16/32/64, radix2 and scale0. Known numeric uses decimal precision
  1..1000, radix10 and signed scale-1000..1000. Unbounded numeric has null
  precision/scale, radix10. Raw_scale is the nullable information-schema integer
  observation and never the normalized signed scale. Inapplicable/unsupported
  facts use null numeric values. Normalization is type-specific and replayable.
- Characters: exactly `state`, `max_length`. Known varchar length is positive
  int32; unbounded varchar/text uses null length; other supported types use
  not-applicable/null and unsupported types unsupported/null.
- Datetime: exactly `state`, `precision`, `timezone`. Timestamp/timestamptz use
  known precision0..6 and naive/aware respectively; date uses known/null/date;
  other supported types not-applicable/null/null, unsupported types
  unsupported/null/null. Default timestamp precision normalizes to6, retaining
  raw typmod separately.
- Nullability: exactly `declared_not_null`, `information_schema_nullable`,
  `constraints`, `guarantee`. The first is bool; the second YES/NO; guarantee
  is non-null/nullable/unknown. Constraints is null on16/17 (not separately
  exposed) or a list of at most 100 closed `{name,validated,enforced}` native
  not-null constraint observations on18. Names are unique, sorted by name.
  On16/17, qualified attnotnull true gives legacy non-null and false nullable.
  On18, a validated/enforced native not-null constraint or verified primary-key
  membership establishes non-null. An enforced but unvalidated constraint
  alone gives unknown even if attnotnull=true and is_nullable=NO. An ordinary
  nullable declaration without an enforced native not-null gives nullable.
  For supported types, an attnotnull=false fact with an enforced native
  constraint or verified PK membership is contradictory and invalid. An
  attnotnull=true fact lacking validated/enforced evidence (and no PK) is
  unknown. Unsupported native types keep guarantee:unknown; do not infer
  domain semantics. Reject invalid shapes rather than filling defaults.
- Materialization: exactly `identity`, `generated`, `has_default`: identity
  none/always/by-default, generated none/stored/virtual and boolean has_default.
  Virtual is a PG18 observation; older profiles reject it. These are flags,
  not equality proofs for default or generation expressions.
- Collation: exactly `state`, `origin`, `schema`, `name`, `provider`, `encoding`,
  `deterministic`, `collate`, `ctype`, `locale`, `rules`, `recorded_version`,
  `actual_version`. State is resolved/not-applicable/unknown; origin is
  explicit/database-default/none/unknown. Noncollatable types use not-applicable,
  none and null scalar fields; recorded_version and actual_version are each
  `{state:"not-applicable",value:null}`. Resolved facts have provider libc/icu/builtin,
  integer encoding(-1..int32), boolean determinism and nullable bounded locale
  strings. Namespace/name describe the catalog object; comparisons use resolved
  provider/locale/rules/encoding/determinism facts, not OIDs or names. Database
  defaults resolve through pg_database facts, not null information-schema fields.
  Version objects each have exactly `state`(known/not-versioned/unknown/not-applicable) and
  `value`(bounded string only when known, otherwise null). Unknown collation
  uses origin unknown and null unresolved scalars; version states remain unknown.
  Legitimately non-versioned C/POSIX facts differ from unavailable versions.

The normalizer must reconstruct numeric/length/time precision and nullability
from its recorded raw facts and capability profile; reject impossible combinations.
For varchar, typmod=-1 means unbounded, otherwise max_length=typmod-4
with a positive result. Timestamp/timestamptz typmod=-1 normalizes to6, otherwise
require0..6. Integer precision derives from its built-in type, never display.
Use `typmod=-1` for unbounded numeric; otherwise precision=((typmod-4)>>16)&65535
and scale=(((typmod-4)&2047)^1024)-1024 under the qualified PostgreSQL numeric
profile. The [PostgreSQL algorithm](https://github.com/postgres/postgres/blob/REL_18_STABLE/src/backend/utils/adt/numeric.c)
requires 11-bit sign extension. Raw information-schema scale 2045 is therefore
not semantic scale 2045 for numeric(2,-3); it normalizes to -3. Never reuse this
formula for arbitrary types or future unqualified profiles.

## 3. Snapshot and observation provenance

Use existing pre-snapshot lock order, pg_catalog search path, RLS/role/type
admission and ONLY queries. Capture the complete metadata inventory after all
locks and before COPY in the same transaction, then bind it after child manifests
exist. Database/catalog facts are transaction observations. Actual provider
version functions observe installed libraries outside MVCC: label both version
objects by their fixed field meaning, never claim a library snapshot. A missing
or changed provider observation must not be silently upgraded to known equality.
PG16 captures locale through colliculocale/daticulocale; PG17/18 use
colllocale/datlocale and admit their documented builtin provider. Resolve
provider d through the database default. A null version for qualified libc
C/POSIX or a documented unversioned builtin is not-versioned; unexplained
absence is unknown. Query errors abort capture, never become partial metadata.
Do not repair/refresh collation versions, rebuild objects, interpret expressions,
or infer source/target snapshot equivalence from metadata. Server-owned generated
column values follow normal PostgreSQL SELECT/COPY semantics; assessment adds
no expression evaluator or expression-evaluation query.

Pinned offline collection-v2 verification enforces exact membership, bounds,
normalization invariants, versioned child verification and every cross-record
binding. It verifies existing source-v2 children, normalized representation,
parent/child facts, totals and exact summary before derived assessment. Metadata
is source-visible adapter evidence; a coherent forged source observation remains
unauthenticated. No database driver/connection is used for offline verification.

## 4. Explicit assessment plan and comparison scope

`representation-assessment-plan-v1` has exactly `assessment_plan_version:1`,
`baseline_manifest_sha256`, `candidate_manifest_sha256`, `tables`, `rules`.
Plan cap is2MiB. Tables is1..32 entries keyed by private logical IDs using the
collection ID grammar. Each entry has exactly `baseline_id`, `candidate_id`,
`evolution`. Each side ID is a collection table ID or null, at least one present;
each input table ID appears exactly once. The union can have32 unpaired entries
for disjoint16-table inputs; at most16 entries are paired. Paired entries require a normalized
schema-evolution-v1 declaration; unpaired entries require evolution:null.
Declarations cover the complete physical column inventory exactly once per side;
use existing stable-ID/lineage/cardinality rules plus per-field IDs matching exactly
`[a-z][a-z0-9_-]{0,31}` (the collection ID grammar). At most100 fields per side per declaration. Unknown old
collection-v1 inventory cannot satisfy this coverage check: report unavailable,
never infer absence from selection alone.

Rules is exactly `integer`, `numeric`, `text_length`, `datetime_precision`,
`nullability`. Each is explicit: exact or widen for the first four, exact or
relax for nullability. There are no defaults, tolerance changes, implicit
exclusions, type coercions or inferred key approvals. Collation policy is fixed
below, not caller-overridable. Any schema-evolution default is review metadata
only and cannot make missing/required fields acceptable by materialization.

Comparison ignores table/column OIDs, physical ordinals, type display/typmod
spelling and catalog names when assessing normalized representation. It still
binds every raw observation and uses explicit lineage for names. Conditions:

- Exact native facts and explicit one-to-one unchanged/renamed mapping are
  ACCEPT-eligible. Whole-table membership change is DENY. Mapped logical ordered
  primary-key IDs must match exactly; changed key role/order is DENY regardless
  of field rename or widen rules.
- Adding/removing a selected or required field is DENY. An explicitly declared
  optional unselected non-key field may be added/removed without a conversion;
  this is declaration compatibility, not approval to exclude comparison data.
  Split/merge needs upstream materialization and is DENY in this first version.
- Integer widen permits only int2→int4→int8 within built-in integer families.
  Other type-name changes, except the text-family widening below, including
  timestamp↔timestamptz, require upstream
  conversion and are DENY; no values are converted. Numeric widen permits
  constrained→unbounded numeric or target_scale>=source_scale AND
  target_precision-target_scale>=source_precision-source_scale. Unbounded→
  constrained is narrowing. Exact numeric requires equal normalized bounds.
- Character widen permits greater varchar length or varchar→text/unbounded
  varchar, treating these as the one explicitly supported text-family widening;
  unbounded→bounded is narrowing. No normalization/collation change is implied.
  Timestamp precision widen permits increased0..6 precision only with identical
  naive/aware type. Equal default/explicit normalized precision is equal.
- Nullable→guaranteed non-null is narrowing; non-null→nullable requires relax.
  Unknown guarantee is INCONCLUSIVE. Declared evolution nullability must agree
  with known native guarantees; conflicting declaration is DENY. Unknown facts
  cannot satisfy a declared non-null guarantee.
- Known collation provider/locale/rules/encoding/determinism change is DENY.
  Recorded/current provider version mismatch is DENY. Unknown/default-unresolved
  facts are INCONCLUSIVE. For versioned providers, all four
  baseline/candidate recorded/actual values must be known and equal, alongside
  equal resolved definitions, for ACCEPT eligibility. A known cross-parent
  provider-version change is DENY/collation_changed even when each source has
  matching recorded/current values. These remain observations, not behavioral proof. Matching genuinely
  non-versioned libc C/POSIX facts are eligible; other versionless providers are
  INCONCLUSIVE. Any version-state combination outside the explicit known-equality
  or all-not-versioned C/POSIX exception is INCONCLUSIVE; null is never a wildcard.
  A collation rename alone does not change these resolved facts.
- Unsupported unselected native representation facts yield INCONCLUSIVE for any
  assessed field, rather than silently broadening COPY support. Changed identity,
  generated or has_default flags are INCONCLUSIVE. Unchanged flags never assert
  equal expression semantics. Valid collection-v1 parents lacking representation
  produce metadata_unavailable for each paired table with complete:false;
  evaluate no other per-field findings and count fields:0 in that case. Known
  unmatched-table membership changes still yield DENY. Invalid/tampered v2
  parents are ERROR.

Fixed not_assessed list, in this order, is `check-constraints`,
`default-expression-semantics`, `generated-expression-semantics`, `triggers`,
`indexes-except-primary-key`, `extension-behavior`. It appears in metadata,
assessment and safe summary. It prevents ACCEPT from being presented as full
schema/application equivalence; row parity and declared reconciliation follow.

## 5. Findings, proposal, evidence and CLI

Private assessment result has exactly `representation_assessment_version:1`,
`kind:"representation-assessment"`, `scope`, `plan_sha256`, `inputs`, `complete`,
`compatibility`, `findings`, `not_assessed`. Inputs is exactly `{baseline: SHA256, candidate: SHA256}` binding verified
parent manifest bytes. Scope is fixed as above. Findings is at most20,000 closed
`{table_id,field_id,compatibility,reason}` records, field_id nullable for table
findings. Sort by logical table ID, field ID(null before strings), then reason;
never emit duplicate findings. Compatibility is DENY if any DENY, otherwise
INCONCLUSIVE if any unknown/unavailable fact, otherwise ACCEPT. Complete is true only when both parents are fully verified collection-v2
records with complete inventories and the declared scope was evaluated; any
collection-v1 parent makes it false, including wholly unpaired scope. It does
not mean every fact resolved or any data comparison completed.

Closed reason codes are table_membership_changed, field_membership_changed,
key_changed, declaration_mismatch, unsupported_representation, type_changed,
numeric_changed, character_length_changed, datetime_precision_changed,
nullability_changed, nullability_unknown, collation_changed,
collation_version_mismatch, collation_unknown, materialization_changed,
upstream_materialization_required, metadata_unavailable. Every changed assessed dimension emits its reason even when an explicit widen
rule makes compatibility ACCEPT; allowed changes are not suppressed. Exact
unchanged facts emit no finding unless unknown. No per-source error text.

Artifact is exactly effective-plan.json, assessment.json, summary.json and
manifest.json. Plan<=2MiB, assessment<=8MiB, summary/manifest<=256KiB each. Summary
has exactly representation_summary_version:1, kind, scope, complete,
compatibility, tables, fields, reason_counts, assessment_sha256, not_assessed.
Tables counts paired table entries. Fields counts distinct declared field IDs
across both sides of paired entries (overlapping stable IDs count once per table); reason_counts contains every code
above including zero counts. Manifest has exactly
representation_assessment_manifest_version:1, kind, files(the other three exact
member digests). Every derived value is reproduced from fully verified parents
and plan, not trusted merely because its digest matches. Verification requires
both bound local parents; a source-free integrity check cannot claim replay.

Mapping proposals are a separate private JSON format with exactly
representation_proposal_version:1, status:"unapproved", inputs, tables and
unresolved_tables. Propose requires two fully verified collection-v2 parents;
older parents lacking full inventory return ERROR2 rather than infer coverage
from selected columns. Inputs are exactly `{baseline: SHA256, candidate: SHA256}`
binding the two verified manifest bytes. Tables contains
at most16 exact `{id,baseline_id,candidate_id,fields,unresolved_baseline,
unresolved_candidate}` suggestions. Match only identical existing private table
IDs and unique exact physical field names as suggestions. Generate unpadded one-based IDs table_1..table_16 in ascending exact common
input-table-ID order. Within each table generate unpadded field_1..field_100
in ascending exact common physical-name Unicode code-point order; no locale,
case folding or Unicode normalization is applied. Arrays retain that generation
order; unresolved ID/name lists use the same exact ordering. These are provisional
labels, never approved stable identity or keys. Each field suggestion has exactly id, baseline_name,
candidate_name and reason:"exact-name-only". Unmatched names/IDs are explicit
bounded lists, never guessed renames. Unresolved_tables is exactly baseline
and candidate arrays (at most16 IDs each); unresolved column arrays and field
suggestions are at most 100 entries per side/table. No keys, tolerances, conversion rules,
exclusion decisions or executable default expressions are generated. Proposal
is not an assessment plan and cannot be supplied as one. Size<=2MiB.

Commands under existing parison, with no new project scripts:
- `parison postgres collection --plan COLLECTION_V2 --output DIR` captures v2;
  collection-plan-v1 continues its existing source-v2 ONLY path unchanged.
- `parison representation propose --baseline DIR --candidate DIR --output FILE`.
- `parison representation assess --plan FILE --baseline DIR --candidate DIR --output DIR`.
- `parison representation verify DIR --baseline DIR --candidate DIR` replays.

Assess/verify return0 ACCEPT,1 DENY,3 INCONCLUSIVE,2 invalid/error,130 interrupted;
stdout is the exact compact safe summary plus LF. Propose returns0 for a valid
unapproved proposal, printing only proposal_version:1, status:"unapproved",
table_suggestions, field_suggestions, unresolved_tables, unresolved_fields and
proposal_sha256. No paths, physical names, keys, values or SQL appear in safe
outputs. Each command uses fixed `parison representation ACTION: invalid or
incomplete representation evidence\n` on exit2 and `...: interrupted\n` on130.
Acquisition keeps contract277 errors. Freeze help/error fixtures before runtime.
All publication uses existing trusted-parent, private staging, pinned-read,
atomic no-overwrite and cleanup boundaries; no partial result/proposal publishes.

## 6. Completion gate and probe evidence

[Raw synthetic probe](../../benchmarks/results-2026-10-30-representation-probe.json)
confirmed negative-scale encoding, PG18 unvalidated NOT NULL with an existing
NULL, default/noncollatable ambiguity and16/17 collation catalog changes on the
three exact installed versions. A 16×100 repeated observed-fact sizing exercise
was 910,450 bytes, not a worst-case capacity guarantee. The 16 MiB metadata cap
still requires bounded strings and explicit overflow tests. Source findings and
links are in [research 283](283-representation-assessment-research.md).

Before implementation, freeze closed schemas, canonical bytes, normalized facts
and negative fixtures for both envelopes, assessment and proposal. Independent
review must challenge this contract's rule precedence and all unknown states.
Live capture must pass all three exact PostgreSQL rows, both 16→18/17→18 metadata
assessment pairs, negative/greater-than-precision/unbounded numeric,0/6 timestamp
precision, PG18 unvalidated native not-null and rejection of unsupported
NOT ENFORCED native not-null, PK order and explicit/default
collations. Include hostile search paths, post-qualification DDL/ONLY scope,
post-acquisition DDL, substituted children, wrong plan/snapshot/session, metadata
oversize and provider drift. Equal metadata with different rows must never be
called parity PASS. Verify offline after server shutdown; proposal never approves
policy. CLI and Workbench/CI summary projectors use one verified result function.
Require old fixtures, narrow/full tests, independent Standards/Spec review and
exact-head full built-wheel Python 3.11–3.14 Linux/macOS/Windows CI before feature
integration. No 2.4 release candidate until all ten features qualify.

## Continuation handoff

Continue from clean develop after this contract PR. Start with make context,
AGENTS.md, ignored AGENTS.local.md and docs/CURRENT.md. Feature1 is integrated
through PR121 at2f4ff18, with599 tests and live/platform gates;2.3.0 remains
released at main/tag a288453. Read research283, this contract and raw probe
before materializing feature2 schemas and byte/negative fixtures. Regress the
negative-scale2045→-3 trap, PG18 invalid NOT NULL, cross-parent provider versions,
32-table disjoint unions and proposal inventory/ordering. Review the wire gate
before capture/assessment runtime, then qualify all three servers and both
migration-pair assessments. All ten features remain together before a2.4
candidate; preserve old bytes/readers/CLI and source-v2 ONLY scope. Stop near95%
five-hour usage; resets belong to the owner. This session stopped at94% after
contract review; no feature2 runtime or live qualification is claimed.
