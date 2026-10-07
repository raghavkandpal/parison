# Parison user guide

This guide covers the current 0.2 development workflow: prepare two local tabular snapshots, review a deterministic comparison recipe, run the comparison, investigate its evidence bundle and repeat the same policy safely.

Parison is local and zero-custody. It does not extract data from production systems, upload inputs, decide which dataset is correct or approve comparison policy for you.

## 1. Choose how to run Parison

Python 3.11 or newer is required.

The published release is 0.2.0:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install \
  https://github.com/raghavkandpal/parison/releases/download/0.2.0/parison-0.2.0-py3-none-any.whl
parison --version
```

To evaluate the current checkout without confusing it with an installed release, prefix commands with `PYTHONPATH=src python -m parison`:

```sh
PYTHONPATH=src python -m parison --version
```

The shorter `parison` spelling below refers to either the installed 0.2 release or the checkout invocation above.

## 2. Prepare comparable snapshots

Create a baseline snapshot and a candidate snapshot representing the same intended population and cutoff.

- **Baseline** is the reference side of the comparison, not automatically the truth.
- **Candidate** is the new output being evaluated.
- Both sides must contain the declared key and compared columns.
- Extraction filters, cutoff and completeness must be known before a result can support a decision.
- Close or freeze upstream writers before comparing. Parison checks that inputs do not change while it reads them, but cannot prove that an upstream export is complete.

Supported inputs on `develop` are:

| Input | How to identify it | Important boundary |
| --- | --- | --- |
| CSV | `.csv` | UTF-8, one header row, no duplicate columns or ragged rows |
| Parquet | `.parquet` or `.pq` | Install the optional `parison[parquet]` dependency; nested values are rejected |
| JSON Lines | `.jsonl` or `.ndjson` | One flat JSON object per line; no blank lines, arrays, nested objects or inconsistent fields |
| SQLite table | `'sqlite:path/to/file.db#table'` | One ordinary local table, read-only; no views, SQL, BLOBs or active WAL/journal sidecars |

The two sides may use different supported formats. Format is an input detail; the recipe and result contract remain the same.

## 3. Draft a recipe

```sh
parison draft-recipe \
  --baseline path/to/baseline.csv \
  --candidate path/to/candidate.csv \
  --output comparison.recipe.json
