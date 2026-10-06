#!/usr/bin/env python3
import argparse
import csv
import json
import math
from decimal import Decimal
from pathlib import Path

PROFILES = ("wide", "long-strings", "composite-keys", "null-heavy", "high-mismatch")


def multiple_count(rows: int, step: int) -> int:
    return (rows - 1) // step + 1


def generate(root: Path, profile: str, rows: int, parquet: bool = False) -> Path:
    case = root / f"{profile}-rows-{rows}"
    case.mkdir(parents=True, exist_ok=True)
    payload_count = 97 if profile == "wide" else (1 if profile == "long-strings" else 7)
    payloads = [f"payload_{index}" for index in range(1, payload_count + 1)]
    keys = ["tenant", "id"] if profile == "composite-keys" else ["id"]
    nullable = [f"nullable_{index}" for index in range(1, 8)] if profile == "null-heavy" else []
    fields = [*keys, "status", "total", *payloads, *nullable]
    status_step = 2 if profile == "high-mismatch" else 250

    def row(index: int) -> dict[str, str]:
        payload = "x" * 4096 if profile == "long-strings" else f"segment-{index % 17:04d}"
        values = {
            "id": f"id-{index:012d}",
            "status": "active",
            "total": f"{index % 10000}.{index % 100:02d}",
            **{name: f"{payload}-{position % 13:02d}" for position, name in enumerate(payloads)},
            **{name: "" if index % 10 else str(index + position) for position, name in enumerate(nullable)},
        }
        if "tenant" in keys:
            values["tenant"] = f"tenant-{index % 101:03d}"
        return values

    baseline_path = case / "baseline.csv"
    candidate_path = case / "candidate.csv"
    with baseline_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index in range(rows):
            writer.writerow(row(index))
    with candidate_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index in range(rows - 1, -1, -1):
            if index % 1000 == 0:
                continue
            values = row(index)
            if index % status_step == 0:
                values["status"] = "changed"
            elif index % 100 == 0:
                values["total"] = str(Decimal(values["total"]) + Decimal("0.01"))
            writer.writerow(values)
        for index in range(max(1, rows // 2000)):
            values = row(rows + index)
            values["id"] = f"extra-{index:012d}"
            writer.writerow(values)

    columns = {
        **{name: {"type": "string", "comparison": "exact"} for name in keys},
        "status": {"type": "string", "comparison": "exact"},
        "total": {
            "type": "decimal", "scale": 2, "comparison": "numeric",
            "tolerance": {"formula": "symmetric-v1", "absolute": "0.01", "relative": "0"},
        },
        **{name: {"type": "string", "comparison": "exact"} for name in payloads},
        **{name: {"type": "integer", "comparison": "exact"} for name in nullable},
    }
    recipe = {
        "recipe_version": 1,
        "comparison_mode": "keyed",
        "keys": keys,
        "scope": {"snapshot": case.name, "cutoff": "2026-10-06T00:00:00Z", "filters": [], "completeness": "full", "expected_empty": False},
        "identity": {"null_keys": "reject", "duplicates": "reject"},
        "nulls_equal": True,
        "columns": columns,
        "output": {"sensitivity": "summary"},
    }
    (case / "recipe.json").write_text(json.dumps(recipe, indent=2) + "\n", encoding="utf-8")

    missing = multiple_count(rows, 1000)
    different = multiple_count(rows, status_step) - multiple_count(rows, math.lcm(status_step, 1000))
    tolerated = (
        multiple_count(rows, 100)
        - multiple_count(rows, math.lcm(100, status_step))
        - multiple_count(rows, 1000)
        + multiple_count(rows, math.lcm(100, status_step, 1000))
    )
    common = rows - missing
    extra = max(1, rows // 2000)
    expected = {
        "outcome": "FAIL",
        "counts": {
            "baseline": rows, "candidate": common + extra, "common_keys": common,
            "baseline_only": missing, "candidate_only": extra,
            "matched_exact": common - different - tolerated,
            "matched_within_tolerance": tolerated,
            "matched_with_required_difference": different,
        },
        "field_discrepancy_count": different + tolerated,
    }
    (case / "expected.json").write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")

    if parquet:
        try:
            import polars as pl
        except ImportError as exc:
            raise SystemExit("Parquet generation requires: pip install 'parison[parquet]'") from exc
        schema = {name: pl.String for name in fields}
        pl.read_csv(baseline_path, schema_overrides=schema).write_parquet(case / "baseline.parquet")
        pl.read_csv(candidate_path, schema_overrides=schema).write_parquet(case / "candidate.parquet")
    return case


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate adversarial Parison benchmark inputs")
    parser.add_argument("--output", type=Path, default=Path("benchmarks/generated"))
    parser.add_argument("--rows", type=int, default=10_000)
    parser.add_argument("--profiles", nargs="+", choices=PROFILES, default=list(PROFILES))
    parser.add_argument("--parquet", action="store_true")
    args = parser.parse_args()
    if args.rows <= 0:
        parser.error("rows must be positive")
    for profile in args.profiles:
        print(generate(args.output, profile, args.rows, args.parquet))


if __name__ == "__main__":
    main()
