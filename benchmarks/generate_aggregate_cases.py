#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path


PROFILES = {"global": 1, "low": 10, "high": None}


def generate(root: Path, profile: str, rows: int) -> Path:
    if profile not in PROFILES:
        raise ValueError(f"unknown aggregate profile: {profile}")
    groups = rows if PROFILES[profile] is None else min(rows, PROFILES[profile])
    case = root / f"aggregate-{profile}-{rows}"
    case.mkdir(parents=True, exist_ok=True)
    fields = ["group", "amount"]
    for name, indexes in (("baseline.csv", range(rows)), ("candidate.csv", range(rows - 1, -1, -1))):
        with (case / name).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for index in indexes:
                writer.writerow({"group": f"group-{index % groups:08d}", "amount": f"{index % 1000}.{index % 100:02d}"})
    group_by = [] if profile == "global" else ["group"]
    recipe = {
        "recipe_version": 2,
        "comparison_mode": "aggregate",
        "group_by": group_by,
        "measures": {
            "rows": {"operator": "count"},
            "amount": {"operator": "sum", "column": "amount", "nulls": "reject"},
        },
        "scope": {
            "snapshot": f"aggregate-{profile}-{rows}",
            "cutoff": "2026-10-09T00:00:00Z",
            "filters": [],
            "completeness": "full",
            "expected_empty": False,
        },
        "columns": {
            "group": {"type": "string"},
            "amount": {"type": "decimal", "scale": 2},
        },
        "output": {"sensitivity": "summary"},
    }
    (case / "recipe.json").write_text(json.dumps(recipe, indent=2) + "\n", encoding="utf-8")
    expected = {
        "outcome": "PASS",
        "counts": {
            "baseline_rows": rows,
            "candidate_rows": rows,
            "baseline_groups": groups,
            "candidate_groups": groups,
            "common_groups": groups,
            "baseline_only_groups": 0,
            "candidate_only_groups": 0,
            "exact_measures": groups * 2,
            "within_tolerance_measures": 0,
            "different_measures": 0,
        },
    }
    (case / "expected.json").write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    return case


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic aggregate benchmark inputs")
    parser.add_argument("--output", type=Path, default=Path("benchmarks/generated"))
    parser.add_argument("--rows", type=int, nargs="+", default=[10_000, 100_000])
    parser.add_argument("--profiles", nargs="+", choices=tuple(PROFILES), default=list(PROFILES))
    args = parser.parse_args()
    if any(rows <= 0 for rows in args.rows):
        parser.error("row counts must be positive")
    for rows in args.rows:
        for profile in args.profiles:
            print(generate(args.output, profile, rows))


if __name__ == "__main__":
    main()