```

The output file must not already exist.

### Why drafting needs both inputs

The draft describes the boundary between two schemas, not only the baseline. Parison uses both sides to:

- retain exact shared column names in baseline order;
- expose baseline-only and candidate-only columns as unresolved exclusions;
- reject pairs with no shared columns; and
- catch malformed or duplicate schemas before policy review.

Drafting reads both inputs and suggests keys, types, scope metadata and exclusion rationales. It does not infer tolerances, and every suggestion still requires human review. A candidate is required for the current command. If you need to author policy before a candidate exists, start from [`examples/orders.recipe.json`](../../examples/orders.recipe.json) and validate it later against the actual pair.

## 4. Review every recipe decision

The generated JSON is structurally valid so you can review concrete starting values. Confirm the keys, scope, null handling, types and exclusions before comparison; validation cannot determine whether those semantics are correct for your data.

### Identity

Choose one or more columns whose typed values uniquely identify a record:

```json
"keys": ["order_id"]
```

Key comparison is always exact. Null key components and duplicate keys are rejected; they produce an inconclusive comparison rather than an arbitrary join or false PASS.

### Scope and provenance

Describe what both snapshots are intended to contain:

```json
"scope": {
  "snapshot": "orders-export-v3",
  "cutoff": "2026-10-06T00:00:00Z",
  "filters": ["status != 'deleted'"],
  "completeness": "full",
  "expected_empty": false
}
```

These fields are recorded assertions. Parison does not run or verify the upstream extraction query.

### Null equality

Set `nulls_equal` explicitly:

- `true`: two null non-key values are exact matches;
- `false`: two null non-key values are differences.

One null and one non-null value always differ. An empty CSV string is parsed as null for non-string types but remains an empty value for a string column.

### Column types

Choose one type for every included column:

- `string` — exact text, including case and whitespace;
- `integer` — exact whole number;
- `decimal` — exact decimal with a required non-negative `scale`;
- `float` — finite binary floating-point value;
- `boolean` — strict `true` or `false`;
- `date` — ISO calendar date;
- `timestamp` — ISO timestamp with an explicit timezone and `"timezone": "require-aware"`.

Parison does not trim strings, fold case, normalize Unicode or cast string keys unless the recipe's declared type does so.

### Exact and numeric comparison

Use `"comparison": "exact"` unless a reviewed numerical tolerance is required. Numeric comparison is valid only for integer, decimal or float columns and requires all tolerance fields:

```json
"amount": {
  "type": "decimal",
  "scale": 2,
  "comparison": "numeric",
  "tolerance": {
    "formula": "symmetric-v1",
    "absolute": "0.10",
    "relative": "0"
  }
}
```

The allowance is `absolute + relative × max(abs(baseline), abs(candidate))`. Tolerances must be finite and non-negative. A value inside tolerance is reported as `within_tolerance`, not as byte-for-byte exact.

### Exclusions

Every input column must be included in `columns` or excluded with a nonempty reason:

```json
"excluded_columns": {
  "updated_at": "nondeterministic load metadata"
}
```

An exclusion removes that column from comparison. Review it as policy, not cleanup.

### Evidence sensitivity

Keep the default unless raw investigation evidence is necessary:

```json
"output": {"sensitivity": "summary"}
```

- `summary` stores complete counts and policy metadata without source keys or raw values.
- `raw` adds a bounded discrepancy sample containing keys and values. Treat the entire bundle as sensitive.

Schema names, table names and recipe metadata may themselves be sensitive even in summary mode.

## 5. Validate the recipe

```sh
parison validate-recipe comparison.recipe.json
```

Do not compare until validation prints `valid`. Validation checks recipe structure and policy constraints; it does not approve whether your chosen key, tolerance, exclusion or scope is appropriate.

Keep reviewed recipes in version control when their schema metadata is safe for that repository. Review recipe changes independently from the candidate code so the code under test cannot relax its own gate.

## 6. Run the comparison

Use a new output directory for every run:

```sh
parison compare \
  --recipe comparison.recipe.json \
  --baseline path/to/baseline.csv \
  --candidate path/to/candidate.csv \
  --output runs/orders-2026-10-06
```

For raw evidence, limit the published sample if needed:

```sh
parison compare \
  --recipe raw.recipe.json \
  --baseline baseline.csv --candidate candidate.csv \
  --sample-limit 50 --output runs/raw-investigation
