# Orchestrator integration guide

Parison is a gate after extraction, not an extraction framework. A dbt, Airflow, Dagster or CI workflow should:

1. materialize the old and new implementations;
2. export both outputs at one coordinated logical snapshot;
3. run a reviewed Parison recipe;
4. preserve the comparison exit code, verify and retain the complete evidence directory regardless of outcome; and
5. allow only PASS (`0`) to advance the cutover.

The copyable [integration examples](../../examples/integrations) keep Parison outside the orchestrator process and pass only local file paths. This preserves the zero-custody boundary and leaves credential rotation, retries, scheduling and warehouse-specific snapshot coordination with the system that already owns them.

## dbt

Run `dbt build` for the selected candidate resources before the project-owned extraction step. dbt documents `build` as building and testing selected resources in dependency order. Do not infer that a successful dbt build means two exports share a snapshot; the adapter-specific extraction step must provide that guarantee.

## Airflow

Use the standard provider's `BashOperator` after both extraction tasks. Store the evidence directory on durable worker-visible storage and retain it when comparison returns FAIL, ERROR or INCONCLUSIVE. The example deliberately uses environment variables rather than interpolating runtime input into the command string.

## Dagster

Represent the verified evidence bundle as a downstream asset. `subprocess.run` receives an argument list rather than a shell command, and a nonzero Parison result fails materialization while leaving the output directory available for retention and investigation.

## References checked

- [dbt command reference](https://docs.getdbt.com/reference/dbt-commands)
- [dbt build reference](https://docs.getdbt.com/reference/commands/build)
- [Airflow operators and hooks reference](https://airflow.apache.org/docs/apache-airflow/stable/operators-and-hooks-ref.html)
- [Dagster asset quickstart](https://docs.dagster.io/getting-started/quickstart)
