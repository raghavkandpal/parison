import csv
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from parity.core import ParityError, compare, load_recipe


def recipe(columns=None, keys=None):
    columns = columns or {
        "id": {"type": "string", "comparison": "exact"},
        "value": {"type": "string", "comparison": "exact"},
    }
    return {
        "recipe_version": 1,
        "comparison_mode": "keyed",
        "keys": keys or ["id"],
        "scope": {"snapshot": "fixture", "cutoff": "2026-10-01T00:00:00Z", "filters": [], "completeness": "full", "expected_empty": False},
        "identity": {"null_keys": "reject", "duplicates": "reject"},
        "columns": columns,
        "output": {"sensitivity": "summary"},
    }


class SemanticCorpus(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write_recipe(self, value):
        path = self.root / "recipe.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def write_csv(self, name, fields, rows):
        path = self.root / name
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def run_rows(self, spec, fields, left_rows, right_rows):
        return compare(
            self.write_recipe(spec),
            self.write_csv("left.csv", fields, left_rows),
            self.write_csv("right.csv", fields, right_rows),
        )

    def test_composite_keys_are_typed_tuples_not_concatenated_strings(self):
        columns = {
            "a": {"type": "string", "comparison": "exact"},
            "b": {"type": "string", "comparison": "exact"},
            "value": {"type": "string", "comparison": "exact"},
        }
        result = self.run_rows(
            recipe(columns, ["a", "b"]), ["a", "b", "value"],
            [{"a": "a|b", "b": "c", "value": "x"}],
            [{"a": "a", "b": "b|c", "value": "x"}],
        )
        self.assertEqual(result["counts"]["common_keys"], 0)
        self.assertEqual(result["outcome"], "FAIL")

    def test_leading_zero_string_key_stays_distinct(self):
        result = self.run_rows(
            recipe(), ["id", "value"],
            [{"id": "001", "value": "x"}], [{"id": "1", "value": "x"}],
        )
        self.assertEqual(result["counts"]["common_keys"], 0)

    def test_row_and_column_order_do_not_change_result(self):
        spec = recipe()
        left = self.write_csv("left.csv", ["id", "value"], [{"id": "1", "value": "a"}, {"id": "2", "value": "b"}])
        right = self.write_csv("right.csv", ["value", "id"], [{"id": "2", "value": "b"}, {"id": "1", "value": "a"}])
        result = compare(self.write_recipe(spec), left, right)
        self.assertEqual(result["outcome"], "PASS")

    def test_swapping_inputs_swaps_only_missing_sides(self):
        spec = self.write_recipe(recipe())
        left = self.write_csv("left.csv", ["id", "value"], [{"id": "1", "value": "a"}])
        right = self.write_csv("right.csv", ["id", "value"], [{"id": "2", "value": "a"}])
        forward = compare(spec, left, right)["counts"]
        reverse = compare(spec, right, left)["counts"]
        self.assertEqual(forward["baseline_only"], reverse["candidate_only"])
        self.assertEqual(forward["candidate_only"], reverse["baseline_only"])

    def test_header_only_input_is_inconclusive(self):
        result = self.run_rows(recipe(), ["id", "value"], [], [])
        self.assertEqual(result["outcome"], "INCONCLUSIVE")
        self.assertFalse(result["complete"])

    def test_declared_empty_scope_passes_only_when_both_inputs_are_empty(self):
        spec = recipe()
        spec["scope"]["expected_empty"] = True
        empty = self.run_rows(spec, ["id", "value"], [], [])
        self.assertEqual(empty["outcome"], "PASS")
        self.assertTrue(empty["complete"])
        one_sided = self.run_rows(spec, ["id", "value"], [], [{"id": "1", "value": "unexpected"}])
        self.assertEqual(one_sided["outcome"], "FAIL")
        self.assertEqual(one_sided["counts"]["candidate_only"], 1)

    def test_missing_unexpected_and_duplicate_columns_are_errors(self):
        spec = self.write_recipe(recipe())
        valid = self.write_csv("valid.csv", ["id", "value"], [{"id": "1", "value": "a"}])
        for name, contents, message in (
            ("missing.csv", "id\n1\n", "missing=value"),
            ("extra.csv", "id,value,extra\n1,a,x\n", "unexpected=extra"),
            ("duplicate.csv", "id,value,value\n1,a,b\n", "duplicate column names"),
        ):
            with self.subTest(name=name):
                path = self.root / name
                path.write_text(contents, encoding="utf-8")
                with self.assertRaisesRegex(ParityError, message):
                    compare(spec, valid, path)

    def test_declared_exclusion_allows_extra_column(self):
        spec = recipe()
        spec["excluded_columns"] = {"updated_at": "nondeterministic metadata"}
        result = self.run_rows(
            spec, ["id", "value", "updated_at"],
            [{"id": "1", "value": "a", "updated_at": "old"}],
            [{"id": "1", "value": "a", "updated_at": "new"}],
        )
        self.assertEqual(result["outcome"], "PASS")

    def test_invalid_utf8_is_an_error(self):
        spec = self.write_recipe(recipe())
        valid = self.write_csv("valid.csv", ["id", "value"], [{"id": "1", "value": "a"}])
        invalid = self.root / "invalid.csv"
        invalid.write_bytes(b"id,value\n1,\xff\n")
        with self.assertRaisesRegex(ParityError, "cannot parse"):
            compare(spec, valid, invalid)

    def test_unicode_and_whitespace_are_exact(self):
        for left_value, right_value in (("é", "e\u0301"), ("value", " value "), ("ABC", "abc")):
            with self.subTest(left=left_value, right=right_value):
                result = self.run_rows(
                    recipe(), ["id", "value"],
                    [{"id": "1", "value": left_value}], [{"id": "1", "value": right_value}],
                )
                self.assertEqual(result["outcome"], "FAIL")

    def test_decimal_tolerance_boundaries_and_symmetry(self):
        columns = {
            "id": {"type": "string", "comparison": "exact"},
            "value": {
                "type": "decimal", "comparison": "numeric",
                "tolerance": {"formula": "symmetric-v1", "absolute": "0.01", "relative": "0.1"},
            },
        }
        spec = recipe(columns)
        for left_value, right_value, expected in (("0", "0.01", "PASS"), ("-10", "-11.01", "PASS"), ("-10", "-11.13", "FAIL")):
            with self.subTest(left=left_value, right=right_value):
                result = self.run_rows(
                    spec, ["id", "value"],
                    [{"id": "1", "value": left_value}], [{"id": "1", "value": right_value}],
                )
                self.assertEqual(result["outcome"], expected)

    def test_nonfinite_numbers_are_errors(self):
        for kind in ("decimal", "float"):
            for token in ("NaN", "Infinity", "-Infinity"):
                with self.subTest(kind=kind, token=token):
                    columns = {
                        "id": {"type": "string", "comparison": "exact"},
                        "value": {
                            "type": kind, "comparison": "numeric",
                            "tolerance": {"formula": "symmetric-v1", "absolute": "0", "relative": "0"},
                        },
                    }
                    with self.assertRaisesRegex(ParityError, "cannot parse"):
                        self.run_rows(recipe(columns), ["id", "value"], [{"id": "1", "value": "1"}], [{"id": "1", "value": token}])

    def test_timestamp_requires_zone_and_compares_instants(self):
        columns = {
            "id": {"type": "string", "comparison": "exact"},
            "value": {"type": "timestamp", "comparison": "exact"},
        }
        spec = recipe(columns)
        equal = self.run_rows(
            spec, ["id", "value"],
            [{"id": "1", "value": "2026-01-01T00:00:00+00:00"}],
            [{"id": "1", "value": "2026-01-01T05:30:00+05:30"}],
        )
        self.assertEqual(equal["outcome"], "PASS")
        with self.assertRaisesRegex(ParityError, "explicit timezone"):
            self.run_rows(
                spec, ["id", "value"],
                [{"id": "1", "value": "2026-01-01T00:00:00"}],
                [{"id": "1", "value": "2026-01-01T00:00:00+00:00"}],
            )

    def test_recipe_rejects_bad_tolerances_and_key_policies(self):
        numeric = {
            "id": {"type": "string", "comparison": "exact"},
            "value": {
                "type": "decimal", "comparison": "numeric",
                "tolerance": {"formula": "symmetric-v1", "absolute": "0", "relative": "0"},
            },
        }
        for mutate, message in (
            (lambda value: value["columns"]["value"]["tolerance"].update(absolute="-1"), "finite and non-negative"),
            (lambda value: value["columns"]["value"]["tolerance"].update(relative="NaN"), "finite and non-negative"),
            (lambda value: value["columns"]["id"].update(comparison="numeric"), "key column id must use exact"),
        ):
            with self.subTest(message=message):
                value = recipe(deepcopy(numeric))
                mutate(value)
                with self.assertRaisesRegex(ParityError, message):
                    load_recipe(self.write_recipe(value))

    def test_scope_requires_cutoff_and_declared_filters(self):
        for field in ("cutoff", "filters", "expected_empty"):
            with self.subTest(field=field):
                value = recipe()
                del value["scope"][field]
                with self.assertRaisesRegex(ParityError, "scope must contain exactly"):
                    load_recipe(self.write_recipe(value))
        value = recipe()
        value["scope"]["filters"] = "status = active"
        with self.assertRaisesRegex(ParityError, "scope.filters"):
            load_recipe(self.write_recipe(value))
        value = recipe()
        value["scope"]["expected_empty"] = "false"
        with self.assertRaisesRegex(ParityError, "scope.expected_empty"):
            load_recipe(self.write_recipe(value))


if __name__ == "__main__":
    unittest.main()