```

Default guards are 1 GB combined input bytes and 5 million rows per side. `--max-input-bytes` and `--max-rows` may change processing limits, but they are not memory or operating-system sandboxes.

## 7. Interpret the outcome and exit code

| Outcome | Exit | Meaning |
| --- | ---: | --- |
| `PASS` | 0 | The complete comparison satisfies the reviewed recipe; within-tolerance differences may still exist |
| `FAIL` | 1 | The comparison completed and found required differences |
| `ERROR` | 2 | Input, recipe, parsing, resource or publication failure prevented a valid comparison |
| `INCONCLUSIVE` | 3 | Identity or scope conditions prevent a trustworthy equivalence decision |
| `INTERRUPTED` | 130 | The run was interrupted, normally with Ctrl-C |

Exit `1` is evidence, not a crashed command. Automation must preserve nonzero codes while still retaining the generated bundle.

## 8. Review the evidence bundle

A completed run directory contains:

| File | Purpose |
| --- | --- |
| `result.json` | Canonical machine-readable outcome, counts, policy and provenance |
| `effective-recipe.json` | Exact reviewed rules used by the run |
| `report.html` | Self-contained human investigation report |
| `manifest.json` | File digests and recorded outcome for integrity checking |

Open `report.html` directly in a browser. Start with scope, policy, record counts and field counts. In 0.2 reports:

- field-summary controls show fields with exact, within-tolerance or required differences;
- raw reports can filter the bounded sample by key text, field or class; and
- “Showing N of M” describes currently visible rows. For raw evidence, `M` is the sampled row count, not necessarily every discrepancy in the full dataset.

Filtering only changes the displayed report rows. It never modifies `result.json`, the recorded outcome or the manifest.

## 9. Verify bundle integrity

```sh
parison verify runs/orders-2026-10-06
```

Verification recomputes the manifest digests and detects missing or changed bundle files. It does not rerun the comparison, prove the inputs were complete or change FAIL into PASS.

Retain all four files together. If the recipe uses raw sensitivity, apply access controls and retention appropriate for the source values in the report and result.

## 10. Repeat a reviewed comparison

For a later candidate:

1. Preserve the reviewed recipe unchanged.
2. Produce a new candidate snapshot with the same declared scope and cutoff convention.
3. Run `compare` into a new output directory.
4. Verify and review the new bundle.
5. If policy must change, review that recipe change explicitly and treat it as a new decision—not as approval of the old result.

Never overwrite or edit an old bundle to represent a new run.

## 11. Use Parison in GitHub Actions

Copy [`examples/github-actions/parison.yml`](../../examples/github-actions/parison.yml) into the consuming repository and replace its recipe and input-generation paths.

The reference workflow:

- runs locally on a GitHub-hosted runner;
- permits comparison exit codes long enough to upload the bundle;
- restores the original outcome code afterward;
- refuses non-summary recipes; and
- uses read-only permissions without `pull_request_target`.

GitHub artifact storage remains under the repository owner's control. Review repository visibility, schema sensitivity, artifact access and retention. Never expose production credentials or raw baselines to untrusted fork jobs.

## 12. Common problems

| Symptom | What to do |
| --- | --- |
| `draft-recipe` refuses an existing destination | Choose a new path or deliberately remove the old draft after preserving anything needed |
| Validation reports unresolved fields | Edit the generated JSON; `draft-recipe --help` lists the required decisions |
| Schema mismatch or unexpected column | Reconcile the exports or add a reviewed exclusion with a reason |
| Duplicate/null key produces `INCONCLUSIVE` | Fix identity or source data; do not increase tolerance |
| Comparison returns exit `1` | Review the valid FAIL bundle; the run completed with required differences |
| Parquet support is unavailable | Install the wheel with its `parquet` extra or install the pinned optional Polars dependency for development |
| JSON Lines fails on a blank/nested record | Emit exactly one flat object with a consistent field set per line |
| SQLite reports an active sidecar | Close/checkpoint the writer or copy a stable database snapshot, then retry |
| `verify` fails | Treat the bundle as incomplete or modified; recover or rerun from trusted inputs |
| Browser filtering is unavailable | The complete report remains readable without JavaScript; use its tables or canonical JSON |

## 13. Know the trust boundary

Parison can establish deterministic comparison behavior for the bytes and reviewed policy it receives. It cannot establish that:

- the baseline is correct;
- upstream extraction used the declared filters or cutoff;
- a key or tolerance is appropriate for the business decision;
- an excluded field is irrelevant;
- a verified bundle's semantic outcome should be approved; or
- local execution alone makes sensitive artifacts safe.

Those are human review responsibilities. For formal 0.2 validation, follow the [human-results checklist](26-human-results-checklist.md).

## Further reference

- [Comparison semantics](../0.1/05-comparison-semantics.md)
- [Security and data handling](../0.1/07-security-and-data-handling.md)
- [Recipe draft contract](22-recipe-draft-contract.md)
- [JSON Lines contract](23-json-lines-contract.md)
- [SQLite contract](24-sqlite-contract.md)
- [GitHub Actions reference](20-github-actions.md)
