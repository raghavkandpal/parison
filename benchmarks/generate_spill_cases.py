#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path


FIELDS = ["event_id", "category", "amount"]


def row(index: int) -> dict[str, str]:
    return {"event_id": f"event-{index:012d}", "category": f"category-{index % 17:02d}", "amount": f"{index % 10000}.{index % 100:02d}"}


def generate(root: Path, rows: int) -> Path:
    case = root / f"multiset-{rows}"
    case.mkdir(parents=True, exist_ok=True)
    for name, indices in (("baseline", range(rows)), ("candidate", range(rows - 1, -1, -1))):
        with (case / f"{name}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            for index in indices:
                writer.writerow(row(index))
    recipe = {
        "recipe_version": 3,
        "comparison_mode": "multiset",
        "scope": {"snapshot": f"synthetic-spill-{rows}", "cutoff": "2026-10-11T00:00:00Z", "filters": [], "completeness": "full", "expected_empty": False},
        "columns": {"event_id": {"type": "string"}, "category": {"type": "string"}, "amount": {"type": "decimal", "scale": 2}},
        "output": {"sensitivity": "summary"},
    }
    expected = {"outcome": "PASS", "rows": rows, "distinct_rows": rows}
    (case / "recipe.json").write_text(json.dumps(recipe, indent=2) + "\n", encoding="utf-8")
    (case / "expected.json").write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    return case


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic high-cardinality multiset cases")
    parser.add_argument("--output", type=Path, default=Path("benchmarks/generated"))
    parser.add_argument("--rows", type=int, nargs="+", default=[10_000, 100_000, 250_000])
    args = parser.parse_args()
    if any(rows <= 0 for rows in args.rows):
        parser.error("row counts must be positive")
    for rows in args.rows:
        print(generate(args.output, rows))


if __name__ == "__main__":
    main()
