import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

try:
    import polars as pl
except ImportError:
    pl = None

from parison.core import ParisonError, compare, explain_recipe


def recipe(projection=True):
    value = {
        "recipe_version": 1,
        "comparison_mode": "keyed",
        "keys": ["id"],
        "scope": {"snapshot": "projection-test", "cutoff": "2026-10-14T00:00:00Z", "filters": [], "completeness": "full", "expected_empty": False},
        "identity": {"null_keys": "reject", "duplicates": "reject"},
        "nulls_equal": True,
        "columns": {
            "id": {"type": "integer", "comparison": "exact"},
            "amount": {"type": "decimal", "scale": 2, "comparison": "exact"},
            "active": {"type": "boolean", "comparison": "exact"},
            "label": {"type": "string", "comparison": "exact"},
            "day": {"type": "date", "comparison": "exact"},
            "observed_at": {"type": "timestamp", "timezone": "require-aware", "comparison": "exact"},
        },
        "output": {"sensitivity": "summary"},
    }
    if projection:
        value["input_projection"] = "semantic-scalar-v1"
    return value


class SemanticScalarProjection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.recipe = self.root / "recipe.json"
        self.recipe.write_text(json.dumps(recipe()), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def sqlite(self, definition, values):
        path = self.root / "input.sqlite"
        with closing(sqlite3.connect(path)) as connection:
            connection.execute(f"CREATE TABLE records ({definition})")
            connection.execute(f"INSERT INTO records VALUES ({','.join('?' for _ in values)})", values)
            connection.commit()
        return f"sqlite:{path}#records"

    def jsonl(self, value):
        path = self.root / "input.jsonl"
        path.write_text(json.dumps(value, separators=(",", ":")) + "\n", encoding="utf-8")
        return path

    def test_policy_directed_scalars_match_across_jsonl_and_sqlite(self):
        baseline = self.jsonl({"id": 1, "amount": "10.00", "active": True, "label": "same", "day": "2026-10-14", "observed_at": "2026-10-14T01:00:00+01:00"})
        candidate = self.sqlite(
            "id INTEGER, amount INTEGER, active TEXT, label TEXT, day TEXT, observed_at TEXT",
            (1, 10, "true", "same", "2026-10-14", "2026-10-14T00:00:00Z"),
        )
        result = compare(self.recipe, baseline, candidate)
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["policy"]["input_projection"], "semantic-scalar-v1")
        self.assertEqual(explain_recipe(self.recipe)["input_projection"], "semantic-scalar-v1")

    def test_projection_rejects_implicit_string_decimal_boolean_and_empty_coercions(self):
        baseline = self.jsonl({"id": 1, "amount": "1.50", "active": True, "label": "1", "day": "2026-10-14", "observed_at": "2026-10-14T00:00:00Z"})
        cases = (
            ("id INTEGER, amount REAL, active TEXT, label TEXT, day TEXT, observed_at TEXT", (1, 1.5, "true", "1", "2026-10-14", "2026-10-14T00:00:00Z"), "amount"),
            ("id INTEGER, amount INTEGER, active INTEGER, label TEXT, day TEXT, observed_at TEXT", (1, 1, 1, "1", "2026-10-14", "2026-10-14T00:00:00Z"), "active"),
            ("id INTEGER, amount INTEGER, active TEXT, label INTEGER, day TEXT, observed_at TEXT", (1, 1, "true", 1, "2026-10-14", "2026-10-14T00:00:00Z"), "label"),
        )
        for index, (definition, values, column) in enumerate(cases):
            with self.subTest(column=column):
                if index:
                    (self.root / "input.sqlite").unlink()
                candidate = self.sqlite(definition, values)
                with self.assertRaisesRegex(ParisonError, f"project column {column}"):
                    compare(self.recipe, baseline, candidate)

        csv = self.root / "empty.csv"
        csv.write_text("id,amount,active,label,day,observed_at\n1,,true,1,2026-10-14,2026-10-14T00:00:00Z\n", encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "project column amount"):
            compare(self.recipe, baseline, csv)

    def test_projection_rejects_integer_outside_signed_64_bit_range(self):
        baseline = self.jsonl({"id": 2**63, "amount": "1.00", "active": True, "label": "x", "day": "2026-10-14", "observed_at": "2026-10-14T00:00:00Z"})
        with self.assertRaisesRegex(ParisonError, "outside signed 64-bit range"):
            compare(self.recipe, baseline, baseline)

    def test_projection_rejects_text_timestamp_beyond_microsecond_precision(self):
        value = {"id": 1, "amount": "1.00", "active": True, "label": "x", "day": "2026-10-14", "observed_at": "1969-12-31T23:59:59.1234567Z"}
        source = self.jsonl(value)
        with self.assertRaisesRegex(ParisonError, "precision exceeds microseconds"):
            compare(self.recipe, source, source)

    def test_legacy_recipe_keeps_incidental_coercions_and_policy_identity(self):
        legacy = self.root / "legacy.json"
        legacy.write_text(json.dumps(recipe(False)), encoding="utf-8")
        baseline = self.jsonl({"id": 1, "amount": "1.50", "active": True, "label": 1, "day": "2026-10-14", "observed_at": "2026-10-14T00:00:00Z"})
        self.assertEqual(compare(legacy, baseline, baseline)["outcome"], "PASS")
        self.assertNotIn("input_projection", explain_recipe(legacy))

    def test_projection_is_shared_by_aggregate_and_multiset_modes(self):
        baseline = self.root / "rows.csv"
        candidate = self.root / "rows.jsonl"
        baseline.write_text("label,amount\neast,10.00\nwest,2.00\n", encoding="utf-8")
        candidate.write_text('{"amount":10,"label":"east"}\n{"label":"west","amount":2}\n', encoding="utf-8")
        common = {
            "scope": {"snapshot": "projection-modes", "cutoff": "2026-10-14T00:00:00Z", "filters": [], "completeness": "full", "expected_empty": False},
            "columns": {"label": {"type": "string"}, "amount": {"type": "decimal", "scale": 2}},
            "input_projection": "semantic-scalar-v1",
            "output": {"sensitivity": "summary"},
        }
        recipes = (
            {"recipe_version": 2, "comparison_mode": "aggregate", "group_by": ["label"], "measures": {"total": {"operator": "sum", "column": "amount", "nulls": "reject"}}, **common},
            {"recipe_version": 3, "comparison_mode": "multiset", **common},
        )
        for spec in recipes:
            with self.subTest(mode=spec["comparison_mode"]):
                path = self.root / f"{spec['comparison_mode']}.json"
                path.write_text(json.dumps(spec), encoding="utf-8")
                result = compare(path, baseline, candidate)
                self.assertEqual(result["outcome"], "PASS")
                self.assertEqual(result["policy"]["input_projection"], "semantic-scalar-v1")


