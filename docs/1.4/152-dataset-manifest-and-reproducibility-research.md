# Deterministic dataset manifests and reproducibility diagnostics research

Date: 16 October 2026

Status: **research recommendation**

## Precise question and boundary

What is the smallest explicit contract that lets Parison bind a coordinated local
dataset collection to durable evidence, then explain why a later verification run
was or was not reproduced?

The capability must answer three different questions without conflating them:

1. did the supplied local collection contain exactly the declared members;
2. did every member have the declared byte identity and verification role; and
3. which relevant execution facts differed between two runs?

It must remain local-first and deterministic. Parison may enumerate explicitly
selected local files, hash their bytes, validate strict JSON, inspect supported
format metadata and record bounded runtime facts. It must not fetch a resource,
connect to a catalog or source system, choose a dataset scope, infer that an export
is complete, install or lock dependencies, repair a file, sign a statement, or
approve a cutover. PASS continues to mean agreement under an explicit policy, not
extraction truth, provenance authenticity, business approval or authorization.

All external sources below are primary specifications or official project
documentation and were accessed **16 October 2026**.

## Recommendation in one sentence

Add a versioned `dataset-manifest-v1` whose canonical identity is determined only
by reviewed policy and ordered local resource identities, and emit a separately
fingerprinted `reproducibility-diagnostic-v1` whose host and runtime facts may
explain differences but never alter verification semantics unless an explicit
policy promotes a closed field into a compatibility requirement.

```text
reviewed collection policy + local files
                  |
                  v
       deterministic manifest ----------> collection identity
                  |
                  +--> existing verification --> result/bundle
                  |
                  +--> runtime observation ----> diagnostic comparison
                                                   (informational by default)
```

This is one larger capability rather than a generic packaging subsystem: it binds
the inputs, effective policies, results and runtime explanation needed to rerun a
migration or backfill rehearsal without taking custody of extraction.

## Lessons from established manifest formats

### BagIt gives the right integrity model, but not Parison's JSON contract

