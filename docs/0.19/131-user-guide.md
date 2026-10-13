# Parison 0.19 user guide

Status: **authoritative consolidated workflow**

Parison compares local baseline and candidate outputs under an explicit reviewed policy, then publishes deterministic portable evidence. PASS means agreement under that policy. It does not prove extraction truth, approve the policy or authorize a cutover.

## Install and start

Python 3.11 or newer is required.

```sh
python -m pip install /path/to/parison-0.19.0-py3-none-any.whl
parison --version
parison init migration-check
cd migration-check
```

The generated sample is a smoke test. Replace its inputs and review `recipe.json` before using it as migration evidence. Initialization never overwrites a nonempty directory.

## Primary migration and backfill workflow

### 1. Materialize coordinated outputs

Create baseline and candidate files at the same logical snapshot or watermark using source-owned extraction jobs. Keep database credentials and network access outside Parison. Retain source-owned receipts when the systems can attest the snapshot, query or job identity, row count, completion status and output digest.

Supported inputs are local CSV or TSV, JSON Lines, Parquet and read-only SQLite tables. Partitioned directories and bounded gzip text inputs are supported under their published contracts. Convert other formats upstream; see the [non-CSV research](124-non-csv-input-research.md) for the trust boundary.

### 2. Review the policy

Review every recipe field rather than approving generated suggestions implicitly:

- `scope.snapshot`, `cutoff`, `filters`, `completeness` and `expected_empty` describe the supplied extracts;
- keys must be stable, non-null and unique for keyed comparison;
- every included column needs an explicit type and comparison;
- mappings and exclusions need reviewed names and rationales;
- tolerances and normalization change equality and therefore require approval;
- `output.sensitivity` should remain `summary` unless bounded raw discrepancies are explicitly required and protected.

`draft-recipe` can create a starting point for keyed, aggregate or multiset comparison. Its output is a suggestion, never policy approval.

### 3. Preflight and lock the policy

```sh
parison validate-recipe recipe.json
parison validate-inputs --records --recipe recipe.json \
  --baseline baseline.csv --candidate candidate.csv

POLICY=$(parison explain recipe.json |
  python -c 'import json,sys; print(json.load(sys.stdin)["policy_sha256"])')
```

Review the complete `explain` output. Store the accepted fingerprint in the migration review or CI configuration. The fingerprint proves exact policy equality only; it is not a signature or approval record.

### 4. Run and retain rehearsals

```sh
mkdir -p runs .parison

parison compare --recipe recipe.json \
  --expected-policy-sha256 "$POLICY" \
  --baseline baseline.csv --candidate candidate.csv \
  --output runs/rehearsal-01

parison verify runs/rehearsal-01
parison inspect runs/rehearsal-01
parison catalog add --database .parison/catalog.sqlite runs/rehearsal-01
```

Use a new output path for every rehearsal. Repeat after correcting the candidate or refreshing both coordinated extracts, then compare verified safe projections:

```sh
parison catalog history --database .parison/catalog.sqlite \
  --policy-sha256 "$POLICY"
parison catalog diff --database .parison/catalog.sqlite \
  runs/rehearsal-01 runs/rehearsal-02
```

History is meaningful only under one exact policy. Input digests show whether supplied bytes changed; they do not prove coordinated extraction.

### 5. Layer the cutover suite

Use a suite when the decision needs aggregate conservation plus exact keyed or multiset parity. Each case owns a reviewed recipe; the suite fixes case order and execution policy.

```sh
parison validate-suite cutover-suite.json
parison run-suite --plan cutover-suite.json --output evidence/cutover
parison verify evidence/cutover
parison inspect evidence/cutover
parison report-ci evidence/cutover --format markdown \
  --output parison-summary.md
```

A production gate normally requires the expected policy identity, `outcome == PASS`, `complete == true`, full suite scope and authenticated source-owned extraction guarantees.

### 6. Authenticate and hand off evidence

```sh
parison statement evidence/cutover --output parison-statement.json

# Authenticate these exact bytes with the organization's reviewed signer.

parison verify-statement evidence/cutover parison-statement.json
parison report-cutover evidence/cutover --output cutover.md
```

The receiving boundary must authenticate the Statement before `verify-statement`, constrain signer identity and issuer, and independently require the expected policy, outcome, completeness and scope. Follow the [evidence handoff guide](../0.17/116-evidence-handoff-guide.md) for the pinned Cosign workflow.

| Evidence | Establishes | Does not establish |
| --- | --- | --- |
| Extraction receipt | Source-owned snapshot and completion claims | Parison equality |
| Verified Parison bundle | Integrity and comparison outcome under its recorded policy | Policy approval or extraction truth |
| Authenticated Statement | An authorized identity signed the exact bundle claim | Cutover authorization |
| Consumer gate decision | Required identity, policy, outcome and scope were accepted | Future correctness after cutover |

