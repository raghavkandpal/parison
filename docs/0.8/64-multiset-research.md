# Multiset comparison research for Parison 0.8

Date: 9 October 2026

## Recommendation

Make 0.8 an **exact keyless multiset comparison** release. A multiset recipe compares complete canonical rows without assigning identity to any column. It proves that every distinct row shape occurs with the same multiplicity on both sides, so duplicate rows are evidence rather than an identity error.

This fills the product gap left intentionally by the existing modes:

- keyed comparison proves row equality when a stable unique key exists;
- aggregate comparison proves declared group coverage and measures, but explicitly cannot prove row equality;
- multiset comparison proves whole-row equality when order is irrelevant and no stable key exists.

This is a wider feature slice, not one more operator: it needs a versioned recipe and result, record preflight, execution, deterministic duplicate-aware evidence, terminal and HTML reporting, drafting, examples, performance limits, bundle verification and release oracles. It should remain one local deterministic workflow rather than grow into a query language or UI.

## Semantic basis

### Equality is multiplicity equality

SQL's `EXCEPT ALL` supplies a precise model. PostgreSQL defines the left surplus for a row seen `m` times on the left and `n` times on the right as `max(m-n, 0)`; `INTERSECT ALL` retains `min(m,n)` copies ([PostgreSQL `SELECT`](https://www.postgresql.org/docs/current/sql-select.html)). Python's standard-library `Counter` is explicitly a bag/multiset whose elements are keys and whose values are counts; subtraction keeps positive count differences and intersection keeps minimum counts ([Python `collections.Counter`](https://docs.python.org/3/library/collections.html#collections.Counter)).

For canonical row `r`, define baseline and candidate multiplicities `B(r)` and `C(r)`:

```text
common(r)         = min(B(r), C(r))
baseline_only(r)  = max(B(r) - C(r), 0)
candidate_only(r) = max(C(r) - B(r), 0)
```

The run passes only when both inputs are complete and `B(r) = C(r)` for every canonical row. Conservation must hold independently on both sides:

```text
baseline_rows  = common_occurrences + baseline_only_occurrences
candidate_rows = common_occurrences + candidate_only_occurrences
```

Distinct-row counts are useful diagnostics, but occurrence counts determine the outcome. Set comparison would be wrong because it would turn `[A, A]` versus `[A]` into a pass.

### Whole-row identity must be exact

Every included canonical column participates in row identity after the existing explicit type parsing, side mapping and normalization policies. Column order in the container is irrelevant; canonical recipe order defines the tuple. Excluded columns remain declared exclusions with rationale.

Multiset-v1 should allow exact comparison only. Numeric tolerance is not an equivalence relation suitable for grouping rows: several candidate values can fall within tolerance of several baseline values, making counts depend on a pairing algorithm. Approximate assignment, fuzzy matching and row-position pairing are different product decisions.

Null must have one explicit reflexive rule for row identity: null equals null in the same canonical column, while null differs from every non-null value. PostgreSQL's duplicate elimination likewise treats null values as equal ([PostgreSQL select lists](https://www.postgresql.org/docs/current/queries-select-lists.html#QUERIES-DISTINCT)). Empty string remains distinct from null. Parison's existing rejection of non-finite numbers should continue; Python's JSON encoder otherwise permits non-standard `NaN` and infinity unless `allow_nan=False` ([Python `json`](https://docs.python.org/3/library/json.html#json.dump)).

### Canonical row keys belong to Parison, not an embedded engine

Do not delegate equality to a database's coercion or collation rules. SQLite can coerce text and numeric values before comparison, has type-dependent ordering, and offers multiple text collations ([SQLite datatypes and comparison](https://www.sqlite.org/datatype3.html)). Those rules are not Parison's typed contract.

Use the existing parsed typed tuple as the semantic value. If a byte key is needed for disk storage or deterministic ordering, specify a collision-free tagged encoding with column boundaries and canonical encodings for null, boolean, integer, scaled decimal, string, date and timestamp. Do not use delimiter concatenation, `repr`, a digest without collision resolution, or JSON's defaults as row identity.

## Proposed 0.8 contract surface

Use `recipe_version: 3` with `comparison_mode: "multiset"`; do not make recipe-v1 keys optional or reinterpret recipe-v2 aggregates.

A reviewed recipe declares:

- the existing complete scope, mappings, input parsing, normalization, exclusions, sensitivity and resource policies;
- a nonempty canonical `columns` object, all of whose entries participate in exact row identity;
- no `keys`, `group_by`, measures, tolerances or user expressions;
- null-equals-null as the fixed multiset identity rule.

The canonical result should report at least:

- baseline, candidate and common occurrence counts;
- baseline-only and candidate-only occurrence counts;
- total distinct row shapes per side;
- distinct shapes with a baseline or candidate surplus;
- complete input digests, effective-policy fingerprint and limit evidence.

Summary sensitivity publishes counts only. Raw sensitivity may publish a bounded sample shaped as `{row, baseline_count, candidate_count, classification}`, sorted by canonical row encoding. One sample item represents a row shape and its multiplicities, not one entry repeated for every surplus occurrence. SQL does not guarantee result order without `ORDER BY` ([PostgreSQL `SELECT`](https://www.postgresql.org/docs/current/sql-select.html#SQL-ORDERBY)); Parison therefore must sort evidence explicitly rather than inherit hash, scan or partition order.

Outcome boundaries should preserve current meanings:

- `PASS`: complete inputs and no one-sided occurrences;
- `FAIL`: complete inputs with any multiplicity difference;
- `INCONCLUSIVE`: an unexpected both-empty scope or a policy condition that prevents the intended comparison;
- `ERROR`: invalid recipe/input, parsing failure, mutation, resource exhaustion or internal failure.

An asymmetric empty comparison is a complete `FAIL`. Two empty inputs pass only when `scope.expected_empty` is true, matching the established strict empty-scope policy.

Drafting must require `draft-recipe --multiset`; Parison must never switch modes because key suggestion fails or duplicate keys appear. The draft can map exact shared names and infer existing safe scalar types, but a person must review exclusions and normalization because both change whole-row identity.

## Execution and resource choices

### Recommended first implementation: counted typed rows with a hard cardinality bound

Count each canonical typed row in a dictionary/`Counter`, one side at a time or as signed deltas, while retaining independent row totals and input digests. Apply an explicit `--max-distinct-rows` bound before accepting a new row shape. This is the smallest engine that directly implements the contract, has no new dependency and reuses the 0.7 pattern of bounding group cardinality.

The bound is on distinct row shapes, not total rows: ten million copies of one row need one counter entry, while one million unique wide rows are expensive. Publish the configured bound and observed cardinalities. Exceeding it is `ERROR`; never sample and return `PASS`.

### Spill-backed alternative: explicit SQLite scratch database

The standard-library SQLite binding could store the collision-free canonical row bytes as a `BLOB PRIMARY KEY` and update multiplicities with `INSERT ... ON CONFLICT DO UPDATE`; SQLite documents UPSERT as updating or omitting an insert when a uniqueness constraint conflicts ([SQLite UPSERT](https://www.sqlite.org/lang_upsert.html)). A file-backed scratch database can move the count index out of Python heap, and SQLite documents temporary files used by sorting, grouping and distinct processing ([SQLite temporary files](https://www.sqlite.org/tempfiles.html)).

This is a prototype candidate, not the default 0.8 commitment. It adds scratch lifecycle, disk limits, cancellation, cleanup, write-amplification and cross-platform performance work. Its SQL columns must store opaque canonical bytes, not independently typed values, to avoid SQLite affinity and collation changing equality. Promote it only if a measured spike beats the in-memory engine on a declared high-cardinality case without semantic drift.

DuckDB also documents spill-to-disk support for grouping and sorting, but notes blocking operators and cases where memory allocations bypass the configured buffer-manager limit ([DuckDB workload tuning](https://duckdb.org/docs/current/guides/performance/how_to_tune_workloads), [DuckDB out-of-memory guidance](https://duckdb.org/docs/current/guides/performance/oom)). Adding a required engine dependency for this slice is not justified before the standard-library designs fail a measured need.

## Alternatives considered

| Slice | Value | Why not the 0.8 focus |
| --- | --- | --- |
| More aggregate operators | Adds averages, distinct counts or quantiles | Deepens 0.7 but still cannot prove row equality; expressions and approximate algorithms multiply semantics without closing a core mode gap. |
| Report filtering and export | Improves investigation after a run | Valuable follow-up, but narrower than a release-defining comparison capability and risks putting raw data into more artifacts. |
| Remote inputs/connectors | Reduces manual export work | Expands credentials, network failure, mutation and provenance boundaries while comparison semantics remain unchanged. |
| Local interactive UI | Improves discoverability | Adds a second interface and security surface before the keyless equality workflow exists. The static report can expose the new evidence first. |
| Spill engine as the headline | Extends scale | Scale without frozen equality and result contracts creates engine-driven semantics. Prove the bounded reference implementation first. |

Exact multiset comparison is the strongest fit: it is orthogonal to both released modes, answers a previously documented user shape, reuses the local typed-input and evidence pipeline, and creates a clear three-mode product story.

## Verification gates

The implementation roadmap should require:

1. hand-audited duplicate cases such as `[A, A, B]` versus `[A, B, B]`, with both occurrence and distinct-shape conservation checked;
2. row, column and partition reordering oracles proving order independence;
3. null/empty-string, leading-zero string, normalized-collision, decimal-scale, timestamp and Unicode cases inherited from the typed contract;
4. adversarial canonical-encoding tests proving boundaries and type tags cannot collide;
5. summary-output checks proving no row values or canonical row keys escape;
6. deterministic raw samples across input orders and Python processes;
7. mutation, cancellation, unexpected-empty and cardinality-limit outcomes with schema-valid bundles;
8. a benchmark matrix crossing total rows, distinct-row ratio, row width, duplicate skew and mismatch rate;
9. optional SQLite-spill measurements against the same oracle before any backend decision;
10. installed-wheel smoke tests for draft, validate, preflight, compare, publish and verify in all three modes.

## Non-goals for 0.8

- tolerant or fuzzy row assignment;
- ignoring multiplicity or silently deduplicating inputs;
- subset, containment or bounded-surplus policies;
- choosing “representative” duplicates by input order;
- nested values, custom expressions or user code;
- automatic mode fallback from invalid keyed comparison;
- remote inputs, a server or a new UI;
- an unqualified larger-than-memory claim.

The stop condition is simple: if a design cannot explain which exact canonical row gained or lost how many occurrences independent of input order, it is not multiset-v1.
