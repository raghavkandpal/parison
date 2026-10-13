#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path


FIELDS = ["event_id", "category", "amount"]


def row(index: int) -> dict[str, str]:
    return {"event_id": f"event-{index:012d}", "category": f"category-{index % 17:02d}", "amount": f"{index % 10000}.{index % 100:02d}"}


def generate(root: Path, rows: int, mode: str = "multiset") -> Path:
    case = root / f"{mode}-{rows}"
    case.mkdir(parents=True, exist_ok=True)
    for name, indices in (("baseline", range(rows)), ("candidate", range(rows - 1, -1, -1))):
        with (case / f"{name}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            for index in indices:
                writer.writerow(row(index))
    recipe = {
        "recipe_version": 3 if mode == "multiset" else 1,
        "comparison_mode": mode,
        "scope": {"snapshot": f"synthetic-spill-{rows}", "cutoff": "2026-10-11T00:00:00Z", "filters": [], "completeness": "full", "expected_empty": False},
        "columns": {"event_id": {"type": "string"}, "category": {"type": "string"}, "amount": {"type": "decimal", "scale": 2}},
        "output": {"sensitivity": "summary"},
    }
    if mode == "keyed":
        recipe.update(keys=["event_id"], identity={"null_keys": "reject", "duplicates": "reject"}, nulls_equal=True)
        expected = {
            "outcome": "PASS",
            "counts": {
                "baseline": rows, "candidate": rows, "common_keys": rows,
                "baseline_only": 0, "candidate_only": 0, "matched_exact": rows,
                "matched_within_tolerance": 0, "matched_with_required_difference": 0,
            },
        }
    else:
        expected = {"outcome": "PASS", "rows": rows, "distinct_rows": rows}
    (case / "recipe.json").write_text(json.dumps(recipe, indent=2) + "\n", encoding="utf-8")
    (case / "expected.json").write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    return case


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic high-cardinality spill-engine cases")
    parser.add_argument("--output", type=Path, default=Path("benchmarks/generated"))
    parser.add_argument("--rows", type=int, nargs="+", default=[10_000, 100_000, 250_000])
    parser.add_argument("--mode", choices=("keyed", "multiset"), default="multiset")
    args = parser.parse_args()
    if any(rows <= 0 for rows in args.rows):
        parser.error("row counts must be positive")
    for rows in args.rows:
        print(generate(args.output, rows, args.mode))


if __name__ == "__main__":
    main()
