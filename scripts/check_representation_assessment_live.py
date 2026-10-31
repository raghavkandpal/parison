"""Disposable 16/17→18 representation qualification; no existing cluster is used."""

from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import psycopg

from parison import representation_assessment as assessment
from parison.analysis import _canonical
from parison.core import ParisonError
from parison.evolution import normalize_evolution
from parison.postgres_collection import export_postgres_collection

COLUMNS = ["id", "n", "amount", "note", "naive"]


def capture(binary, major, root, results):
    cluster = root / str(major)
    cluster.mkdir()
    data, sock = cluster / "data", cluster / "s"
    sock.mkdir()
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        port = reserve.getsockname()[1]
    subprocess.run(
        [
            str(binary / "initdb"),
            "-D",
            str(data),
            "-U",
            "parison_admin",
            "--auth=trust",
            "--encoding=UTF8",
            "--no-locale",
        ],
        stdout=subprocess.DEVNULL,
        check=True,
    )
    subprocess.run(
        [
            str(binary / "pg_ctl"),
            "-D",
            str(data),
            "-l",
            str(cluster / "server.log"),
            "-o",
            f"-k {sock} -p {port} -h ''",
            "-w",
            "start",
        ],
        stdout=subprocess.DEVNULL,
        check=True,
    )
    outputs = {}
    try:
        with psycopg.connect(
            host=str(sock), port=port, user="parison_admin", dbname="postgres", autocommit=True
        ) as admin:
            version = int(admin.execute("SHOW server_version_num").fetchone()[0])
            assert version == {16: 160015, 17: 170011, 18: 180006}[major]
            results["versions"].append(version)
            admin.execute("CREATE ROLE representation_reader LOGIN")
            admin.execute("CREATE SCHEMA gate")
            admin.execute("GRANT USAGE ON SCHEMA gate TO representation_reader")
            admin.execute(
                "CREATE TABLE gate.facts(id int PRIMARY KEY, n int, amount numeric(2,-3), note varchar(10), naive timestamp(0))"
            )
            admin.execute("INSERT INTO gate.facts VALUES(1,1,1000,%s,'2026-01-01 01:00:00')", (f"v{major}",))
            admin.execute("GRANT SELECT ON gate.facts TO representation_reader")
            plan = {
                "collection_plan_version": 2,
                "source_id": "synthetic-representation",
                "tables": {"facts": {"schema": "gate", "table": "facts", "columns": COLUMNS, "primary_key": ["id"]}},
                "limits": {
                    "max_rows": 10,
                    "max_output_bytes": 100000,
                    "max_representation_bytes": 1048576,
                    "statement_timeout_ms": 10000,
                    "wall_timeout_ms": 30000,
                },
            }
            plan_file = root / f"capture-plan-{major}.json"
            plan_file.write_bytes(_canonical(plan) + b"\n")
            with patch.dict(
                os.environ,
                {
                    "PGHOST": str(sock),
                    "PGPORT": str(port),
                    "PGUSER": "representation_reader",
                    "PGDATABASE": "postgres",
                    "PGOPTIONS": "",
                },
            ):

                def export(label):
                    output = root / f"capture-{major}-{label}"
                    summary = export_postgres_collection(plan_file, output)
                    assert summary["postgres_collection_summary_version"] == 2
                    outputs[label] = output
                    results["gates"].append(f"pg{major}-capture-{label}")

                export("equal")
                if major == 18:
                    admin.execute(
                        "ALTER TABLE gate.facts ALTER n TYPE bigint, ALTER amount TYPE numeric(3,-3), ALTER note TYPE varchar(20), ALTER naive TYPE timestamp(6)"
                    )
                    export("widen")
                    admin.execute("ALTER TABLE gate.facts ADD CONSTRAINT n_nn NOT NULL n NOT VALID")
                    export("unknown")
                    admin.execute(
                        "CREATE COLLATION gate.stale (provider=icu, locale='en-US', version='parison-synthetic')"
                    )
                    admin.execute("ALTER TABLE gate.facts ALTER note TYPE text COLLATE gate.stale")
                    export("drift")
    finally:
        subprocess.run(
            [str(binary / "pg_ctl"), "-D", str(data), "-m", "immediate", "-w", "stop"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    return outputs


def plan_for(baseline, candidate, widen):
    parents = assessment._parents(baseline, candidate)
    # These are explicit synthetic operator choices, not generated policy approval.
    fields = [
        {"id": name, "name": name, "presence": "required", "nullability": "non-null" if name == "id" else "nullable"}
        for name in COLUMNS
    ]
    evolution = normalize_evolution(
        {
            "evolution_version": 1,
            "direction": "baseline-to-candidate",
            "changes": [{"change": "unchanged", "baseline": [field], "candidate": [dict(field)]} for field in fields],
        }
    )
    return {
        "assessment_plan_version": 1,
        **{f"{side}_manifest_sha256": digest for side, digest in assessment._inputs(parents).items()},
        "tables": {"facts": {"baseline_id": "facts", "candidate_id": "facts", "evolution": evolution}},
        "rules": {
            name: ("relax" if name == "nullability" else "widen") if widen else "exact" for name in assessment._RULES
        },
    }


def qualify(args):
    results = {
        "python": platform.python_version(),
        "psycopg": psycopg.__version__,
        "platform": platform.platform(),
        "versions": [],
        "gates": [],
        "pairs": [],
        "scope": assessment.SCOPE,
        "row_parity_claim": False,
    }
    with tempfile.TemporaryDirectory(prefix="pr-repr-") as temporary:
        root = Path(temporary)
        captures = {major: capture(getattr(args, f"pg{major}"), major, root, results) for major in (16, 17, 18)}
        # Every cluster is stopped before any derived operation is run.
        for major in (16, 17):
            baseline = captures[major]["equal"]
            csv = baseline / "tables/facts/data.csv"
            assert csv.read_bytes() != (captures[18]["equal"] / "tables/facts/data.csv").read_bytes()
            for label, candidate_label, widen, expected in (
                ("equal-different-rows", "equal", False, "ACCEPT"),
                ("exact-rejects-widen", "widen", False, "DENY"),
                ("explicit-widen", "widen", True, "ACCEPT"),
                ("unknown-native-guarantee", "unknown", True, "INCONCLUSIVE"),
                ("provider-drift-deny-precedence", "drift", True, "DENY"),
            ):
                candidate = captures[18][candidate_label]
                plan = plan_for(baseline, candidate, widen)
                plan_file, output = root / f"plan-{major}-{label}.json", root / f"assessment-{major}-{label}"
                plan_file.write_bytes(_canonical(plan) + b"\n")
                summary = assessment.assess(plan_file, baseline, candidate, output)
                assert summary["compatibility"] == expected, (major, label, summary)
                assert summary["complete"] is True
                assert assessment.verify(output, baseline, candidate) == summary
                assert "PASS" not in json.dumps(summary)
                if label == "explicit-widen":
                    assert summary["reason_counts"]["numeric_changed"] == 2
                    assert summary["reason_counts"]["character_length_changed"] == 1
                    assert summary["reason_counts"]["datetime_precision_changed"] == 1
                if label == "unknown-native-guarantee":
                    assert summary["reason_counts"]["nullability_unknown"] == 1
                if label == "provider-drift-deny-precedence":
                    assert summary["reason_counts"]["collation_version_mismatch"] == 1
                    assert summary["reason_counts"]["nullability_unknown"] == 1
                results["pairs"].append(
                    {
                        "baseline": major,
                        "candidate": 18,
                        "case": label,
                        "compatibility": expected,
                        "fields": summary["fields"],
                        "reason_counts": summary["reason_counts"],
                    }
                )
                results["gates"].append(f"{major}-18-{label}-offline-replay")
            proposal_file = root / f"proposal-{major}.json"
            proposal_summary = assessment.propose(baseline, captures[18]["widen"], proposal_file)
            assert proposal_summary["status"] == "unapproved" and proposal_summary["field_suggestions"] == 5
            proposal = json.loads(proposal_file.read_bytes())
            assert "rules" not in proposal and "keys" not in proposal
            try:
                assessment.validate_plan(proposal, assessment._parents(baseline, captures[18]["widen"]))
            except ParisonError:
                pass
            else:
                raise AssertionError("unapproved proposal accepted as executable plan")
            results["gates"].append(f"{major}-18-unapproved-proposal")
    args.report.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "versions": results["versions"],
                "gates": len(results["gates"]),
                "pairs": len(results["pairs"]),
                "report": str(args.report),
            }
        )
    )


def main():
    parser = argparse.ArgumentParser()
    for major in (16, 17, 18):
        parser.add_argument(f"--pg{major}", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    qualify(parser.parse_args())


if __name__ == "__main__":
    main()
