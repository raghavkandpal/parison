# Use Parison for a data-change gate

Parison compares local baseline and candidate outputs under an explicit policy,
then produces deterministic evidence that can be verified elsewhere. A `PASS`
means agreement under that policy. It does not prove extraction truth, approve
the policy or authorize a cutover.

This is the maintained guide for the released 1.x line and active 2.0
workbench development. The
[generated command reference](command-reference.md) lists every option; frozen
version contracts remain the normative record for artifact semantics.

## Install and start

Python 3.11 or newer is required.

```sh
python -m pip install /path/to/parison-1.5.0-py3-none-any.whl
parison --version
parison init migration-check
cd migration-check
```

The generated project is a smoke test. Replace its inputs and review every
field in `recipe.json`; initialization and drafting suggest policy but never
approve it.

## Choose the smallest workflow that establishes the needed claim

| Need | Workflow | Primary evidence |
| --- | --- | --- |
| Compare one logical dataset | direct comparison | run bundle |
| Gate several independent comparisons | suite | suite bundle |
| Review renamed or structurally changed fields | schema evolution | normalized declaration and policy diff |
| Check one window across related datasets | reconciliation | reconciliation bundle |
| Bind a declared file collection and runtime facts | dataset evidence | dataset-evidence bundle |
| Explain change across exact-policy rehearsals | discrepancy analysis | analysis bundle |
| Authenticate a completed bundle | evidence handoff | in-toto Statement plus external signature |

Keep extraction, credentials, signing and cutover approval outside Parison.
Use source-owned jobs to materialize coordinated local inputs and retain their
receipts separately.

## Start the unified Workbench

The active 2.0 interface is one Python-hosted local application. The host binds
only numeric loopback on an ephemeral port and requires a per-launch capability.
The application is still under development. Plans reviews CLI-native recipes;
Run preflights and executes one explicit local comparison; Results verifies a
bundle before display; History, Investigate and Compare operate only on verified
summary-safe evidence. Continue to use the released CLI for automation and
suite execution.

```sh
parison workbench --workspace .
```

Stop it with **Stop workbench** in the application or Ctrl-C in the launching
terminal. Closing the browser tab alone does not stop the local host. The
earlier generated evidence and plan applications were
prototypes and are not the 2.0 interface. Their safety contracts are being
migrated behind this unified host.

Workbench Run accepts workspace-relative paths for the recipe, baseline,
candidate and a new output bundle. Only one run can be active. Its progress
states are bounded, and **Cancel run** stops cooperatively while reading inputs;
no partial bundle is published. If atomic publication has already started, the
completed bundle is preserved, verified and registered instead of being
misreported as cancelled.

## Compare one dataset

### 1. Review and lock policy

Supported inputs are CSV/TSV, JSON Lines, explicit JSON document record arrays,
Parquet, read-only SQLite tables and explicit XLSX value ranges. Partitioned
directories and bounded gzip text inputs are also supported.

Select JSON document records with an RFC 6901 JSON Pointer. The selected value
must be an array of flat objects with consistent fields; duplicate members,
nested values and implicit array discovery are rejected:

```sh
parison draft-recipe \
  --baseline 'json:baseline.json#/exports/records' \
  --candidate 'json:candidate.json#/exports/records' \
  --output recipe.json
```

Review the generated `semantic-scalar-v1` policy. See the
[JSON document projection contract](1.8/178-json-document-projection-contract.md).

To select nested scalar fields from each JSON record, write and review a
recipe-version 4, 5 or 6 policy instead of relying on drafting. Each logical
field has one explicit RFC 6901 pointer, while a flat side uses an equally
explicit direct mapping:

```json
{
  "field_projection": {
    "version": 1,
    "baseline": {
      "kind": "json-pointer-v1",
      "fields": {"id": "/identity/id", "amount": "/totals/net"}
    },
    "candidate": {
      "kind": "direct-v1",
      "fields": {"id": "id", "amount": "amount"}
    }
  }
}
```

The maps must cover exactly the configured logical fields. Missing paths and
selected containers are errors; unselected members are outside comparison
scope. The selectors affect the policy fingerprint but are excluded from
summary results. See the
[JSON field-projection contract](1.9/189-json-field-projection-contract.md).

Select XML records with an exact root-to-record QName path and explicit,
percent-encoded namespace bindings:

```sh
parison draft-recipe \
  --baseline 'xml:baseline.xml#p:root/p:records/p:record?ns=p,https%3A%2F%2Fexample.com%2Fv1' \
  --candidate 'xml:candidate.xml#p:root/p:records/p:record?ns=p,https%3A%2F%2Fexample.com%2Fv1' \
  --output recipe.json
```

Records contain direct, attribute-free text child elements only. Parison
rejects DTDs, entities, XPath-like selection and undeclared namespaces. See
the [XML record projection contract](1.8/180-xml-record-projection-contract.md).

To project record attributes or bounded nested XML leaves, write and review a
recipe-version 4, 5 or 6 policy. The XML side owns a separate namespace map
and uses exact attribute or child-path selectors:

```json
{
  "kind": "xml-field-v1",
  "namespaces": {"o": "https://example.com/orders/v1"},
  "fields": {"id": "@id", "amount": "o:totals/o:net"}
}
```

Every attribute and branch in each selected record must belong to the declared
projection; missing, repeated, unselected and mixed-content shapes are errors.
Unprefixed selectors mean no namespace, including for attributes. Drafting
does not invent these selectors. See the
[XML field-projection contract](1.9/191-xml-field-projection-contract.md).

Install the XLSX extra, then identify the workbook and either one bounded
worksheet rectangle, one exact workbook table name or one exact
workbook-scoped defined name. The first row is the header:

```sh
python -m pip install 'parison[xlsx]'
parison draft-recipe \
  --baseline 'xlsx:baseline.xlsx#Export!A1:F1000' \
  --candidate 'xlsx:candidate.xlsx#Export!A1:F1000' \
  --output recipe.json
parison validate-inputs --records --recipe recipe.json \
  --baseline 'xlsx:baseline.xlsx#table=Orders' \
  --candidate 'xlsx:candidate.xlsx#table=Orders'
parison validate-inputs --records --recipe recipe.json \
  --baseline 'xlsx:baseline.xlsx#defined-name=OrdersExport' \
  --candidate 'xlsx:candidate.xlsx#defined-name=OrdersExport'
```

Review the generated `semantic-scalar-v1` policy. Formula and error cells are
rejected; Parison never infers the active sheet or used range and does not
evaluate formulas. Named tables use their stored rectangle and reject totals,
calculated columns and mismatched table/header metadata. See the released
[XLSX values contract](1.6/170-xlsx-values-projection-contract.md) and the
[named-table contract](1.8/183-xlsx-named-table-projection-contract.md).
Defined names must be exact, non-reserved, workbook-scoped static references
to one local absolute rectangle; local, dynamic, relative, external, union and
whole-row or whole-column definitions are rejected. See the
[defined-name contract](1.9/193-xlsx-defined-name-contract.md).

```sh
parison draft-recipe --baseline baseline.csv --candidate candidate.csv \
  --output recipe.json
parison validate-recipe recipe.json
parison validate-inputs --records --recipe recipe.json \
  --baseline baseline.csv --candidate candidate.csv
parison explain recipe.json > effective-policy.json
```

Review keys, mappings, types, tolerances, normalization, exclusions, declared
scope and output sensitivity. Record the `policy_sha256` from
`effective-policy.json` only after review.

### 2. Run, verify and inspect

```sh
parison compare --recipe recipe.json \
  --expected-policy-sha256 POLICY_SHA256 \
  --baseline baseline.csv --candidate candidate.csv \
  --output runs/rehearsal-01
parison verify runs/rehearsal-01
parison inspect runs/rehearsal-01
```

Output paths must not exist. Publication is atomic and refuses overwrite. A
completed `FAIL` returns exit 1 and still publishes verifiable evidence.
`ERROR`, `INCONCLUSIVE` and interruption return 2, 3 and 130 respectively.

Summary sensitivity excludes source keys and values. Raw sensitivity includes
only the bounded sample requested by policy and must be protected as source
data. Exporting evidence never upgrades a summary bundle:

```sh
parison export-evidence runs/raw-failure --output evidence.jsonl --limit 100
```

For keyed or multiset inputs that exceed comfortable process memory, select
the existing SQLite engine explicitly and bound its temporary storage:

```sh
parison compare --recipe recipe.json --baseline baseline.csv \
  --candidate candidate.csv --engine sqlite \
  --max-temp-bytes 1000000000 --output runs/rehearsal-01
```

See the [compatibility contract](0.19/126-compatibility-contract.md) and
[SQLite keyed-engine contract](0.18/121-keyed-engine-contract.md).

## Gate a suite

A suite composes independently reviewed recipes in a fixed order. Validate the
plan, inspect its exact selection, then execute it:

```sh
parison validate-suite cutover-suite.json
parison list-suite cutover-suite.json --json
parison run-suite --plan cutover-suite.json --jobs 2 \
  --output evidence/cutover
parison verify evidence/cutover
parison inspect evidence/cutover
parison report-ci evidence/cutover --format markdown \
  --output parison-summary.md
```

External workers may run explicit shards and assemble their verified outputs.
Workspace resume reuses only children whose policy, inputs, limits and artifact
semantics still match.

```sh
parison run-suite --plan cutover-suite.json --shard-index 0 --shard-count 2 \
  --output evidence/shard-0
parison assemble-suite --plan cutover-suite.json \
  --input evidence/shard-0 --input evidence/shard-1 \
  --output evidence/assembled
```

See the [suite-v2 contract](0.11/84-scalable-suite-contract.md) and
[bounded concurrency guide](0.12/92-user-guide.md).

## Review schema evolution before comparison

Schema evolution is data-free policy review. It can compile identity-preserving
renames into mappings and classify policy impact; split and merge declarations
remain explanatory and are not automatic transforms.

