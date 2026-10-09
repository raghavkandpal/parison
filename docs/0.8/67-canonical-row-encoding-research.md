# Canonical row encoding research

Date: 9 October 2026

Status: implementation guidance for multiset-v1

## Finding

Keep typed tuples for in-memory counting, but implement the declared `typed-length-prefixed-v1` bytes and use those bytes as the sole raw-evidence sort key. The current tuple identity is adequate only because a recipe fixes one scalar type for every tuple position. The current JSON-derived sort key is deterministic for many ordinary values, but it is not encoding-v1, does not normalize equal decimal or timestamp representations, and can therefore make the selected bounded sample depend on which equal Python object became the retained dictionary key.

Length-prefixing is not the only possible collision-free framing scheme, but it is required by the multiset-v1 contract. Delimiter concatenation cannot distinguish fields such as `("a", "bc")` and `("ab", "c")` without an independently specified escaping rule. A type tag distinguishes null, Boolean, integer, decimal, string, date and timestamp payloads; a fixed-width length distinguishes adjacent payloads and embedded NUL or delimiter bytes. RFC 3629 defines UTF-8 as a one-to-four-octet encoding of Unicode code points, so lengths must count **encoded octets**, not Python characters ([RFC 3629](https://www.rfc-editor.org/rfc/rfc3629)).

The contract should remove one ambiguity before implementation: define the unsigned length width. Recommend an 8-byte unsigned big-endian length after every one-byte tag (`tag || uint64be(len(payload)) || payload`). Reject a payload longer than `2^64-1`; normal input byte limits make that unreachable in practice. The row needs no field-count prefix because recipe-v3 fixes the column count and sorted column order, although adding a versioned row header would make standalone decoding safer.

## Recommended encoding-v1 payloads

Assign stable tag bytes in the specification, for example null `00`, Boolean `01`, integer `02`, decimal `03`, string `04`, date `05`, timestamp `06`, and float `07`. Tags are schema, not implementation details, and must never be renumbered within v1.

| Type | Canonical UTF-8 payload |
|---|---|
| null | empty |
| Boolean | ASCII `0` or `1` |
| integer | minimal base-10 ASCII: `0`, or optional `-` followed by digits; no `+` or leading zeroes |
| decimal | quantize exactly to the declared scale, emit fixed-point ASCII with exactly that many fractional digits, and canonicalize every zero to positive zero |
| string | the post-policy string exactly; apply `trim`, `casefold`, or `unicode_nfc` only when the recipe declares them |
| date | zero-padded ASCII `YYYY-MM-DD` |
| timestamp | convert the aware value to UTC and emit ASCII `YYYY-MM-DDTHH:MM:SS.ffffffZ`, with exactly six fractional digits (Python's supported precision) |

Decimal canonicalization must follow numerical identity rather than input significance: Python documents that equal values can retain different trailing-zero representations and that `normalize()` removes them ([`decimal.Decimal`](https://docs.python.org/3/library/decimal.html)). Fixed-scale rendering is simpler here because scale is already policy. Explicitly collapse `-0` to `0`; Python Decimal treats signed zeroes as equal, so unequal bytes would violate “equal tuple implies equal encoding.”

Timestamp canonicalization must follow instant identity. Python says aware datetimes compare equal when they represent the same date and time taking timezone into account, and `astimezone()` adjusts while preserving the instant ([`datetime`](https://docs.python.org/3/library/datetime.html)). Thus `2026-10-09T00:00:00Z` and `2026-10-09T05:30:00+05:30` need identical UTC payloads. RFC 3339 also distinguishes local offset notation from the represented instant ([RFC 3339](https://www.rfc-editor.org/rfc/rfc3339)). Preserve microseconds exactly; do not route through floating-point epoch seconds.

Document the accepted timestamp language as well as its output. RFC 3339 permits leap-second `:60` and gives `-00:00` a distinct “offset unknown” meaning, while Python `datetime` cannot represent leap seconds. Parison's current parser rejects both forms; retain that behavior explicitly rather than appearing to implement all RFC 3339 timestamps.

Do not add unconditional Unicode normalization. UAX #15 explains that canonically equivalent strings can have different binary representations and that NFC gives them a unique representation ([Unicode UAX #15](https://www.unicode.org/reports/tr15/)). Multiset-v1 already makes `unicode_nfc` an explicit identity-changing rule, so exact strings must remain byte-distinct when that rule is absent. Python's string ordering is suitable for the contract's column-name order (Unicode code points), and UTF-8 is suitable for payload transport; neither implies locale collation. Record the normalization rule and, for reproducibility across runtimes, the Unicode database version in runtime provenance when `casefold` or `unicode_nfc` is used.

## Assessment of the current implementation

`Counter(tuple(...))` is acceptable for one loaded recipe, but it is not literally type-tagged. Python documents that `bool` is a subclass of `int`, and that equal numeric values across types share a hash ([Boolean type](https://docs.python.org/3/library/stdtypes.html#boolean-type-bool), [numeric hashing](https://docs.python.org/3/library/stdtypes.html#hashing-of-numeric-types)). Fixed per-column types prevent those cross-type equalities inside one comparison; retain that invariant and test it. Do not reuse untagged tuples across policies, persisted caches, or mixed-schema operations.

The JSON sort key should be replaced. Python's JSON encoder offers serialization controls, not Parison's typed scalar canonicalization ([`json`](https://docs.python.org/3/library/json.html)); RFC 8785's JSON canonicalization has its own number serialization and UTF-16 property-name sorting rules, which do not match this contract ([RFC 8785](https://www.rfc-editor.org/rfc/rfc8785)). Encoding-v1 bytes should be generated from canonical values, cached per distinct row, used to assert injectivity during tests, and used directly for lexicographic evidence ordering. Evidence JSON may continue to use human-readable values after ordering is fixed.

## Required implementation tests

1. Golden bytes for every tag and payload, including byte lengths for empty string, embedded NUL, non-ASCII BMP text and a supplementary-plane character.
2. Framing adversaries: two-field rows `("a", "bc")` versus `("ab", "c")`, delimiter-containing strings, empty string versus null, and Boolean versus integer in separately typed policies all encode differently.
3. Decimal equivalence: `1`, `1.0`, and `1.00` at scale 2 encode identically as `1.00`; `-0`, `0`, and `0.00` encode identically; excess scale remains a parse error.
4. Timestamp equivalence: UTC and nonzero-offset spellings of one instant encode identically; adjacent microseconds differ; naive timestamps remain errors.
5. Unicode policy: composed and decomposed spellings differ without `unicode_nfc` and match with it; ordering is locale-independent and stable for supplementary characters; lone surrogates are rejected before UTF-8 encoding.
6. Determinism: permute input rows, partitions, insertion order, and `PYTHONHASHSEED`; the complete ordered evidence and its first `sample_limit` items remain byte-for-byte identical.
7. Injectivity/property test: for generated supported values, unequal typed rows never share encoding bytes, while values equal under tuple semantics always do.
8. Regression test showing raw evidence is sorted by complete encoding bytes, not JSON text, and that summary results remain unchanged.

These tests should run on every supported Python version and operating system. A checked-in golden vector file would also let future non-Python implementations verify byte-for-byte interoperability.