BagIt separates opaque payload files from tag files. Every payload file must be
listed exactly once in every payload manifest, with a checksum over its bytes. A
bag is valid only when it is complete and every listed checksum verifies. Its
optional `Payload-Oxum` byte-count/file-count value is explicitly only a quick
incompleteness check; it does not replace checksum validation. BagIt also warns
against paths that escape the bag, including absolute, parent-relative and
platform-specific paths ([RFC 8493](https://www.rfc-editor.org/rfc/rfc8493.html)).

**Consequences for Parison:**

- completeness and digest agreement are separate predicates with separate reason
  codes;
- byte count is useful for early diagnosis but can never establish identity;
- membership is a closed set, not whatever a later directory walk happens to find;
- paths use normalized relative POSIX spelling, are sorted by Unicode code point,
  and must not be interpreted through host locale;
- v1 uses an explicit `sha256` algorithm and lowercase hexadecimal digest; MD5 and
  SHA-1 compatibility from archival formats is not inherited;
- no BagIt serializer or dependency is needed. Parison borrows the integrity
  semantics and retains strict canonical JSON.

### RO-Crate gives useful provenance vocabulary, not fixity

RO-Crate represents a root dataset, its parts and contextual entities in a
JSON-LD graph, and supports provenance such as software used to create a file. Its
metadata document is intentionally descriptive and may refer to local or remote
entities; the specification does not make it an exhaustive integrity manifest.
RO-Crate is designed to coexist with fixity mechanisms such as BagIt
([RO-Crate 1.1 recommendation](https://www.researchobject.org/ro-crate/specification/1.1/index.html),
[RO-Crate structure](https://www.researchobject.org/ro-crate/specification/1.1/structure.html)).
The current RO-Crate quick reference likewise distinguishes a crate's Data
Entities and `hasPart` relations from file size and accessibility metadata
([RO-Crate quick reference](https://www.researchobject.org/ro-crate/quick-reference)).

**Consequences for Parison:** resource roles, generation context and software
identity are useful concepts, but JSON-LD expansion, remote context retrieval and
open-ended graph interpretation would undermine strict, offline execution. A
future exporter may map Parison evidence into an RO-Crate profile, but core v1
must not consume remote contexts or claim RO-Crate conformance.

### Frictionless Data Package is a useful descriptor precedent with unsafe defaults

The Data Package specification requires a `resources` array. Data Resource permits
local relative POSIX paths and records properties such as byte size, hash, media
type, encoding and schema; local paths must stay within the package directory. It
also permits inline data and HTTP(S) resources, and its v1 unprefixed resource hash
is MD5 ([Data Package](https://specs.frictionlessdata.io/data-package/),
[Data Resource](https://specs.frictionlessdata.io/data-resource/)). Table Schema
keeps ordered declared fields and logical constraints separate from the physical
resource ([Table Schema](https://specs.frictionlessdata.io/table-schema/)).

**Consequences for Parison:** adopt stable resource IDs, explicit media/format
claims and the distinction between a resource and its schema, but reject URLs,
inline payloads, parent paths and an implicit hash algorithm. Unknown properties
fail strict schema validation rather than becoming an unreviewed extension point.

## Recommended contract: `dataset-manifest-v1`

The manifest is a new opt-in strict-JSON artifact. It describes one closed local
collection used in one verification rehearsal. It does not change any released
recipe, suite, result, bundle, exit code or canonical byte sequence.

```json
{
  "version": "dataset-manifest-v1",
  "collection_id": "september-backfill-candidate",
  "policy": {
    "suite_sha256": "...",
    "membership": "closed"
  },
  "resources": [
    {
      "id": "customers",
      "role": "candidate",
      "format": "parquet",
      "path": "candidate/customers.parquet",
      "bytes": 248113,
      "digest": {"algorithm": "sha256", "value": "..."},
      "schema_sha256": "..."
    },
    {
      "id": "orders",
      "role": "candidate",
      "format": "jsonl",
      "path": "candidate/orders.jsonl",
      "bytes": 917004,
      "digest": {"algorithm": "sha256", "value": "..."},
      "schema_sha256": "..."
    }
  ]
}
```

### Exact v1 semantics

- `collection_id` is a stable policy identifier supplied by the operator. It is
  not inferred from a directory, filename, database or table name.
- `suite_sha256` binds the already canonical effective suite or reconciliation
  policy. The manifest does not duplicate or reinterpret that policy.
- `membership` is fixed to `closed`. Every selected regular file must be declared
  exactly once; every declared member must exist and be verified.
- `resources` is canonicalized in ascending `(id, role, path)` order. Input array
  order, directory enumeration order and worker completion order do not affect
  bytes.
- `id` and `role` form the logical binding used by the suite. IDs are unique within
  a role. The closed v1 roles are `baseline`, `candidate`, `receipt` and
  `supporting`; unknown roles fail validation.
- `path` is UTF-8, slash-separated and relative to one explicit manifest root. It
  must already be lexically normalized. Empty segments, `.`, `..`, leading `/`,
  backslash, NUL, URI schemes and Windows drive/namespace forms are rejected.
- each path is resolved beneath the opened root without following a symlink at any
  component. The final object must be a regular file. Directories, devices, FIFOs,
  sockets and hard-link aliases to the same opened file identity are rejected.
- `bytes` is the exact nonnegative octet count observed while hashing. A changed
  byte count is reported before the digest mismatch but never substitutes for it.
- the digest algorithm is exactly `sha256` in v1. The digest covers the complete
  stored byte stream, not decoded rows, decompressed content or selected SQLite
  tables. Semantic identity remains the job of existing Parison policies.
- `format` is one of Parison's released input formats. It controls existing parsing
  behavior; filename suffix does not.
- `schema_sha256`, when present, binds an existing canonical Parison schema or
  semantic projection. Embedded file metadata does not override it.
- omitted and empty are never synonyms. Unknown fields, duplicate JSON keys,
  invalid Unicode, out-of-range integers and malformed digests are controlled
  input errors.

The canonical manifest fingerprint uses Parison's released canonical JSON rules
and a new domain separator. Creation time, manifest location, absolute root path,
file modification time, inode, device number, owner, permissions and runtime
facts are excluded. These may be useful observations, but would make an otherwise
identical collection machine-dependent.

### Safe creation and verification

Manifest creation must use the same defensive publication properties as evidence
bundles: explicit destination, atomic no-overwrite publication, no symlink
traversal, deterministic ordering and sensitive staging cleanup on failure or
interruption.

Verification opens each resource under the trusted root and computes size and
digest from one file descriptor. It must detect replacement or mutation during
the read using descriptor metadata before and after hashing and fail with
`resource-changed-during-read`; retrying automatically would hide an unstable
input. The verifier must not trust modification time as identity and must not
silently follow a path after validating only its string form.

The membership walk itself is bounded by explicit policy: either named files are
the complete collection or a reviewed list of relative subtrees is enumerated.
Hidden files and unknown extensions are not implicitly ignored. A future include/
exclude language requires a new manifest version; v1 should avoid glob semantics
whose case and matching behavior differ by platform.

## File-format identity caveats

### SQLite

An SQLite database's live state may include a rollback journal or WAL in addition
to the main file. SQLite states that a hot journal or WAL can be part of database
state and cannot be ignored; in WAL mode, committed transactions may be lost or
the database corrupted if the database file is separated from its WAL
([SQLite database file format](https://www.sqlite.org/fileformat2.html),
[SQLite WAL](https://www.sqlite.org/wal.html)). SQLite's online backup API instead
produces a destination snapshot of the source database
([SQLite Backup API](https://sqlite.org/backup.html)).

**Consequence:** Parison must not manifest a possibly live `.sqlite` main file as
though its digest identified the logical database. `dataset-manifest-v1` accepts
SQLite only when the input is a quiescent, self-contained snapshot supplied by the
operator. The recommended upstream step is the SQLite Backup API or `VACUUM INTO`.
Parison may preflight journal mode and adjacent `-wal`/`-journal` files and fail
closed, but must not checkpoint, back up or mutate the database. Logical table
selection and ordering remain explicit in the existing SQLite recipe.

Two logically identical SQLite databases need not have identical file bytes after
different write, vacuum or page-allocation histories. Therefore the resource
digest proves the exact snapshot file was reused; existing semantic result
fingerprints prove row agreement. Neither substitutes for the other.

### Parquet

Parquet stores file metadata after the data, with row groups and column chunks
whose layout is writer-controlled. Its metadata can carry writer identity,
key/value metadata, encodings, statistics and physical offsets
([Parquet file format](https://parquet.apache.org/docs/file-format/),
[Parquet format definition](https://github.com/apache/parquet-format/blob/master/src/main/thrift/parquet.thrift)).
Page CRC32 values are optional and cover serialized page bytes, not the whole
dataset ([Parquet checksumming](https://parquet.apache.org/docs/file-format/data-pages/checksumming/)).

**Consequence:** the whole-file SHA-256 remains the byte identity. Parquet page
checksums and footer statistics are diagnostics or parser checks, never a
replacement. Different writers, versions, row-group sizes, compression levels or
metadata order can produce different file digests for semantically equal rows.
That is an expected `byte-identity-differs` diagnostic alongside an independently
computed semantic PASS, not evidence corruption. Footer metadata may expose
schema and statistics, so summary-safe output must not copy it wholesale.

### Delimited text and JSONL

Newline spelling, Unicode normalization, byte-order marks, quoting and numeric
lexemes may change bytes without changing projected values. The manifest never
normalizes payload bytes. It binds what was actually supplied, while the released
format parser and semantic policy determine whether values agree.

## `reproducibility-diagnostic-v1`

Reproducible Builds guidance identifies filesystem ordering, timestamps, locale,
timezone, paths and environment variation as common sources of irreproducibility,
and recommends stable inputs plus separately recorded build/environment data
([stable inputs](https://reproducible-builds.org/docs/stable-inputs/),
[timestamps](https://reproducible-builds.org/docs/timestamps/),
[recording the environment](https://reproducible-builds.org/docs/recording/),
[build paths](https://reproducible-builds.org/docs/build-path/)). This strongly
supports keeping volatile facts outside canonical verification identity.

The diagnostic is deterministic for one observation but is a separate artifact:

```json
{
  "version": "reproducibility-diagnostic-v1",
  "manifest_sha256": "...",
  "result_sha256": "...",
  "runtime": {
    "parison_version": "1.4.0",
    "python_implementation": "cpython",
    "python_version": "3.13.8",
    "os_family": "darwin",
    "architecture": "arm64"
  },
  "readers": {
    "parquet": {"distribution": "pyarrow", "version": "..."},
    "sqlite": {"library_version": "..."}
  },
  "observations": []
}
```

Python exposes implementation and language versions separately through
`sys.implementation`; Python packaging defines normalized environment fields such
as implementation, Python version, OS and machine architecture
([Python `sys`](https://docs.python.org/3/library/sys.html),
[Python dependency specifiers](https://packaging.python.org/en/latest/specifications/dependency-specifiers/)).
Installed distribution versions can be obtained from `importlib.metadata`, but
import packages and distributions are not a guaranteed one-to-one mapping
([`importlib.metadata`](https://docs.python.org/3/library/importlib.metadata.html)).

### Closed diagnostic fields

Record only facts with a demonstrated explanation value:

- Parison distribution version and evidence/schema versions;
- Python implementation and full major/minor/patch version;
- normalized OS family and architecture;
- SQLite runtime library version for SQLite inputs;
- the exact supported Parquet reader distribution and version for Parquet inputs;
- selected deterministic reader options that can change interpretation;
- stable reason-coded observations, such as `parquet-writer-differs`,
  `runtime-version-differs` or `semantic-pass-byte-identity-differs`.

Do not capture usernames, hostnames, absolute paths, environment variables,
process arguments, dependency dumps, installed-package inventories, timestamps,
kernel build strings or machine identifiers. Those are noisy, may be sensitive,
and create a new disclosure surface without reliably explaining Parison semantics.
Missing facts are explicit `null` or a reason code as defined by schema; they are
never guessed from an import name.

### Comparison and policy promotion

Diagnostic comparison is ordered by schema-defined field name and emits only
`same`, `different`, `missing-left`, `missing-right` and stable reason codes. It
does not compare arbitrary dictionaries or render raw host strings in
summary-safe output.

By default, a diagnostic difference cannot change PASS, FAIL or INCONCLUSIVE. An
explicit `runtime-compatibility-v1` policy may promote a closed field to a gate,
for example requiring the same Parison major/minor version or the same Parquet
reader distribution/version. That policy has its own fingerprint and must be
evaluated before data comparison. The operator, never a generated suggestion,
chooses which differences matter.

SLSA provenance usefully separates output subjects identified by digest, build
definition inputs and run details; it also treats provenance trust as dependent on
the identified producer ([SLSA provenance](https://slsa.dev/spec/v1.2/provenance),
[SLSA build requirements](https://slsa.dev/spec/v1.2/build-requirements)). Parison
should borrow that separation, not its trust claim: a locally generated diagnostic
is self-reported evidence until an external signing system authenticates it.

## Result and evidence semantics

Manifest verification has distinct outcomes:

- malformed schema, unsafe path, unsupported algorithm, duplicate identity or
  non-regular input is a controlled input error;
- absent declared file or undeclared discovered file is `FAIL` with membership
  reason codes;
- size or digest mismatch is `FAIL` with identity reason codes;
- a resource that changes while read is a controlled unstable-input failure;
- all members present with matching bytes is `PASS` for collection integrity only.

The full result binds manifest fingerprint, effective suite fingerprint, ordered
resource IDs/roles, byte counts and digests, semantic results and diagnostic
fingerprint. Summary-safe output excludes source paths, filenames, table and column
names, schema contents, runtime paths, host identifiers, keys, values and samples.
It may expose collection/result/policy fingerprints, roles, formats, aggregate
counts, statuses, versions already safe under policy and stable reason codes.

A verified evidence bundle should contain the canonical manifest, diagnostic,
effective policies and existing results as separately digested members. The bundle
verifier checks their bindings; it does not rerun extraction or reinterpret the
claim. A matching manifest proves exact declared local bytes. A semantic PASS over
different manifests proves policy-scoped agreement. Neither proves the source was
complete or that a cutover is authorized.

Released readers must continue to read old bundles unchanged. New bundle members
are introduced by a versioned bundle schema; old readers reject the new version
rather than partially verify it. Unknown manifest or diagnostic versions fail
closed.

## Threats and controls

1. **Manifest completeness theater.** A producer can omit an unwanted file. Bind a
   reviewed closed scope; report that completeness is relative to that scope and
   never source completeness.
2. **Path traversal and symlink substitution.** Lexical checks alone can race the
   filesystem. Resolve beneath one trusted root, reject symlinks at every component
   and hash from one validated descriptor.
3. **Mutation during hashing.** A writer can change bytes during the read. Compare
   descriptor metadata before/after and fail without automatic retry.
4. **Alias ambiguity.** Hard links can present one file under several names. Reject
   duplicate opened file identities so membership counts cannot be inflated.
5. **Filesystem-order nondeterminism.** Directory order varies. Sort using fixed
   Unicode code-point ordering and never locale collation.
6. **Case and normalization collisions.** Filesystems differ in case sensitivity
   and Unicode normalization. Reject resource paths whose portable collision key
   conflicts, while hashing original UTF-8 path spelling into canonical bytes.
7. **Digest substitution.** An implicit or weak algorithm can be misread. Fix v1 to
   explicit SHA-256 and domain-separate the manifest fingerprint.
8. **Metadata mistaken for identity.** Size, mtime, inode, Parquet CRCs or footer
   statistics are not whole-file identities. Only the declared cryptographic
   digest establishes byte agreement.
9. **Live SQLite truncation.** Hashing only the main file can omit committed WAL
   state. Require a quiescent snapshot and reject live journal sidecars.
10. **Semantic/byte conflation.** Re-encoded Parquet or JSONL can differ in bytes
    while rows agree. Report byte and semantic outcomes independently.
11. **Environment fingerprint explosion.** Capturing every installed package makes
    reruns incomparable and leaks local state. Keep a closed, minimal diagnostic
    vocabulary tied to supported readers.
12. **Diagnostic policy smuggling.** A tool could convert a host difference into a
    failure. Differences are informational unless a separately reviewed policy
    promotes the exact field.
13. **Self-asserted provenance overclaim.** Runtime metadata can be forged by the
    process that emits it. Describe it as an observation, not authenticated origin.
14. **Sensitive summary leakage.** Paths and metadata can reveal customers,
    projects or schemas. Summary-safe output uses stable IDs, counts and reason
    codes only.
15. **Resource exhaustion.** Huge collections can exhaust descriptors or memory.
    Stream one file at a time, bound counts/path lengths, and use existing cleanup
    and interruption behavior.

## Non-goals

- data extraction, connectors, remote URLs, object-store listings or catalog sync;
- discovering which files, tables, partitions or schemas belong to a dataset;
- replacing BagIt, RO-Crate, Frictionless Data Package, SBOM or SLSA provenance;
- JSON-LD processing, remote context loading or a general metadata graph;
- dependency resolution, environment locking, containers or environment capture;
- byte-for-byte normalization or rewriting of SQLite, Parquet, JSONL or CSV;
- treating file digests as semantic row equality or semantic PASS as byte identity;
- proving source completeness, authorship, custody, authorization or freshness;
- embedded credentials, signing, timestamp authorities or transparency logs;
- glob languages, ignore files, recursive remote manifests or automatic repair;
- arbitrary environment collection or exposing local machine details;
- approval, deployment, rollback or cutover orchestration.

## Alternatives considered

### Put runtime provenance inside the canonical manifest

This makes identical datasets acquire different identities across Python patches,
operating systems or reader upgrades. It also encourages collection of sensitive
host state. Keep observations separately fingerprinted and promote only reviewed
fields through explicit policy.

### Use one semantic dataset digest instead of file digests

A semantic digest can prove projected equality but loses exact artifact identity,
format metadata and the ability to explain re-encoding. Existing Parison result
fingerprints already cover policy-scoped semantics. Preserve both layers.

### Adopt BagIt or Data Package directly

Both contain useful precedents, but their path, serialization, remote-resource and
hash compatibility surfaces do not match Parison's strict JSON and zero-network
core. A narrow native contract is smaller and can be exported later.

### Hash directory archives

Archive bytes depend on member order, timestamp, permission and tool behavior, and
hide membership diagnostics. Hash each declared regular file and canonicalize the
manifest instead.

### Infer scope from a directory on every run

This lets temporary files, editor artifacts and platform conventions change the
gate without policy review. Scope must be explicit and fingerprinted.

## Recommended delivery sequence

1. Specify strict schemas and byte fixtures for `dataset-manifest-v1`, path
   normalization, ordering and the new domain-separated fingerprint.
2. Implement safe local creation and verification for named regular files, with
   mutation, symlink, alias, missing and extra-member tests on supported platforms.
3. Bind manifests to existing suite/reconciliation policies and results without
   changing their canonical forms.
4. Add SQLite snapshot preflight and Parquet footer observations as bounded,
   format-specific checks; do not normalize either format.
5. Specify and implement `reproducibility-diagnostic-v1` plus deterministic
   comparison and summary-safe rendering.
6. Add opt-in `runtime-compatibility-v1` only after concrete cross-version fixtures
   demonstrate which runtime fields can alter interpretation.
7. Version the evidence bundle to carry manifest and diagnostic members, then run
   built-wheel CI on Python 3.11–3.14, macOS and Windows.

Do not add connector, package-manager, JSON-LD, archive or environment-capture
abstractions in this release.

## Checkable promotion gate

Promote the capability from research only when all of the following are true:

- two independently created manifests over identical policy and bytes have exactly
  the same canonical bytes on Python 3.11–3.14, macOS and Windows;
- fixture coverage proves stable ordering, path collision rejection, symlink and
  traversal refusal, hard-link alias refusal, mutation detection and atomic
  no-overwrite publication;
- missing, extra, size-mismatched and digest-mismatched members have distinct stable
  outcomes and never expose paths in summary-safe output;
- live/ambiguous SQLite inputs fail closed while quiescent snapshot fixtures remain
  readable, and Parquet byte differences remain distinct from semantic results;
- diagnostics compare deterministically, exclude sensitive host state and cannot
  affect status without an explicit fingerprinted compatibility policy;
- old recipes, suites, schemas, bundles, exit codes, canonical bytes and CLI JSON
  remain byte-for-byte compatible and old bundles remain readable;
- a realistic multi-dataset backfill can be verified from copied local artifacts
  using only the manifest, effective policies and bundle, with no network access;
- documentation states plainly that manifest PASS proves only declared local
  membership and byte identity, not extraction truth, approval or cutover safety.

The smallest coherent 1.4 slice is therefore not “package every dataset.” It is a
stable local collection identity plus a disciplined explanation layer: enough to
make migration and backfill evidence reproducible without turning Parison into a
custody, orchestration or environment-management system.
