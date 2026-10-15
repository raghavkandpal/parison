import json
import csv
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

try:
    import polars as pl
except ImportError:
    pl = None

from parison.core import ParisonError, _multiset_encoding, _parse_input, _read, compare, explain_recipe, load_recipe


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
        timestamps = (
            "1969-12-31T23:59:59.1234567Z",
            "1969-12-31t23:59:59.1234567Z",
            "1969-12-31 23:59:59.1234567Z",
            "19691231T235959.1234567Z",
            "1969-12-31T235959.1234567Z",
        )
        for timestamp in timestamps:
            with self.subTest(timestamp=timestamp):
                value = {"id": 1, "amount": "1.00", "active": True, "label": "x", "day": "2026-10-14", "observed_at": timestamp}
                source = self.jsonl(value)
                with self.assertRaisesRegex(ParisonError, "precision exceeds microseconds"):
                    compare(self.recipe, source, source)

    def test_legacy_recipe_keeps_incidental_coercions_and_policy_identity(self):
        legacy = self.root / "legacy.json"
        legacy.write_text(json.dumps(recipe(False)), encoding="utf-8")
        baseline = self.jsonl({"id": 1, "amount": "1.50", "active": True, "label": 1, "day": "2026-10-14", "observed_at": "2026-10-14T00:00:00Z"})
        self.assertEqual(compare(legacy, baseline, baseline)["outcome"], "PASS")
        raw = "2026-10-14 00:00:00.1234567Z"
        with patch("parison.core._parse", return_value="legacy-result") as parse:
            self.assertEqual(_parse_input(raw, {"type": "timestamp"}, "observed_at", recipe(False)), "legacy-result")
            parse.assert_called_once_with(raw, {"type": "timestamp"}, "observed_at")
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


