# Feature 3 hash discovery wire checkpoint

Date: 31 October 2026
Status: schemas/fixtures implemented; independent review and exact-head CI pending

[Contract291](291-composite-key-discovery-contract.md) merged through PR #129
at `974a3d41c584ba6e6b1be432f7bf15fb6a77334e`, after independent Standards/Spec
review and [quality CI](https://github.com/raghavkandpal/parison/actions/runs/41194223507)
on exact final head `5f8b1b17064997de17b59a7849b4b756315f2425`.

This slice adds four standalone structural schemas under explicit
partition-plan/receipt/summary/manifest-v2 names in the existing schema command.
Released names retain their definitions. No hash discovery execution, source
reader, snapshot writer, recovery, concurrency or raw-investigation admission
is implemented by this gate. Feature3 remains incomplete; two of ten features
are integrated, and all ten must qualify before a2.4 candidate.

The synthetic `tests/fixtures/partition_hash/` tree freezes a composite
string/integer recipe, original CRLF CSVs and expected canonical four-member
FAIL artifact. The expected bucket records were constructed with a literal
protocol encoder and the existing exact comparator as oracle, not a new
producer. Counts/field counts match full keyed execution. File digests bind LF
on published JSON; plan SHA omits LF. Private derived-recipe bytes omit LF,
matching the existing comparison seam. Contract291 now states those byte rules
explicitly; no released serialization changes. Explicit Git attributes preserve
the fixture CSV bytes through clean archives.

Eighteen key vectors pin typed preimages, SHA256 and bucket indexes2/3/7/128,
including16 components, ambiguous-looking tuples, signed integers, string versus
integer, empty/NULL, delimiter, NUL/newline and non-BMP text. Eleven additional
vectors reuse released parsing/normalization for raw integer spellings, NFC
on/off, casefold expansion, ordered rules, non-string empty and mixed keys.
Digest interpretation is checked explicitly in big-endian and equivalent
reversed-byte/little-endian form; this does not claim qualification on physical
big-endian hardware.

The negative corpus separates structural errors from eight schema-valid future
runtime rejection obligations: exact JSON numeric tokens, bucket index/count,
plan binding, copied-source/derived-size staged arithmetic, summary token types
and context consistency. Foreign numeric contexts remain structurally readable;
that grants neither execution admission nor source-backed replay permission.
The frozen context is synthetic protocol evidence and is not asserted to match
every test interpreter. Runtime must enforce actual context and source bindings.

Narrow gate: `make test TEST=tests.test_partition_hash_wire`. Before integration,
require full `make check`, independent Standards/Spec review and exact-head
quality plus manually dispatched built-wheel Python3.11–3.14 Linux/macOS/Windows
CI because schemas and schema CLI choices changed. Fixed vectors must pass on all
four interpreters. Next implement pinned version2 inputs, routing, exact work and
verification under the frozen contract; then run the collision/null/duplicate/
Unicode/skew/publication gate. No source or row parity is established by passing
these structural fixtures.

Local wire gate: all646 repository tests pass under `make check` on3.14.7.
All six focused wire tests pass on3.11.18,3.12.5,3.13.18 and3.14.7. These check
structures, canonical bindings and released encoding/oracle behavior only;
they do not qualify an unimplemented hash producer or replay verifier.
