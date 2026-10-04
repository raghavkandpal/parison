# Parity sources and evidence gaps

Research accessed on 4 October 2026. Sources below are primary maintainer/vendor pages. Versions and public pricing can change. The dossier paraphrases capabilities briefly and separates them from our proposed design. No vendor performance claims are adopted as Parity benchmarks.

## Source register

| ID | Primary source | Used for |
| --- | --- | --- |
| S01 | [DataComPy CLI](https://capitalone.github.io/datacompy/cli.html) | Closest file/CI comparison baseline |
| S02 | [DataComPy repository](https://github.com/capitalone/datacompy) | Backend/report API and candidate reuse |
| S03 | [DataComPy API](https://capitalone.github.io/datacompy/api/datacompy.html) | Tolerance/typed-result behavior to evaluate |
| S04 | [Datafold product](https://www.datafold.com/) | Commercial competition and agent-tool positioning |
| S05 | [Datafold AI agents](https://www.datafold.com/ai-agents/) | Existing AI-assisted migration/review offering |
| S06 | [Datafold pricing route](https://www.datafold.com/pricing/) | No usable numerical quote in fetched route |
| S07 | [Archived Datafold data-diff](https://github.com/datafold/data-diff) | Maintenance status; not commercial-product status |
| S08 | [Google Cloud DVT](https://github.com/GoogleCloudPlatform/professional-services-data-validator) | Migration-validation alternative and file limitations |
| S09 | [Reladiff documentation](https://reladiff.readthedocs.io/en/latest/) | Database-diff alternative |
| S10 | [Reladiff repository](https://github.com/erezsh/reladiff) | Maintainer/reuse follow-up |
| S11 | [JuxtAPPose product](https://www.juxtappose.com/) | Local file/query comparison competitor |
| S12 | [JuxtAPPose pricing](https://www.juxtappose.com/pricing) | Free/perpetual packaging text; amounts unverified |
| S13 | [Beyond Compare feature matrix](https://beyond-compare.com/kb/feature_compare) | Existing table-comparison alternative |
| S14 | [Soda contracts repository](https://github.com/sodadata/soda-core) | Declarative checks alternative |
| S15 | [Soda reconciliation](https://docs.soda.io/reference/contract-language-reference/reconciliation-checks) | Direct source-target validation overlap |
| S16 | [Soda license file](https://github.com/sodadata/soda-core/blob/main/LICENSE) | Dependency-license caution; release-specific review needed |
| S17 | [dbt data tests](https://docs.getdbt.com/docs/build/data-tests) | Existing assertion workflow |
| S18 | [dbt unit tests](https://docs.getdbt.com/docs/build/unit-tests) | Fixture-based model testing alternative |
| S19 | [GX integrity guidance](https://legacy.docs.greatexpectations.io/docs/reference/learn/data_quality_use_cases/integrity/) | Adjacent validation category; legacy guidance |
| S20 | [GX pricing](https://greatexpectations.io/pricing/) | Public tier names; numerical prices not retrieved |
| S21 | [Pandera docs](https://pandera.readthedocs.io/en/stable/) | Dataframe/schema validation substitute |
| S22 | [Polars lazy CSV](https://docs.pola.rs/api/python/stable/reference/api/polars.scan_csv.html) | Explicit parsing and lazy execution candidate |
| S23 | [Polars streaming](https://docs.pola.rs/user-guide/concepts/streaming/) | Candidate execution behavior; not our performance proof |
| S24 | [DuckDB workload tuning](https://duckdb.org/docs/current/guides/performance/how_to_tune_workloads) | Later spill-backed execution candidate |
| S25 | [DuckDB OOM guidance](https://duckdb.org/docs/current/guides/performance/oom) | Limitations of a memory-limit promise |
| S26 | [DuckDB security guidance](https://duckdb.org/docs/current/operations_manual/securing_duckdb/overview) | Engine embedding and untrusted-input constraints |
| S27 | [DuckDB security model](https://duckdb.org/security) | Need for application/OS security boundaries |
| S28 | [OWASP CSV injection](https://community.owasp.org/attacks/CSV_Injection) | Spreadsheet-safe export requirement |

## What this research establishes

The public sources establish substantial competitive overlap and plausible technical building blocks. They support comparing Parity against libraries, commercial platforms and local desktop tools—not claiming the category is new.

They do not establish competitor market share, revenues, customer satisfaction, performance under our workload or lack of unlisted features. Documentation version numbers are observed page context, not a guarantee that a locally installed package behaves identically.

## Evidence ledger

| Claim or decision | Current evidence level | Needed next |
| --- | --- | --- |
| Basic file comparison is already served | Primary documentation | Hands-on baseline with pinned releases |
| Recurring investigation friction exists for our target users | Hypothesis | Independent task observations/interviews |
| Parity saves time without increasing false passes | Unverified | Counterbalanced comparative study |
| An existing engine meets our semantics | Unverified | Adapter spike and adversarial corpus |
| Local mode has no unintended network egress | Design requirement | Offline/network-denied tests |
| Sensitive data stays out of reports/logs by default | Design requirement | Canary tests and byte-level inspection |
| A paid local/team product is viable | Hypothesis | Purchase, recurrence and cost evidence |
| AI-generated alternatives are inferior for repeated use | Not established | Fair substitution benchmark |
| Parity naming/package rights are available | Not established | Package/domain/name due diligence |

## Retrieval limitations

Datafold's numerical pricing was not retrievable from its pricing route. JuxtAPPose's accessible text did not expose numerical prices and includes older contextual material; verify current license availability and release maintenance directly. GX's accessible pricing text exposed tier names but not amounts.

GateMap's “Parity Gate” surfaced in search, but its page failed to fetch; treat it as a follow-up lead only. PageParity also surfaced as a naming-adjacent software product, not evidence of tabular-engine overlap. No package/domain/trademark clearance or commercial-vendor trial was performed.

## Research updates

Before implementation, capture exact dependency versions, license texts and tested commands. Before monetization, refresh competitor packaging and verify actual buying behavior. Record changed decisions in an architecture log. Preserve failed tests, non-adoption reasons and inconclusive findings alongside positive evidence.