class SemanticScalarCompatibilityCorpus(unittest.TestCase):
    columns = ("id", "amount", "ratio", "active", "label", "day", "observed_at")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.rows = [
            (-2**63, "-0.00", -0.0, False, "e\u0301", "1969-12-31", "1969-12-31T18:59:59.123456-05:00"),
            (2**63 - 1, "123.00", 2.0, True, "雪", "2026-10-15", "2026-10-15T05:30:00+05:30"),
            (0, None, None, None, "", None, None),
        ]

    def tearDown(self):
        self.tmp.cleanup()

    def spec(self, mode):
        common = {
            "scope": {"snapshot": "semantic-corpus", "cutoff": "2026-10-15T00:00:00Z", "filters": [], "completeness": "full", "expected_empty": False},
            "columns": {
                "id": {"type": "integer"},
                "amount": {"type": "decimal", "scale": 2},
                "ratio": {"type": "float"},
                "active": {"type": "boolean"},
                "label": {"type": "string", "normalize": ["unicode_nfc"]},
                "day": {"type": "date"},
                "observed_at": {"type": "timestamp", "timezone": "require-aware"},
            },
            "null_tokens": {"baseline": ["NULL"], "candidate": ["NULL"]},
            "input_projection": "semantic-scalar-v1",
            "output": {"sensitivity": "summary"},
        }
        if mode == "keyed":
            return {"recipe_version": 1, "comparison_mode": "keyed", "keys": ["id"], "identity": {"null_keys": "reject", "duplicates": "reject"}, "nulls_equal": True, **common}
        if mode == "aggregate":
            return {"recipe_version": 2, "comparison_mode": "aggregate", "group_by": ["id"], "measures": {"rows": {"operator": "count"}}, **common}
        return {"recipe_version": 3, "comparison_mode": "multiset", **common}

    def write_csv(self):
        path = self.root / "rows.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(self.columns)
            for row in self.rows:
                writer.writerow("NULL" if value is None else str(value).lower() if isinstance(value, bool) else value for value in row)
        return path

    def write_tsv(self):
        csv_path = self.write_csv()
        path = self.root / "rows.tsv"
        with csv_path.open(newline="", encoding="utf-8") as source, path.open("w", newline="", encoding="utf-8") as target:
            writer = csv.writer(target, delimiter="\t")
            writer.writerows(csv.reader(source))
        return path

    def write_jsonl(self):
        path = self.root / "rows.jsonl"
        values = [
            (-2**63, "-0.00", -0.0, False, "é", "1969-12-31", "1969-12-31T23:59:59.123456Z"),
            (2**63 - 1, 123, 2, True, "雪", "2026-10-15", "2026-10-15T00:00:00Z"),
            (0, None, None, None, "", None, None),
        ]
        values = [values[2], values[0], values[1]]
        path.write_text("".join(json.dumps(dict(zip(self.columns, row)), ensure_ascii=False, separators=(",", ":")) + "\n" for row in values), encoding="utf-8")
        return path

    def write_sqlite(self):
        path = self.root / "rows.sqlite"
        with closing(sqlite3.connect(path)) as connection:
            connection.execute("CREATE TABLE records (id INTEGER, amount, ratio, active TEXT, label TEXT, day TEXT, observed_at TEXT)")
            connection.executemany("INSERT INTO records VALUES (?,?,?,?,?,?,?)", [
                (-2**63, "-0.00", -0.0, "false", "é", "1969-12-31", "1969-12-31T23:59:59.123456+00:00"),
                (2**63 - 1, 123, 2, "true", "雪", "2026-10-15", "2026-10-15T00:00:00Z"),
                (0, None, None, None, "", None, None),
            ])
            connection.commit()
        return f"sqlite:{path}#records"

    def write_parquet(self):
        path = self.root / "rows.parquet"
        pl.DataFrame({
            "id": pl.Series([-2**63, 2**63 - 1, 0], dtype=pl.Int64),
            "amount": pl.Series([Decimal("-0.00"), Decimal("123.00"), None], dtype=pl.Decimal(20, 2)),
            "ratio": pl.Series([-0.0, 2.0, None], dtype=pl.Float64),
            "active": pl.Series([False, True, None], dtype=pl.Boolean),
            "label": pl.Series(["é", "雪", ""], dtype=pl.String),
            "day": pl.Series([date(1969, 12, 31), date(2026, 10, 15), None], dtype=pl.Date),
            "observed_at": pl.Series([
                datetime(1969, 12, 31, 23, 59, 59, 123456, tzinfo=timezone.utc),
                datetime(2026, 10, 15, tzinfo=timezone.utc),
                None,
            ], dtype=pl.Datetime("us", "UTC")),
        }).write_parquet(path)
        return path

    def sources(self):
        sources = {"csv": self.write_csv(), "tsv": self.write_tsv(), "jsonl": self.write_jsonl(), "sqlite": self.write_sqlite()}
        if pl:
            sources["parquet"] = self.write_parquet()
        return sources

    def test_all_stdlib_formats_converge_in_every_mode_and_canonical_row(self):
        sources = self.sources()
        encodings = {}
        for mode in ("keyed", "aggregate", "multiset"):
            for left_name, left in sources.items():
                for right_name, right in sources.items():
                    with self.subTest(mode=mode, left=left_name, right=right_name):
                        recipe_path = self.root / f"{mode}.recipe.json"
                        spec = self.spec(mode)
                        spec["delimiters"] = {"baseline": "\t" if left_name == "tsv" else ",", "candidate": "\t" if right_name == "tsv" else ","}
                        recipe_path.write_text(json.dumps(spec), encoding="utf-8")
                        self.assertEqual(compare(recipe_path, left, right)["outcome"], "PASS")
            for name, source in sources.items():
                recipe_path = self.root / f"{mode}-{name}.recipe.json"
                spec = self.spec(mode)
                spec["delimiters"] = {"baseline": "\t" if name == "tsv" else ",", "candidate": ","}
                recipe_path.write_text(json.dumps(spec), encoding="utf-8")
                loaded = load_recipe(recipe_path)
                names = sorted(loaded["columns"])
                rows, _ = _read(source, loaded, 10, "baseline")
                encodings[name] = sorted(
                    _multiset_encoding(tuple(row[column] for column in names), names, loaded).hex()
                    for row in rows
                )
        self.assertEqual(len({tuple(value) for value in encodings.values()}), 1)
        self.assertEqual(encodings["csv"], json.loads((Path(__file__).parent / "fixtures" / "semantic-scalar-v1-rows.json").read_text(encoding="utf-8")))

    def test_every_ambiguous_or_lossy_scalar_class_fails_closed(self):
        projection = {"input_projection": "semantic-scalar-v1"}
        cases = (
            (1, {"type": "string"}, "string"),
            (b"text", {"type": "string"}, "string"),
            (1.0, {"type": "integer"}, "integer"),
            (Decimal("1"), {"type": "integer"}, "integer"),
            (True, {"type": "integer"}, "integer"),
            ("", {"type": "integer"}, "integer"),
            (2**63, {"type": "integer"}, "outside signed 64-bit"),
            (1.0, {"type": "decimal", "scale": 2}, "decimal"),
            (True, {"type": "decimal", "scale": 2}, "decimal"),
            ("", {"type": "decimal", "scale": 2}, "decimal"),
            (Decimal("NaN"), {"type": "decimal", "scale": 2}, "non-finite"),
            ("1.001", {"type": "decimal", "scale": 2}, "configured scale"),
            (Decimal("1"), {"type": "float"}, "float"),
            (True, {"type": "float"}, "float"),
            ("", {"type": "float"}, "float"),
            (float("nan"), {"type": "float"}, "non-finite"),
            ("Infinity", {"type": "float"}, "non-finite"),
            (0, {"type": "boolean"}, "boolean"),
            ("1", {"type": "boolean"}, "expected true or false"),
            ("TRUE", {"type": "boolean"}, "expected true or false"),
            ("", {"type": "boolean"}, "boolean"),
            (datetime(2026, 10, 15, tzinfo=timezone.utc), {"type": "date"}, "date"),
            (0, {"type": "date"}, "date"),
            ("15/10/2026", {"type": "date"}, "date"),
            ("", {"type": "date"}, "date"),
            (date(2026, 10, 15), {"type": "timestamp"}, "timestamp"),
            (0, {"type": "timestamp"}, "timestamp"),
            (datetime(2026, 10, 15), {"type": "timestamp"}, "timezone required"),
            ("2026-10-15T00:00:00", {"type": "timestamp"}, "explicit timezone"),
            ("", {"type": "timestamp"}, "timestamp"),
            ("2026-10-15T00:00:00.1234567Z", {"type": "timestamp"}, "precision exceeds microseconds"),
        )
        for raw, policy, diagnostic in cases:
            with self.subTest(raw=raw, type=policy["type"]), self.assertRaisesRegex(ParisonError, diagnostic):
                _parse_input(raw, policy, "value", projection)


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

    def assert_parquet_value_matches(self, policy, baseline_value, series, suffix):
        spec = {
            "recipe_version": 1,
            "comparison_mode": "keyed",
            "keys": ["id"],
            "scope": {"snapshot": "parquet-dtypes", "cutoff": "2026-10-15T00:00:00Z", "filters": [], "completeness": "full", "expected_empty": False},
            "identity": {"null_keys": "reject", "duplicates": "reject"},
            "nulls_equal": True,
            "columns": {"id": {"type": "integer"}, "value": policy},
            "input_projection": "semantic-scalar-v1",
            "output": {"sensitivity": "summary"},
        }
        recipe_path = self.root / f"dtype-{suffix}.recipe.json"
        baseline = self.root / f"dtype-{suffix}.jsonl"
        candidate = self.root / f"dtype-{suffix}.parquet"
        recipe_path.write_text(json.dumps(spec), encoding="utf-8")
        baseline.write_text(json.dumps({"id": 1, "value": baseline_value}) + "\n", encoding="utf-8")
        pl.DataFrame({"id": pl.Series([1], dtype=pl.Int64), "value": series}).write_parquet(candidate)
        self.assertEqual(compare(recipe_path, baseline, candidate)["outcome"], "PASS")

    def test_admitted_parquet_scalars_match_jsonl(self):
        self.assertEqual(compare(self.recipe, self.baseline, self.parquet())["outcome"], "PASS")

    def test_every_admitted_parquet_scalar_dtype_family_matches_text(self):
        integer_dtypes = (pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64)
        cases = []
        cases.extend(({"type": "integer"}, 1, pl.Series([1], dtype=dtype), f"integer-{dtype}") for dtype in integer_dtypes)
        cases.extend([
            ({"type": "integer"}, 1, pl.Series(["1"], dtype=pl.String), "integer-string"),
            ({"type": "decimal", "scale": 2}, "1.20", pl.Series([Decimal("1.20")], dtype=pl.Decimal(10, 2)), "decimal-native"),
            ({"type": "decimal", "scale": 2}, "1.00", pl.Series([1], dtype=pl.Int64), "decimal-integer"),
            ({"type": "decimal", "scale": 2}, "1.20", pl.Series(["1.20"], dtype=pl.String), "decimal-string"),
            ({"type": "float"}, "1.5", pl.Series([1.5], dtype=pl.Float32), "float32"),
            ({"type": "float"}, "1.5", pl.Series([1.5], dtype=pl.Float64), "float64"),
            ({"type": "float"}, "1", pl.Series([1], dtype=pl.UInt64), "float-integer"),
            ({"type": "float"}, "1.5", pl.Series(["1.5"], dtype=pl.String), "float-string"),
            ({"type": "boolean"}, True, pl.Series([True], dtype=pl.Boolean), "boolean-native"),
            ({"type": "boolean"}, True, pl.Series(["true"], dtype=pl.String), "boolean-string"),
            ({"type": "string"}, "é", pl.Series(["é"], dtype=pl.String), "string"),
            ({"type": "date"}, "1969-12-31", pl.Series([date(1969, 12, 31)], dtype=pl.Date), "date-native"),
            ({"type": "date"}, "1969-12-31", pl.Series(["1969-12-31"], dtype=pl.String), "date-string"),
            ({"type": "timestamp", "timezone": "require-aware"}, "1969-12-31T23:59:59.123000Z", pl.Series([datetime(1969, 12, 31, 23, 59, 59, 123000, tzinfo=timezone.utc)], dtype=pl.Datetime("ms", "UTC")), "timestamp-ms"),
            ({"type": "timestamp", "timezone": "require-aware"}, "1969-12-31T23:59:59.123456Z", pl.Series([datetime(1969, 12, 31, 23, 59, 59, 123456, tzinfo=timezone.utc)], dtype=pl.Datetime("us", "UTC")), "timestamp-us"),
            ({"type": "timestamp", "timezone": "require-aware"}, "1969-12-31T23:59:59Z", pl.Series(["1969-12-31T23:59:59Z"], dtype=pl.String), "timestamp-string"),
        ])
        for policy, baseline, series, suffix in cases:
            with self.subTest(suffix=suffix):
                self.assert_parquet_value_matches(policy, baseline, series, suffix)
        for kind, policy in (
            ("string", {"type": "string"}), ("integer", {"type": "integer"}),
            ("decimal", {"type": "decimal", "scale": 2}), ("float", {"type": "float"}),
            ("boolean", {"type": "boolean"}), ("date", {"type": "date"}),
            ("timestamp", {"type": "timestamp", "timezone": "require-aware"}),
        ):
            with self.subTest(null=kind):
                self.assert_parquet_value_matches(policy, None, pl.Series([None], dtype=pl.Null), f"null-{kind}")

    def test_complete_parquet_schema_rejects_nested_even_when_excluded(self):
        self.spec["excluded_columns"] = {"extra": "not compared"}
        self.recipe.write_text(json.dumps(self.spec), encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "unsupported semantic-scalar-v1 type"):
            compare(self.recipe, self.baseline, self.parquet(extra=pl.Series([[1]], dtype=pl.List(pl.Int64))))

    def test_complete_parquet_schema_rejects_every_unsupported_dtype_family(self):
        self.spec["excluded_columns"] = {"extra": "not compared"}
        self.recipe.write_text(json.dumps(self.spec), encoding="utf-8")
        values = (
            pl.Series([b"x"], dtype=pl.Binary),
            pl.Series([time(1, 2, 3)], dtype=pl.Time),
            pl.Series([timedelta(seconds=1)], dtype=pl.Duration("us")),
            pl.Series(["x"]).cast(pl.Categorical),
            pl.Series([[1]], dtype=pl.List(pl.Int64)),
            pl.Series([{"part": 1}], dtype=pl.Struct({"part": pl.Int64})),
        )
        for value in values:
            with self.subTest(dtype=str(value.dtype)), self.assertRaisesRegex(ParisonError, "unsupported semantic-scalar-v1 type"):
                compare(self.recipe, self.baseline, self.parquet(extra=value))

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