@unittest.skipUnless(pl, "Polars optional dependency is not installed")
class SemanticScalarParquetProjection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.recipe = self.root / "recipe.json"
        self.spec = recipe()
        self.recipe.write_text(json.dumps(self.spec), encoding="utf-8")
        self.baseline = self.root / "baseline.jsonl"
        self.baseline.write_text('{"id":1,"amount":"10.00","active":true,"label":"same","day":"2026-10-14","observed_at":"2026-10-14T00:00:00Z"}\n', encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def parquet(self, **overrides):
        columns = {
            "id": pl.Series([1], dtype=pl.Int64),
            "amount": pl.Series([Decimal("10.00")], dtype=pl.Decimal(10, 2)),
            "active": pl.Series([True], dtype=pl.Boolean),
            "label": pl.Series(["same"], dtype=pl.String),
            "day": pl.Series([date(2026, 10, 14)], dtype=pl.Date),
            "observed_at": pl.Series([datetime(2026, 10, 14, tzinfo=timezone.utc)], dtype=pl.Datetime("us", "UTC")),
        }
        columns.update(overrides)
        path = self.root / "candidate.parquet"
        pl.DataFrame(columns).write_parquet(path)
        return path

    def test_admitted_parquet_scalars_match_jsonl(self):
        self.assertEqual(compare(self.recipe, self.baseline, self.parquet())["outcome"], "PASS")

    def test_complete_parquet_schema_rejects_nested_even_when_excluded(self):
        self.spec["excluded_columns"] = {"extra": "not compared"}
        self.recipe.write_text(json.dumps(self.spec), encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "unsupported semantic-scalar-v1 type"):
            compare(self.recipe, self.baseline, self.parquet(extra=pl.Series([[1]], dtype=pl.List(pl.Int64))))

    def test_parquet_rejects_nanoseconds_and_timezone_naive_datetimes(self):
        values = (
            pl.Series([datetime(2026, 10, 14, tzinfo=timezone.utc)], dtype=pl.Datetime("ns", "UTC")),
            pl.Series([datetime(2026, 10, 14)], dtype=pl.Datetime("us")),
        )
        for index, value in enumerate(values):
            with self.subTest(index=index):
                with self.assertRaisesRegex(ParisonError, "lossy or timezone-naive"):
                    compare(self.recipe, self.baseline, self.parquet(observed_at=value))


if __name__ == "__main__":
    unittest.main()
