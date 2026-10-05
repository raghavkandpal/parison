#!/usr/bin/env python3
import argparse
import json
import time
import tracemalloc
from pathlib import Path

from parity.core import compare


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure generated Parity cases and verify accuracy")
    parser.add_argument("cases", type=Path, nargs="+", help="directories created by generate_cases.py")
    args = parser.parse_args()
    measurements = []
    for case in args.cases:
        expected = json.loads((case / "expected.json").read_text(encoding="utf-8"))
        tracemalloc.start()
        started = time.perf_counter()
        result = compare(case / "recipe.json", case / "baseline.csv", case / "candidate.csv")
        elapsed = time.perf_counter() - started
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        if result["outcome"] != expected["outcome"] or result["counts"] != expected["counts"] or result["field_discrepancy_count"] != expected["field_discrepancy_count"]:
            raise SystemExit(f"accuracy check failed for {case}")
        measurements.append({
            "case": case.name,
            "accuracy": "verified",
            "elapsed_seconds": round(elapsed, 6),
            "peak_python_bytes": peak,
            "input_bytes": sum((case / name).stat().st_size for name in ("baseline.csv", "candidate.csv")),
            **expected,
        })
    print(json.dumps(measurements, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

