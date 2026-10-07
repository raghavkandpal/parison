import argparse
import csv
import json
from pathlib import Path


def rows(status_keys, note_key, missing_key, extra_key):
    baseline, candidate = [], []
    for number in range(1, 201):
        key = f"{number:04d}"
        base = {"id": key, "amount": f"{number}.00", "status": "ready", "note": "stable"}
        changed = dict(base)
        if number % 10 == 0:
            changed["amount"] = f"{number}.05"
        if key in status_keys:
            changed["status"] = "held"
        if key == note_key:
            changed["note"] = "changed"
        baseline.append(base)
        if key != missing_key:
            candidate.append(changed)
    candidate.append({"id": extra_key, "amount": "9999.00", "status": "ready", "note": "extra"})
    return baseline, candidate


def write_csv(path, values):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "amount", "status", "note"])
        writer.writeheader()
        writer.writerows(values)


def main():
    parser = argparse.ArgumentParser(description="Generate deterministic inputs for the report-filtering study")
    parser.add_argument("output", nargs="?", default="/tmp/parison-report-filtering-01")
    output = Path(parser.parse_args().output)
    output.mkdir(parents=True, exist_ok=True)
    baseline, candidate_a = rows({"0042", "0137"}, "0088", "0077", "9001")
    _, candidate_b = rows({"0053", "0148"}, "0099", "0066", "9002")
    write_csv(output / "baseline.csv", baseline)
    write_csv(output / "candidate-a.csv", candidate_a)
    write_csv(output / "candidate-b.csv", candidate_b)
    recipe = {
        "recipe_version": 1, "comparison_mode": "keyed", "keys": ["id"],
        "scope": {"snapshot": "synthetic-filter-study-v1", "cutoff": "2026-10-06T00:00:00Z", "filters": [], "completeness": "full", "expected_empty": False},
        "identity": {"null_keys": "reject", "duplicates": "reject"}, "nulls_equal": True,
        "columns": {
            "id": {"type": "string", "comparison": "exact"},
            "amount": {"type": "decimal", "scale": 2, "comparison": "numeric", "tolerance": {"formula": "symmetric-v1", "absolute": "0.10", "relative": "0"}},
            "status": {"type": "string", "comparison": "exact"}, "note": {"type": "string", "comparison": "exact"}},
        "output": {"sensitivity": "raw"}}
    (output / "recipe.json").write_text(json.dumps(recipe, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
