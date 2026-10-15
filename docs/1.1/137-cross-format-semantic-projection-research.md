# Deterministic cross-format semantic projection research

Date: 14 October 2026

Status: **research recommendation**

## Precise question and boundary

What is the smallest versioned projection that can make one reviewed Parison recipe mean the same thing when its two row sources are CSV, JSON Lines, an ordinary SQLite table, or Parquet?

This is a reader-to-existing-row-model question. It does not propose a new comparison mode, infer a schema, declare two source types equivalent, or convert files. PASS must continue to mean that the selected records agree under explicit recipe policy. It cannot mean that the source systems used equivalent schemas, that an export was complete, or that a lossy source representation was repaired.

The repository already permits mixed formats and sends each raw value through the recipe's `string`, `integer`, `decimal`, `float`, `boolean`, `date`, or timezone-aware `timestamp` parser ([current parser](../../src/parison/core.py), [JSON Lines contract](../0.2/23-json-lines-contract.md), [SQLite contract](../0.2/24-sqlite-contract.md)). The open issue is therefore not whether values can happen to compare today. It is whether the accepted source domains and conversions are narrow, documented, stable across the supported platform matrix, and protected from reader upgrades.

All external sources are primary specifications or official implementation documentation and were accessed **14 October 2026**.

## What the current readers expose

