# Semantic scalar projection contract

Status: **implemented 1.1 contract**

## Purpose

`semantic-scalar-v1` makes the raw-value seam shared by CSV/TSV, JSON Lines, SQLite and Parquet explicit. It is an opt-in input projection before the released keyed-v1, aggregate-v1 or multiset-v1 comparison contract:

```json
"input_projection": "semantic-scalar-v1"
```

Omitting the field preserves the released recipe-version 1–3 reader behavior and policy fingerprints. Selecting it changes the effective-policy fingerprint, but not the recipe version, comparison contract, canonical row encoding, result schema, exit code or bundle readability.

PASS still means that the supplied rows agree under the reviewed projection and comparison policy. It does not establish equivalent source schemas, extraction truth, snapshot coordination, completeness or cutover approval.

## Projection order

For every configured column, Parison:

1. identifies the exact source column through the reviewed mapping;
2. applies only format-level decoding and configured delimited-text null tokens;
3. admits or rejects the raw scalar according to this contract;
4. parses the admitted scalar into the existing recipe type;
5. applies configured string normalization;
6. runs the unchanged comparison contract.

There is no generic stringification, type inference, repair or fallback conversion.

## Admitted representations

Native null is admitted for every recipe type. Other raw values are admitted as follows:

| Recipe type | Admitted raw representations | Rejected examples |
|---|---|---|
| `string` | text only | integer, float, decimal, boolean, date, timestamp, bytes, nested value |
| `integer` | integer lexical text or a non-boolean integer in signed 64-bit range | float, decimal, boolean, empty text, overflow |
| `decimal` | numeric lexical text, non-boolean integer or exact decimal within configured scale | binary float, boolean, empty text, excessive scale, non-finite value |
| `float` | finite numeric lexical text, non-boolean integer or finite binary float | decimal, boolean, empty text, NaN, infinity |
| `boolean` | native boolean or exact lowercase `true`/`false` text | `0`, `1`, uppercase spellings, truthy values, empty text |
| `date` | ISO date text or a native date that is not a datetime | datetime, epoch number, locale date, empty text |
| `timestamp` | ISO timestamp text with an explicit offset or a timezone-aware native datetime | naive datetime, date, epoch number, excess precision, empty text |

Configured CSV/TSV null tokens become native null before this table is applied. An unconfigured empty text value is not null under `semantic-scalar-v1`; it is valid only for a string column. No implicit Unicode normalization, trimming or case folding occurs beyond the existing reviewed string-normalization policy.

## Format rules

### CSV, TSV and JSON Lines

Existing UTF-8, schema, duplicate-key, ragged-row, nested-value, non-finite and decoded-size controls remain unchanged. JSON numbers retain their lexical spelling until semantic parsing; JSON booleans retain boolean meaning even though the reader's internal scalar handoff uses the canonical lowercase spelling.

### SQLite

The selected object must remain an ordinary table in a regular, non-symlink, journal-free database opened read-only. BLOB values remain unsupported. SQLite storage classes are authoritative per value: INTEGER is not boolean or string, and REAL is never exact decimal. The projection does not interpret declared affinity, arbitrary SQL, row order, date conventions or application sentinels.

### Parquet

Before materializing rows, Parison validates the complete file schema, including excluded columns. The closed scalar dtype set is null, UTF-8 string, boolean, signed/unsigned integer, finite float, decimal, date and datetime. Binary, list, array, struct, map, time, duration, categorical/enum, object, extension and unknown types fail closed.

Configured columns must also match the representation table. Datetime values require a declared timezone and microsecond-or-coarser precision. Nanosecond timestamps are rejected before Python conversion so sub-microsecond differences cannot compare equal through truncation. Unsigned integers remain subject to the signed 64-bit semantic range.

Text timestamp precision is checked by the projection before the standard-library parser for every admitted date-time separator. Recipes that omit `input_projection` retain the released legacy parser behavior.

Parquet support remains optional and pinned. A parser upgrade requires the projection corpus and built-wheel matrix to pass before promotion.

## Schema and partition rules

Exact nonempty source names, reviewed mappings and exclusions remain authoritative. Missing columns, unexpected columns, duplicate names, inserted all-null columns, positional matching and field inference are not projection behavior. Partition directories retain one-format, immediate-file, deterministic-order and consistent-schema requirements; every Parquet partition is checked independently.

Record order is not semantic for keyed, aggregate or multiset comparison. SQLite scan order is undefined and cannot affect deterministic output.

## Evidence and disclosure

The selected projection is included in the effective policy and its fingerprint and is repeated in the full result policy. Installed editor schemas admit only the exact identifier `semantic-scalar-v1`.

Summary-safe output continues to exclude source paths, keys, values and discrepancy samples. Projection errors name the configured field/type class needed for diagnosis but never echo the rejected value. Input digests, runtime versions and the existing parser/runtime evidence remain unchanged.

## Stable failures

The following fail before a PASS can be produced:

- a raw scalar outside the admitted representation for its configured type;
- an integer outside the signed 64-bit range;
- a non-finite number or decimal exceeding configured scale;
- an empty non-string field not selected by an explicit null token;
- a timezone-naive or nanosecond Parquet datetime;
- any unsupported Parquet dtype, including one in an excluded column;
- every existing malformed, unsafe, changed-during-read or resource-limit condition.

Record validation reports invalid rows and fields without values. Direct comparison stops with a controlled input error. No partial comparison can produce PASS.

## Non-goals

- automatic schema or type inference;
- numeric/string/boolean convenience coercion;
- locale-aware numbers or dates, epoch interpretation or timezone guessing;
- nested JSON or Parquet comparison;
- file conversion, repair, query execution or upstream extraction;
- source lexical preservation after semantic parsing;
- an order-sensitive comparison mode;
- any change to released recipes that omit `input_projection`.

## Compatibility gate

Promotion requires:

1. admitted equivalents converge across CSV/TSV, JSON Lines, SQLite and supported Parquet dtypes in keyed, aggregate and multiset modes;
2. ambiguous, lossy, nested, binary, non-finite, overflow, empty and temporal-precision cases fail closed with stable diagnostics;
3. the Parquet schema is rejected before row materialization when any column is unsupported;
4. legacy effective-policy hashes and the released compatibility corpus remain unchanged and readable;
5. installed JSON Schemas validate both legacy and opt-in recipes;
6. built wheels pass on Python 3.11–3.14 across Linux, macOS and Windows, with optional-Polars skips only when Polars is absent;
7. `make check` passes and no reader performs network access, credentials, signing, repair, writes or remote orchestration.
