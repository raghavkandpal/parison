#!/usr/bin/env python3
import argparse
import json
import platform
import statistics
import time
import tracemalloc
from datetime import date
from pathlib import Path

from parity.core import compare


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure generated Parity cases and verify accuracy")
    parser.add_argument("cases", type=Path, nargs="+", help="directories created by generate_cases.py")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--max-memory-per-row", type=float, help="fail when median peak Python bytes per baseline row exceeds this value")
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    if args.repeats <= 0:
        parser.error("repeats must be positive")
    measurements = []
    for case in args.cases:
        expected = json.loads((case / "expected.json").read_text(encoding="utf-8"))
        elapsed_runs = []
        peak_runs = []
        for _ in range(args.repeats):
            tracemalloc.start()
            started = time.perf_counter()
            result = compare(case / "recipe.json", case / "baseline.csv", case / "candidate.csv")
            elapsed_runs.append(time.perf_counter() - started)
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            peak_runs.append(peak)
            if result["outcome"] != expected["outcome"] or result["counts"] != expected["counts"] or result["field_discrepancy_count"] != expected["field_discrepancy_count"]:
                raise SystemExit(f"accuracy check failed for {case}")
        elapsed = statistics.median(elapsed_runs)
        peak = statistics.median(peak_runs)
        baseline_rows = expected["counts"]["baseline"]
        memory_per_row = peak / baseline_rows
        if args.max_memory_per_row is not None and memory_per_row > args.max_memory_per_row:
            raise SystemExit(f"memory regression for {case}: {memory_per_row:.1f} > {args.max_memory_per_row:.1f} bytes/row")
        measurements.append({
            "case": case.name,
            "accuracy": "verified",
            "repeats": args.repeats,
            "median_elapsed_seconds": round(elapsed, 6),
            "min_elapsed_seconds": round(min(elapsed_runs), 6),
            "max_elapsed_seconds": round(max(elapsed_runs), 6),
            "baseline_rows_per_second": round(baseline_rows / elapsed, 1),
            "median_peak_python_bytes": peak,
            "peak_python_bytes_per_baseline_row": round(memory_per_row, 1),
            "input_bytes": sum((case / name).stat().st_size for name in ("baseline.csv", "candidate.csv")),
            **expected,
        })
    payload = {
        "environment": {
            "date": date.today().isoformat(),
            "machine": platform.machine(),
            "platform": platform.system(),
            "python": platform.python_version(),
            "measurement": "median of repeated local runs with tracemalloc; not a supported performance claim",
        },
        "cases": measurements,
    }
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.json_output:
        args.json_output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