```sh
parison validate-evolution evolution.json
parison explain-evolution evolution.json
parison compile-evolution evolution.json
parison diff-policy --baseline-recipe old-recipe.json \
  --candidate-recipe new-recipe.json --evolution evolution.json --summary
```

Review the [schema-evolution and policy-diff contract](1.2/143-schema-evolution-and-policy-diff-contract.md)
and [semantic scalar guide](1.1/140-semantic-scalar-guide.md) before enabling
cross-format projection.

## Reconcile related datasets in one event window

Reconciliation combines time-alignment preflight, per-dataset parity, identity
and reference checks, and grouped-sum conservation. The receipt is source-owned:
Parison binds its bytes but cannot prove its claims.

```sh
parison validate-time-alignment alignment.json
parison validate-reconciliation reconciliation.json
parison preflight-alignment --alignment alignment.json \
  --reconciliation reconciliation.json --receipt extraction-receipt.json \
  --dataset payments payments.recipe.json old-payments.csv new-payments.csv \
  --dataset payouts payouts.recipe.json old-payouts.csv new-payouts.csv
parison reconcile --alignment alignment.json \
  --reconciliation reconciliation.json --receipt extraction-receipt.json \
  --dataset payments payments.recipe.json old-payments.csv new-payments.csv \
  --dataset payouts payouts.recipe.json old-payouts.csv new-payouts.csv \
  --output evidence/reconciliation
parison verify-reconciliation evidence/reconciliation
parison inspect-reconciliation evidence/reconciliation
```

Use the complete synthetic policy and inputs under [`examples/1.3`](../examples/1.3)
and the [frozen reconciliation contract](1.3/149-time-alignment-and-reconciliation-contract.md).

## Bind a declared dataset collection

A dataset manifest names a closed collection of local files, roles and formats.
It establishes byte identity and scope; it does not reinterpret receipt claims
or turn runtime diagnostics into semantic outcomes.

```sh
parison validate-dataset-manifest dataset-manifest.json
parison verify-dataset-manifest --manifest dataset-manifest.json --root . \
  --policy-file suite.json
parison capture-reproducibility --manifest dataset-manifest.json \
  --output diagnostic.json
parison publish-dataset-evidence --manifest dataset-manifest.json --root . \
  --policy-file suite.json --result-bundle result-bundle \
  --output evidence/dataset
parison verify evidence/dataset
parison inspect evidence/dataset
```

To compare two diagnostics without changing the verification outcome:

```sh
parison diff-reproducibility before.json after.json
```

Start from [`examples/1.4`](../examples/1.4) and use the
[dataset-manifest contract](1.4/154-dataset-manifest-and-reproducibility-contract.md).

## Compare repeated rehearsals

Catalog history and analysis require one exact policy. Analysis groups already
published counters; it does not rescan inputs or declare root cause.

```sh
parison catalog add --database .parison/catalog.sqlite runs/rehearsal-01
parison catalog add --database .parison/catalog.sqlite runs/rehearsal-02
parison catalog history --database .parison/catalog.sqlite \
  --policy-sha256 POLICY_SHA256
parison catalog diff --database .parison/catalog.sqlite \
  runs/rehearsal-01 runs/rehearsal-02
parison analyze runs/rehearsal-01 runs/rehearsal-02 \
  --output evidence/analysis
parison verify-analysis evidence/analysis
```

For a selected group, raw drill-down is available only when the source run
already contains raw samples:

```sh
parison drilldown runs/raw-failure --group-id GROUP_ID \
  --output evidence/group.jsonl
parison verify-drilldown evidence/group.jsonl
```

See the [discrepancy-analysis guide](1.5/162-discrepancy-analysis-guide.md).

## Authenticate and hand off evidence

Parison emits deterministic unsigned statements. An external reviewed signing
system authenticates the exact statement bytes.

```sh
parison statement evidence/cutover --output parison-statement.json
# Sign and authenticate parison-statement.json outside Parison.
parison verify-statement evidence/cutover parison-statement.json
parison report-cutover evidence/cutover --output cutover.md
```

The receiver must authenticate signer identity and issuer before local
statement verification, then independently require the intended policy,
outcome, completeness and scope. Follow the [evidence handoff guide](0.17/116-evidence-handoff-guide.md).

## Automation and offline authoring

Use `--json` where a command documents structured output. Do not parse human
stderr summaries. Export installed schemas for offline editors rather than
fetching them at runtime:

```sh
parison schema recipe-v3
parison export-editor-schemas --output editor-schemas
```

Tested CI and orchestrator patterns are under
[`examples/github-actions`](../examples/github-actions) and
[`examples/integrations`](../examples/integrations). They invoke Parison as a
local process and keep orchestration, credentials and remote state external.

## Investigation rules

- Verify before inspecting or deriving evidence.
- Treat `FAIL` as a completed comparison, not a tool crash.
- Compare exact-policy rehearsals; do not present policy drift as progress.
- Treat input digests as supplied-byte identity, not extraction coordination.
- Keep raw bundles, drill-down and exported evidence under source-data controls.
- Require a human or external gate to approve policy and authorize cutover.
