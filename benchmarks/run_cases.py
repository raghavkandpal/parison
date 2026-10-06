#!/usr/bin/env python3
import argparse
import json
import platform
import subprocess
import statistics
import sys
import time
import tracemalloc
from datetime import date
from importlib import metadata
from pathlib import Path

from parity.core import compare


def measure(case: Path, input_format: str = "csv") -> dict:
    expected = json.loads((case / "expected.json").read_text(encoding="utf-8"))
    suffix = ".parquet" if input_format == "parquet" else ".csv"
    tracemalloc.start()
    started = time.perf_counter()
    result = compare(case / "recipe.json", case / f"baseline{suffix}", case / f"candidate{suffix}")
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    if result["outcome"] != expected["outcome"] or result["counts"] != expected["counts"] or result["field_discrepancy_count"] != expected["field_discrepancy_count"]:
        raise SystemExit(f"accuracy check failed for {case}")
    try:
        import resource
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        rss_bytes = rss if platform.system() == "Darwin" else rss * 1024
    except ImportError:
        rss_bytes = None
    return {"elapsed_seconds": elapsed, "peak_python_bytes": peak, "peak_rss_bytes": rss_bytes}


def child_measurement(case: Path, input_format: str) -> dict:
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--worker", "--format", input_format, str(case.resolve())],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def package_version() -> str:
    try:
        return metadata.version("parity-compare")
    except metadata.PackageNotFoundError:
        return "source-tree"


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure generated Parity cases and verify accuracy")
    parser.add_argument("cases", type=Path, nargs="+", help="directories created by generate_cases.py")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--max-memory-per-row", type=float, help="fail when median peak Python bytes per baseline row exceeds this value")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--format", choices=("csv", "parquet"), default="csv")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        if len(args.cases) != 1:
            parser.error("worker requires exactly one case")
        print(json.dumps(measure(args.cases[0], args.format)))
        return
    if args.repeats <= 0:
        parser.error("repeats must be positive")
    measurements = []
    for case in args.cases:
        expected = json.loads((case / "expected.json").read_text(encoding="utf-8"))
        child_measurement(case, args.format)  # Unmeasured warm-up verifies the case and primes filesystem caches.
        runs = []
        for _ in range(args.repeats):
            runs.append(child_measurement(case, args.format))
        elapsed_runs = [run["elapsed_seconds"] for run in runs]
        peak_runs = [run["peak_python_bytes"] for run in runs]
        rss_runs = [run["peak_rss_bytes"] for run in runs if run["peak_rss_bytes"] is not None]
        elapsed = statistics.median(elapsed_runs)
        peak = statistics.median(peak_runs)
        baseline_rows = expected["counts"]["baseline"]
        memory_per_row = peak / baseline_rows
        if args.max_memory_per_row is not None and memory_per_row > args.max_memory_per_row:
            raise SystemExit(f"memory regression for {case}: {memory_per_row:.1f} > {args.max_memory_per_row:.1f} bytes/row")
        measurements.append({
            "case": case.name,
            "format": args.format,
            "accuracy": "verified",
            "repeats": args.repeats,
            "median_elapsed_seconds": round(elapsed, 6),
            "min_elapsed_seconds": round(min(elapsed_runs), 6),
            "max_elapsed_seconds": round(max(elapsed_runs), 6),
            "baseline_rows_per_second": round(baseline_rows / elapsed, 1),
            "median_peak_python_bytes": peak,
            "peak_python_bytes_per_baseline_row": round(memory_per_row, 1),
            "median_peak_rss_bytes": statistics.median(rss_runs) if rss_runs else None,
            "min_peak_rss_bytes": min(rss_runs) if rss_runs else None,
            "max_peak_rss_bytes": max(rss_runs) if rss_runs else None,
            "input_bytes": sum((case / f"{name}.{'parquet' if args.format == 'parquet' else 'csv'}").stat().st_size for name in ("baseline", "candidate")),
            **expected,
        })
    payload = {
        "environment": {
            "date": date.today().isoformat(),
            "machine": platform.machine(),
            "platform": platform.system(),
            "python": platform.python_version(),
            "parity": package_version(),
            "measurement": "median of fresh subprocess runs after one warm-up; tracemalloc and process peak RSS; not a supported performance claim",
        },
        "cases": measurements,
    }
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.json_output:
        args.json_output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
