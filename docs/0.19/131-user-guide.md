# Parison 0.19 user guide

Status: **authoritative consolidated workflow and command manual**

Parison compares local baseline and candidate outputs under an explicit reviewed policy, then publishes deterministic portable evidence. PASS means agreement under that policy. It does not prove extraction truth, approve the policy or authorize a cutover.

This guide consolidates the operational guidance previously introduced across versioned user guides. Historical guides remain the normative record for their releases; this is the single current entry point for using every supported command.

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

## Command reference

Run `parison COMMAND --help` for the installed version's exact parser. Paths passed as outputs must not already exist; Parison publishes atomically and refuses overwrite.

### `parison --version`

Print the installed Parison version. Record this alongside evidence and troubleshooting output.

```sh
parison --version
```

### `parison init`

Create a minimal keyed migration project containing a recipe, two sample inputs and usage instructions. The destination must be absent or empty. Generated policy is a starting point, not approval.

```sh
parison init migration-check
```

### `parison draft-recipe`

Inspect two local inputs and write a suggested recipe. The default is keyed; select exactly one of `--aggregate` or `--multiset` for those modes. Review keys, scope, exclusions, types, tolerances, normalization and sensitivity before use.

```sh
parison draft-recipe --baseline old.csv --candidate new.csv --output recipe.json
parison draft-recipe --aggregate --baseline old.csv --candidate new.csv --output totals.json
parison draft-recipe --multiset --baseline old.csv --candidate new.csv --output rows.json
```

`--max-input-bytes` and `--max-decoded-bytes` bound inspection. Drafting never compares records or approves its suggestions.

### `parison validate-recipe`

Validate recipe structure and policy rules without reading inputs. Success prints `valid`; invalid recipes exit 2 with a controlled diagnostic.

```sh
parison validate-recipe recipe.json
```

### `parison explain`

Print the effective, data-free policy as JSON, including defaults and `policy_sha256`. Use the fingerprint to lock an approved policy before input access.

```sh
parison explain recipe.json > effective-policy.json
```

### `parison validate-inputs`

Check input schemas, mappings and partition layouts against a recipe. Add `--records` to scan types and mode-specific identity across all records.

```sh
parison validate-inputs --recipe recipe.json \
  --baseline baseline.csv --candidate candidate.csv --records \
  --expected-policy-sha256 "$POLICY"
```

The byte, decoded-byte, row, group and distinct-row limits are hard guards. JSON diagnostics go to stdout; the command exits 0 only when valid and 2 otherwise. Preflight does not publish comparison evidence.

### `parison compare`

Run one comparison and publish a deterministic run bundle.

```sh
parison compare --recipe recipe.json \
  --baseline baseline.csv --candidate candidate.csv \
  --expected-policy-sha256 "$POLICY" \
  --output runs/rehearsal-01
```

Important options:

- `--sample-limit N` bounds published raw discrepancy samples; it has no effect on summary evidence.
- `--max-input-bytes`, `--max-decoded-bytes`, `--max-rows`, `--max-groups` and `--max-distinct-rows` fail closed at resource boundaries.
- `--engine sqlite` is explicit and supports keyed and multiset recipes. Pair it with `--max-temp-bytes`; `--temp-directory` selects an existing parent for the private temporary workspace.
- `--expected-policy-sha256` rejects an unapproved effective policy before reading inputs.

Stdout contains a small JSON result locator, stderr contains a human summary, and the process uses the outcome exit codes below. FAIL still publishes complete verifiable evidence.

### `parison verify`

Verify manifest-covered bytes and internal bundle semantics recursively. It does not authenticate a signer, approve policy or assert extraction truth.

```sh
parison verify runs/rehearsal-01
parison verify runs/rehearsal-01 --json
```

`--json` emits verified manifest metadata for automation. The command never repairs or rewrites a bundle.

### `parison inspect`

Verify a run, suite or suite-shard bundle and print its summary-safe projection. Use this for triage without exposing raw discrepancy evidence.

```sh
parison inspect runs/rehearsal-01
```

### `parison export-evidence`

Export a bounded JSON Lines subset from an already verified raw-sensitivity run. Summary bundles cannot be upgraded to raw evidence.

```sh
parison export-evidence runs/raw-failure --output evidence.jsonl \
  --classification different --kind field --name amount --limit 100
```

Filters are exact. `--kind` accepts `record`, `field`, `group`, `measure` or `row`. Treat the output as source-sensitive data.

### `parison validate-suite`

