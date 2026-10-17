# Deterministic discrepancy analysis across rehearsal runs

Date: 17 October 2026

Status: **research recommendation**

## Question and boundary

Parison can prove policy-scoped agreement, publish bounded raw discrepancy
samples, and show whether total discrepancy counts rose or fell across runs. It
cannot yet answer the next investigation questions in one stable contract:

- Which *kinds* of discrepancies persist across repeated rehearsals?
- Which explicit scope, identity, normalization, null, comparison or tolerance
  rule explains how each kind was produced?
- Which already-published evidence items can an operator inspect without
  mistaking a bounded sample for the complete population?

The recommended 1.5 capability is a versioned `discrepancy-analysis-v1`
projection over verified ordinary run bundles. It standardizes exhaustive,
summary-safe reason groups from result counters, compares those groups across
an explicitly ordered same-policy run series, and permits bounded drill-down
only into evidence already present in raw bundles. It does not reread inputs,
infer causes from source values, suggest repairs, or alter PASS/FAIL/INCONCLUSIVE.

This is deliberately larger than another display command: it adds one common
reason vocabulary across keyed, aggregate and multiset modes; binds every reason
to exact effective-policy locations; supplies deterministic cross-run
transitions; and preserves the existing privacy and compatibility boundaries.

External sources below are primary specifications or official implementation
documentation and were accessed **17 October 2026**.

## Recommendation

Specify and build `discrepancy-analysis-v1` with two related outputs:

1. A per-run analysis derived from a verified result's exhaustive counters,
   effective policy and scope. Its ordered `groups` identify a comparison mode,
   discrepancy kind, classification and logical field or measure where one
   exists; carry an exact count; and explain the result through stable reason
   codes and closed effective-policy references.
2. A series analysis over two or more explicitly ordered, current, verified
   bundles with the same `policy_sha256`. It aligns groups by canonical group ID
   and reports each run's count plus adjacent deltas. A group absent from a run
   has count zero; missing or invalid evidence is an error, not an inferred zero.

An optional drill-down selects at most a declared positive limit from each
bundle's existing `discrepancy_sample`, in its existing deterministic order,
after exact group matching. The result must state sample coverage per run and
must never call sampled evidence exhaustive. Summary bundles produce the group
analysis but cannot produce raw drill-down.

The analysis explains **which declared rule classified an observed difference**.
For example, a keyed field group may refer to its column type, normalization
chain, null equality and comparison/tolerance paths. It does not claim why the
upstream data differs, whether the rule is correct, or what anyone should
change.

## Why the model is defensible

### Stable identity must come from declared semantics

