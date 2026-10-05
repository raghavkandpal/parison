#!/usr/bin/env python3
import argparse
import csv
import json
from decimal import Decimal
from pathlib import Path


PAYLOAD_COLUMNS = [f"payload_{index}" for index in range(1, 8)]
FIELDS = ["id", "status", "total", *PAYLOAD_COLUMNS]


def multiple_count(rows: int, step: int) -> int:
    return (rows - 1) // step + 1


def source_row(index: int) -> dict[str, str]:
    return {
        "id": f"id-{index:012d}",
        "status": "active",
        "total": f"{index % 10000}.{index % 100:02d}",
        **{name: f"segment-{index % (position + 7):04d}" for position, name in enumerate(PAYLOAD_COLUMNS)},
    }


def generate(root: Path, rows: int) -> None:
    case = root / f"rows-{rows}"
    case.mkdir(parents=True, exist_ok=True)
    baseline = case / "baseline.csv"
    candidate = case / "candidate.csv"

    with baseline.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for index in range(rows):
            writer.writerow(source_row(index))

    with candidate.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for index in range(rows - 1, -1, -1):
            if index % 1000 == 0:
                continue
            row = source_row(index)
            if index % 250 == 0:
                row["status"] = "changed"
            elif index % 100 == 0:
                row["total"] = str(Decimal(row["total"]) + Decimal("0.01"))
            writer.writerow(row)
        extra_rows = max(1, rows // 2000)
        for index in range(extra_rows):
            row = source_row(rows + index)
            row["id"] = f"extra-{index:012d}"
            writer.writerow(row)

    columns = {
        "id": {"type": "string", "comparison": "exact"},
        "status": {"type": "string", "comparison": "exact"},
        "total": {
            "type": "decimal",
            "scale": 2,
            "comparison": "numeric",
            "tolerance": {"formula": "symmetric-v1", "absolute": "0.01", "relative": "0"},
        },
        **{name: {"type": "string", "comparison": "exact"} for name in PAYLOAD_COLUMNS},
    }
    recipe = {
        "recipe_version": 1,
        "comparison_mode": "keyed",
        "keys": ["id"],
        "scope": {
            "snapshot": f"synthetic-benchmark-{rows}",
            "cutoff": "2026-10-05T00:00:00Z",
            "filters": [],
            "completeness": "full",
            "expected_empty": False,
        },
        "identity": {"null_keys": "reject", "duplicates": "reject"},
        "nulls_equal": True,
        "columns": columns,
        "output": {"sensitivity": "summary"},
    }
    (case / "recipe.json").write_text(json.dumps(recipe, indent=2) + "\n", encoding="utf-8")

    baseline_only = multiple_count(rows, 1000)
    different = multiple_count(rows, 250) - baseline_only
    tolerated = multiple_count(rows, 100) - multiple_count(rows, 500)
    common = rows - baseline_only
    extra_rows = max(1, rows // 2000)
    expected = {
        "outcome": "FAIL",
        "counts": {
            "baseline": rows,
            "candidate": common + extra_rows,
            "common_keys": common,
            "baseline_only": baseline_only,
            "candidate_only": extra_rows,
            "matched_exact": common - different - tolerated,
            "matched_within_tolerance": tolerated,
            "matched_with_required_difference": different,
        },
        "field_discrepancy_count": different + tolerated,
    }
    (case / "expected.json").write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic Parity benchmark inputs")
    parser.add_argument("--output", type=Path, default=Path("benchmarks/generated"))
    parser.add_argument("--rows", type=int, nargs="+", default=[10_000, 100_000])
    args = parser.parse_args()
    if any(rows <= 0 for rows in args.rows):
        parser.error("row counts must be positive")
    for rows in args.rows:
        generate(args.output, rows)
        print(args.output / f"rows-{rows}")


if __name__ == "__main__":
    main()
