# Versioned schema evolution and meaningful policy diff research

Date: 14 October 2026

Status: **research recommendation**

## Precise question and boundary

What is the smallest explicit contract that lets Parison compare datasets across a reviewed schema evolution and explain the compatibility impact of the corresponding policy change?

The capability must cover renamed, added, removed, split and merged fields without becoming a migration engine. It may determine whether two declared policies are mechanically compatible with a narrow Parison contract. It must not infer business equivalence, approve a mapping, synthesize missing values, transform source records, or authorize cutover.

This is deliberately larger than a field-list diff. A rename changes physical identity but need not change meaning; a default can invent values; a nullable field can still be present in every record; and a split or merge computes new values. The result therefore needs both a versioned evolution declaration and a semantic diff of the effective policies that consume it.

All external sources below are primary specifications or official project documentation and were accessed **14 October 2026**.

## Repository starting point

Parison already has most of the safe foundation:

- `column_mappings` maps one canonical policy column to one exact physical name on each side; candidates are never guessed, and mappings participate in the effective-policy fingerprint ([column mapping contract](../0.3/28-column-mapping-contract.md)).
- strict input validation requires a fixed row schema. Missing, unexpected, duplicate and changing fields fail rather than being filled or unioned ([semantic scalar contract](../1.1/139-semantic-scalar-contract.md)).
- recipe versions 1–3 define keyed, aggregate and multiset comparisons. Released meanings, canonical bytes, JSON contracts, bundles and exit codes remain readable through 1.x ([compatibility contract](../0.19/126-compatibility-contract.md)).
- `policy_sha256` is SHA-256 over canonical compact JSON for the fully expanded, data-free policy. It proves exact policy equality, not approval, identity or authenticity ([fingerprint contract](../0.4/40-policy-fingerprint.md)).
- current `catalog diff` intentionally rejects unequal policy fingerprints because run trends are meaningful only under one exact comparison policy ([catalog history contract](../0.15/101-catalog-history-contract.md)).

The missing layer is a deterministic explanation of *why* two effective policies differ and whether a separately reviewed evolution declaration accounts for those differences. Run-to-run evidence under unequal policy fingerprints must remain incomparable unless and until a distinct future evidence contract defines a safe bridge.

## Lessons from established schema systems

### Identity must survive names

