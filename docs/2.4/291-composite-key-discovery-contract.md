# Exact hash-bucket discovery contract

Date: 31 October 2026
Status: proposed feature 3 contract; independent review required before freeze

This implements feature3 of [roadmap275](275-ten-feature-research-and-roadmap.md),
using [primary-source research290](290-composite-key-discovery-research.md).
Hashing routes rows only. Exact keyed comparison remains authoritative for
identity, field classification and outcome. PASS means agreement under the
explicit policy, never extraction truth, approval or cutover authorization.
Preserve released range-v1 plans, recipes, envelopes, bytes, aliases and exit
codes. All ten features must qualify before a2.4 candidate.

## 1. Admission and bounded plan

Add partition-plan-v2 with exactly partition_plan_version:2, routing and limits.
Routing is exactly `{kind:"hash-v1", hash:"sha256", encoding:"typed-key-v1",
buckets:N}`. N is an exact integer token2..128; no salt, seed, chosen hash,
automatic sizing, source filter or adaptive repartitioning. Limits has the five
range-v1 names/caps plus mandatory max_key_bytes (exact integer1..65536):

| Limit | Inclusive maximum |
| --- | ---: |
| max_input_bytes (per source) | 1,000,000,000 |
| max_rows_per_input | 5,000,000 |
| max_rows_per_partition_side | 1,000,000 |
| max_staged_bytes | 2,000,000,000 |
| max_partition_bytes (per side/bucket) | 1,000,000,000 |
| max_key_bytes (entire framed key) | 65,536 |

Every limit is mandatory and positive. Bool/float equivalents are invalid.
Plan JSON is strict, duplicate-free and at most256KiB. Version1 retains its
exact fields and interpretation; no implicit upgrade or absent-field defaults.

Version2 admits only the existing simple keyed summary CSV recipe subset:
comparison_mode keyed; output.sensitivity summary; no column_mappings,
field_projection, input_projection or excluded_columns. There are1..16 ordered
unique key names, each declared integer or string, and at most100 total columns.
Other non-key scalar policies/tolerances remain those of the released engine.
Do not infer keys, normalize beyond the recipe or approve tolerances. Recipe
JSON and its canonical mechanically derived recipe are each at most256KiB.
The original effective policy fingerprint remains authoritative. Key order is
recipe.keys, never dictionary order or sorted physical names. Range-v1 keeps
its single integer-key admission and its existing null-routing error.

## 2. Exact routing byte grammar

Parse each row through the existing side-aware input reader and _parse_row,
including the original null-token and ordered normalization rules. For the
ordered parsed key tuple K, encode:

```
b"parison-key-v1\x00"
+ len(K).to_bytes(2, "big")
+ component_1 + ... + component_len(K)

component = tag(one byte) + payload_length.to_bytes(8,"big") + payload
NULL:    tag 0x00, length 0, empty payload
integer: tag 0x02, str(parsed_integer).encode("ascii")
string:  tag 0x04, normalized_string.encode("utf-8", errors="strict")
```

The component grammar is the integer/string/None subset of the released
comparison._multiset_encoding. Reuse that implementation; do not modify its
released encoding. Domain and tuple arity belong only to typed-key-v1 routing.
Measure all lengths in bytes, including the fixed prefix/arity and all framing.
Reject over-budget components before building an oversized composite buffer;
check character count before UTF-8 encoding, then actual byte length. Invalid
UTF-8/surrogates are controlled errors; no replacement or locale encoding.
Canonical integers erase raw signs/leading zeros exactly as the existing parser
does. No bool, decimal, float, date or timestamp key is admitted in this profile.

Bucket index is `int.from_bytes(hashlib.sha256(encoded).digest(),"big") % N`.
Never use Python hash(), repr(), separator joining, native byte order or a row
hash as a comparison key. Neither side, input digest/path, runtime descriptor,
column name nor raw spelling enters the preimage. The shared recipe fixes the
position types; equal normalized tuples must reach the same bucket on both
sides. Bucket collisions—including forced full-digest collisions—must never
collapse unequal tuples, drop rows or imply equality. No distribution/skew or
universal capacity promise follows from SHA256.

NULL has a distinct routing tag solely to co-locate tuples; it is not approved
as a valid key. The unchanged exact engine reports null components and duplicate
normalized keys as INCONCLUSIVE. String empty remains distinct from NULL unless
explicit null-token policy maps it to None; non-string empty retains the core
parser's None meaning. Never pre-deduplicate. Preserve every raw row in original
per-side order within its bucket. Stage headers in Unicode code-point sorted
recipe-column-name order, with values aligned by exact name; key order still
comes from recipe.keys. Stage original values, not normalized values,
so comparison applies the policy once to original input values. Existing null
re-emission behavior is retained for the core reader's None representation.

## 3. Input snapshots, staging and exact work