| Reader | Current repository behavior | Values presented to the recipe parser | Important information already lost or left ambiguous |
|---|---|---|---|
| CSV/TSV | Python `csv.DictReader`, UTF-8 text, reviewed one-character delimiter, strict syntax, fixed nonempty unique headers, ragged-row rejection, and side-specific exact null tokens. | Every non-null field is a Python `str`; a matching null token becomes `None`. Empty text remains `""` until non-string recipe parsing, where it becomes null. | CSV supplies fields, quoting and record boundaries, not semantic types. RFC 4180 treats spaces as field content and asks records to have the same field count; it defines no null, number, boolean or time type ([RFC 4180](https://www.rfc-editor.org/rfc/rfc4180.html)). Quoting is not retained as a semantic distinction after parsing. |
| JSON Lines | One UTF-8 JSON object per physical line; duplicate/empty keys, blank lines, non-objects, nested values, non-finite constants and changing field sets are rejected. `parse_int=str` and `parse_float=str` preserve accepted JSON number spelling; booleans become lowercase strings. | `None`, `str`, or the strings `"true"`/`"false"`; JSON number tokens also arrive as their original decimal lexical text. | JSON string versus number versus boolean is partly erased before recipe parsing. JSON itself distinguishes null, boolean, number and string, forbids NaN/Infinity, allows implementations to limit numeric range/precision, and does not make member order portable ([RFC 8259](https://www.rfc-editor.org/rfc/rfc8259.html)). Array/object values are deliberately outside Parison's row domain. |
| SQLite | A read-only `SELECT *` over one verified ordinary table through Python `sqlite3`; the reader rejects BLOBs, views, symlinks and active journal sidecars. | Python `None`, `int`, `float`, or `str`; `bytes` is rejected. A single column may expose different Python types in different rows. | Declared affinity is not a row type. SQLite columns can hold different storage classes, NUMERIC affinity can change lexical inputs (for example `3.0e+5` to integer `300000`), and REAL is binary64 ([SQLite datatypes](https://www.sqlite.org/datatype3.html)). `SELECT *` has no `ORDER BY`, so row order is undefined ([SQLite SELECT](https://www.sqlite.org/lang_select.html)). |
| Parquet | Pinned optional Polars 1.44.2; schema through `scan_parquet`, row count then full `read_parquet`, followed by `iter_rows(named=True)`. Headers are validated after materialization. | Python-native values produced by Polars, potentially including `None`, `bool`, integers, floats, strings, `Decimal`, `date`, `datetime`, `time`, `timedelta`, bytes, lists, dictionaries and other values depending on the Parquet logical/physical schema. | Parquet has a small physical type set and many logical annotations; nullity is separate definition-level data ([physical types](https://parquet.apache.org/docs/file-format/types/), [logical types](https://parquet.apache.org/docs/file-format/types/logicaltypes/), [nulls](https://parquet.apache.org/docs/file-format/nulls/)). The current reader has no explicit dtype allowlist before Python conversion. Polars documents that row conversion truncates nanosecond temporal values to Python's microsecond precision ([`iter_rows`](https://docs.pola.rs/api/python/version/0.18/reference/dataframe/api/polars.DataFrame.iter_rows.html)) and exposes nested, binary, temporal, decimal and other data types ([Polars data types](https://docs.pola.rs/api/python/stable/reference/datatypes.html)). |

This asymmetry is consequential. JSONL intentionally preserves numeric spelling, while SQLite may already have discarded it and Parquet may expose a typed exact decimal. CSV cannot distinguish an empty string from a conventional null without reviewed null-token policy. SQLite and Parquet can carry null independently of text. Parquet can carry a date or timestamp as a logical type; CSV, JSONL and SQLite commonly carry the same intended value as text.

## Safe common projections

There is no safe, useful universal *inferred* type shared by all four readers. There are two defensible projections, both controlled by the existing reviewed column policy.

### 1. Policy-directed semantic scalar projection (recommended)

For each configured column, convert an explicitly allowed raw source representation directly into the recipe's semantic domain:

| Recipe domain | Safe accepted source representations | Required safeguards |
|---|---|---|
| null | Native JSON/SQLite/Parquet null; exact configured CSV/TSV null token | Never treat a spelling such as `NULL`, empty text, zero, or whitespace as null without side-specific policy. Preserve current non-string empty-text behavior only as released compatibility until a versioned policy can replace it. |
| string | Text/string values only | Do not stringify booleans, numbers, bytes, dates, lists or structs. Such coercion makes source type changes invisible and is format-dependent (`True`, `true`, `1`). Apply only the existing explicit trim/casefold/NFC rules. |
| integer | JSON/CSV text matching the accepted integer grammar; SQLite/Python integer but not boolean; Parquet signed or unsigned integer within Parison's supported range | Reject float-to-integer even when integral unless a versioned policy explicitly permits it. Reject overflow before platform/library coercion. |
| decimal | Decimal lexical text or an exact Parquet decimal/Python `Decimal` within configured scale | Do not promote SQLite REAL or Parquet float to exact decimal. Precision, scale and range must be checked before canonicalization. |
| float | Finite numeric lexical text, integer, or IEEE float | The recipe explicitly selects approximate binary numeric semantics. Reject NaN and infinities from every reader and test signed zero deliberately. |
| boolean | Native JSON/Parquet boolean or exact lowercase text `true`/`false` | SQLite integers `0`/`1`, uppercase spellings, and other truthy values require an explicit versioned source-conversion policy; Python `bool` must never pass as integer. |
| date | ISO date text or a native date that is not a datetime | No locale parsing, epoch guessing, integer-day conversion or timestamp-to-date truncation. |
| timestamp | ISO timestamp text with explicit offset, or a timezone-aware native datetime | Normalize the instant only under the existing timestamp contract. Reject timezone-naive values. Reject precision beyond the supported canonical precision rather than silently truncating it. |

This projection is deep because downstream keyed, multiset and aggregate logic remains unchanged. The recipe type is the authority; source metadata can validate an allowed representation but cannot approve meaning.

### 2. Lossless lexical projection (narrow fallback)

CSV and JSONL already support a useful lexical bridge for scalar text and JSON numbers. It is safe only when the recipe deliberately parses that lexical form. It should not be generalized by rendering every SQLite or Parquet value as text: SQLite affinity may already have changed spelling, float rendering is an implementation choice, timestamps have multiple equivalent spellings, and nested/binary values have no canonical textual representation in the current contract.

Accordingly, cross-format parity should be described as **common recipe-domain equality**, not raw type equality and not universal string equality.

## Conversions that require explicit policy or upstream extraction

The following must not become implicit reader conveniences:

- SQLite `0`/`1`, `Y`/`N`, or arbitrary numeric values to boolean;
- epoch integers or floating seconds to dates/timestamps, timezone attachment, offset assumption, daylight-saving resolution, or date truncation;
- SQLite REAL or Parquet FLOAT/DOUBLE to exact decimal;
- numeric-to-string, boolean-to-string, date/time-to-string, or bytes-to-text conversion;
- Unicode normalization, whitespace trimming, case folding, locale collation, thousands separators, decimal commas, currency removal, or percent scaling beyond reviewed existing policy;
- Parquet nested LIST/MAP/STRUCT/VARIANT/JSON values, binary values, UUIDs, intervals, durations, time-of-day, enums, extension types, or unknown future logical annotations;
- schema union, missing-column insertion, field-ID mapping, positional column matching, or type inference from values;
- JSON arrays/objects, generic JSON documents, or SQLite JSON text expansion;
- parsing application-specific sentinels (`N/A`, zero dates, empty objects) as null;
- extraction from spreadsheets, documents, APIs, archives or databases other than the selected ordinary SQLite table. Those belong upstream with a pinned extractor, explicit options and source/output digests.

## Order, null, number, time, text and schema pitfalls

### Order

CSV and JSONL have physical record order; a Parquet reader reconstructs logical row order from row groups/pages; SQLite returns undefined order without `ORDER BY`. JSON object member order is not interoperable. Parison's keyed and multiset modes should remain order-insensitive after projection. Aggregate input order must not affect exact results. A future order-sensitive comparison cannot use the current SQLite locator and would need explicit ordering keys and tie policy.

Column order is likewise not semantic after exact name/mapping validation. Drafting may use first-seen order for presentation, but policy hashes and multiset canonical encoding must keep their existing deterministic rules.

### Null and absence

Native null, missing column, absent JSON key, CSV empty field, empty string and a configured null token are different states. Current JSONL rejects absent keys after the first record, Parquet/SQLite provide fixed selected schemas, and CSV rejects ragged rows. Keep that closed-world row schema. Do not use Polars' optional missing-column insertion; its official API can insert all-null columns, but Parison must fail on an unreviewed schema change ([Polars `read_parquet`](https://docs.pola.rs/api/python/stable/reference/api/polars.read_parquet.html)).

The current parser maps `""` to null for every non-string recipe type. That is released behavior, but it is a cross-format asymmetry because native empty text and native null collapse only after recipe selection. Preserve it for old recipes; any tightening needs a new recipe/projection version and migration fixtures.

### Numbers

Lexical equality is not numeric equality: `1`, `1.0`, and `1e0` are distinct spellings but may represent one mathematical value. JSON does not cap precision but warns that implementations commonly use binary64; Parison correctly retains JSON number text until policy parsing ([RFC 8259](https://www.rfc-editor.org/rfc/rfc8259.html)). SQLite INTEGER is signed 64-bit in ordinary query results, while REAL is binary64 and affinity can irreversibly convert inserted text. Parquet distinguishes integer widths, IEEE float widths and DECIMAL precision/scale.

Therefore exact integer and decimal projection must reject out-of-domain values rather than wrap or round. Float projection must define finite-only behavior, signed zero and NaN rejection. Decimal scale equality is policy; source scale metadata must not silently override it. A reader upgrade must not change decimal, unsigned integer or float materialization without fixture evidence.

### Time

Text timestamps may express an instant with different offsets; Parquet `TIMESTAMP` additionally declares whether it is adjusted to UTC and has a unit. SQLite has no dedicated date/time storage class. Native naive datetimes, local wall times, dates, times and durations are not interchangeable. The existing requirement for an explicit offset is the correct common boundary.

Parquet-to-Python row conversion is currently unsafe for nanoseconds because Polars documents truncation to microseconds. Reject a timestamp column whose declared precision exceeds the canonical representation until Parison can project from a non-lossy scalar path. Do not round silently. Preserve offset/instant semantics explicitly and include pre-epoch, offset, leap-day and precision boundaries in fixtures. Leap seconds remain unsupported by Python ISO parsing and should fail closed.

### Text

All accepted textual inputs should be valid Unicode strings, but Unicode code-point equality, NFC equality, locale collation and visual equality differ. Keep normalization explicit. Do not case-fold headers or column names. Embedded NUL, lone surrogate behavior, control characters and extremely large strings require consistent rejection/limits across readers. Parquet STRING is UTF-8, while unannotated BYTE_ARRAY is not text and must remain unsupported ([Parquet logical types](https://parquet.apache.org/docs/file-format/types/logicaltypes/)).

### Schema

Schema agreement means exact nonempty unique source names plus reviewed mappings/exclusions, not equal physical declarations. A Parquet logical type, SQLite affinity, JSON token kind and CSV text field may all feed one recipe domain, but only through its allowlist. Conversely, two Parquet files with the same apparent Polars dtype can still use format features with different reader compatibility. Apache notes that new encodings may be forward-incompatible and that the file metadata `version` field has historically not identified used features reliably ([Parquet format versions](https://parquet.apache.org/docs/file-format/versions/)). Pinning Polars is necessary but not sufficient; supported fixtures define the compatibility claim.

## Threats and controls

1. **Silent coercion and type confusion.** Python makes `bool` a subclass of `int`; SQLite mixes storage classes; `str(value)` hides source changes. Use exact raw-type allowlists before semantic parsing.
2. **Precision loss.** Binary floats, oversized integers, Parquet decimals and nanosecond timestamps can round or truncate. Validate source dtype and bounds before Python-native conversion where conversion itself is lossy.
3. **Reader-version drift.** Polars or Python upgrades can change dtype materialization, malformed-input handling or rendering. Pin the optional dependency, record it in runtime evidence, and gate upgrades on byte fixtures.
4. **Unsupported-type smuggling.** An excluded Parquet nested/binary column could still stress or exploit the parser, and today the entire frame is materialized. Validate the complete schema against a closed allowlist before reading rows, including excluded columns.
5. **Resource exhaustion.** Compressed/encoded Parquet may expand far beyond file size; huge row groups, schemas, strings and nested levels are distinct limits. Add decoded/materialized bounds or keep the format outside a stronger guarantee until they exist.
6. **Nondeterministic source state.** Continue before/after digests, SQLite sidecar rejection, regular-file/symlink checks, bounded local reads and interruption cleanup.
7. **Privacy leakage.** Dtype diagnostics may name columns or reveal schema. Summary-safe output must keep excluding paths, keys, values, samples and sensitive schema details.
8. **False authority.** A projection can verify supplied values only. It cannot certify upstream extraction, database consistency beyond the hashed snapshot, declared Parquet semantics, or business correctness.

## Non-goals

- a cross-format schema inference or automatic type-coercion engine;
- preserving source lexical spelling after semantic parsing;
- recursively comparing JSON or Parquet nested values;
- making SQLite table order deterministic or adding arbitrary SQL;
- accepting BLOB/binary columns, decoding encodings, or interpreting application payloads;
- locale-aware number/time parsing, timezone guessing, fuzzy text matching or hidden normalization;
- repairing malformed files, inserting missing fields, widening schemas, or reconciling incompatible types;
- converting formats or claiming that CSV, JSONL, SQLite and Parquet schemas are intrinsically equivalent;
- changing existing recipes, canonical bytes, result JSON, exit codes or released bundles in place.

## Dependency and compatibility consequences

CSV, JSONL and SQLite remain standard-library readers. A closed raw-value adapter can deepen the existing input module without another dependency. Parquet remains the one optional stack, pinned today to Polars 1.44.2. The projection contract must name supported Parquet dtypes independently of the library's larger type catalog and must reject new/unknown logical types until promoted deliberately.

Any change to accepted coercions is semantic and therefore versioned. Existing recipes and bundles must retain their current meaning. The safest introduction is a new projection contract selected by a new recipe version or explicit policy field, while legacy recipes continue through their released parser. If the implementation can prove a change is rejection-only for inputs that never had a documented compatibility claim, document that boundary precisely rather than retroactively redefining released PASS results.

Because this touches packaging and platform-sensitive optional code, promotion requires built-wheel CI on Python 3.11–3.14, macOS and Windows. Optional-Polars skips are valid only when Polars is absent. Record Python, SQLite and Polars versions already exposed in runtime metadata, and treat upgrades as compatibility changes requiring the same corpus.

## Realistic workflow

1. A producer exports each side locally in any supported format and closes/checkpoints SQLite writers.
2. The operator drafts a recipe, then reviews scope, column mappings, exclusions, semantic types, null tokens, normalization, decimal scale, timestamp requirements and tolerances. Suggestions do not approve them.
3. Preflight reads schemas only, rejects unsupported raw/logical types across all columns, and reports non-sensitive incompatibility classes.
4. Record validation projects each raw scalar through the format/type allowlist into the configured semantic type; no generic stringify or inference occurs.
5. Existing keyed, multiset or aggregate comparison consumes the projected rows unchanged.
6. Full evidence binds input digests, effective policy digest, projection contract version and runtime versions. Summary-safe evidence retains no local paths, keys, values or discrepancy samples.
7. When a source representation is unsupported, the user fixes/export-materializes it upstream and reruns with the same reviewed recipe; Parison does not repair it.

## Narrow recommendation

Specify and implement **`semantic-scalar-v1` as a closed, policy-directed adapter in front of the existing semantic parser**, not a new comparison mode and not a universal intermediate string model.

The first slice should do only four things:

1. define the exact raw Python/source representations accepted for each existing recipe type, with native null plus text/integer/decimal/finite-float/boolean/date/aware-datetime boundaries as above;
2. preflight every Parquet column against a small scalar dtype allowlist and reject nested, binary, time, duration, object/extension, unknown logical types and nanosecond timestamps before row materialization;
3. reject implicit coercions that are not already released contract, especially native non-text values under `string`, boolean-as-integer, REAL-as-decimal and timestamp precision loss; introduce this under a versioned recipe/projection boundary rather than changing old recipes silently;
4. add a cross-product fixture corpus proving that equivalent supported representations project to identical canonical rows and that ambiguous/lossy representations fail with stable diagnostics.

Do not add a dependency or a generic `Value` abstraction first. The existing recipe parser is the deep seam; deepen its input boundary and make the reader contract explicit.

## Checkable compatibility and promotion gate

Promote the slice only when all of the following are demonstrated from built wheels:

- for every existing semantic type, a fixture matrix covers CSV, JSONL, SQLite and each admitted Parquet physical/logical representation; every admitted equivalent produces identical typed canonical row bytes and identical keyed, multiset and aggregate result JSON apart from documented input metadata;
- null, empty text, configured null tokens, booleans, signed/unsigned integer bounds, exponent forms, decimal scale/precision, float signed zero/non-finite values, Unicode normalization boundaries, timezone offsets, pre-epoch values and temporal precision boundaries have positive and negative fixtures;
- nested/binary/unknown Parquet types, SQLite BLOB/mixed incompatible storage classes, JSON nested values, ragged CSV, naive/native ambiguous time values and all lossy conversions fail closed with stable machine-readable diagnostics and no partial PASS;
- Parquet nanosecond timestamps are either rejected before Python row conversion or projected through a proven lossless path; no fixture can compare equal solely because sub-microsecond data was truncated;
- row-order permutations and Parquet row-group/layout changes do not change keyed, multiset or aggregate canonical results; SQLite's undefined scan order cannot affect output;
- the same corpus passes on Python 3.11, 3.12, 3.13 and 3.14 on macOS and Windows, with Linux retained in normal CI, using the pinned Polars build;
- legacy recipes, schemas, canonical byte fixtures, bundles, exit codes and CLI JSON remain readable and byte-compatible; any new semantic behavior requires an explicit new version and migration documentation;
- `make check` passes, full evidence records projection/runtime identity, summary-safe artifacts remain free of paths, keys, values and samples, and no read performs network access, credentials, repair, writes or remote orchestration.

Until that gate passes, current mixed-format results should be understood as the behavior of the existing individual readers plus recipe parser, not as a promised general cross-format type-equivalence layer.