Apache Iceberg assigns every field a never-reused ID. A rename changes the name but not the ID; an added field receives a new ID so old data cannot be mistaken for that field. Iceberg also forbids structural changes such as grouping sibling fields into a nested struct because they are not simple identity-preserving evolution ([Iceberg schema evolution](https://iceberg.apache.org/spec/#schema-evolution), [Iceberg schemas](https://iceberg.apache.org/docs/latest/schemas/)).

Protocol Buffers likewise treats field numbers as persistent wire identity. Deleted numbers must be reserved and never reused; changing a number is deletion plus addition, not rename ([Proto3 language guide](https://protobuf.dev/programming-guides/proto3/#deleting)).

**Consequence for Parison:** name similarity is not evidence of continuity. `schema-evolution-v1` needs immutable logical field IDs owned by the declaration. A rename preserves one ID while changing a side-specific physical name. Removing an ID retires it permanently within that evolution lineage. Reusing an old name does not resurrect its identity.

### Compatibility is directional and defaults are semantic

Avro resolves a writer schema against a reader schema. Fields match by name after optional alias application; a reader field absent from the writer can be filled only when the reader declares a default, while an absent field without a default is an error. Avro explicitly says a default is for reading missing instances and does not make a field optional when writing ([Avro 1.12 specification](https://avro.apache.org/docs/1.12.0/specification/#schema-resolution)).

JSON Schema separates three states that are often conflated: a property is optional unless listed in `required`; an absent property is not the same as a present property whose value is `null`; and `default` is an annotation, not a general instruction for validators to insert data ([JSON Schema object reference](https://json-schema.org/understanding-json-schema/reference/object), [JSON Schema validation specification](https://json-schema.org/draft/2020-12/json-schema-validation.html#name-default)).

**Consequence for Parison:** compatibility questions must name a direction, and absence, nullability and a declared default remain independent. Parison should not fill a missing field from a default. Doing so would manufacture comparison evidence and make PASS depend on a transformation rather than supplied values.

### Type compatibility is not value equivalence

Avro and Iceberg permit small, explicit sets of type promotions. Protocol Buffers warns that changing a field type can parse existing bytes under a different meaning and recommends almost never doing it ([Avro schema resolution](https://avro.apache.org/docs/1.12.0/specification/#schema-resolution), [Iceberg schema evolution](https://iceberg.apache.org/spec/#schema-evolution), [Protocol Buffers best practices](https://protobuf.dev/best-practices/dos-donts/#dont-change-field-type)).

**Consequence for Parison:** do not inherit another format's promotion table. Parison already has exact semantic domains and explicit tolerances. A change of Parison column type, decimal scale, timestamp rule, normalization, tolerance, key/group/measure role, null handling or comparison mode changes verification meaning and must be reported as a policy change, even if a storage system calls the underlying change compatible.

## Evolution model by change kind

`schema-evolution-v1` should be a strict, local JSON declaration independent of any source format. Each logical field has an immutable non-secret ID, a baseline physical name, a candidate physical name or explicit absence, and exactly one change kind. Names remain case-sensitive nonempty strings. IDs are stable policy identifiers, not inferred hashes of names or values.

| Change kind | What the declaration may say | Safe Parison treatment | What remains upstream |
|---|---|---|---|
| `unchanged` | one ID has the same physical name on both sides | ordinary one-to-one mapping | nothing |
| `renamed` | one ID has exactly one baseline name and one candidate name | compile to the existing one-to-one `column_mappings`; compare under one unchanged canonical column policy | deciding that the business meaning really survived the rename |
| `added` | a fresh ID is absent on baseline and has one candidate name | report addition and whether it is outside verification, excluded with rationale, or would change keys/values/groups/measures | backfilling or deriving baseline values |
| `removed` | a retired ID has one baseline name and is absent on candidate | report removal and every policy role it previously held; never silently drop it | retaining, archiving or deriving the lost value |
| `split` | one retired baseline ID names two or more fresh candidate IDs | report lineage only; no row projection and no claim that recombination is lossless | parsing, allocation, rounding, null propagation and recombination logic |
| `merged` | two or more retired baseline IDs name one fresh candidate ID | report lineage only; no row projection and no claim of invertibility | concatenation, precedence, aggregation, delimiter escaping and null propagation |

Only `unchanged` and `renamed` are safe value mappings in v1. They are total one-to-one functions over field identity and preserve the configured Parison semantic policy exactly. Added and removed fields are structural facts, not mappings. Split and merged fields are transformations even when an operator believes them to be reversible. They require upstream materialization into comparable scalar columns, followed by an ordinary Parison recipe over those materialized columns.

The declaration must reject cycles, duplicate IDs, duplicate physical names on one side, an ID appearing in multiple operations, name-only matches that conflict with IDs, reused retired IDs, and a `renamed` entry whose two physical names are equal. It must not inspect values to resolve ambiguity.

## Presence, null and default semantics

For every logical field, record these axes separately in the normalized model:

1. **presence:** `required` means the field must occur in every record; `optional` means it may be absent;
2. **nullability:** `non-null` or `nullable` governs the value when present;
3. **default metadata:** absent, or a canonical typed literal carried only for review;
4. **comparison role:** key, compared value, group, measure input, or excluded with a nonempty rationale.

The current CSV/JSONL/SQLite/Parquet readers expose fixed schemas and reject per-record missing fields, so the first contract should admit only `required` fields at the Parison input boundary. An optional source field must be materialized upstream into a required column with an explicit representation, or remain outside the comparison. This avoids introducing an internal missing-value state beside null.

Changing `non-null` to `nullable` widens admitted data and may turn later nulls into PASS, FAIL or INCONCLUSIVE depending on recipe policy. Changing `nullable` to `non-null` narrows the accepted domain. Neither is equivalent to a rename. A null default is still a default and must not collapse into nullability. A non-null default is especially consequential because it invents values for absent fields. `schema-evolution-v1` records default additions, removals and value changes in the diff but never applies them.

## Meaningful policy diff

The diff inputs should be two independently validated, fully expanded effective policies plus one independently validated evolution declaration. Recipe source formatting, object member order and omitted defaults have already disappeared at this level. The output is deterministic, contains both policy fingerprints, contains the evolution declaration fingerprint, and never reads datasets.

The normalized change list is ordered by a fixed category order and then logical field ID, never by authoring order. Each item contains only policy metadata:

- `path` in a small versioned policy-path vocabulary, not an unrestricted JSON Pointer;
- `kind`: unchanged, renamed, added, removed, split, merged or policy-modified;
- baseline and candidate logical IDs and physical names when disclosure permits;
- affected role: scope, identity, key, value, group, measure, parsing, normalization, null, tolerance, output sensitivity, mapping or exclusion;
- old/new canonical policy fragments, omitted from summary-safe rendering where they could reveal sensitive schema names or source conventions;
- `impact`: `none`, `input-only`, `verification-widened`, `verification-narrowed`, `meaning-changed`, `unsupported-transformation` or `unknown`;
- `classification`, stable reason code and a short non-authoritative explanation.

The diff must explicitly report changes outside schema evolution: snapshot/cutoff/filter/completeness, expected-empty, key and duplicate behavior, null equality, parsing/null tokens/delimiters, semantic type and scale, normalization, tolerance, aggregate operators and null behavior, multiset encoding/column order, input projection, output sensitivity and resource-bound fields that participate in the effective policy. No changed effective-policy field may disappear into a generic hash mismatch.

A second implementation must be able to reproduce the same normalized change list, classification and canonical bytes without source data. Unknown fields or future policy versions fail closed as `INCONCLUSIVE`; they are never ignored.

## `ACCEPT`, `DENY` and `INCONCLUSIVE`

These are **compatibility assessment labels**, not workflow approvals and not comparison outcomes. To avoid confusion, structured output should call the field `compatibility`, while documentation renders the values in capitals.

### `ACCEPT`

`ACCEPT` means every difference is mechanically accounted for by `schema-evolution-v1` and belongs to its closed safe set:

- an unchanged field has identical complete semantic policy and role;
- a declared one-to-one rename preserves logical ID and complete semantic policy and role;
- an added field is fresh, required and non-null at the Parison boundary, is explicitly excluded with a nonempty rationale on the candidate, and does not alter scope, identity, comparison columns, groups or measures;
- a removed field was explicitly excluded with a nonempty rationale on the baseline, is retired, and did not participate in scope, identity, comparison columns, groups or measures;
- only non-semantic authoring representation changed, which normally produces no effective-policy change at all.

An `ACCEPT` result still changes the policy fingerprint whenever mappings, exclusions or evolution identity change. It says the new policy is compatible with this narrow mechanical contract; it does not say the exclusion, rationale, field identity or deployment has been reviewed or approved.

### `DENY`

`DENY` means a validated declaration or policy contains a known incompatible change:

- removal of, or addition substituting for, a key, compared value, group or measure input;
- reuse of a retired field ID or physical field identity conflict;
- a semantic type, decimal scale, timestamp rule, normalization, tolerance, null-equality, identity, aggregate operator, measure-null, scope or comparison-mode change;
- required/optional, nullable/non-null or default semantics are used to make absent data compare as though supplied;
- an undeclared physical rename, missing required mapping, or unexpected compared field;
- an attempted split/merge projection inside Parison;
- a policy fingerprint claim that does not match either normalized effective policy.

`DENY` is not a veto on the migration. It means this pair cannot share the narrow compatibility bridge; the operator must use a newly reviewed policy and, where needed, materialize transformations upstream.

### `INCONCLUSIVE`

`INCONCLUSIVE` means the tool cannot establish either safe compatibility or a definite contract violation from validated metadata alone:

- a split or merge is declared as lineage but no row projection is attempted;
- an added/removed/defaulted/optional field has an unclear or future role;
- multiple plausible rename mappings exist, IDs are unavailable, or external schema metadata conflicts;
- a policy or evolution version, path or change kind is unknown;
- only a storage-level promotion or application-specific assertion supports equivalence;
- an upstream transformation receipt identifies artifacts but does not prove its business logic.

Invalid JSON, invalid schema, cycles, duplicate IDs and fingerprint mismatches are controlled input errors, not `INCONCLUSIVE` assessments. This distinction prevents malformed declarations from acquiring a neutral-looking result.

The overall result is `DENY` if any item is `DENY`; otherwise `INCONCLUSIVE` if any item is `INCONCLUSIVE`; otherwise `ACCEPT`. No label updates an approval state or changes an expected policy lock.

## Fingerprints and compatibility impact

Keep three identities separate:

1. baseline `policy_sha256`;
2. candidate `policy_sha256`;
3. `evolution_sha256`, SHA-256 over canonical UTF-8 JSON for the fully normalized `schema-evolution-v1` declaration.

The diff artifact also gets `policy_diff_sha256` over its version, the three identities, direction and ordered change records. It must not replace either policy fingerprint or create a transitive equivalence class. Two accepted edges `A -> B` and `B -> C` do not prove `A -> C`; the exact declaration and diff must be evaluated for that pair.

Any effective mapping, exclusion, field role, parsing rule, default metadata that participates in assessment, or evolution-contract identifier changes a fingerprint. Physical source paths, source bytes, values, samples, approvals, signatures and reviewer identities do not belong in these policy fingerprints. Existing recipes and results keep their released bytes; the new identities live in a new diff artifact and, only for a future opt-in comparison contract, an explicit policy field.

Current catalog history and run diff continue requiring exact policy equality. An `ACCEPT` policy diff must not make results gathered under different fingerprints trend-comparable: changed exclusions or mappings can change the observed population even when mechanically safe.

## Realistic workflows

### Database column rename

An orders migration renames `gross_amount` to `order_total` without changing values. The operator assigns one logical field ID, declares `renamed`, and keeps the exact decimal policy, scale and comparison role. Policy diff returns `ACCEPT`; record preflight and ordinary comparison still verify the supplied data. The label does not approve that the business meaning remained the same.

### Additive rollout metadata

The candidate adds `migration_batch`. It is outside verification and is explicitly excluded with a rationale. The diff reports a fresh ID, candidate-only presence, exclusion and a changed candidate policy fingerprint, then returns `ACCEPT`. If the new field becomes a key, filter or compared value, the result is `DENY` until a newly reviewed comparison policy is used.

### Field retirement

The baseline contains an already excluded legacy note and the candidate removes it. The declaration retires the ID and the diff returns `ACCEPT`. Removing a compared `status` or a group-by field returns `DENY`; Parison must not silently shrink verification scope.

### Name split

`customer_name` becomes `given_name` and `family_name`. The declaration records one-to-many lineage, but policy diff returns `INCONCLUSIVE` when no internal projection is requested. The producer materializes a reviewed `customer_name_for_verification` on the candidate, documents normalization upstream, and Parison compares that scalar under a separate explicit recipe. The evolution diff never claims that the transformation is reversible.

### Address merge and defaults

Several address fields become one formatted address, and missing country is filled with `US`. The merge algorithm, punctuation, precedence, locale and default all create values. An attempted Parison mapping is `DENY`; lineage-only review is `INCONCLUSIVE`. Upstream materialization plus an explicit newly reviewed policy is required.

## Threats and controls

1. **Rename guessing hides delete/add.** Similar names or matching samples can falsely join unrelated fields. Require explicit stable IDs and one-to-one declarations; never sample values for identity.
2. **Field-ID laundering.** An author can assert that meaning survived while reusing an ID. Report every policy-role and semantic change and classify contradictions as `DENY`; an ID is evidence of declaration continuity, not truth.
3. **Scope erosion through exclusions.** Reclassifying a compared field as excluded can manufacture compatibility. Only fields already excluded on their present side qualify for the narrow added/removed `ACCEPT` cases.
4. **Default manufacture.** Filling missing fields can create false agreement. Record defaults as metadata only and never execute them.
5. **Split/merge ambiguity.** Transformations may be lossy, non-invertible, locale-sensitive or order-sensitive. Keep them upstream and return `INCONCLUSIVE` for lineage-only declarations or `DENY` for attempted projection.
6. **Directional confusion.** Forward and backward compatibility can differ. Bind canonical bytes to explicit baseline-to-candidate direction; never silently reverse a declaration.
7. **Hash equivalence overclaim.** A bridge could be mistaken for equal policies or approval. Preserve both policy hashes, avoid transitive equivalence, and state the narrow assessment meaning in every rendering.
8. **Schema disclosure.** Physical names, defaults, filters and rationales can be sensitive. Full local output may contain reviewed policy metadata; summary-safe output reports counts, impact classes, reason codes and fingerprints but no names, paths, values or policy fragments.
9. **Parser/version drift.** New recipe or evolution fields could be ignored by an old tool. Strict schemas reject unknown members; fingerprints bind contract versions; golden canonical fixtures gate upgrades.
10. **Unbounded diff input.** Large declarations or strings can exhaust resources. Apply existing bounded JSON depth, size and collection limits before normalization.

## Non-goals

- schema discovery, rename inference or similarity scoring;
- applying migrations, defaults, backfills, casts, splits, merges or repair;
- proving business equivalence, extraction truth, reversibility or upstream transformation correctness;
- treating optional, absent, null and default as interchangeable;
- importing Avro, Protobuf, Iceberg, registry or database compatibility rules as Parison policy;
- comparing nested structures or adding an expression language;
- approving policy, recording reviewer authority, signing artifacts or authorizing cutover;
- making evidence from unequal policy fingerprints directly trend-comparable;
- changing released recipe/result schemas, canonical bytes, bundles, exit codes or catalog behavior in place;
- contacting schema registries, databases or remote orchestration services.

## Narrow versioned recommendation

Introduce a data-free **`schema-evolution-v1` declaration plus `policy-diff-v1` artifact** before any runtime schema-evolution comparison.

The first implementation should:

1. validate immutable logical IDs and only the six declared change kinds;
2. compile only `unchanged` and one-to-one `renamed` entries to the existing mapping model;
3. classify already-excluded additive/removal changes narrowly, report split/merge as lineage without projection, and reject attempted transformations;
4. diff two fully expanded effective policies through a closed versioned path vocabulary;
5. emit deterministic per-change impact and `ACCEPT`/`DENY`/`INCONCLUSIVE` compatibility plus the four fingerprints;
6. provide full local and summary-safe renderings without reading source datasets;
7. leave comparison execution, catalog trends and approval workflow unchanged.

Do not begin with a generic schema graph, compatibility registry or transformation DSL. A strict declaration compiler and semantic policy diff deepen the existing mapping and fingerprint seams while keeping data computation upstream.

## Checkable promotion gate

Promote this research into a released contract only when all of the following pass:

- strict JSON Schemas and golden canonical-byte fixtures cover direction, IDs, unchanged/renamed/added/removed/split/merged operations, retirement and every stable failure;
- two independent implementations produce identical normalized declarations, ordered change records, classifications, reason codes, `evolution_sha256` and `policy_diff_sha256` for the golden corpus;
- exhaustive fixtures prove that only one-to-one unchanged/rename mappings and already-excluded additive/removal cases can return `ACCEPT`;
- compared/key/group/measure additions or removals, undeclared renames, ID reuse, semantic-policy changes, default application and attempted split/merge projection return `DENY`;
- ambiguous identities, lineage-only split/merge, unknown future semantics and unsupported storage assertions return `INCONCLUSIVE`, while malformed declarations remain controlled errors;
- required/optional, nullable/non-null, absent/default/null and role changes are independently represented and cannot collapse during normalization;
- every field of every released effective policy version is either compared through the closed path vocabulary or causes fail-closed `INCONCLUSIVE`; mutation tests prove no semantic field is silently ignored;
- summary-safe fixtures contain no source paths, physical/logical names, values, defaults, filters, rationales or policy fragments;
- existing `policy_sha256` golden vectors, recipes, bundles, result JSON, exit codes and exact-policy catalog history/diff behavior remain byte-compatible;
- the implementation reads no datasets, performs no network access, applies no transformations or defaults, changes no approval state and does not authorize comparison or cutover;
- built-wheel CI passes on Python 3.11–3.14 across Linux, macOS and Windows, and `make check` is green.

Until this gate passes, use existing explicit one-to-one `column_mappings` for reviewed renames, materialize all other evolution upstream, and treat unequal policy fingerprints as incomparable rather than interpreting their hash difference.
