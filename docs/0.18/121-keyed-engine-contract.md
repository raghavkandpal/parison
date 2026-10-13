# SQLite keyed execution contract

Date: 13 October 2026

Status: **accepted for implementation**

## Selection and scope

The default keyed-v1 engine remains `memory`. SQLite execution is an explicit
opt-in through `parison compare --engine sqlite`; suite-v2 selection is a later
0.18 slice. Selecting SQLite for keyed-v1 or multiset-v1 is valid. Aggregate-v1
remains memory-only.

Engine choice is operational policy. It does not change recipe semantics,
effective-policy fingerprints, comparison classifications, evidence sensitivity
or publication rules. Parison never selects SQLite from input size.

```console
parison compare --recipe recipe.json --baseline old.csv --candidate new.csv \
  --engine sqlite --max-temp-bytes 5000000000 --output run
```

Use `--temp-directory` to select an existing trusted local parent for the
private scratch directory. Omitting it uses the platform temporary directory.

## Semantic ownership

Parison parses, normalizes and compares every value under the existing keyed-v1
contract. SQLite stores opaque Parison-owned encodings and JSON renderings; its
type affinity, numeric coercion, collation and null rules never define key
identity, value equality, tolerance or evidence order.

Key identity uses an injective typed, length-prefixed encoding of the normalized
key components in recipe key order. The encoding distinguishes null, boolean,
integer, decimal, float, string, date and timestamp values and reuses the scalar
representation already specified by `typed-length-prefixed-v1`. The encoding is
an execution detail and is not added to the keyed-v1 result policy.

Each side records the total row count, distinct keys, null-key row count and keys
seen more than once. A duplicate or null key produces the same INCONCLUSIVE
result and bounded problem text as the memory engine. Invalid identity never
becomes a database uniqueness error and never produces PASS.

For valid identity, the engine performs the existing symmetric-v1 field
classification in Parison code. Missing keys, exact rows, rows within tolerance,
rows with required differences, field counts and discrepancy counts are
identical to memory execution.

## Determinism and equivalence

The memory engine is the semantic oracle. For the same recipe, ordered input
snapshots and limits, both engines must produce byte-identical canonical result
JSON after removing only these documented operational differences:

- `runtime.execution_engine`;
- SQLite-only `runtime.temporary_bytes`; and
- SQLite-only `resource_limits.max_temp_bytes`.

All other fields—including outcome, completeness, problems, counts, policy and
recipe digests, input metadata and bounded discrepancy evidence—must match.
Summary-sensitive output contains no key or record values from the scratch
database.

Raw evidence retains the existing keyed-v1 order: baseline-only keys,
candidate-only keys, then common-key field discrepancies; keys use the existing
tuple-of-string ordering and fields use recipe column order. SQLite query order
is never accepted as evidence order unless it is driven by an opaque
Parison-owned ordering token proven equivalent to that rule.

## Storage and cleanup

Each invocation creates one new private directory and disposable SQLite database.
`--temp-directory` selects only an existing non-symlink parent and never a
resumable database. The database may contain normalized keys and complete row
values, so its filesystem is sensitive even when published evidence is summary
only. Parison provides neither temporary-file encryption nor secure erasure.

The implementation uses the existing SQLite spill lifecycle: journaling is
disabled, the database page ceiling enforces `--max-temp-bytes`, the connection
closes before cleanup, and the private directory is removed after success,
handled error or Ctrl-C. An uncatchable process or host termination can leave an
orphan for the operator to remove.

Publication remains atomic and no-overwrite. A temporary-storage, disk, parse,
row-limit or input-mutation failure cannot publish a complete PASS, FAIL or
INCONCLUSIVE bundle. Handled ERROR and INTERRUPTED bundles retain the selected
engine and `max_temp_bytes` without referring to the removed scratch path.

## Limits and observability

Existing input-byte, decoded-byte and per-input row limits apply unchanged.
`max_temp_bytes` limits only the SQLite database, not filesystem metadata, input
files, Python allocations or the final evidence bundle. A ceiling too small to
initialize the database and a database-full condition are controlled errors.

Successful SQLite execution records `runtime.execution_engine = "sqlite"` and
the final database size as `runtime.temporary_bytes`. With journaling disabled
and a disposable monotonically growing database, that size is the supported
temporary-storage measurement. Memory execution records
`runtime.execution_engine = "memory"` and does not report temporary bytes.

## Acceptance oracle

Cross-engine tests cover PASS, missing keys, exact and tolerance differences,
null values, column mappings, raw and summary sensitivity, empty inputs, null
keys and duplicate keys. Tests compare canonical result bytes after the three
operational exclusions above and verify cleanup after success, controlled
failure and interruption.

Implementation remains experimental until installed-wheel CI passes on Python
3.11–3.14, macOS and Windows and machine-specific benchmarks demonstrate lower
peak memory on a high-cardinality keyed case without semantic drift.

## Non-goals

- Automatic engine selection or a changed keyed-v1 schema.
- Aggregate spill, remote databases, resume or preservation of scratch state.
- SQLite-defined equality, tolerance, ordering or repair.
- A universal capacity claim derived from one benchmark machine.