RFC 6901 defines JSON Pointer as a syntax for identifying a specific value in a
JSON document and defines escaping and evaluation precisely. It also performs
no Unicode normalization while matching object-member names
([RFC 6901](https://www.rfc-editor.org/rfc/rfc6901)). This makes a closed,
contract-owned pointer vocabulary suitable for locating explanatory policy
fields, provided Parison rejects unknown paths and never uses source-controlled
free text as a semantic identifier.

RFC 8259 says unique object names are necessary for interoperable name/value
interpretation and notes that implementations differ in whether object-member
ordering is visible ([RFC 8259](https://www.rfc-editor.org/rfc/rfc8259)). RFC
8785 addresses hashing by constraining JSON and recursively sorting object
properties while preserving array order
([RFC 8785](https://www.rfc-editor.org/rfc/rfc8785)). Parison already uses
strict JSON plus compact, sorted-key canonical bytes. The new contract should
continue that repository convention rather than claim RFC 8785 compatibility,
whose number and string requirements differ from Parison's established
canonical formats.

**Consequence:** a group ID should be a domain-separated SHA-256 digest of a
closed canonical descriptor, not a label, rendered message, source key, source
value or positional sample index. The descriptor should contain only stable
semantic coordinates:

```json
{
  "analysis_version": 1,
  "comparison_mode": "keyed",
  "kind": "field",
  "classification": "different",
  "logical_name": "gross-amount"
}
```

The ordered descriptor list is part of the contract; messages remain
non-authoritative presentation. Logical names are the names in the effective
policy, after explicit column mapping, never input header spelling.

### Grouping and ordering must be explicit

SQLite documents that rows returned without `ORDER BY` have undefined order,
that ties remain undefined unless later ordering terms break them, and that
aggregate input order can be arbitrary unless it is explicitly ordered
([SQLite `SELECT`](https://www.sqlite.org/lang_select.html), [SQLite aggregate
functions](https://www.sqlite.org/lang_aggfunc.html)). SQLite also documents
that grouping equality depends on storage class and collation, including its
numeric INTEGER/REAL exception
([SQLite datatypes](https://www.sqlite.org/datatype3.html)).

**Consequence:** memory and SQLite implementations must not inherit host map,
database collation or query-plan order. Counts are integer additions over
already-defined result classifications. Groups sort by contract-defined ASCII
enumeration ordinals and UTF-8 bytes of normalized logical names, followed by
group ID as a total tie-breaker. Runs retain explicit catalog insertion order;
that order is a user-supplied rehearsal sequence, not a timestamp or causality
claim.

### Explanation is provenance, not diagnosis or repair

W3C PROV distinguishes entities, activities and agents and models derivation as
influence rather than proof that an upstream assertion is true
([PROV-O](https://www.w3.org/TR/prov-o/), [PROV
Primer](https://www.w3.org/TR/prov-primer/)). JSON Schema likewise keeps
assertion results separate from annotations and attaches detailed output to
specific instance and schema locations; its security considerations warn
implementations to bound resource consumption while collecting output
([JSON Schema Core 2020-12](https://json-schema.org/draft/2020-12/draft-bhutton-json-schema-01)).

**Consequence:** each reason is a derivation trace from verified result counter
to effective-policy locations, not an upstream root-cause claim. A reason has a
closed code, a count source, and ordered policy references. Explanatory text is
generated from the code. No field accepts free-form advice, severity, owner,
approval state or remediation.

### Sampling cannot establish prevalence

Parison's frozen investigation contract says `export-evidence` selects only
from the already-published `discrepancy_sample` and never claims completeness
beyond that sample. Current comparison code fills samples in deterministic but
mode-specific order and stops at `discrepancy_sample_limit`. Early groups can
therefore consume the limit before later groups appear.

**Consequence:** group counts must be derived from exhaustive result counters,
never reconstructed by counting sample items. Drill-down returns
`population_count`, `published_sample_size`, `matched_sample_size`,
`returned_size`, and `sample_complete`; the last is true only when the verified
result proves all discrepancies were published. Zero matching sample items does
not mean the group lacks discrepancies. Cross-run change is computed from group
counts, never sample membership or key/value similarity.

## Proposed semantic surface

### Closed reason groups

The first contract should normalize only discrepancy facts already represented
exhaustively in released result schemas:

| Mode | Kind and logical name | Classifications | Exhaustive count source |
|---|---|---|---|
| keyed | `record`, no name | `baseline_only`, `candidate_only` | `counts` |
| keyed | `field`, column name | `within_tolerance`, `different` | `field_counts` |
| aggregate | `group`, no name | `baseline_only`, `candidate_only` | aggregate `counts` |
| aggregate | `measure`, measure name | `within_tolerance`, `different` | `measure_counts` |
| multiset | `row`, no name | `baseline_surplus`, `candidate_surplus` | multiset `counts` |

`exact` is useful denominator context but is not a discrepancy group. Row-level
keyed classifications summarize severity across fields and overlap the field
population, so they should remain context rather than become a second set of
apparently additive discrepancy groups. Problems that make a run INCONCLUSIVE
belong in a separate `conditions` array with closed codes; they must not be
mixed into discrepancy totals.

Each group contains:

- `group_id`, the domain-separated digest of its canonical descriptor;
- descriptor fields (`comparison_mode`, `kind`, `classification`, and optional
  `logical_name`);
- exact nonnegative `count` and its closed `count_source`;
- a closed ordered list of `reason_codes`;
- ordered `policy_refs`, each containing an RFC 6901 pointer and the canonical
  data-free policy value at that pointer;
- optional denominator counts whose meaning is explicit and non-overlapping.

The closed policy-reference vocabulary should cover only paths needed to
explain released classifications: comparison mode; scope snapshot, cutoff,
filters, completeness and expected-empty; identity/key or group definitions;
column mapping and semantic type; ordered normalization rules; null behavior;
exact versus tolerance comparison; tolerance values; aggregate operator and
measure-null behavior; multiset canonical encoding and column order; and input
projection. A future policy path yields INCONCLUSIVE analysis until the
analysis contract is versioned; it is never silently omitted.

Scope is important context for *every* group, but repeating all scope values in
every descriptor would create a new group identity for facts already isolated
by `policy_sha256`. Store one run-level scope explanation and reference it from
groups. Normalization references appear only for affected keyed fields,
aggregate group columns or source columns feeding measures, and multiset
columns. The explanation must distinguish raw evidence values from normalized
values used for comparison.

### Same-policy series

A series request declares an ordered list of verified bundle identities and an
optional closed group filter. It requires:

- ordinary run bundles only;
- the same nonempty `policy_sha256` on every run;
- current byte identity for catalog-backed bundles, or direct verification for
  explicit paths;
- one supported result schema/mode throughout;
- at least two distinct bundle digests, while repeated paths or digests are
  rejected rather than double-counted.

The output includes each run's immutable bundle digest and caller-provided
ordinal, not source path in summary-safe output. For every group in the union,
it records counts in run order and adjacent signed deltas. It may label a
transition `introduced`, `resolved`, `increased`, `decreased` or `unchanged`
strictly from zero/nonzero and integer delta. Those labels describe evidence,
not causality, quality or readiness.

Policy changes require a separate `policy-diff-v1` result and a new series.
Automatically aligning groups across different policies would blur changes to
scope, normalization, tolerances or identity with changes in data—the exact
ambiguity this capability is intended to remove.

### Bounded drill-down

Drill-down is a read of verified published evidence, not a new comparison. The
request contains exact group IDs and a global and per-run positive limit. Items
match only on the group's closed descriptor fields; names match logical fields
or measures exactly. Selection preserves result order, run order and stable
first-N truncation.

The output is raw-sensitivity and must retain bundle and policy provenance. It
may include source keys, groups, row shapes and values already present in the
sample. It must not add source paths, reread inputs, join keys across runs,
calculate similarity, or infer that the same key/row denotes the same upstream
incident. Publication follows the existing private staging, atomic
no-overwrite and interruption-cleanup rules.

## Repository evidence

The repository already contains most primitives needed for a deep existing
module rather than a new subsystem:

- [`comparison.py`](../../src/parison/comparison.py) computes exhaustive
  `counts`, per-field or per-measure classification counts, and multiset surplus
  shape counts before it creates bounded samples. Memory and SQLite keyed and
  multiset paths already have equivalence tests and deterministic ordering.
- [`policies.py`](../../src/parison/policies.py) expands recipes into data-free
  effective policies and hashes canonical compact JSON. It records scope,
  identity, logical/source mappings, type, normalization, null, tolerance,
  group, measure and multiset encoding semantics.
- [`evidence.py`](../../src/parison/evidence.py) verifies bundles before
  inspection or export, keeps summaries free of raw discrepancy material, and
  exports only existing bounded samples with provenance and atomic
  no-overwrite publication.
- [`catalog.py`](../../src/parison/catalog.py) already supplies immutable
  insertion order, verifies bundles on add, rechecks live state, and limits
  history/diff to exact policy identity. Its current transitions expose only
  outcome and total discrepancy count.
- The frozen [investigation contract](../0.9/74-investigation-contract.md)
  forbids promoting summaries into raw evidence and explicitly exposes sample
  coverage. The [catalog history contract](../0.15/101-catalog-history-contract.md)
  rejects unequal policies and warns that catalog order is not execution time.
- The [`policy-diff-v1` contract](../1.2/143-schema-evolution-and-policy-diff-contract.md)
  already establishes the safe pattern of a closed policy-path vocabulary,
  explicit impact/reason codes and INCONCLUSIVE handling for unknown paths.
- Current result versions differ materially: keyed and aggregate use named
  field/measure counts, while multiset uses surplus-shape totals. The analysis
  layer should adapt these released shapes without changing their canonical
  bytes or schemas.

Important gaps are also visible. `catalog` stores only the summary-safe
inspection projection, so it cannot derive field/measure groups from its
database alone. Raw samples are prefix-bounded and unsuitable for prevalence.
Some human-readable `problems` strings are not a stable taxonomy. Therefore the
implementation should verify and read selected bundles at analysis time,
derive closed conditions from structural result facts where possible, and
version any new condition code rather than parse prose.

## Design consequences

1. **Analysis is derived evidence.** Bind `analysis_version`, every bundle
   digest, the one policy digest, the canonical request and the generated
   analysis digest. Verification must recompute outcome-independent group
   counts and IDs from bundle members.
2. **No released bytes change.** Existing recipes, results, bundles, catalog
   schema/rows, exit codes and CLI JSON remain readable and byte-identical. A
   new analysis artifact is separately versioned and optionally bundled only
   through a new bundle kind or member contract.
3. **One adapter per released result mode.** Keep classification extraction
   close to result verification in `evidence.py`; deepen catalog history to
   orchestrate ordered verified bundles instead of introducing a general query
   or plugin layer.
4. **Counts are authoritative; samples are illustrative.** Reject negative,
   inconsistent or overlapping totals and analysis/results whose recomputed
   total does not match `discrepancy_count` under the mode's definition.
5. **Explanations are policy-local.** Reason codes map to exact canonical policy
   pointers. They never inspect raw values to guess upstream cause or prescribe
   a change.
6. **Sensitivity is monotone.** Summary analysis stays summary-safe. Any raw
   drill-down is a separate raw output and cannot be embedded in a summary
   artifact or catalog row.
7. **Bounds are explicit.** Cap runs, groups, selected group IDs, drill-down
   items, JSON bytes/depth/string sizes and generated output bytes. Exceeding a
   limit fails deterministically without partial publication.
8. **Series order is asserted, not discovered.** Use explicit request order or
   existing catalog order. Do not infer chronology from filesystem metadata,
   names, bundle contents or clocks.

## Threats and mitigations

1. **Sample-frequency fallacy.** A group dominating the prefix sample may be
   rare in the full population. Use exhaustive counters for every trend and
   state sample coverage next to drill-down.
2. **False root cause.** A normalization or tolerance rule explains a
   classification but not why source systems emitted different values. Use
   `reason`, never `root_cause`; document this limit in CLI and schema text.
3. **Policy drift hidden as progress.** A broader tolerance could reduce counts
   while weakening the gate. Require exact policy identity; direct callers to
   `policy-diff-v1` for changed policies.
4. **Privacy leakage through group names.** Source column names, paths, keys or
   values can identify systems or subjects. Use logical policy identifiers in
   summary groups and keep raw material solely in explicit raw drill-down.
5. **Cross-run key tracking.** Correlating raw keys can create a sensitive
   incident history and still be semantically wrong after upstream reuse. Do
   not join or persist key identities across runs in v1.
6. **Unstable database order.** SQLite or map iteration can reorder groups or
   samples across machines. Specify a total byte-level order and test memory,
   SQLite, Python and platform equivalence.
7. **Digest substitution or stale catalog state.** Stored metadata may no
   longer describe live evidence. Verify exact bundles and reject modified or
   missing entries before analysis.
8. **Count overflow and resource exhaustion.** Adversarial results or long
   series can create huge unions and outputs. Enforce schema integer bounds,
   checked delta arithmetic and hard collection/output limits.
9. **Unknown future classifications.** Treat unknown modes, kinds,
   classifications, result versions or policy paths as INCONCLUSIVE/unsupported,
   never coerce them into an existing group.
10. **Advice smuggling.** Free-form labels or templates could become generated
    repair recommendations. Keep codes and messages closed; reject advice,
    action, owner, approval and severity fields.
11. **Partial or interrupted publication.** Analysis can contain sensitive
    drill-down. Reuse private staging, atomic no-replace publication,
    symlink-safe paths and cleanup on failure or signal.
12. **Misreading a falling count as readiness.** A downward trend says only
    that fewer discrepancies were counted under one exact policy over the
    supplied ordered runs. Repeat the PASS and cutover disclaimers in every
    series result.

## Non-goals

- automatic root-cause analysis, anomaly diagnosis, repair, transformation or
  policy recommendations;
- approving keys, scope, mappings, exclusions, normalizations, null behavior,
  tolerances or cutover;
- comparing or merging histories across unequal policies;
- rereading source inputs, executing queries, connecting to remote systems or
  assuming custody of credentials;
- fuzzy clustering, value similarity, semantic field matching, AI-generated
  explanations or learned prioritization;
- exhaustive raw discrepancy retention, unbounded pagination, a local server,
  dashboard or general analytical query language;
- treating catalog insertion order as wall-clock time, causality or proof that
  snapshots were coordinated;
- changing released comparison outcomes, result schemas or sample order;
- replacing `policy-diff-v1`, reproducibility diagnostics or source-owned
  extraction receipts.

## Alternatives considered

### Trend only total discrepancy counts

This already exists and remains useful, but two runs with the same total can
have entirely different missing-record, field, measure or surplus-shape
populations. It cannot explain which explicit rule produced a classification.

### Group the published samples

This is simple but unsound for prevalence and trends because samples are
bounded prefixes in mode-specific order. It would turn sample-limit and
ordering effects into apparent changes in the data.

### Persist every discrepancy in the bundle

This would make arbitrary later queries possible, but changes Parison from
bounded evidence into potentially unbounded sensitive data custody. It
increases bundle size, publication risk and compatibility surface without being
needed for reason-level trend analysis.

### Rerun comparisons during analysis

Rereading inputs could generate a new complete index, but the inputs may have
changed and the result would not be the evidence originally cataloged. It also
violates the investigation boundary and duplicates comparison execution.

### Align groups across policy changes

Policy-aware alignment sounds convenient, but changes to scope, normalization,
identity or tolerance alter what a discrepancy means. Keep each exact-policy
series separate and present a reviewed policy diff alongside it.

### Add a generic SQL/JSON query surface

This exposes implementation details, invites nondeterministic grouping and
ordering, and creates a much wider compatibility and security contract. A
closed reason/group/filter vocabulary covers the identified workflow.

### Generate repair suggestions

Suggestions would blur evidence and decision-making, and could silently approve
weaker tolerances, excluded fields or normalization. Parison should show the
exact declared rule and observed class; the operator owns interpretation and
action.

## Concrete completion and promotion gate

Promote `discrepancy-analysis-v1` into the 1.5 implementation roadmap only if a
contract spike proves that every supported released result mode can produce
exhaustive reason groups from existing verified bundle content—never from
samples—and that every group can be tied to a closed effective-policy path or
an explicitly policy-independent count reason.

The capability is complete only when all of the following pass:

1. Strict installed schemas and canonical byte fixtures cover a per-run
   analysis, a same-policy series and raw drill-down provenance. Duplicate JSON
   keys, unknown fields, unknown reason codes/paths and invalid counts fail
   closed.
2. A checked matrix covers keyed exact and tolerance differences, missing
   records, normalization and null boundaries; aggregate missing groups and
   measure differences; and multiset baseline/candidate surplus shapes.
3. For every fixture, group counts recompute exactly from the verified result,
   sum to the released mode's `discrepancy_count` definition, and are
   byte-identical under memory and SQLite execution where both engines exist.
4. A three-run same-policy rehearsal demonstrates introduced, increased,
   decreased, resolved and unchanged groups. Reordering runs changes only the
   declared series order and derived adjacent transitions; repeated or unequal
   policy inputs are rejected.
5. Adversarial fixtures prove that sample truncation cannot alter group counts;
   an unsampled nonzero group remains visible with zero matched sample items;
   summary bundles cannot yield raw drill-down; and limits fail without partial
   publication.
6. Explanation fixtures verify exact scope, identity/group, mapping, type,
   normalization, null, comparison, tolerance and multiset-encoding references,
   including Unicode names and RFC 6901 escaping. No output field or rendered
   message suggests repair, approval, severity or cutover readiness.
7. Existing recipes, schemas, canonical fixtures, bundles, catalog databases,
   CLI JSON and exit codes remain byte-compatible. Old bundles remain readable,
   and unrecognized future semantics fail analysis explicitly.
8. Direct and catalog-backed analysis both verify bundle integrity; modified,
   missing, symlinked or aliased artifacts are rejected. Raw publication is
   atomic, no-overwrite and cleans private staging after failure or
   interruption.
9. The full `make check` gate and built-wheel CI pass on Python 3.11–3.14,
   macOS and Windows, including wheel-only schema discovery and optional-Polars
   behavior.
10. One realistic migration or reconciliation rehearsal shows that an operator
    can identify a persistent reason group, inspect bounded raw evidence, and
    cite the exact policy/scope/normalization rule without consulting source
    paths or receiving a repair recommendation.

If exhaustive grouping requires a new unbounded raw index, if released counters
cannot reconcile exactly, or if explanations require heuristic inspection of
source values, do not promote this design. Version result semantics first or
reduce the capability to the modes whose released evidence supports it.

## Source list

External primary sources, accessed 17 October 2026:

- [RFC 6901: JSON Pointer](https://www.rfc-editor.org/rfc/rfc6901)
- [RFC 8259: The JavaScript Object Notation (JSON) Data Interchange
  Format](https://www.rfc-editor.org/rfc/rfc8259)
- [RFC 8785: JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785)
- [SQLite `SELECT` documentation](https://www.sqlite.org/lang_select.html)
- [SQLite built-in aggregate functions](https://www.sqlite.org/lang_aggfunc.html)
- [SQLite datatypes and comparison behavior](https://www.sqlite.org/datatype3.html)
- [JSON Schema Core, Draft 2020-12](https://json-schema.org/draft/2020-12/draft-bhutton-json-schema-01)
- [W3C PROV-O Recommendation](https://www.w3.org/TR/prov-o/)
- [W3C PROV Model Primer](https://www.w3.org/TR/prov-primer/)

Repository evidence:

- [Investigation contract](../0.9/74-investigation-contract.md)
- [Catalog history and safe diff contract](../0.15/101-catalog-history-contract.md)
- [Product direction and release arc](../0.15/104-product-direction-and-release-arc.md)
- [Schema evolution and policy-diff contract](../1.2/143-schema-evolution-and-policy-diff-contract.md)
- [Dataset manifest and reproducibility contract](../1.4/154-dataset-manifest-and-reproducibility-contract.md)
- [`src/parison/comparison.py`](../../src/parison/comparison.py)
- [`src/parison/policies.py`](../../src/parison/policies.py)
- [`src/parison/evidence.py`](../../src/parison/evidence.py)
- [`src/parison/catalog.py`](../../src/parison/catalog.py)
- [`tests/test_catalog.py`](../../tests/test_catalog.py)
- [`tests/test_semantics.py`](../../tests/test_semantics.py)
- [`tests/test_multiset_recipe.py`](../../tests/test_multiset_recipe.py)
