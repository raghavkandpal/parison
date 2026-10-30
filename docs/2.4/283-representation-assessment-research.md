# PostgreSQL representation assessment: feature 2 research

Date and primary-source access: 30 October 2026
Status: design research; implementation contract and wire fixtures remain to be frozen

## Decision proposed

Add private same-snapshot representation observations through an explicit new
collection version, then assess two verified observations under a caller-owned
field/evolution declaration. Keep acquisition and assessment separate: observing
matching types or compatible declared changes cannot establish data parity,
approve keys/tolerances/exclusions, or authorize a migration. The existing
collection-v1/source-v2 readers and all 2.3 contracts remain unchanged.

## Primary-source findings and consequences

- `information_schema.columns` exposes accessible columns, declared length,
  numeric precision/radix/scale, datetime precision and known nullability.
  Domain identity is separate from the underlying type. Collation fields can be
  null for either a default collation or a noncollatable type. Missing rows or
  null fields therefore need typed meaning; they cannot silently mean compatible.
  [16](https://www.postgresql.org/docs/16/infoschema-columns.html),
  [17](https://www.postgresql.org/docs/17/infoschema-columns.html),
  [18](https://www.postgresql.org/docs/18/infoschema-columns.html).
- `pg_attribute.atttypmod` is type-specific, not a universal precision encoding;
  `format_type` supplies display text, not a cross-version semantic identity.
  Preserve raw typmod privately when useful and capture documented semantic
  fields independently. Ignore dropped/system columns and distinguish physical
  ordinal from reviewed selection order. Capture identity/generated/default
  flags without evaluating or emitting their SQL expressions in safe output.
  [pg_attribute](https://www.postgresql.org/docs/18/catalog-pg-attribute.html),
  [format_type](https://www.postgresql.org/docs/18/functions-info.html).
- Numeric declarations permit negative scale and scale greater than precision;
  unconstrained numeric has different coercion behavior from a declared scale.
  Do not assume `0 <= scale <= precision`, use unsigned scale, or interpret
  unconstrained precision as zero. Rounding and range must be assessed separately.
  [Numeric types](https://www.postgresql.org/docs/18/datatype-numeric.html).
- `timestamp` has no time zone; `timestamptz` represents an instant and uses the
  session time zone for rendering. Precision can be 0–6. Matching printed values
  in one UTC fixture does not prove those types interchangeable. A naive/aware
  change needs an explicit upstream conversion policy and boundary examples.
  [Date/time types](https://www.postgresql.org/docs/18/datatype-datetime.html).
- Collation catalogs differ: PostgreSQL 16 uses `colliculocale`, while 17/18 use
  `colllocale` and include the builtin provider. Capture a normalized provider,
  locale/rules, determinism, encoding and recorded version through qualified
  version/capability-specific queries. Resolve database-default collations using
  database facts; do not equate a null information-schema collation with absence.
  [16 catalog](https://www.postgresql.org/docs/16/catalog-pg-collation.html),
  [17 catalog](https://www.postgresql.org/docs/17/catalog-pg-collation.html),
  [18 catalog](https://www.postgresql.org/docs/18/catalog-pg-collation.html),
  [database facts](https://www.postgresql.org/docs/18/catalog-pg-database.html).
- `pg_collation_actual_version` exposes installed provider version observations;
  the database default has analogous version tracking. A recorded/current
  mismatch signals a concern; refreshing a catalog version does not verify
  rebuilding dependent objects. Missing versions and equal version strings do
  not prove equal behavior. Provider libraries are external to MVCC: label these
  as acquisition-time observations, not immutable transaction-snapshot contents.
  Never refresh, rebuild or repair from Parison.
  [ALTER COLLATION](https://www.postgresql.org/docs/18/sql-altercollation.html).
- PostgreSQL18 records not-null constraints in `pg_constraint`, including
  enforcement/validation state;16 represents not-null differently. Its
  `pg_attribute.attnotnull` can describe a possibly invalid constraint. Record
  declared nullability separately from validated/enforced guarantees rather
  than treating one catalog flag as proof that every existing row is non-null.
  [16 constraints](https://www.postgresql.org/docs/16/catalog-pg-constraint.html),
  [18 constraints](https://www.postgresql.org/docs/18/catalog-pg-constraint.html).
- OIDs are internal catalog keys, not portable identifiers for corresponding
  objects in independent databases. Use explicit field IDs and qualified type
  facts; never infer cross-instance identity from equal OIDs or rendered regtype
  names. Keep all built-in resolution under pinned `pg_catalog` search path.
  [Object identifiers](https://www.postgresql.org/docs/18/datatype-oid.html).

## Minimal architecture seam

Prefer a new `collection-plan-v2`/receipt/manifest envelope that always captures
one bounded private `representation.json` in the existing acquisition transaction,
after all relation locks and before COPY. Retain existing source-v2 ONLY child
bundles. Bind observations to the exact collection plan, selected columns,
source/version/session/snapshot facts and child-manifest digests. The parent
receipt binds the metadata digest; metadata can bind child manifests without a
hash cycle because children do not refer to the parent. Define new closed shapes
rather than adding fields to collection-v1 or making a hidden capture flag.

A separately captured post-transaction sidecar could declare a source-owned
association, but cannot establish the same snapshot merely by hashing an earlier
bundle. Do not use it to satisfy same-snapshot assessment. Exported snapshots
add lifetime/connection complexity without a present need. Reuse the same optional
adapter, source validators and pinned publication/verifier primitives; no new
connector platform, registry framework or database dependency is needed.

First capture should retain feature 1's bounded built-in type profile and exact
server matrix. Assessing unsupported native types must return an explicit
unsupported/error state; it must not silently broaden acquisition admission.
Freeze whether a separate metadata-only diagnostic is necessary before adding it.
Capture an entire bounded physical column inventory, plus declared selection,
if added/dropped-column assessment is to distinguish absent from unselected.
Propose at most 100 physical columns per table and 16 tables, with a separately
budgeted metadata cap; a single aggregate file must not inherit 256 KiB blindly.
These are proposed bounds requiring a prototype and fixture sizing.

## Assessment semantics to freeze

Reuse `schema-evolution-v1` explicit stable IDs/lineage and `policy-diff-v1`
mechanical ACCEPT/DENY/INCONCLUSIVE vocabulary through existing evolution/preflight
modules. Add representation assessment as a versioned result, not a changed
meaning for existing policy diffs. Use fixed safe reason counts and private
field-level findings; no inferred rename becomes an approved mapping.

- ACCEPT eligibility: complete verified facts and an explicit mapping, matching
  selected representation facts or a narrowly frozen directional widening rule.
  This describes declaration compatibility only; row comparison remains required.
- DENY: a complete known narrowing/precision loss, changed key role without an
  explicit reviewed declaration, unsupported required conversion, or a declared
  rule violation. Never silently change a recipe to obtain ACCEPT.
- INCONCLUSIVE: missing/unqualified metadata, unresolved default/provider facts,
  incomplete inventory or an unrecognized capability/version. Distinguish unknown,
  unbounded, not-applicable and not-versioned with explicit states.
- Timestamp-zone changes, collation/provider differences and decimal scale changes
  need explicit conversion semantics; equality of metadata is insufficient.
  Defaults are review metadata only. Generated expressions are not executed by
  assessment; source materialization rules must be explicit if selected for COPY.

## Adversarial completion gate and next decisions

Use all three qualified server versions and both 16→18/17→18 reference pairs.
Exercise renamed/dropped/unselected columns, precision/radix/negative scale,
nullable or unvalidated constraints, composite PK order, timestamp-zone/DST
boundaries, explicit/default collation, provider/version drift and null versions.
Attempt same-digest child substitution, wrong snapshot/selection, hostile search
path, post-acquisition DDL, missing metadata and recomputed forged assessments.
Verify offline with servers stopped; old readers/bytes remain intact and safe
CLI/Workbench projections contain no field/source names, paths, values or SQL.

Freeze metadata completeness scope, normalized facts per server capability,
parent/child binding and size limits, compatibility rules and reason vocabulary,
unknown-state handling, mapping-proposal format and command/exit behavior before
runtime edits. No data repair, implicit conversion, policy approval, source
truth, cross-instance snapshot equivalence or cutover authorization is introduced.
All ten 2.4 capabilities remain required before a release candidate.
