# Verification workbench product research

Date: 19 October 2026

Status: **future-direction research; not an active release contract**

## Question

Parison exposes 52 documented command and subcommand entries after 1.8, with
the 1.9 structured-selection train still active. The commands cover policy
authoring, preflight, comparison, suites, reconciliation, investigation,
catalog history, evidence publication and independent verification. Is a human
interface now justified, and which features from adjacent products would help
without turning Parison into a hosted data platform, repair tool or approval
system?

This research evaluates product interaction patterns, not vendor correctness
claims or market position. Sources were accessed on 19 October 2026. Product
documentation and vendor-owned repositories are treated as primary sources for
documented behavior; performance and accuracy claims were not independently
validated.

## Existing Parison constraints

The accepted direction positions Parison as a local-first verification layer:
a reviewed policy produces portable evidence. Distributed orchestration stays
external. PASS records agreement under the declared policy; it does not mean
that extraction is truthful or that a migration is approved.

A compatible interface therefore must:

- use released Parison semantics rather than interpreting agreement itself;
- preserve local execution and zero-custody operation;
- verify bundles before rendering their contents;
- show summary-safe information by default;
- keep policies, limits, exclusions and tolerances explicit;
- preserve canonical artifacts and exact CLI automation;
- avoid credentials, repair, deployment and cutover authorization;
- keep scheduling and distributed execution external.

The earlier decision not to prioritize a dashboard or desktop UI was sound
while the verification workflow was still shallow. The present question is
different: whether the breadth of the released workflow now makes navigation
and progressive disclosure a material part of verification correctness.

## Products reviewed

### Datafold Data Diff

Datafold presents table comparison as a first-class workflow available through
a UI, API and automation. Its product description emphasizes value-level row
and column differences, cross-database comparison, CI integration and visual
exploration. Its documented manual diff flow also supports configuration such
as time-axis plotting and statistical confidence.

Useful interaction patterns:

- one recognizable object representing a comparison;
- summary-to-row-and-column drill-down;
- the same capability exposed through UI and automation;
- comparison embedded into CI rather than confined to an interactive session;
- visible scope and configuration before execution.

Parison consequence: adopt the comparison-as-saved-plan and
summary-to-investigation flow. Do not adopt direct warehouse connections,
remote custody or probabilistic confidence as a substitute for Parison's
explicit deterministic policies.

Sources:

- [Data Diff product documentation](https://www.datafold.com/data-diff/)
- [Manual Data Diff documentation source](https://github.com/datafold/documentation/blob/main/introduction/data-diff/manual-data-diff.md)

### Redgate SQL Data Compare

SQL Data Compare organizes work around saved projects. A project retains data
sources, configuration, mappings, selected tables and columns, comparison keys
and row filters. Results first group objects by difference type, then expose
counts for source-only, changed, target-only and identical rows. Users can
search, filter and inspect side-by-side row differences. Results can be
exported for reporting or retained as a record.

Useful interaction patterns:

- saved project as the durable unit of intent;
- side-by-side source and target mapping;
- warnings when structural changes invalidate mappings;
- explicit comparison-key selection;
- grouped overview before sensitive row-level detail;
- search and navigation between differences;
- exportable result summaries.

Risks exposed by the product:

- the same results interface also selects rows for deployment;
- projects can contain connection information;
- filtering and mapping assistance can obscure policy choices if accepted
  implicitly.

Parison consequence: a saved verification plan and mapping preview are strong
models, but Parison must not place repair or deployment actions beside evidence.
Suggested mappings must remain drafts until explicitly reviewed and saved.

Sources:

- [Working with projects](https://documentation.red-gate.com/sdc/setting-up-the-comparison/working-with-projects)
- [Selecting tables, columns and comparison keys](https://documentation.red-gate.com/sdc/setting-up-the-comparison/selecting-tables-and-views)
- [Viewing comparison results](https://documentation.red-gate.com/sdc/reviewing-the-comparison-results/viewing-the-comparison-results)
- [Viewing row differences](https://documentation.red-gate.com/sdc15/reviewing-the-comparison-results/viewing-the-row-differences)
- [Exporting results](https://documentation.red-gate.com/sdc/reviewing-the-comparison-results/exporting-the-comparison-results)

### Great Expectations Data Docs

Great Expectations groups reusable expectations into suites, applies them
through checkpoints, saves validation results and produces human-readable Data
Docs. Its result format can range from boolean-only through summary and
complete detail, including identifiers or queries capable of retrieving
unexpected rows.

Useful interaction patterns:

- policy, execution and rendered result are distinct objects;
- a checkpoint provides a repeatable execution entry point;
- generated static documentation makes results locally browsable;
- result-detail levels acknowledge that investigation detail can be sensitive
  or expensive;
- each failed assertion remains visible within the overall run.

Parison consequence: generated local evidence navigation is a good first
surface. Detail levels should not be a cosmetic UI switch, however: Parison
must keep summary-safe inspection and raw evidence export as separate,
auditable operations.

Sources:

- [Great Expectations validation workflow](https://docs.greatexpectations.io/docs/0.18/oss/guides/validation/validate_data_overview/)
- [Validation result formats](https://docs.greatexpectations.io/docs/0.18/reference/learn/expectations/result_format/)

### Soda

Soda separates executable checks from its cloud result and collaboration
surface. Its UI presents latest check states, historical metric views,
filterable dashboards, warnings and failures. It can create and assign
incidents, attach multiple failed checks, record status and resolution, send
notifications and connect to collaboration systems.

Useful interaction patterns:

- checks remain individually identifiable within a scan;
- latest state and history are both accessible;
- filtering by dataset, check and result reduces navigation cost;
- related failures can be grouped for investigation;
- a result page connects overview, history and detail;
- explicit `not evaluated` or error states avoid collapsing incomplete work
  into failure.

Features outside Parison's boundary:

- automatically learned anomaly baselines;
- hosted credentials and connected data sources;
- incident ownership and organizational workflow;
- notifications, ticketing and chat integration;
- health scores that compress unlike policies into one number.

Parison consequence: borrow navigational history, grouping and explicit state,
not organizational incident management or an aggregate quality score. Parison
should never invite users to treat PASS counts as a universal health measure.

Sources:

- [Soda product overview](https://docs.soda.io/soda-documentation/soda-v3/learning-resources/product-overview)
- [Metrics and checks](https://docs.soda.io/soda-documentation/soda-v3/sodacl-reference/metrics-and-checks)
- [Incident workflow](https://docs.soda.io/manage-issues/incidents)
- [Metric-monitor detail](https://docs.soda.io/data-observability/metric-monitor-page)

### AWS Database Migration Service validation

AWS DMS integrates comparison into migration tasks. It reports validation
status and metrics, supports explicit validation-only tasks, can revalidate
selected tables and distinguishes one-pass full-load validation from ongoing
CDC validation. Its documentation describes latency, retries, failure limits,
resource impact and cases where concurrent writes make results unreliable.

Useful interaction patterns:

- validation-only is a distinct task type;
- execution mode and completeness are visible;
- revalidation is explicit rather than silently changing old evidence;
- resource and latency behavior is part of the result context;
- limitations are product-visible, not buried implementation facts.

Features outside Parison's boundary:

- continuous CDC validation;
- live source and target credentials;
- cloud service ownership of execution;
- data resynchronization and automatic repair.

Parison consequence: make execution completeness, bounds, input stability and
rehearsal identity prominent. Preserve immutable prior results when rerunning.
Do not add continuous validation or repair to the workbench.

Source:

- [AWS DMS data validation](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Validating.html)

### Airflow and GitHub Actions as orchestration surfaces

Airflow's UI covers schedules, task graphs, run history, logs, retries,
connections, pools and administrative configuration. GitHub Actions provides
workflow-run summaries and immutable uploaded artifacts. Together they show
that orchestration and remote presentation already have mature hosts.

Parison consequence: publish structured progress, summaries and evidence that
these systems can display. Do not reproduce their schedulers, workers,
credential stores or notification systems.

Sources:

- [Airflow UI overview](https://airflow.apache.org/docs/apache-airflow/stable/ui.html)
- [GitHub Actions job summaries](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/workflow-commands-for-github-actions)
- [GitHub Actions workflow artifacts](https://docs.github.com/en/actions/tutorials/store-and-share-data)

## Cross-product findings

The strongest recurring product model is:

```text
saved definition
    -> explicit run
    -> grouped result summary
    -> bounded detail
    -> history and comparison
    -> portable or integrated report
```

Parison already implements most of the underlying semantics. What is missing
is a coherent human navigation layer across them.

| Pattern | Product value | Parison treatment |
| --- | --- | --- |
| Saved project or checkpoint | Reuse and review | Transparent versioned verification plan |
| Intent-led setup | Reduces command discovery | Guide users to released plan types |
| Scope and mapping preview | Prevents accidental comparison | Show inputs, projections, keys and exclusions before run |
| Grouped results | Makes large diffs navigable | Use summary-safe discrepancy classes and suite states |
| Side-by-side detail | Speeds investigation | Explicit raw-evidence operation, never default dashboard content |
| Run history | Shows progression | Build on catalog history and same-policy diff |
| Rerun or revalidate | Supports rehearsal | Create a new immutable run; retain prior evidence |
| Static result site | Easy local review | Generate or serve verified local views |
| CI integration | Fits existing operation | Preserve CLI JSON and add stable display projections if needed |
| Alerts and incidents | Coordinates organizations | Leave to external systems |
| Repair or deployment | Closes operational loop | Explicit non-goal |
| Health score | Fast portfolio summary | Reject cross-policy score compression |

## Product opportunity

The proposed product is **Parison Workbench**, a local-first peer interface to
the CLI centered on four user activities:

1. **Define** a verification plan from intent while keeping every policy choice
   explicit.
2. **Run** the plan or suite locally with bounded progress and an exact
   reproducible command representation.
3. **Investigate** verified results from safe summaries into separately
   authorized evidence.
4. **Compare** rehearsals, policies and provenance without treating unlike runs
   as equivalent.

The top-level object should be a transparent workspace containing plans, local
input locators, runs, suites, evidence bundles and catalog history. Commands
remain stable automation primitives but cease to be the primary information
architecture for a human user.

## Threats and required controls

### Semantic drift

Threat: forms or UI code independently reproduce policy and outcome logic.

Control: CLI and workbench must call shared application services and consume
released schemas. The workbench renders outcomes returned by core.

### Sensitive disclosure

Threat: convenient drill-down exposes paths, keys, values or samples.

Control: summary-safe views are the default. Raw evidence requires an explicit
operation, displays its sensitivity and remains bounded and auditable.

### Implied authorization

Threat: visual success states become migration approval.

Control: use PASS only with its policy context. Never show approval, readiness,
deploy or cutover controls.

### Mutable evidence

Threat: refresh or rerun silently replaces the result being reviewed.

Control: every execution creates a separately identified immutable artifact;
history links old and new runs.

### Hidden policy

Threat: suggested mappings, defaults or generated plans become tacit policy.

Control: suggestions remain unapproved drafts. Show effective policy and its
fingerprint before execution.

### Scope expansion

Threat: a local workbench grows into a hosted orchestrator.

Control: exclude credentials, remote workers, schedules, notifications,
organizational roles, repairs and deployment from the workbench contract.

## Conclusion

A human interface is now directionally justified because Parison's breadth
creates a navigation and comprehension problem. The best adjacent-product
features are saved plans, intent-led setup, explicit mappings, progressive
result detail, run history and comparison. The least compatible features are
hosted connections, anomaly scoring, continuous monitoring, incident workflow,
repair and deployment.

The first implementation should be a read-only evidence navigator. It can
validate the information architecture and disclosure model before Parison adds
plan authoring or local execution controls.
