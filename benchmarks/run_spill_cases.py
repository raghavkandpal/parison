#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import sys
import time
import tracemalloc
from datetime import date
from pathlib import Path

from parison import __version__
from parison.core import compare


def peak_rss_bytes() -> int | None:
    try:
        import resource
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return rss if platform.system() == "Darwin" else rss * 1024
    except ImportError:
        if platform.system() != "Windows":
            return None
        import ctypes
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD), ("page_fault_count", wintypes.DWORD),
                ("peak_working_set_size", ctypes.c_size_t), ("working_set_size", ctypes.c_size_t),
                ("quota_peak_paged_pool_usage", ctypes.c_size_t), ("quota_paged_pool_usage", ctypes.c_size_t),
                ("quota_peak_non_paged_pool_usage", ctypes.c_size_t), ("quota_non_paged_pool_usage", ctypes.c_size_t),
                ("pagefile_usage", ctypes.c_size_t), ("peak_pagefile_usage", ctypes.c_size_t),
            ]

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        if not ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            return None
        return counters.peak_working_set_size


def measure(case: Path, engine: str) -> dict:
    expected = json.loads((case / "expected.json").read_text(encoding="utf-8"))
    tracemalloc.start()
    started = time.perf_counter()
    result = compare(
        case / "recipe.json", case / "baseline.csv", case / "candidate.csv",
        engine=engine, max_temp_bytes=20_000_000_000,
    )
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    counts = result["counts"]
    accurate = counts == expected["counts"] if "counts" in expected else (
        counts["baseline_rows"] == expected["rows"] and counts["baseline_distinct_rows"] == expected["distinct_rows"]
    )
    if result["outcome"] != expected["outcome"] or not accurate:
        raise SystemExit(f"accuracy check failed for {case} with {engine}")
    return {
        "elapsed_seconds": elapsed,
        "peak_python_bytes": peak,
        "peak_rss_bytes": peak_rss_bytes(),
        "temporary_bytes": result["runtime"].get("temporary_bytes", 0),
        "counts": counts,
    }


def child(case: Path, engine: str) -> dict:
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--worker", "--engine", engine, str(case.resolve())],
        check=True, capture_output=True, text=True,
    )
    return json.loads(completed.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare memory and SQLite engines in fresh processes")
    parser.add_argument("cases", type=Path, nargs="+")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--engine", choices=("memory", "sqlite"), help=argparse.SUPPRESS)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        if len(args.cases) != 1 or args.engine is None:
            parser.error("worker requires one case and one engine")
        print(json.dumps(measure(args.cases[0], args.engine)))
        return
    if args.repeats <= 0:
        parser.error("repeats must be positive")
    measurements = []
    for case in args.cases:
        expected = json.loads((case / "expected.json").read_text(encoding="utf-8"))
        engine_runs = {}
        for engine in ("memory", "sqlite"):
            child(case, engine)
            runs = [child(case, engine) for _ in range(args.repeats)]
            rss_runs = [run["peak_rss_bytes"] for run in runs if run["peak_rss_bytes"] is not None]
            engine_runs[engine] = {
                "median_elapsed_seconds": round(statistics.median(run["elapsed_seconds"] for run in runs), 6),
                "median_peak_python_bytes": statistics.median(run["peak_python_bytes"] for run in runs),
                "median_peak_rss_bytes": statistics.median(rss_runs) if rss_runs else None,
                "median_temporary_bytes": statistics.median(run["temporary_bytes"] for run in runs),
            }
            if any(run["counts"] != runs[0]["counts"] for run in runs):
                raise SystemExit(f"nondeterministic counts for {case} with {engine}")
        measurements.append({"case": case.name, **expected, "engines": engine_runs})
    payload = {
        "environment": {
            "date": date.today().isoformat(), "machine": platform.machine(), "platform": platform.system(),
            "python": platform.python_version(), "parison": __version__,
            "measurement": "median of fresh subprocess runs after one warm-up; accuracy checked; machine-specific, not a supported scale claim",
        },
        "cases": measurements,
    }
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.json_output:
        args.json_output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
