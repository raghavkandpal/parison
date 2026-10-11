# Feature opportunities after Parison 0.12

Date: 10 October 2026

Status: **research recommendation**

## Starting point

Parison already has strict JSON recipes, installed Draft 2020-12 schemas, deterministic policy fingerprints, keyed/aggregate/multiset comparison, bounded evidence, recursively verified bundles, suite selection and external sharding, verified resume, CI reports, and development support for bounded local concurrency. The opportunities below preserve local execution, exact semantics, deterministic publication, and zero custody.

## Ranked recommendation

### 1. Ship editor-ready schemas and a local run catalog

This is the widest low-risk workflow slice. Publish stable schema identifiers for recipes and suite plans, add descriptions/examples to the existing schemas, and document workspace associations for common editors. VS Code can associate local or remote schemas by `$schema` or `json.schemas` and uses them for validation, completion, and hover text; SchemaStore exposes the same model to many editors and tools ([VS Code JSON documentation](https://code.visualstudio.com/docs/languages/json), [SchemaStore catalog](https://www.schemastore.org/), [JSON Schema 2020-12 specification](https://json-schema.org/specification)). Keep runtime validation authoritative: editor support is assistance, not a weaker recipe dialect.

Pair this with an optional **local run catalog** backed by Python's standard-library `sqlite3`: `parison catalog add RUN`, `list`, and `show`. Store only verified, summary-safe metadata plus bundle paths and manifest digests; never copy raw evidence. SQLite is serverless and disk-backed, so this adds searchable local history without hosted custody or a daemon ([Python `sqlite3` documentation](https://docs.python.org/3/library/sqlite3.html)).

Concrete seams:

- schema resources remain owned by the schema module; add stable `$id` values and checked-in editor association examples;
- a new catalog module consumes the existing verified `inspect` projection, not bundle internals;
- catalog writes are explicit and transactional; comparisons do not silently mutate a global database;
- relocation is handled by re-indexing or an explicit path update, never by guessing bundle identity.

Acceptance gates:

1. every shipped example validates identically through CLI and editor schema;
2. offline workspace associations work without fetching a schema;
3. cataloging a raw-sensitivity bundle stores no raw keys or values;
4. missing, moved, modified, and duplicate bundles have deterministic states;
5. the catalog can be deleted without affecting any bundle or comparison.

Risk is modest: schema URLs need a versioning policy, and a catalog path is mutable local state. Both are isolated from comparison semantics.

### 2. Prototype an explicit spill-backed execution mode

Larger-than-memory exact comparison is a strong product fit, especially for high-cardinality keyed and multiset cases. It must be an explicit backend with the same canonical input and result contracts—not a silent engine switch.

Two credible implementations differ materially:

| Candidate | Strength | Main cost | Recommendation |
| --- | --- | --- | --- |
| SQLite | Already in Python; disk-backed tables and indexes; transient `ORDER BY`, `GROUP BY`, and `DISTINCT` structures can spill after their page caches fill ([SQLite temporary files](https://www.sqlite.org/tempfiles.html)). | Parison must implement ingestion, canonical typed encoding, indexing, joins, cleanup, and performance tuning; SQLite's temporary-file behavior is explicitly not an application contract. | Prototype first as the semantic reference and dependency-free fallback. |
| DuckDB | Native larger-than-memory grouping, joining, sorting, and windowing with configurable `temp_directory`, `memory_limit`, and `max_temp_directory_size` ([DuckDB larger-than-memory guide](https://duckdb.org/docs/stable/guides/performance/how_to_tune_workloads), [configuration](https://duckdb.org/docs/stable/configuration/overview)). | New binary dependency; some operations still exceed the buffer-manager limit or cannot spill; unordered SQL results and engine type/coercion rules cannot define Parison semantics ([DuckDB OOM guidance](https://duckdb.org/docs/stable/guides/performance/oom), [order preservation](https://duckdb.org/docs/stable/sql/dialect/order_preservation)). | Benchmark after the SQLite reference; consider an optional extra only if it wins materially. |

Concrete seam: normalize each input row through Parison's existing type and canonical-encoding layer, then hand canonical keys/values to a private disk index. The backend may find matches and counts, but Parison owns null equality, decimals, tolerances, evidence ordering, limits, and outcome reduction. Temporary storage belongs inside the run workspace so interruption and resume rules can clean or reject it predictably.

Acceptance gates:

1. byte-equivalent semantic result content against the current engine for keyed, aggregate, and multiset golden corpora;
2. forced spill demonstrated under a fixed memory ceiling on Linux, macOS, and Windows;
3. bounded temp bytes, explicit disk-full behavior, atomic output, and no orphaned sensitive files after success or interruption;
4. deterministic evidence order independent of query plan, thread count, and insertion order;
5. encrypted-input expectations documented—the spill area may contain derived sensitive data;
6. benchmarks show the scale reached, wall time, peak RSS, and peak temporary storage without claiming a universal bound.

Do not make DuckDB the default merely because it spills: its documentation notes that multiple blocking operators and some aggregate states can still fail out of memory, while its default memory limit applies only to the buffer manager.

### 3. Add detached bundle signatures as an integration, not a trust oracle

Parison manifests already bind bundle files by digest. The smallest trustworthy addition is to define a canonical **manifest-signing target** and document detached signing and verification with an external tool. Sigstore Cosign can sign arbitrary files and its recommended bundle carries the signature, certificate, and transparency-log proof; verification can constrain certificate identity and issuer ([Sigstore blob signing](https://docs.sigstore.dev/cosign/signing/signing_with_blobs/), [Sigstore verification](https://docs.sigstore.dev/cosign/verifying/verify/)). This keeps credentials, OIDC, keys, KMS, and network policy outside Parison.

Concrete seam:

- `parison signing-payload RUN --output manifest.payload` emits a domain-separated canonical statement containing the manifest digest, schema version, and bundle kind;
- `verify` continues to mean internal integrity; a separate `verify-signature` wrapper, if later justified, invokes no network unless the user explicitly selects a Sigstore policy;
- signer identity and trust policy are caller inputs, never inferred from “signature present.”

Acceptance gates:

1. signing one bundle cannot validate another bundle or another artifact type;
2. path, timestamp, and JSON formatting changes outside the signed semantic target cannot introduce nondeterminism;
3. offline self-managed-key and identity-constrained keyless examples are tested;
4. signature absence does not change ordinary bundle verification;
5. documentation clearly separates integrity, signer authentication, transparency inclusion, and upstream data truth.

Do **not** label local comparison metadata “SLSA provenance.” SLSA provenance describes how software build outputs were produced and places trust in an identified build platform ([SLSA provenance](https://slsa.dev/spec/v1.2/provenance), [SLSA terminology](https://slsa.dev/spec/v1.0/terminology)). A Parison run is not necessarily a software build, and a self-reported local invocation does not create an independent trusted builder. A generic in-toto-style attestation could be explored later only after Parison defines a precise predicate and verifier policy.

## Features to defer

- **SARIF export:** SARIF is standardized for static-analysis results tied to programming artifacts. GitHub accepts third-party SARIF as code-scanning alerts, with repository/source-location and size constraints ([OASIS SARIF project](https://github.com/oasis-tcs/sarif-spec), [GitHub SARIF upload](https://docs.github.com/en/code-security/how-tos/find-and-fix-code-vulnerabilities/integrate-with-existing-tools/upload-sarif-file)). Parison discrepancies concern data snapshots, usually have no source-code location, and should not masquerade as vulnerabilities. Existing Markdown and JUnit reports are the better CI seam.
- **Automatic data repair or fuzzy matching:** both change the question from verifying a reviewed policy to inventing correspondence or modifying data. They weaken reproducibility and can conceal migration defects.
- **Remote connectors and hosted history:** credentials, pagination, snapshot consistency, retention, deletion, tenancy, and network failure would dominate the trust model. Local materialized snapshots and the proposed catalog preserve zero custody.
- **A UI or YAML dialect:** neither increases comparison capability. Editor-aware JSON addresses authoring friction while retaining one strict, canonicalizable syntax.

## Suggested sequence

After closing the remaining 0.12 interruption gate, make the next release a workflow slice: stable editor schemas plus the opt-in local catalog. Run spill execution as a separately gated prototype against the current engine; promote it only after semantic equivalence and sensitive-temp cleanup are proven. Add the canonical signing payload after that, while leaving actual trust establishment to Sigstore or another external signer.
