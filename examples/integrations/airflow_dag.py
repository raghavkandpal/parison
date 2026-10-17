import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG

with DAG(
    dag_id="parison_migration_gate",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
) as dag:
    # Make this task depend on your coordinated baseline/candidate extraction tasks.
    compare_outputs = BashOperator(
        task_id="compare_outputs",
        bash_command=(
            'set +e; parison compare --recipe "$PARISON_RECIPE" '
            '--baseline "$PARISON_BASELINE" --candidate "$PARISON_CANDIDATE" '
            '--output "$PARISON_OUTPUT"; code=$?; set -e; '
            'parison verify "$PARISON_OUTPUT"; exit "$code"'
        ),
        env={
            "PARISON_RECIPE": "/data/migration.recipe.json",
            "PARISON_BASELINE": "/data/baseline.csv",
            "PARISON_CANDIDATE": "/data/candidate.csv",
            "PARISON_OUTPUT": "/evidence/parison-run",
        },
        append_env=True,
    )
