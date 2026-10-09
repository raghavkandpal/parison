# Aggregate-v1 contract research

Date: 8 October 2026

This pass checks the planned 0.7 aggregate contract against primary documentation. It is deliberately narrow: the findings below affect semantics, reproducibility, result shape or disclosure boundaries in the [0.7 roadmap](58-roadmap.md).

## Findings

### Nulls and counts need operator-level definitions

PostgreSQL documents `count(*)` as the number of input rows, while `count(expression)` counts non-null inputs. It defines `sum` over non-null inputs and notes that, except for `count`, aggregates return null when no rows are selected; notably, an empty sum is null rather than zero ([PostgreSQL aggregate functions](https://www.postgresql.org/docs/current/functions-aggregate.html)). Polars deliberately differs: its sum returns zero when there are no non-null values ([Polars `sum`](https://docs.pola.rs/api/python/stable/reference/expressions/api/polars.sum.html)).

This makes the roadmap's single `count` name and “every input row is counted once per declared measure” invariant ambiguous. Under `null: ignore`, an input row may contribute to the group row count but not to a measure.

**Recommendation:** define aggregate-v1 `count` as a no-source row count, equivalent to `count(*)`. Keep `group_counts` as the auditable per-group row conservation value. Do not add a non-null-value count in 0.7 unless it has a distinct operator name. Replace the invariant with: every complete input row contributes exactly once to one group count; for every measure, `contributing_count + ignored_null_count = group_count`, while `reject` makes any null a preflight failure. Never inherit the host engine's empty-sum behavior.

### Empty global and grouped inputs are different shapes

PostgreSQL treats aggregates without `GROUP BY` as one group containing all selected rows, whereas `GROUP BY` condenses only rows that exist into groups ([PostgreSQL `SELECT`, `GROUP BY`](https://www.postgresql.org/docs/current/sql-select.html)). Combined with the aggregate rules above, an empty global input has one aggregate result (`count = 0`; `sum`, `min` and `max` have no value), while an empty grouped input has no groups.

**Recommendation:** specify these shapes directly:

- empty `group_by` always emits exactly one global group, including for zero rows;
- non-empty `group_by` emits zero groups for zero rows;
- `sum`, `min` and `max` with zero contributing values use an explicit `no_value` state, not numeric zero and not a missing field;
- two complete inputs with identical empty shapes may PASS; one empty and one non-empty grouped input fails group coverage;
- all-null under `ignore` has `no_value` plus a non-zero ignored count, so it remains distinguishable from an empty input.

This should be covered by separate empty-global, empty-grouped and all-null fixtures. A JSON `null` can encode `no_value`, but the schema and prose must say it is an aggregate state rather than an input null.

### Group nulls should not silently acquire SQL semantics

SQL grouping forms one output row for each shared set of grouping values, but null comparison and ordering have context-specific rules; PostgreSQL, for example, exposes explicit `NULLS FIRST`/`LAST` ordering and `IS NOT DISTINCT FROM` semantics ([PostgreSQL `SELECT`](https://www.postgresql.org/docs/current/sql-select.html), [PostgreSQL comparison functions](https://www.postgresql.org/docs/current/functions-comparison.html)). Importing those rules implicitly would make group identity harder to review across CSV, JSON, SQLite and Parquet.

**Recommendation:** reject null `group_by` values in aggregate-v1 during preflight. This matches the roadmap's “exact, typed” group identity and its existing invalid-group boundary. If null groups are supported later, they need an explicit equality and canonical-order contract rather than whichever input engine happens to provide.

### `Decimal` alone does not guarantee order-independent sums

Python's `Decimal` represents decimal inputs exactly, but arithmetic runs under a context with precision, rounding, exponent limits and traps. The official documentation demonstrates that insufficient precision can break associativity, so regrouping or partitioning the same values can change a rounded sum ([Python `decimal`](https://docs.python.org/3/library/decimal.html#floating-point-notes)). Arrow decimal types also carry explicit precision, scale and bit width ([Arrow columnar format](https://arrow.apache.org/docs/format/Columnar.html)).

The existing roadmap promise—“use `Decimal` arithmetic”—is therefore insufficient for the stated row- and partition-reordering oracle.

**Recommendation:** because Parison decimals already have a declared scale, accumulate each parsed decimal as an unbounded Python integer coefficient at that scale, then render one canonical decimal at the boundary. Accumulate integers as Python integers. This is exact, associative, independent of row order and simpler than calculating a safe `decimal.Context` for every group. Reject values that cannot be represented at the declared scale before aggregation. Apply tolerance only when comparing the two completed totals, never during accumulation.

### Group coverage is a first-class comparison, not a measure

`GROUP BY` produces a separate aggregate result for every group present in the input ([PostgreSQL `SELECT`, `GROUP BY`](https://www.postgresql.org/docs/current/sql-select.html)). Consequently, totals alone cannot establish equivalent grouped coverage: offsetting missing groups can preserve a global count or sum.

**Recommendation:** compare canonical group-key sets before measures and publish disjoint counts for baseline-only, candidate-only and common groups. Evaluate measures only for common groups. Any one-sided group produces FAIL even when global conservation totals match. Add an adversarial fixture with equal global totals but offsetting group membership. Deterministic output should sort typed group tuples by a contract-defined type-aware order; it must not depend on scan/hash iteration. Python JSON can sort object keys when requested, but JSON object keys are strings, so structured group tuples should remain array values rather than be coerced into object keys ([Python `json`](https://docs.python.org/3/library/json.html#json.dump)).

### Aggregate output remains potentially sensitive

Removing raw records and group keys from summary mode reduces exposure but does not make aggregate evidence anonymous. The U.S. Census Bureau describes safeguards applied before publishing statistics and specifically uses suppression, coarsening and other controls to prevent learning about a person from a statistic ([Census statistical safeguards](https://www.census.gov/about/policies/privacy/statistical_safeguards.html)); its disclosure guidance identifies very small cell counts as a risk ([FSRDC disclosure handbook](https://www.census.gov/content/dam/Census/programs-surveys/sipp/methodology/FSRDC%20Disclosure%20Avoidance%20Methods%20Handbook%20v.4.pdf)).

**Recommendation:** preserve the current summary/raw boundary, but state that aggregate results are reconciliation evidence, not a privacy mechanism. Summary mode should publish only total group-classification and measure-classification counts—no group keys, per-group counts or per-group measures. Raw mode may include the already-planned bounded deterministic samples, must retain the sensitive label, and should record the configured sample bound in the policy fingerprint. Do not add automatic small-cell suppression in 0.7: it would make reconciliation incomplete and could turn PASS into a sampled claim.

## Roadmap impacts

Before implementation, update the normative-contract slice to require:

1. distinct global-empty, grouped-empty and all-null states;
2. row-count semantics for `count` and the conservation equation for contributing versus ignored values;
3. rejection of null group keys;
4. integer-coefficient accumulation for scaled decimals instead of context-dependent `Decimal` reduction;
5. canonical type-aware group ordering and structured group-key serialization;
6. group-set comparison before common-group measures;
7. an explicit warning that aggregate output is not de-identified output.

Add fixtures for an all-null ignored measure, equal global totals with offsetting groups, decimal cancellation under multiple row orders, and both forms of empty input. These changes narrow ambiguity without adding operators, dependencies or a general query layer.
