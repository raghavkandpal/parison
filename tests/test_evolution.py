import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from jsonschema import Draft202012Validator

from parison.cli import main
from parison.core import ParisonError, explain_recipe, load_schema
from parison.evolution import _closed_policy_path, canonical_evolution_bytes, compile_evolution_mappings, diff_policies, explain_evolution, load_evolution, normalize_evolution, summarize_policy_diff


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

    def test_runtime_rejects_boolean_version_and_structured_enums(self):
        base = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        invalid = []
        boolean_version = json.loads(json.dumps(base))
        boolean_version["evolution_version"] = True
        invalid.append(boolean_version)
        for key in ("presence", "nullability"):
            structured = json.loads(json.dumps(base))
            structured["changes"][0]["candidate"][0][key] = ["invalid"]
            invalid.append(structured)
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ParisonError):
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
            "scope-snapshot": lambda recipe: recipe["scope"].update(snapshot="other"),
            "scope-cutoff": lambda recipe: recipe["scope"].update(cutoff="2026-10-15T00:00:00Z"),
            "scope-filters": lambda recipe: recipe["scope"].update(filters=["status = active"]),
            "scope-expected-empty": lambda recipe: recipe["scope"].update(expected_empty=True),
            "nulls": lambda recipe: recipe.update(nulls_equal=False),
            "delimiter": lambda recipe: recipe.update(delimiters={"baseline": ",", "candidate": ";"}),
            "null-token": lambda recipe: recipe.update(null_tokens={"baseline": [], "candidate": ["NULL"]}),
            "projection": lambda recipe: recipe.update(input_projection="semantic-scalar-v1"),
            "sensitivity": lambda recipe: recipe.update(output={"sensitivity": "raw"}),
            "role": lambda recipe: recipe.update(keys=["order-id", "gross-amount"]),
            "type": lambda recipe: recipe["columns"].update({"gross-amount": {"type": "integer", "comparison": "exact"}}),
            "scale": lambda recipe: recipe["columns"]["gross-amount"].update(scale=3),
            "normalization": lambda recipe: recipe["columns"]["order-id"].update(normalize=["trim"]),
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

    def test_policy_diff_uses_closed_measure_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline_recipe = self._stable_recipe("aggregate", "gross_amount")
            candidate_recipe = self._stable_recipe("aggregate", "order_total")
            candidate_recipe["measures"]["gross"]["operator"] = "max"
            baseline = self._write_json(root, "baseline.json", baseline_recipe)
            candidate = self._write_json(root, "candidate.json", candidate_recipe)
            result = diff_policies(baseline, candidate, EXAMPLE)
            changed = [item for item in result["changes"] if item["reason"] == "GLOBAL_POLICY_CHANGED"]
            self.assertEqual(changed[0]["path"], "measures[].operator")
            self.assertEqual(changed[0]["policy_names"], ["gross"])
            self.assertNotIn("gross", json.dumps(summarize_policy_diff(result)))

    def test_every_effective_global_policy_leaf_has_a_closed_path(self):
        def leaves(value, path=()):
            if isinstance(value, dict):
                for key, item in value.items():
                    yield from leaves(item, path + (key,))
            else:
                yield path

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for mode in ("keyed", "aggregate", "multiset"):
                recipe = self._stable_recipe(mode, "gross_amount")
                recipe["input_projection"] = "semantic-scalar-v1"
                if mode == "aggregate":
                    recipe["measures"]["gross"].update({
                        "comparison": "numeric",
                        "tolerance": {"formula": "symmetric-v1", "absolute": "0.01", "relative": "0"},
                    })
                path = self._write_json(root, f"{mode}.json", recipe)
                policy = explain_recipe(path)
                global_policy = {key: value for key, value in policy.items() if key not in {"policy_sha256", "columns", "excluded_columns"}}
                for leaf in leaves(global_policy):
                    with self.subTest(mode=mode, leaf=leaf):
                        self.assertIsNotNone(_closed_policy_path(leaf)[0])

    def test_aggregate_policy_mutations_use_closed_paths_and_deny(self):
        mutations = {
            "group_by": (lambda recipe: recipe.update(group_by=["gross-amount"]), "group_by"),
            "operator": (lambda recipe: recipe["measures"]["gross"].update(operator="max"), "measures[].operator"),
            "nulls": (lambda recipe: recipe["measures"]["gross"].update(nulls="ignore"), "measures[].nulls"),
            "comparison-and-tolerance": (lambda recipe: recipe["measures"]["gross"].update(comparison="numeric", tolerance={"formula": "symmetric-v1", "absolute": "0.01", "relative": "0"}), "measures[].comparison"),
            "added-measure": (lambda recipe: recipe["measures"].update(rows={"operator": "count"}), "measures[]"),
        }
        for name, (mutate, expected_path) in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                baseline_recipe = self._stable_recipe("aggregate", "gross_amount")
                candidate_recipe = self._stable_recipe("aggregate", "order_total")
                mutate(candidate_recipe)
                baseline = self._write_json(root, "baseline.json", baseline_recipe)
                candidate = self._write_json(root, "candidate.json", candidate_recipe)
                result = diff_policies(baseline, candidate, EXAMPLE)
                self.assertEqual(result["compatibility"], "DENY")
                self.assertIn(expected_path, {item.get("path") for item in result["changes"]})
                self.assertNotIn("UNKNOWN_POLICY_PATH", {item["reason"] for item in result["changes"]})

    def test_tolerance_leaf_and_whole_object_use_closed_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline_recipe = self._stable_recipe("aggregate", "gross_amount")
            candidate_recipe = self._stable_recipe("aggregate", "order_total")
            for recipe in (baseline_recipe, candidate_recipe):
                recipe["measures"]["gross"].update(comparison="numeric", tolerance={"formula": "symmetric-v1", "absolute": "0.01", "relative": "0"})
            candidate_recipe["measures"]["gross"]["tolerance"]["absolute"] = "0.02"
            baseline = self._write_json(root, "baseline.json", baseline_recipe)
            candidate = self._write_json(root, "candidate.json", candidate_recipe)
            result = diff_policies(baseline, candidate, EXAMPLE)
            self.assertIn("measures[].tolerance.absolute", {item.get("path") for item in result["changes"]})
            del candidate_recipe["measures"]["gross"]["tolerance"]
            candidate_recipe["measures"]["gross"]["comparison"] = "exact"
            candidate = self._write_json(root, "candidate-without-tolerance.json", candidate_recipe)
            result = diff_policies(baseline, candidate, EXAMPLE)
            self.assertIn("measures[].tolerance", {item.get("path") for item in result["changes"]})

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
            changed = json.loads(json.dumps(declaration))
            changed["changes"][1]["candidate"][0]["nullability"] = "non-null"
            changed_evolution = self._write_json(root, "changed-evolution.json", changed)
            denied = diff_policies(baseline, candidate, changed_evolution)
            self.assertEqual(denied["compatibility"], "DENY")
            self.assertIn("FIELD_CONTRACT_CHANGED", {item["reason"] for item in denied["changes"]})

    def test_added_and_removed_fields_cover_safe_unknown_and_denied_roles(self):
        base_declaration = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scenarios = []

            candidate_active = self._stable_recipe("keyed", "order_total")
            candidate_active["excluded_columns"] = {}
            candidate_active["columns"]["migration-batch"] = {"type": "string"}
            candidate_active["column_mappings"]["migration-batch"] = {"baseline": "migration_batch", "candidate": "migration_batch"}
            scenarios.append(("added-active", self._stable_recipe("keyed", "gross_amount"), candidate_active, base_declaration, "DENY", "STRUCTURAL_FIELD_IS_COMPARED"))

            candidate_unknown = self._stable_recipe("keyed", "order_total")
            candidate_unknown["excluded_columns"] = {}
            scenarios.append(("added-unknown", self._stable_recipe("keyed", "gross_amount"), candidate_unknown, base_declaration, "INCONCLUSIVE", "STRUCTURAL_FIELD_ROLE_UNKNOWN"))

            unsafe = json.loads(json.dumps(base_declaration))
            unsafe["changes"][0]["candidate"][0]["presence"] = "optional"
            scenarios.append(("added-optional", self._stable_recipe("keyed", "gross_amount"), self._stable_recipe("keyed", "order_total"), unsafe, "DENY", "STRUCTURAL_FIELD_CONTRACT_UNSAFE"))

            removed = json.loads(json.dumps(base_declaration))
            removed["changes"][0] = {"change": "removed", "baseline": [{"id": "legacy", "name": "legacy_note", "presence": "required", "nullability": "non-null"}], "candidate": []}
            baseline_removed = self._stable_recipe("keyed", "gross_amount")
            baseline_removed["excluded_columns"] = {"legacy_note": "retired metadata"}
            candidate_removed = self._stable_recipe("keyed", "order_total")
            candidate_removed["excluded_columns"] = {}
            scenarios.append(("removed-excluded", baseline_removed, candidate_removed, removed, "ACCEPT", "EXCLUDED_STRUCTURAL_FIELD"))

            baseline_active = json.loads(json.dumps(baseline_removed))
            baseline_active["excluded_columns"] = {}
            baseline_active["columns"]["legacy"] = {"type": "string"}
            baseline_active["column_mappings"]["legacy"] = {"baseline": "legacy_note", "candidate": "legacy_note"}
            scenarios.append(("removed-active", baseline_active, candidate_removed, removed, "DENY", "STRUCTURAL_FIELD_IS_COMPARED"))

            for name, baseline_recipe, candidate_recipe, declaration, compatibility, reason in scenarios:
                with self.subTest(name=name):
                    baseline = self._write_json(root, f"{name}-baseline.json", baseline_recipe)
                    candidate = self._write_json(root, f"{name}-candidate.json", candidate_recipe)
                    evolution = self._write_json(root, f"{name}-evolution.json", declaration)
                    result = diff_policies(baseline, candidate, evolution)
                    self.assertEqual(result["compatibility"], compatibility)
                    self.assertIn(reason, {item["reason"] for item in result["changes"]})

    def test_policy_diff_denies_optional_compared_field(self):
        declaration = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        compared = next(item for item in declaration["changes"] if item["change"] == "unchanged")
        compared["baseline"][0]["presence"] = "optional"
        compared["candidate"][0]["presence"] = "optional"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline = self._write_json(root, "baseline.json", self._stable_recipe("keyed", "gross_amount"))
            candidate = self._write_json(root, "candidate.json", self._stable_recipe("keyed", "order_total"))
            evolution = self._write_json(root, "evolution.json", declaration)
            result = diff_policies(baseline, candidate, evolution)
            self.assertEqual(result["compatibility"], "DENY")
            self.assertIn("COMPARED_FIELD_NOT_REQUIRED", {item["reason"] for item in result["changes"]})

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

    def test_compared_split_and_excluded_merge_follow_transformation_boundary(self):
        common = {"id": "order-id", "name": "order_id", "presence": "required", "nullability": "non-null"}
        split = {
            "evolution_version": 1, "direction": "baseline-to-candidate", "changes": [
                {"change": "unchanged", "baseline": [common], "candidate": [common]},
                {"change": "split", "baseline": [{"id": "amount", "name": "amount", "presence": "required", "nullability": "non-null"}], "candidate": [
                    {"id": "whole", "name": "whole", "presence": "required", "nullability": "non-null"},
                    {"id": "fraction", "name": "fraction", "presence": "required", "nullability": "non-null"},
                ]},
            ],
        }
        merge = {
            "evolution_version": 1, "direction": "baseline-to-candidate", "changes": [
                {"change": "unchanged", "baseline": [common], "candidate": [common]},
                {"change": "merged", "baseline": [
                    {"id": "given", "name": "given", "presence": "required", "nullability": "nullable"},
                    {"id": "family", "name": "family", "presence": "required", "nullability": "nullable"},
                ], "candidate": [{"id": "name", "name": "name", "presence": "required", "nullability": "nullable"}]},
            ],
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline_split = self._recipe("amount")
            candidate_split = self._recipe("whole", {"fraction": "upstream component"})
            split_result = diff_policies(
                self._write_json(root, "split-baseline.json", baseline_split),
                self._write_json(root, "split-candidate.json", candidate_split),
                self._write_json(root, "split.json", split),
            )
            self.assertEqual(split_result["compatibility"], "DENY")
            self.assertIn("TRANSFORMATION_FIELD_IS_COMPARED", {item["reason"] for item in split_result["changes"]})

            baseline_merge = self._recipe("unused", {"given": "upstream", "family": "upstream"})
            candidate_merge = self._recipe("unused", {"name": "upstream"})
            del baseline_merge["columns"]["unused"]
            del candidate_merge["columns"]["unused"]
            merge_result = diff_policies(
                self._write_json(root, "merge-baseline.json", baseline_merge),
                self._write_json(root, "merge-candidate.json", candidate_merge),
                self._write_json(root, "merge.json", merge),
            )
            self.assertEqual(merge_result["compatibility"], "INCONCLUSIVE")
            self.assertIn("TRANSFORMATION_REQUIRES_UPSTREAM_MATERIALIZATION", {item["reason"] for item in merge_result["changes"]})


if __name__ == "__main__":
    unittest.main()
