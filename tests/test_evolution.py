import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from jsonschema import Draft202012Validator

from parison.cli import main
from parison.core import ParisonError, load_schema
from parison.evolution import canonical_evolution_bytes, compile_evolution_mappings, diff_policies, explain_evolution, load_evolution, normalize_evolution, summarize_policy_diff


ROOT = Path(__file__).parents[1]
EXAMPLE = ROOT / "examples" / "1.2" / "orders.schema-evolution.json"


class SchemaEvolution(unittest.TestCase):
    def _recipe(self, amount_name, excluded=None):
        return {
            "recipe_version": 1,
            "comparison_mode": "keyed",
            "keys": ["order_id"],
            "scope": {"snapshot": "orders", "cutoff": "2026-10-14T00:00:00Z", "filters": [], "completeness": "full", "expected_empty": False},
            "identity": {"null_keys": "reject", "duplicates": "reject"},
            "nulls_equal": True,
            "columns": {
                "order_id": {"type": "string", "comparison": "exact"},
                amount_name: {"type": "decimal", "scale": 2, "comparison": "exact"},
            },
            "excluded_columns": excluded or {},
            "output": {"sensitivity": "summary"},
        }

    def _write_json(self, root, name, value):
        path = root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def _stable_recipe(self, mode, amount_source):
        mappings = {
            "order-id": {"baseline": "order_id", "candidate": "order_id"},
            "gross-amount": {"baseline": amount_source, "candidate": amount_source},
        }
        common = {
            "recipe_version": {"keyed": 1, "aggregate": 2, "multiset": 3}[mode],
            "comparison_mode": mode,
            "scope": {"snapshot": "orders", "cutoff": "2026-10-14T00:00:00Z", "filters": [], "completeness": "full", "expected_empty": False},
            "columns": {
                "order-id": {"type": "string", "comparison": "exact"},
                "gross-amount": {"type": "decimal", "scale": 2, "comparison": "exact"},
            },
            "column_mappings": mappings,
            "excluded_columns": {"migration_batch": "operational metadata"} if amount_source == "order_total" else {},
            "output": {"sensitivity": "summary"},
        }
        if mode == "keyed":
            common.update({"keys": ["order-id"], "identity": {"null_keys": "reject", "duplicates": "reject"}, "nulls_equal": True})
        elif mode == "aggregate":
            common.update({"group_by": ["order-id"], "measures": {"gross": {"operator": "sum", "column": "gross-amount", "nulls": "reject", "comparison": "exact"}}})
        return common

    def test_example_has_order_independent_canonical_identity(self):
        value = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        shuffled = {**value, "changes": list(reversed(value["changes"]))}
        self.assertEqual(canonical_evolution_bytes(value), canonical_evolution_bytes(shuffled))
        self.assertEqual(
            canonical_evolution_bytes(value) + b"\n",
            (ROOT / "tests" / "fixtures" / "schema-evolution-v1.canonical.json").read_bytes(),
        )
        explained = explain_evolution(EXAMPLE)
        self.assertEqual([item["change"] for item in explained["changes"]], ["unchanged", "renamed", "added"])
        self.assertEqual(explained["evolution_sha256"], "3c22abf3e84962fb05d4c3d76290c4c4299b5fb2ed494082f1de31921d46efe9")

    def test_rejects_identity_and_name_conflicts(self):
        base = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        cases = []
        duplicate_id = json.loads(json.dumps(base))
        duplicate_id["changes"][0]["candidate"][0]["id"] = "gross-amount"
        cases.append(duplicate_id)
        duplicate_name = json.loads(json.dumps(base))
        duplicate_name["changes"][0]["candidate"][0]["name"] = "order_total"
        cases.append(duplicate_name)
        reused_retired = {
            "evolution_version": 1, "direction": "baseline-to-candidate", "changes": [{
                "change": "split",
                "baseline": [{"id": "name", "name": "name", "presence": "required", "nullability": "nullable"}],
                "candidate": [
                    {"id": "name", "name": "given", "presence": "required", "nullability": "nullable"},
                    {"id": "family", "name": "family", "presence": "required", "nullability": "nullable"},
                ],
            }],
        }
        cases.append(reused_retired)
        for value in cases:
            with self.subTest(value=value), self.assertRaises(ParisonError):
                normalize_evolution(value)

    def test_rejects_invalid_cardinality_and_non_scalar_defaults(self):
        for change, baseline, candidate in (
            ("added", [], []),
            ("removed", [], []),
            ("split", [{}], [{}]),
            ("merged", [{}], [{}]),
        ):
            value = {"evolution_version": 1, "direction": "baseline-to-candidate", "changes": [{"change": change, "baseline": baseline, "candidate": candidate}]}
            with self.subTest(change=change), self.assertRaises(ParisonError):
                normalize_evolution(value)
        value = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        value["changes"][0]["candidate"][0]["default"] = {"manufactured": True}
        with self.assertRaisesRegex(ParisonError, "finite JSON scalar"):
            normalize_evolution(value)

    def test_rejects_duplicate_json_members(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.json"
            path.write_text('{"evolution_version":1,"evolution_version":1,"direction":"baseline-to-candidate","changes":[]}', encoding="utf-8")
            with self.assertRaisesRegex(ParisonError, "duplicate JSON member"):
                load_evolution(path)

    def test_cli_validates_explains_and_prints_schema(self):
        for arguments in (("validate-evolution", str(EXAMPLE)), ("explain-evolution", str(EXAMPLE)), ("schema", "schema-evolution")):
            with self.subTest(arguments=arguments), redirect_stdout(StringIO()) as stdout, redirect_stderr(StringIO()):
                self.assertEqual(main(list(arguments)), 0)
                self.assertTrue(stdout.getvalue())

    def test_policy_diff_accepts_exact_rename_and_excluded_addition(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline = self._write_json(root, "baseline.json", self._recipe("gross_amount"))
            candidate = self._write_json(root, "candidate.json", self._recipe("order_total", {"migration_batch": "operational metadata"}))
            result = diff_policies(baseline, candidate, EXAMPLE)
            self.assertEqual(result["compatibility"], "ACCEPT")
            Draft202012Validator(load_schema("policy-diff")).validate(result)
            self.assertEqual([item["reason"] for item in result["changes"]], [
                "FIELD_IDENTITY_PRESERVED", "FIELD_IDENTITY_PRESERVED", "EXCLUDED_STRUCTURAL_FIELD",
            ])
            summary = summarize_policy_diff(result)
            rendered = json.dumps(summary)
            for secret in ("order_id", "gross_amount", "order_total", "migration_batch"):
                self.assertNotIn(secret, rendered)
            self.assertNotIn("changes", summary)
            with redirect_stdout(StringIO()) as stdout, redirect_stderr(StringIO()):
                self.assertEqual(main(["diff-policy", "--baseline-recipe", str(baseline), "--candidate-recipe", str(candidate), "--evolution", str(EXAMPLE), "--summary"]), 0)
                self.assertEqual(json.loads(stdout.getvalue()), summary)

    def test_example_policy_diff_has_pinned_canonical_bytes(self):
        result = diff_policies(
            ROOT / "examples" / "1.2" / "baseline.recipe.json",
            ROOT / "examples" / "1.2" / "candidate.recipe.json",
            EXAMPLE,
        )
        rendered = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        self.assertEqual(rendered, (ROOT / "tests" / "fixtures" / "policy-diff-v1.canonical.json").read_bytes())
        self.assertEqual(result["policy_diff_sha256"], "d15d1881735f3e6f3453384388d00dd80e105d84b0c47d08e6a9752f5c5e6fa5")

    def test_compile_emits_only_identity_preserving_mappings(self):
        compiled = compile_evolution_mappings(EXAMPLE)
        self.assertEqual(compiled["column_mappings"], {
            "gross-amount": {"baseline": "gross_amount", "candidate": "order_total"},
            "order-id": {"baseline": "order_id", "candidate": "order_id"},
        })
        with redirect_stdout(StringIO()) as stdout, redirect_stderr(StringIO()):
            self.assertEqual(main(["compile-evolution", str(EXAMPLE)]), 0)
            self.assertEqual(json.loads(stdout.getvalue()), compiled)

    def test_policy_diff_denies_semantic_change_and_undeclared_field(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline_recipe = self._recipe("gross_amount")
            candidate_recipe = self._recipe("order_total", {"migration_batch": "operational metadata", "secret": "not compared"})
            candidate_recipe["nulls_equal"] = False
            baseline = self._write_json(root, "baseline.json", baseline_recipe)
            candidate = self._write_json(root, "candidate.json", candidate_recipe)
            result = diff_policies(baseline, candidate, EXAMPLE)
            self.assertEqual(result["compatibility"], "DENY")
            self.assertIn("GLOBAL_POLICY_CHANGED", {item["reason"] for item in result["changes"]})
            self.assertIn("UNDECLARED_POLICY_FIELD", {item["reason"] for item in result["changes"]})

    def test_policy_diff_accepts_stable_logical_columns_in_every_mode(self):
        for mode in ("keyed", "aggregate", "multiset"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                baseline = self._write_json(root, "baseline.json", self._stable_recipe(mode, "gross_amount"))
                candidate = self._write_json(root, "candidate.json", self._stable_recipe(mode, "order_total"))
                self.assertEqual(diff_policies(baseline, candidate, EXAMPLE)["compatibility"], "ACCEPT")

    def test_policy_diff_denies_each_keyed_semantic_axis(self):
        mutations = {
            "scope": lambda recipe: recipe["scope"].update(snapshot="other"),
            "nulls": lambda recipe: recipe.update(nulls_equal=False),
            "delimiter": lambda recipe: recipe.update(delimiters={"baseline": ",", "candidate": ";"}),
            "null-token": lambda recipe: recipe.update(null_tokens={"baseline": [], "candidate": ["NULL"]}),
            "projection": lambda recipe: recipe.update(input_projection="semantic-scalar-v1"),
            "sensitivity": lambda recipe: recipe.update(output={"sensitivity": "raw"}),
            "role": lambda recipe: recipe.update(keys=["order-id", "gross-amount"]),
            "type": lambda recipe: recipe["columns"].update({"gross-amount": {"type": "integer", "comparison": "exact"}}),
            "comparison": lambda recipe: recipe["columns"].update({"gross-amount": {"type": "decimal", "scale": 2, "comparison": "numeric", "tolerance": {"formula": "symmetric-v1", "absolute": "0.01", "relative": "0"}}}),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                baseline_recipe = self._stable_recipe("keyed", "gross_amount")
                candidate_recipe = self._stable_recipe("keyed", "order_total")
                mutate(candidate_recipe)
                baseline = self._write_json(root, "baseline.json", baseline_recipe)
                candidate = self._write_json(root, "candidate.json", candidate_recipe)
                self.assertEqual(diff_policies(baseline, candidate, EXAMPLE)["compatibility"], "DENY")

    def test_excluded_field_identity_can_survive_a_rename(self):
        common = {"id": "order-id", "name": "order_id", "presence": "required", "nullability": "non-null"}
        declaration = {
            "evolution_version": 1, "direction": "baseline-to-candidate", "changes": [
                {"change": "unchanged", "baseline": [common], "candidate": [common]},
                {"change": "renamed", "baseline": [{"id": "note", "name": "old_note", "presence": "required", "nullability": "nullable"}], "candidate": [{"id": "note", "name": "new_note", "presence": "required", "nullability": "nullable"}]},
            ],
        }
        baseline_recipe = self._recipe("amount", {"old_note": "not compared"})
        candidate_recipe = self._recipe("amount", {"new_note": "still not compared"})
        del baseline_recipe["columns"]["amount"]
        del candidate_recipe["columns"]["amount"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline = self._write_json(root, "baseline.json", baseline_recipe)
            candidate = self._write_json(root, "candidate.json", candidate_recipe)
            evolution = self._write_json(root, "evolution.json", declaration)
            result = diff_policies(baseline, candidate, evolution)
            self.assertEqual(result["compatibility"], "ACCEPT")
            self.assertIn("EXCLUDED_FIELD_IDENTITY_PRESERVED", {item["reason"] for item in result["changes"]})

    def test_policy_diff_reports_excluded_split_as_inconclusive(self):
        common = {"id": "order-id", "name": "order_id", "presence": "required", "nullability": "non-null"}
        evolution = {
            "evolution_version": 1, "direction": "baseline-to-candidate", "changes": [
                {"change": "unchanged", "baseline": [common], "candidate": [common]},
                {"change": "split", "baseline": [{"id": "name", "name": "name", "presence": "required", "nullability": "nullable"}], "candidate": [
                    {"id": "given", "name": "given_name", "presence": "required", "nullability": "nullable"},
                    {"id": "family", "name": "family_name", "presence": "required", "nullability": "nullable"},
                ]},
            ],
        }
        baseline_recipe = self._recipe("amount", {"name": "materialized upstream"})
        candidate_recipe = self._recipe("amount", {"given_name": "materialized upstream", "family_name": "materialized upstream"})
        del baseline_recipe["columns"]["amount"]
        del candidate_recipe["columns"]["amount"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline = self._write_json(root, "baseline.json", baseline_recipe)
            candidate = self._write_json(root, "candidate.json", candidate_recipe)
            declaration = self._write_json(root, "evolution.json", evolution)
            result = diff_policies(baseline, candidate, declaration)
            self.assertEqual(result["compatibility"], "INCONCLUSIVE")
            self.assertEqual(result["changes"][-1]["reason"], "TRANSFORMATION_REQUIRES_UPSTREAM_MATERIALIZATION")
            with self.assertRaisesRegex(ParisonError, "upstream materialization"):
                compile_evolution_mappings(declaration)


if __name__ == "__main__":
    unittest.main()
