import csv
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from parison.core import ParisonError, compare, load_recipe


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
        "nulls_equal": True,
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

    def test_explicit_column_mappings_cover_keys_values_and_raw_evidence(self):
        spec = recipe()
        spec["column_mappings"] = {
            "id": {"baseline": "legacy_id", "candidate": "id"},
            "value": {"baseline": "legacy_value", "candidate": "value"},
        }
        left = self.write_csv("left.csv", ["legacy_id", "legacy_value"], [{"legacy_id": "001", "legacy_value": "same"}])
        right = self.write_csv("right.csv", ["value", "id"], [{"id": "001", "value": "same"}])
        result = compare(self.write_recipe(spec), left, right)
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["column_mappings"], spec["column_mappings"])

        spec["output"]["sensitivity"] = "raw"
        right = self.write_csv("different.csv", ["id", "value"], [{"id": "001", "value": "different"}])
        result = compare(self.write_recipe(spec), left, right)
        self.assertEqual(result["outcome"], "FAIL")
        self.assertEqual(result["discrepancy_sample"][0]["field"], "value")

    def test_column_mappings_reject_ambiguous_or_invalid_sources(self):
        invalid = (
            ({"missing": {"baseline": "a", "candidate": "b"}}, "canonical column"),
            ({"id": {"baseline": "legacy_id"}}, "exactly baseline and candidate"),
            ({"id": {"baseline": "same", "candidate": "id"}, "value": {"baseline": "same", "candidate": "value"}}, "unique baseline"),
        )
        for mappings, message in invalid:
            with self.subTest(message=message):
                spec = recipe()
                spec["column_mappings"] = mappings
                with self.assertRaisesRegex(ParisonError, message):
                    load_recipe(self.write_recipe(spec))

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
                with self.assertRaisesRegex(ParisonError, message):
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
        with self.assertRaisesRegex(ParisonError, "cannot parse"):
            compare(spec, valid, invalid)

    def test_unicode_and_whitespace_are_exact(self):
        for left_value, right_value in (("é", "e\u0301"), ("value", " value "), ("ABC", "abc")):
            with self.subTest(left=left_value, right=right_value):
                result = self.run_rows(
                    recipe(), ["id", "value"],
                    [{"id": "1", "value": left_value}], [{"id": "1", "value": right_value}],
                )
                self.assertEqual(result["outcome"], "FAIL")

    def test_boolean_tokens_are_strict(self):
        columns = {
            "id": {"type": "string", "comparison": "exact"},
            "value": {"type": "boolean", "comparison": "exact"},
        }
        spec = recipe(columns)
        matching = self.run_rows(spec, ["id", "value"], [{"id": "1", "value": "true"}], [{"id": "1", "value": "true"}])
        self.assertEqual(matching["outcome"], "PASS")
        with self.assertRaisesRegex(ParisonError, "expected true or false"):
            self.run_rows(spec, ["id", "value"], [{"id": "1", "value": "true"}], [{"id": "1", "value": "TRUE"}])

    def test_dates_are_exact_calendar_dates(self):
        columns = {
            "id": {"type": "string", "comparison": "exact"},
            "value": {"type": "date", "comparison": "exact"},
        }
        spec = recipe(columns)
        different = self.run_rows(spec, ["id", "value"], [{"id": "1", "value": "2026-01-01"}], [{"id": "1", "value": "2026-01-02"}])
        self.assertEqual(different["outcome"], "FAIL")
        with self.assertRaisesRegex(ParisonError, "cannot parse column value as date"):
            self.run_rows(spec, ["id", "value"], [{"id": "1", "value": "2026-01-01"}], [{"id": "1", "value": "2026-01-01T00:00:00"}])

    def test_large_integers_are_not_coerced_to_float(self):
        columns = {
            "id": {"type": "string", "comparison": "exact"},
            "value": {"type": "integer", "comparison": "exact"},
        }
        result = self.run_rows(
            recipe(columns), ["id", "value"],
            [{"id": "1", "value": "9007199254740992"}],
            [{"id": "1", "value": "9007199254740993"}],
        )
        self.assertEqual(result["outcome"], "FAIL")

    def test_quoted_newlines_are_parsed_without_row_loss(self):
        result = self.run_rows(
            recipe(), ["id", "value"],
            [{"id": "1", "value": "line one\nline two"}],
            [{"id": "1", "value": "line one\nline two"}],
        )
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["counts"]["baseline"], 1)

    def test_decimal_tolerance_boundaries_and_symmetry(self):
        columns = {
            "id": {"type": "string", "comparison": "exact"},
            "value": {
                "type": "decimal", "comparison": "numeric",
                "scale": 2,
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
                    if kind == "decimal":
                        columns["value"]["scale"] = 2
                    with self.assertRaisesRegex(ParisonError, "cannot parse"):
                        self.run_rows(recipe(columns), ["id", "value"], [{"id": "1", "value": "1"}], [{"id": "1", "value": token}])

    def test_null_equality_is_explicit_and_one_null_never_matches(self):
        columns = {
            "id": {"type": "string", "comparison": "exact"},
            "value": {"type": "integer", "comparison": "exact"},
        }
        spec = recipe(columns)
        both_null = [{"id": "1", "value": ""}]
        self.assertEqual(self.run_rows(spec, ["id", "value"], both_null, both_null)["outcome"], "PASS")
        spec["nulls_equal"] = False
        self.assertEqual(self.run_rows(spec, ["id", "value"], both_null, both_null)["outcome"], "FAIL")
        spec["nulls_equal"] = True
        one_null = self.run_rows(spec, ["id", "value"], both_null, [{"id": "1", "value": "1"}])
        self.assertEqual(one_null["outcome"], "FAIL")

    def test_recipe_requires_explicit_null_policy(self):
        value = recipe()
        del value["nulls_equal"]
        with self.assertRaisesRegex(ParisonError, "nulls_equal"):
            load_recipe(self.write_recipe(value))

    def test_timestamp_requires_zone_and_compares_instants(self):
        columns = {
            "id": {"type": "string", "comparison": "exact"},
            "value": {"type": "timestamp", "comparison": "exact", "timezone": "require-aware"},
        }
        spec = recipe(columns)
        equal = self.run_rows(
            spec, ["id", "value"],
            [{"id": "1", "value": "2026-01-01T00:00:00+00:00"}],
            [{"id": "1", "value": "2026-01-01T05:30:00+05:30"}],
        )
        self.assertEqual(equal["outcome"], "PASS")
        with self.assertRaisesRegex(ParisonError, "explicit timezone"):
            self.run_rows(
                spec, ["id", "value"],
                [{"id": "1", "value": "2026-01-01T00:00:00"}],
                [{"id": "1", "value": "2026-01-01T00:00:00+00:00"}],
            )

    def test_timestamp_policy_must_be_explicit_and_type_specific(self):
        value = recipe({
            "id": {"type": "string", "comparison": "exact"},
            "time": {"type": "timestamp", "comparison": "exact"},
        })
        with self.assertRaisesRegex(ParisonError, "timezone must be 'require-aware'"):
            load_recipe(self.write_recipe(value))
        value = recipe()
        value["columns"]["value"]["timezone"] = "require-aware"
        with self.assertRaisesRegex(ParisonError, "only valid for timestamps"):
            load_recipe(self.write_recipe(value))

    def test_recipe_rejects_bad_tolerances_and_key_policies(self):
        numeric = {
            "id": {"type": "string", "comparison": "exact"},
            "value": {
                "type": "decimal", "comparison": "numeric",
                "scale": 2,
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
                with self.assertRaisesRegex(ParisonError, message):
                    load_recipe(self.write_recipe(value))

    def test_decimal_scale_is_explicit_and_excess_precision_errors(self):
        columns = {
            "id": {"type": "string", "comparison": "exact"},
            "value": {"type": "decimal", "scale": 2, "comparison": "exact"},
        }
        spec = recipe(columns)
        with self.assertRaisesRegex(ParisonError, "exceeds configured scale 2"):
            self.run_rows(spec, ["id", "value"], [{"id": "1", "value": "1.00"}], [{"id": "1", "value": "1.001"}])
        del columns["value"]["scale"]
        with self.assertRaisesRegex(ParisonError, "scale must be"):
            load_recipe(self.write_recipe(recipe(columns)))

    def test_scope_requires_cutoff_and_declared_filters(self):
        for field in ("cutoff", "filters", "expected_empty"):
            with self.subTest(field=field):
                value = recipe()
                del value["scope"][field]
                with self.assertRaisesRegex(ParisonError, "scope must contain exactly"):
                    load_recipe(self.write_recipe(value))
        value = recipe()
        value["scope"]["filters"] = "status = active"
        with self.assertRaisesRegex(ParisonError, "scope.filters"):
            load_recipe(self.write_recipe(value))
        value = recipe()
        value["scope"]["expected_empty"] = "false"
        with self.assertRaisesRegex(ParisonError, "scope.expected_empty"):
            load_recipe(self.write_recipe(value))


if __name__ == "__main__":
    unittest.main()