The cutover owner—not Parison—reviews these facts and authorizes the change.

## Comparison modes

### Keyed

Recipe version 1 matches rows by reviewed unique keys and compares configured non-key fields exactly or with the symmetric-v1 numeric tolerance. Null keys and duplicate keys are rejected. Use keyed mode when records have stable identities and row-level diagnosis matters.

### Aggregate

Recipe version 2 computes global or grouped `count`, `sum`, `min` and `max` measures. Integer and scaled-decimal sums are exact; numeric tolerances are explicit. Use aggregate mode as a cheap conservation layer, not as proof of row parity.

### Multiset

Recipe version 3 compares complete canonical row occurrence counts without keys. Duplicate multiplicity matters. Use multiset mode when every row occurrence must be conserved but stable keys do not exist.

Memory execution is the default. Keyed and multiset modes may explicitly select SQLite with `--engine sqlite --max-temp-bytes BYTES`; this trades runtime and local disk for lower process memory without changing comparison meaning. Parison never selects an engine automatically.

## Inputs and typing

- CSV and TSV support explicit side-specific one-character delimiters and null-token lists.
- JSON Lines requires one object per nonblank line and consistent columns across each logical input.
- Parquet requires the optional `parison[parquet]` dependency and rejects unsupported nested values.
- SQLite input uses `sqlite:PATH#TABLE`, opens the database read-only and rejects views, BLOB values and active journal state.
- Directories represent one logical input only when every immediate file has the same supported format and compatible schema.
- `.csv.gz`, `.tsv.gz`, `.jsonl.gz` and `.ndjson.gz` are bounded by both physical and decoded-byte limits.

Configured column types are string, integer, decimal, float, boolean, date and timezone-aware timestamp. String normalization is opt-in and ordered: `trim`, `casefold`, then/or `unicode_nfc` exactly as listed. Missing, null and empty-string behavior follows the format and explicit null-token policy; Parison does not collapse them silently.

## Suites, sharding and concurrency

Suite-v2 supports tags, explicit case IDs, deterministic external shards, exact-coverage assembly and resumable workspaces. `run-suite --jobs N` runs independent cases locally with one to sixteen workers while preserving declared result order. Resource limits apply per active case, so peak use can approach `N` times one case.

Use external orchestration for distributed execution. Parison accepts materialized local inputs and emits portable bundles; it does not hold warehouse credentials or schedule extraction.

## Outcomes and exit codes

| Outcome | Exit | Meaning |
| --- | ---: | --- |
| PASS | 0 | Complete comparison agreed under policy |
| FAIL | 1 | Complete comparison found differences |
| ERROR | 2 | Input, policy, resource or operational failure |
| INCONCLUSIVE | 3 | The declared comparison could not establish a complete result |
| INTERRUPTED | 130 | Execution was interrupted |

Do not collapse the non-PASS outcomes. A FAIL is valid completed evidence; ERROR and INTERRUPTED are not. Verify any published bundle before inspecting or handing it off.

## Investigation and safe output

`parison inspect BUNDLE` returns a verified summary-safe projection. `output.sensitivity` defaults to `summary`, which stores no source paths, keys, values or discrepancy samples. Raw sensitivity retains a bounded sample and must be protected as source data.

```sh
parison export-evidence BUNDLE --limit 100 --output evidence.jsonl
```

Evidence export works only for an existing raw-sensitivity bundle and supports exact classification, field or measure filters. It does not rerun the comparison or upgrade summary evidence into raw evidence.

## Resource and security boundaries

Default direct-comparison guards are 1 GB combined physical input, 1 GB combined decoded gzip input and five million rows per side. Mode-specific group, distinct-row and SQLite temporary-byte limits also apply. These values are processing guards, not capacity promises; use the [machine-qualified performance envelope](127-performance-envelope.md) to plan representative measurements.

Parison performs no network access, credential use, signing, repair or remote orchestration. Protect inputs, raw bundles, catalogs, receipts, Statements and reports according to their metadata sensitivity. Publication is atomic and no-overwrite; preserve released bundles byte-for-byte rather than repairing them in place.

## Schemas and compatibility

Use `parison schema NAME` or `parison export-editor-schemas --output DIRECTORY` for installed Draft 2020-12 schemas. Runtime validation remains authoritative. The [compatibility contract](126-compatibility-contract.md) freezes released recipe meaning, artifact readability, CLI exit meanings, canonical encodings and summary-safety boundaries.

For normative details and specialized workflows, use the [documentation index](../README.md). The [1.0 readiness checklist](128-1.0-readiness-checklist.md) records which stability gates are complete and which still require a release decision.
