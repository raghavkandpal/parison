# Composite and text key discovery research

Date and primary-source access: 31 October 2026
Status: design research for feature 3; wire contract and implementation not frozen

## Recommended direction

Extend the existing sequential partition discovery module with one explicitly
versioned hash-routing profile for ordered integer/string key tuples. Route
already parsed and policy-normalized keys; preserve original CSV field values
in staging; compare each bucket with the unchanged exact keyed engine. Hashes
choose a location only. Neither a bucket number nor an equal digest establishes
key equality, row equality, policy approval or extraction truth.

This is an implementation/design inference for [roadmap275](275-ten-feature-research-and-roadmap.md),
not a promise made by the external sources. Preserve every released range-v1
plan, receipt, summary, CLI alias and canonical byte. Recovery/checkpoints and
concurrent execution belong to features4/5; do not introduce them here.

## Primary-source findings and design consequences

Python salts built-in string/bytes hashes between interpreter invocations, so
`hash(key)` is not a persistent routing protocol. A fixed `PYTHONHASHSEED` is not
a replacement for a named, versioned byte encoding and routing algorithm.
Use a fixed hashlib algorithm over explicit bytes instead.
[Python3.11 data model](https://docs.python.org/3.11/reference/datamodel.html#object.__hash__).

`hashlib.sha256` consumes bytes and returns a message digest; the named SHA256
constructor is part of the documented standard interface. SHA-256 is specified
by the Secure Hash Standard. This supplies a standard implementation seam, not
permission to replace exact comparison with a cryptographic assumption.
[hashlib](https://docs.python.org/3.11/library/hashlib.html),
[NIST FIPS180-4](https://csrc.nist.gov/pubs/fips/180-4/upd1/final).
A finite digest and a much smaller bucket space necessarily merge some distinct
inputs: collision tolerance must be a correctness property of the architecture.

Python string case folding deliberately removes more distinctions than simple
lowercasing; for example, it can expand one character into several. Strict
UTF-8 encoding raises for invalid encoding input instead of silently replacing
it. Consequently, route the exact normalization result, measure payload lengths
in encoded bytes, and reject unsupported/surrogate values rather than applying
an alternative normalization or encoding error handler.
[Python string methods](https://docs.python.org/3.11/library/stdtypes.html#str.casefold).

Unicode distinguishes canonical normalization from compatibility normalization;
compatibility transformations can erase meaningful distinctions. Its stability
guarantee is qualified by both versions having assigned the characters involved;
characters unassigned in an older UCD can change normalization behavior later.
Do not add NFKC, case folding, trimming or normalization implicitly.
[Unicode UAX15](https://www.unicode.org/reports/tr15/#Versioning).

Python exposes the database version through `unicodedata.unidata_version`.
The Python3.11 documentation identifies UCD14.0.0, while Python3.14 identifies
UCD16.0.0. Supporting both interpreters does not by itself establish identical
normalization for every possible string.
[Python3.11 unicodedata](https://docs.python.org/3.11/library/unicodedata.html),
[Python3.14 unicodedata](https://docs.python.org/3.14/library/unicodedata.html).
Python also exposes the implementation name and full major/minor/patch version.
[Python platform identification](https://docs.python.org/3.14/library/platform.html#platform.python_implementation).

## Existing implementation seams and constraints

Repository observations below are from the current source, rather than claims
about an external standard:

- `policies._parse_row` applies each side's declared null tokens, parsing and
  ordered `trim`/`casefold`/`unicode_nfc` rules through existing input handling.
  String empty is retained; non-string empty parses as None. CSV input rejects
  ragged rows and maps only explicitly configured null tokens to None.
- The exact keyed engine in `comparison._read_stream_index` and `_index` uses
  normalized ordered tuples, reports null components and duplicate normalized
  keys as problems, and does not approve them. Its incomplete-result semantics
  must remain authoritative; discovery must not invent a successful identity.
- `comparison._multiset_encoding` already uses a distinct type tag, an eight-byte
  big-endian payload length and payload bytes. The integer/string/None subset
  supplies the needed self-delimiting building block. Integer payloads use the
  parsed canonical integer spelling; string payloads use UTF-8; None has its
  own tag and empty payload. Confirm and pin its reuse with byte vectors.
- `comparison._key_order_encoding` stringifies values for ordering. It is not
  the type-preserving equality encoding and must not become routing identity.
- `partition_discovery._recipe` currently admits a single integer key and a
  simple summary CSV recipe, excluding mappings/projections/exclusions. Extend
  admission only for the new profile; retain range-v1 admission unchanged.
- `_route` already parses for routing but writes raw CSV fields and re-emits a
  configured null token. Preserve this pattern: serializing normalized strings
  would subject them to the normalization pipeline again inside `compare`.
- `_compare_ranges` runs exact comparison, sums its counts, suppresses match and
  field counts after any incomplete partition, and applies the original global
  empty-input policy. Reuse this authority rather than write another comparator.
  Sources/staging are digest-bound and later checked for mutation.

### NULL, empty and duplicates

Range-v1 rejects a null routing key as an error before exact comparison. The
full keyed engine instead reports null-key problems as INCONCLUSIVE. Preserve
that released range behavior. For the new hash profile, encode None with its
own tag solely to co-locate equivalent tuples, then let the exact engine enforce
its existing rejection policy. Empty string remains a different payload unless
an explicit side-specific null token makes it None. This permits a truthful
full-engine outcome/count equivalence gate without silently approving nulls.

Equal normalized keys must always reach the same bucket, including differently
spelled raw integers or text that becomes equal under approved normalization.
Duplicate normalized keys then meet inside that bucket and remain INCONCLUSIVE.
Staging all raw rows in input order also preserves the exact engine's duplicate
accounting; never pre-deduplicate or keep one representative to save space.

### Encoding and runtime context

Preferred inference: reuse the integer/string/None portion of the existing
length-framed encoding, with a distinct routing domain and explicit tuple arity.
Freeze the complete byte grammar and a big-endian digest-to-bucket operation in
the contract; do not rely on native byte order, `repr`, locale, separator joins or
JSON settings left implicit. The preimage must not contain input side, source
path, raw spelling or per-source digest: those could split equal keys across
baseline and candidate buckets. Do not expose per-key hashes in safe summaries.

Injective pre-hash framing is useful for a clear protocol, but exactness must
still survive deliberate routing collisions. Unequal framed keys sharing a
bucket are harmless if the exact engine keeps their actual tuple identities.
Reject the alternative of using the digest itself as a row key or equality test.

Record a new receipt normalization context containing Python implementation,
full Python version and UCD version. Require that context to match for new
source-backed replay; mismatch is a controlled unsupported replay, not a parity
result. Integrity-only reading should remain available for an otherwise valid
record with an unfamiliar context. Do not retrofit this condition onto range-v1.
This conservative design rejects some harmless patch upgrades, but neither UCD
identity nor a major/minor label proves that patch-level parsing or string
behavior cannot change. A looser equivalence requires a separately qualified
compatibility profile. OS, host name and machine architecture are unnecessary
normalization identity and should not enter this record.

## Threats, bounds and non-goals

Freeze explicit caps on bucket count, key arity, encoded key bytes, input/row
counts, per-bucket rows/bytes and total private staging. Check encoded-key bounds
before allocating an unbounded composite buffer. A full-bucket/skew overflow is
an error with no output, never permission to repartition, drop data or retry with
an undeclared plan. Do not promise uniformly distributed data or universal
capacity. Qualify any performance claim on the measured machine.

Bound live file descriptors as well as bytes: the current router retains both
sides' bucket files until cleanup. The new profile must qualify its maximum
bucket count on each supported platform or close side handles before opening the
other side. Preserve atomic no-overwrite, symlink-safe publication and cleanup on
failure/interruption. Pin verification reads for new evidence rather than widen
the trust boundary with verify-then-reopen reads.

No new dependencies, network, credentials, source-side hashing/SQL, probabilistic
comparison, adaptive scope, automatic normalization, key approval, resume store,
workers or signing. No new installed project script. Existing task-oriented CLI
paths and released readers remain intact. All ten 2.4 features must qualify before
any candidate.

## Contract and adversarial gate to freeze next

1. Close the new plan/receipt/summary/manifest shapes, routing-profile identifier,
   normalization context, exact error/outcome mapping and integrity-only versus
   source-backed verification semantics. Freeze canonical/negative fixtures
   before runtime; keep old range and investigation records readable unchanged.
2. Pin byte/hash/bucket vectors for signed/leading-zero integers after parsing,
   text including delimiter/NUL/newline/non-BMP characters, empty/None components,
   tuple arity/order, and normalization on versus off. Check all supported Python
   versions and both byte-order conventions through fixed vectors.
3. Force all routing to one bucket via a routing-only test seam, leaving source,
   policy and evidence digests intact. Compare exact outcomes/counts/field counts
   with full keyed execution for matching rows, differences, one-sided keys,
   duplicate normalized keys and null components.
4. Exercise explicit side null tokens, ambiguous-looking composite tuples,
   NFC-equivalent versus non-normalized text, casefold expansion, ordered
   normalization rules and changed runtime context. Never normalize twice.
5. Test skew, empty buckets, globally empty inputs, every configured cap, last
   bucket failure/interruption, mutated inputs/staging, symlinks, raced output and
   malformed/extra/type-confused fields. No partial publication or source samples
   may escape in summaries/errors.
6. Retain old byte fixtures; pass narrow/full tests, independent Standards/Spec
   review and exact-head full Python3.11–3.14 Linux/macOS/Windows built-wheel CI.

The final wire design and exact numerical caps remain decisions for the next
contract gate. This note does not declare feature3 implemented or integrated.