Keep sequential execution. Before routing version2, open and pin regular
non-symlink source CSVs and the recipe under trusted-parent checks. Read the
recipe from its pinned bounded handle into the existing recipe-text loader.
Copy each source from its pinned handle into private staging while hashing its
exact bytes, enforcing source and shared staging caps before writes. Check file
identity/size/mtime/ctime before and after snapshot reads and before publication;
require original source/recipe names still identify those regular files. Parse
and compare only private source snapshots and derived bucket files thereafter,
never verify an original path and reopen it for semantic input. A transient
source-path replacement cannot substitute different bytes into comparison.
The plan also needs a pinned, bounded regular-file read; it is held in memory
for the run. Publication never modifies inputs or places output within them.

Version2 staged_bytes counts the two complete private source snapshots, all
bucket CSV contents including headers, and the canonical derived-recipe file.
Record derived_recipe_bytes so integrity arithmetic can reproduce that total.
No raw recipe copy is retained on disk. Check the shared budget before every
snapshot/bucket/derived write; no truncated file can qualify. Final evidence
metadata is separate: plan/summary/manifest<=256KiB each, receipt<=8MiB. Temporary
contents are removed before final evidence is written; final metadata is thus
also bounded independently. These are file-content bounds, not filesystem
allocation or process-memory promises.

All N buckets are materialized on both sides, including empty ones. At most N
bucket writer descriptors remain open at a time: close each side before opening
the other. Enforce per-side/bucket row and byte caps; count original source rows
under the inherited parser limit. Skew/full-bucket overflow is an error, never a
request to change N, omit a key or use a different comparator. Check all staged
CSV/snapshot digests and pinned source stamps before publication. Detect source,
recipe, staged-file, directory-membership or symlink substitution and abort.

Run the unchanged exact engine over each pair, mechanically deriving only
scope.expected_empty:true for local empty-bucket handling. Preserve the original
policy hash in evidence. Aggregate exact counts and field counts in bucket
order. If any bucket is incomplete, suppress all aggregate match/field counts
as the released full engine does. Apply the original global expected_empty
policy to global empty inputs. For admitted inputs within every configured cap,
aggregate outcome, complete, counts, field_counts and discrepancy_count must
match full released keyed execution with the same parser/policy and zero samples.
No source paths, names, keys, values, samples or per-key hashes appear in safe
summary output. Private field_counts may retain approved recipe field names.

## 4. Version2 evidence and runtime context

Root remains exactly plan.json, receipt.json, summary.json and manifest.json.
All published JSON is canonical _canonical plus one LF. User plan/recipe files
need not already be canonical, but duplicate members/nonfinite constants and
invalid exact types are errors. Version2 readers require canonical member bytes;
range-v1 reader acceptance and all released byte fixtures are unchanged.

Receipt-v2 retains the12 receipt-v1 fields with partition_receipt_version:2 and
adds exactly routing, normalization_runtime and derived_recipe_bytes. Routing
equals plan.routing. Partitions is an N-entry array in index order; each closed
record replaces upper with exact bucket:index and retains baseline, candidate,
counts, field_counts, outcome, complete. Side records stay rows/bytes/sha256.
No per-key digest is published. Derived_recipe_bytes is positive<=256KiB.
Staged total is `sum(inputs[side].bytes) + sum(partition[side].bytes)
+ derived_recipe_bytes`, under max_staged_bytes. Input descriptors bind the
original snapshot SHA256/byte counts. Other arithmetic and exact token checks
retain the existing invariants. Complete cannot be true if any bucket is
incomplete; if all buckets complete and both sources nonempty it must be true.
Integrity-only cannot infer the original empty-scope choice from a policy hash;
source-backed replay supplies that policy and reproduces its outcome.

Normalization_runtime is exactly implementation, python_version, unicode_version.
Implementation is "CPython" for this initial capability. Python_version has the
bounded ASCII grammar `[0-9]{1,2}\.[0-9]{1,2}\.[0-9]{1,3}`; Unicode_version uses
`[0-9]{1,2}\.[0-9]{1,2}\.[0-9]{1,2}`. Capture actual platform.python_implementation(),
platform.python_version() and unicodedata.unidata_version; a runtime outside this
profile is a controlled unsupported error. Creation and exact source-backed replay admit CPython minor versions3.11,
3.12,3.13 and3.14 only; other minor/major versions remain unsupported until
explicitly qualified. Integrity-only reading does not apply this execution
allowlist. Full patch versions are still captured and matched exactly for replay.
There is no OS, hostname, architecture, file path or user value here.
All member shapes are closed and context strings cannot become arbitrary safe
output text. Integrity-only reading accepts otherwise valid unfamiliar numeric
versions; it does not claim reproducibility on the current interpreter.

