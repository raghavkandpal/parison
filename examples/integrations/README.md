# Orchestrator integration examples

These examples run Parison as an external CLI after user-owned tasks produce baseline and candidate files. Parison receives no warehouse, orchestrator or cloud credentials.

- `dbt-paration-gate.sh` shows the ordering around `dbt build`, extraction and comparison.
- `airflow_dag.py` uses Airflow's standard-provider `BashOperator` for the comparison gate.
- `dagster_assets.py` materializes a verified evidence directory as a downstream asset.

Replace every `/data/...` and `/evidence/...` placeholder. The two extracts must represent the same logical snapshot; orchestration order alone does not establish that guarantee. Pin the Parison release in the execution environment, keep recipes under review, and retain the complete bundle when the task exits nonzero.

The Python files are reference snippets and require their named orchestrator packages. Repository tests compile their syntax and check their Parison command contract without adding those packages to Parison.
