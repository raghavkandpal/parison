#!/usr/bin/env python3
import argparse
import json
import os
import platform
import tempfile
import time
from datetime import date
from pathlib import Path

from parison import __version__
from parison.core import assemble_suite, run_suite, verify_bundle


def measure_suite_scale(repository: Path, case_count: int, shard_count: int = 4) -> dict:
    if case_count <= 0 or shard_count <= 0:
        raise ValueError("case and shard counts must be positive")
    shard_count = min(case_count, shard_count)
    # Keep the generated plan on the checkout's filesystem so Windows can form
    # portable relative references even when its system temp uses another drive.
    with tempfile.TemporaryDirectory(prefix=".parison-suite-bench-", dir=repository) as temporary:
        root = Path(temporary)
        references = {
            "recipe": os.path.relpath(repository / "examples/orders.recipe.json", root),
            "baseline": os.path.relpath(repository / "examples/baseline.csv", root),
            "candidate": os.path.relpath(repository / "examples/candidate.csv", root),
        }
        plan = root / "suite.json"
        plan.write_text(json.dumps({
            "suite_version": 2,
            "cases": [{"id": f"case-{index:03d}", "tags": ["benchmark"], **references} for index in range(case_count)],
        }), encoding="utf-8")

        started = time.perf_counter()
        clean = run_suite(plan, root / "clean")
        clean_seconds = time.perf_counter() - started

        concurrent_seconds = {}
        concurrent_results = {}
        for jobs in (2, 4):
            started = time.perf_counter()
            concurrent_results[jobs] = run_suite(plan, root / f"jobs-{jobs}", jobs=jobs)
            concurrent_seconds[jobs] = time.perf_counter() - started

        shards = []
        started = time.perf_counter()
        for index in range(shard_count):
            output = root / f"shard-{index}"
            run_suite(plan, output, shard_index=index, shard_count=shard_count)
            shards.append(output)
        shard_execution_seconds = time.perf_counter() - started
        started = time.perf_counter()
        assembled = root / "assembled"
        assemble_suite(plan, shards, assembled)
        assembly_seconds = time.perf_counter() - started

        workspace = root / "workspace"
        run_suite(plan, root / "workspace-seed", workspace=workspace)
        started = time.perf_counter()
        resumed = run_suite(plan, root / "resumed", workspace=workspace, resume=True)
        resume_seconds = time.perf_counter() - started
        semantic = lambda result: (result["outcome"], result["outcome_counts"], [(case["id"], case["outcome"]) for case in result["cases"]])
        if (
            clean["outcome"] != "PASS"
            or resumed["outcome"] != "PASS"
            or verify_bundle(assembled)["outcome"] != "PASS"
            or any(semantic(result) != semantic(clean) or verify_bundle(root / f"jobs-{jobs}")["outcome"] != "PASS" for jobs, result in concurrent_results.items())
        ):
            raise RuntimeError("suite benchmark accuracy check failed")
        return {
            "cases": case_count,
            "shards": shard_count,
            "accuracy": "verified",
            "clean_seconds": round(clean_seconds, 6),
            "jobs_2_seconds": round(concurrent_seconds[2], 6),
            "jobs_4_seconds": round(concurrent_seconds[4], 6),
            "sequential_shard_execution_seconds": round(shard_execution_seconds, 6),
            "assembly_seconds": round(assembly_seconds, 6),
            "resume_seconds": round(resume_seconds, 6),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure Parison suite orchestration overhead")
    parser.add_argument("--cases", type=int, nargs="+", default=[10, 25, 100])
    parser.add_argument("--shards", type=int, default=4)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[1]
    payload = {
        "environment": {
            "date": date.today().isoformat(),
            "machine": platform.machine(),
            "platform": platform.system(),
            "python": platform.python_version(),
            "parison": __version__,
            "measurement": "single local run; jobs 1/2/4 plus sequential external shards; comparison, bundle copying and verification included; not a supported performance claim",
        },
        "cases": [measure_suite_scale(repository, count, args.shards) for count in args.cases],
    }
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.json_output:
        args.json_output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
