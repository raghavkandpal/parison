from datetime import datetime

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG


with DAG(
    dag_id="parison_migration_gate",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
) as dag:
    # Make this task depend on your coordinated baseline/candidate extraction tasks.
    compare_outputs = BashOperator(
        task_id="compare_outputs",
        bash_command=(
            'parison compare --recipe "$PARISON_RECIPE" '
            '--baseline "$PARISON_BASELINE" --candidate "$PARISON_CANDIDATE" '
            '--output "$PARISON_OUTPUT"'
        ),
        env={
            "PARISON_RECIPE": "/data/migration.recipe.json",
            "PARISON_BASELINE": "/data/baseline.csv",
            "PARISON_CANDIDATE": "/data/candidate.csv",
            "PARISON_OUTPUT": "/evidence/parison-run",
        },
        append_env=True,
    )

    verify_evidence = BashOperator(
        task_id="verify_evidence",
        bash_command='parison verify "$PARISON_OUTPUT"',
        env={"PARISON_OUTPUT": "/evidence/parison-run"},
        append_env=True,
    )

    compare_outputs >> verify_evidence