Exact source-backed creation/replay requires the current context to match the
recorded context exactly, even when no normalization rule is present. This
conservative restriction binds parsing and all string-column normalization,
including trim/casefold/NFC. Patch upgrades may require replay under the original
runtime. Do not infer cross-version equivalence or rewrite old context; a looser
compatibility profile or another implementation needs explicit qualification.
Hashing the same normalized tuple itself stays byte-stable across runtimes.

Summary-v2 has the existing summary fields, partition_receipt_version:2, plus
routing and normalization_runtime; it omits derived_recipe_bytes and private
partitions/field_counts. Manifest-v2 is exactly partition_manifest_version:2
and files binding the other three canonical members. Preserve old schema names;
add explicit partition-plan/receipt/summary/manifest-v2 schema names to the
existing schema command. JSON schemas are structural; runtime verifies bounds,
context, canonical bytes, cross-bindings, counts and replay.

## 5. Verification, CLI and compatibility

Deepen the existing verifier with pinned root/member handles, bounded reads and
final file/directory stamps for version2; never validate a manifest then reopen
untrusted JSON paths for derived interpretation. Integrity-only validates exact
membership, bytes/digests, profile, context shapes and arithmetic, returning
verification:"integrity-only". It does not prove input truth or parity.

Exact-source-backed requires the original recipe and both CSVs. Check recorded
runtime context before source work, create fresh pinned private snapshots under
the same total budget, rerun and reproduce the entire private receipt, and
recheck bound evidence before returning verification:"exact-source-backed".
Missing source arguments or context mismatch is a controlled error, not
INCONCLUSIVE/PASS. Changing source bytes, normalized recipe semantics or routing
plan cannot reuse old evidence. Preserve old range-v1 verification behavior.

Use existing `parison partitions discover|verify` and legacy parison-partitions
alias. Do not add a project script. Keep existing argument/help/error parsing
fixtures. Discover exit0 PASS,1 FAIL,2 INCONCLUSIVE/error; successful verify exit0
with its explicit verification label, invalid verify exit2. Version2 execution
errors use a fixed value-free message once its version is known; interruption
returns130 with fixed text and removes sensitive staging. Preserve released
version1 exit/error behavior. No private values or source paths in new-version
runtime errors; pre-admission CLI behavior remains the existing contract.

Released investigation-plan/cases-v1 are single-integer/range formats. They must
continue reading old evidence and explicitly reject version2 discovery before
attempting range/upper interpretation, including single-integer hash plans.
Raw tuple/text investigation requires a separate versioned case contract and is
not silently admitted here. This feature3 scope is exact summary discovery;
no raw samples, checkpoints, resume journal, workers, probabilistic equality,
source SQL/hash pushdown, credentials, repairs, key/policy approval or signing.
Features4/5 own recovery/concurrency. No release until the all-ten boundary.

## 6. Freeze and adversarial completion gate

Before runtime implementation, materialize and independently review all four
closed schemas, canonical/negative envelopes and fixed encoding/SHA/bucket
vectors. Retain released fixtures byte-for-byte. Qualify:

1. Typed framing: integer signs/leading zeros, tuple arity/order, mixed integer/
   string, ambiguous separator strings, NUL/newline/non-BMP, empty/NULL and strict
   UTF-8 failure. Pin exact key bytes, SHA256 and indexes for N=2,3,7,128.
2. Policy: NFC on/off, casefold expansion, trim and ordered rule chains, explicit
   side null tokens, non-string empty, normalized duplicates on either/both sides,
   empty buckets and globally empty sources under both empty policies.
3. Exact authority: force all routes to one bucket through a routing-only test
   seam. Leave source/policy/evidence digests untouched. Outcome/count/field-count/
   discrepancy agreement must survive collisions and duplicates; never compare
   per-key hashes. Test permutations and all supported bucket counts.
4. Bounds/publication: every cap and exact-token error, maximum arity/buckets,
   skew, key-byte boundary, final-side failure, interruption during snapshots/
   routing/comparison/publication, directory/file/symlink mutation, raced output
   and cleanup. No partial evidence or sensitive staging survives errors.
5. Replay: changed input/plan/policy/context, substituted bucket/member, malformed
   private arithmetic, version mismatch, canonical byte mutation and foreign
   context integrity-only acceptance/source-backed rejection before source I/O.
   Legacy range and raw investigation fixtures still verify unchanged; v1
   investigation explicitly rejects hash-v2 without raw output.
6. Check zero samples/summary privacy and root/legacy CLI aliases/exit codes.
   Pass narrow/full tests, independent Standards/Spec review and exact-head
   quality/full built-wheel Python3.11–3.14 Linux/macOS/Windows matrix. Pin
   cross-version byte/hash vectors, not a promise that all Unicode normalizations
   are equal under different UCDs. Machine-specific measurements only if made.

A bounded prototype (not implementation/qualification) routed four composite
corpora at N=2,3,7,128 and matched the full exact engine for normalized equality,
NULL versus empty and duplicate keys on either side. The research and prototype
justify this gate; they do not declare feature3 integrated.