Validate a suite plan and every referenced recipe/input path without executing comparisons.

```sh
parison validate-suite cutover-suite.json
```

### `parison list-suite`

List the deterministic case selection without reading case inputs. Repeat `--case ID` or `--tag TAG` to filter; supply `--shard-index` and `--shard-count` together for an external shard. `--json` provides structured output.

```sh
parison list-suite cutover-suite.json --tag required --json
parison list-suite cutover-suite.json --shard-index 0 --shard-count 4
```

### `parison run-suite`

Execute selected suite cases and atomically publish a suite or suite-shard bundle.

```sh
parison run-suite --plan cutover-suite.json --output evidence/cutover \
  --tag required --jobs 2
```

Selection options match `list-suite`. `--jobs` accepts 1–16 and preserves plan-order results; resource limits apply to each active case. `--workspace DIRECTORY` retains verified case checkpoints, and `--resume` reuses only children whose integrity, policy, limits, versions and current inputs still match. The comparison limit options apply to every selected case unless suite-v2 defines a stricter effective value.

### `parison assemble-suite`

Verify external suite shards, require exact non-overlapping plan coverage and publish one deterministic assembled suite.

```sh
parison assemble-suite --plan cutover-suite.json \
  --input evidence/shard-0 --input evidence/shard-1 \
  --output evidence/assembled
```

Assembly does not rerun cases and rejects missing, duplicate, mismatched or modified shard evidence.

### `parison report-ci`

Verify a suite bundle and export a bounded summary-safe Markdown or JUnit projection for CI presentation.

```sh
parison report-ci evidence/cutover --format markdown --output summary.md
parison report-ci evidence/cutover --format junit --output results.xml
```

The report is derived evidence, not the portable source bundle.

### `parison catalog add`

Verify a run, suite or shard and index only its safe metadata in a local SQLite catalog. Re-adding the same current bundle is idempotent; a different bundle at an indexed path is rejected.

```sh
parison catalog add runs/rehearsal-01 --database .parison/catalog.sqlite
```

### `parison catalog list`

List indexed entries and their live state. Filter by `--outcome`, `--kind`, exact `--policy-sha256`, or `--state current|modified|missing`.

```sh
parison catalog list --database .parison/catalog.sqlite --state current
```

### `parison catalog show`

Show one indexed path's stored safe projection and current state.

```sh
parison catalog show runs/rehearsal-01 --database .parison/catalog.sqlite
```

### `parison catalog history`

Show insertion-ordered ordinary runs and outcome/discrepancy transitions for one exact policy fingerprint.

```sh
parison catalog history --database .parison/catalog.sqlite \
  --policy-sha256 "$POLICY"
```

### `parison catalog diff`

Compare stored safe projections of two ordinary run bundles with the same policy. It reports metadata/count changes without reading raw result evidence.

```sh
parison catalog diff --database .parison/catalog.sqlite \
  runs/rehearsal-01 runs/rehearsal-02
```

### `parison catalog remove`

Remove one indexed path from the catalog without deleting or modifying its bundle.

```sh
parison catalog remove runs/rehearsal-01 --database .parison/catalog.sqlite
```

### `parison statement`

Verify a bundle and atomically export a deterministic unsigned in-toto Statement binding its exact manifest bytes and safe policy projection.

```sh
parison statement evidence/cutover --output parison-statement.json
```

Authenticate those exact Statement bytes outside Parison with an approved signer.

### `parison verify-statement`

After the receiving boundary authenticates the Statement, verify that it is well formed and binds the exact local verified bundle.

```sh
parison verify-statement evidence/cutover parison-statement.json
```

This command deliberately performs no cryptography, network access or signer authorization.

### `parison report-cutover`

Verify a run, suite or suite shard and atomically export a deterministic summary-safe Markdown cover sheet for human approval.

```sh
parison report-cutover evidence/cutover --output cutover.md
```

The report separates extraction, comparison, authentication and approval facts; generating it does not authorize cutover.

### `parison schema`

Print one installed Draft 2020-12 JSON Schema to stdout. Names include recipe/result/preflight versions, manifest versions, suite plan/result/manifest versions, authoring schemas and `statement`.

```sh
parison schema recipe-v3 > recipe-v3.schema.json
parison schema statement > statement.schema.json
```

### `parison export-editor-schemas`

Atomically export the offline recipe and suite authoring schemas for editor configuration.

```sh
parison export-editor-schemas --output .parison/editor-schemas
```

Runtime validation remains authoritative.

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
