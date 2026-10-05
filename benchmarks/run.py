#!/usr/bin/env python3
import argparse
import csv
import json
import tempfile
import time
import tracemalloc
from pathlib import Path

from parity.core import compare, load_recipe, publish


def main():
    parser = argparse.ArgumentParser(description="Run a seeded Parity CSV benchmark")
    parser.add_argument("--rows", type=int, default=10_000)
    parser.add_argument("--columns", type=int, default=10)
    parser.add_argument("--mismatch-every", type=int, default=100)
    args = parser.parse_args()
    if args.rows <= 0 or args.columns <= 0 or args.mismatch_every <= 0:
        parser.error("rows, columns and mismatch-every must be positive")

    fields = ["id", *(f"value_{index}" for index in range(args.columns))]
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        recipe_path = root / "recipe.json"
        recipe_path.write_text(json.dumps({
            "recipe_version": 1,
            "comparison_mode": "keyed",
            "keys": ["id"],
            "scope": {"snapshot": "seeded-benchmark", "cutoff": "fixed", "filters": [], "completeness": "full"},
            "identity": {"null_keys": "reject", "duplicates": "reject"},
            "columns": {name: {"type": "string", "comparison": "exact"} for name in fields},
            "output": {"sensitivity": "summary"},
        }), encoding="utf-8")
        paths = [root / "baseline.csv", root / "candidate.csv"]
        handles = [path.open("w", encoding="utf-8", newline="") for path in paths]
        try:
            writers = [csv.DictWriter(handle, fieldnames=fields) for handle in handles]
            for writer in writers:
                writer.writeheader()
            for index in range(args.rows):
                row = {"id": f"id-{index:012d}", **{name: f"value-{index}-{name}" for name in fields[1:]}}
                writers[0].writerow(row)
                candidate = row.copy()
                if index % args.mismatch_every == 0:
                    candidate[fields[-1]] += "-changed"
                writers[1].writerow(candidate)
        finally:
            for handle in handles:
                handle.close()

        tracemalloc.start()
        started = time.perf_counter()
        result = compare(recipe_path, *paths)
        elapsed = time.perf_counter() - started
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        output = root / "run"
        publish(output, result, load_recipe(recipe_path))
        print(json.dumps({
            "rows_per_input": args.rows,
            "value_columns": args.columns,
            "mismatch_every": args.mismatch_every,
            "input_bytes": sum(path.stat().st_size for path in paths),
            "output_bytes": sum(path.stat().st_size for path in output.iterdir()),
            "elapsed_seconds": round(elapsed, 6),
            "peak_python_bytes": peak,
            "outcome": result["outcome"],
            "field_discrepancy_count": result["field_discrepancy_count"],
        }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
