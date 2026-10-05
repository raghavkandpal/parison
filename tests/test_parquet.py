import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

try:
    import polars as pl
except ImportError:
    pl = None

from parity.core import ParityError, compare


@unittest.skipUnless(pl, "Polars optional dependency is not installed")
class ParquetCompatibility(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.recipe = self.root / "recipe.json"
        self.recipe.write_text(json.dumps({
            "recipe_version": 1,
            "comparison_mode": "keyed",
            "keys": ["id"],
            "scope": {"snapshot": "parquet-fixture", "completeness": "full"},
            "identity": {"null_keys": "reject", "duplicates": "reject"},
            "columns": {
                "id": {"type": "string", "comparison": "exact"},
                "amount": {
                    "type": "decimal",
                    "comparison": "numeric",
                    "tolerance": {"formula": "symmetric-v1", "absolute": "0.01", "relative": "0"},
                },
            },
            "output": {"sensitivity": "summary"},
        }), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def parquet(self, name, ids, amounts):
        path = self.root / name
        pl.DataFrame({
            "id": pl.Series(ids, dtype=pl.String),
            "amount": pl.Series(amounts, dtype=pl.Decimal(precision=20, scale=4)),
        }).write_parquet(path)
        return path

    def test_decimal_parquet_comparison(self):
        left = self.parquet("left.parquet", ["001", "002"], [Decimal("10.0000"), Decimal("2.0000")])
        right = self.parquet("right.parquet", ["002", "001"], [Decimal("2.0000"), Decimal("10.0100")])
        result = compare(self.recipe, left, right)
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["counts"]["matched_within_tolerance"], 1)

    def test_nested_parquet_value_is_rejected(self):
        nested = self.root / "nested.parquet"
        pl.DataFrame({"id": ["001"], "amount": [{"value": 1}]}).write_parquet(nested)
        valid = self.parquet("valid.parquet", ["001"], [Decimal("1.0000")])
        with self.assertRaisesRegex(ParityError, "cannot parse column amount as decimal"):
            compare(self.recipe, valid, nested)

    def test_row_limit_is_checked_before_parquet_materialization(self):
        left = self.parquet("left.parquet", ["001", "002"], [Decimal("1.0000"), Decimal("2.0000")])
        right = self.parquet("right.parquet", ["001", "002"], [Decimal("1.0000"), Decimal("2.0000")])
        with self.assertRaisesRegex(ParityError, "row count.*exceeds limit 1"):
            compare(self.recipe, left, right, max_rows=1)


if __name__ == "__main__":
    unittest.main()
