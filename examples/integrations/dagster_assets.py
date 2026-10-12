import subprocess

import dagster as dg


@dg.asset(deps=["candidate_output"])
def parison_evidence() -> dg.MaterializeResult:
    """Replace paths and attach this asset to both coordinated extraction assets."""
    output = "/evidence/parison-run"
    comparison = subprocess.run(
        [
            "parison", "compare",
            "--recipe", "/data/migration.recipe.json",
            "--baseline", "/data/baseline.csv",
            "--candidate", "/data/candidate.csv",
            "--output", output,
        ],
        check=False,
    )
    subprocess.run(["parison", "verify", output], check=True)
    if comparison.returncode:
        raise dg.Failure(f"Parison comparison exited {comparison.returncode}; verified bundle: {output}")
    return dg.MaterializeResult(metadata={"parison_bundle": dg.MetadataValue.path(output)})
