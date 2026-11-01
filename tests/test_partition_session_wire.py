"""Session structures are not execution, source bindings or authenticated caches."""

import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

from parison import partition_discovery as discovery
from parison.analysis import _canonical
from parison.cli import main
from parison.comparison import compare
from parison.core import ParisonError, _checked_policy_sha256, load_recipe, load_schema

ROOT = Path(__file__).parent / "fixtures" / "partition_session"
PROFILES = ("range-original", "range-reordered", "hash", "hash-pass", "hash-inconclusive")
NAMES = ("partition-session-v1", "partition-checkpoint-v1", "partition-session-result-v1")


def read(path):
    return json.loads(path.read_bytes())


def sha(data):
    return hashlib.sha256(data).hexdigest()


class SessionWire(unittest.TestCase):
    def test_standalone_schemas_and_existing_schema_cli(self):
        for name in NAMES:
            schema = load_schema(name)
            Draft202012Validator.check_schema(schema)

            def local_refs(value):
                if isinstance(value, dict):
                    if "$ref" in value:
                        self.assertTrue(value["$ref"].startswith("#/$defs/"))
                    for child in value.values():
                        local_refs(child)
                elif isinstance(value, list):
                    for child in value:
                        local_refs(child)

            local_refs(schema)
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(["schema", name]), 0)
            self.assertEqual(json.loads(out.getvalue()), schema)

    def test_all_canonical_states_children_and_response_examples(self):
        for path in ROOT.rglob("*.json"):
            expected = _canonical(read(path))
            self.assertEqual(path.read_bytes(), expected if path.name == "derived-recipe.json" else expected + b"\n")
        for profile in PROFILES:
            root = ROOT / profile
            for directory, name in (("journals", NAMES[0]), ("results", NAMES[1]), ("responses", NAMES[2])):
                validator = Draft202012Validator(load_schema(name))
                for path in (root / directory).glob("*.json"):
                    with self.subTest(profile=profile, path=path.name):
                        validator.validate(read(path))
            self.assertEqual(
                {p.stem for p in (root / "journals").glob("*.json")},
                {"initializing", "routed", "comparing", "ready", "published", "abandoning"},
            )

    def test_frozen_cross_file_bindings_and_exact_engine_children(self):
        for profile in PROFILES:
            root = ROOT / profile
            journal = read(root / "journals/ready.json")
            recipe = load_recipe(root / "recipe.json")
            plan = read(root / "plan.json")
            identity = journal["identity"]
            self.assertEqual(identity["plan_sha256"], sha(_canonical(plan)))
            self.assertEqual(identity["policy_sha256"], _checked_policy_sha256(recipe))
            self.assertEqual(
                identity["derived_recipe_sha256"], sha((root / "routing/derived-recipe.json").read_bytes())
            )
            for name, descriptor in journal["routing"]["files"].items():
                data = (root / "routing" / name).read_bytes()
                self.assertEqual(descriptor, {"sha256": sha(data), "bytes": len(data)})
            for side in ("baseline", "candidate"):
                data = (root / f"{side}.csv").read_bytes()
                self.assertEqual(identity["inputs"][side], {"sha256": sha(data), "bytes": len(data)})
                self.assertEqual(journal["routing"]["receipt"]["inputs"][side], identity["inputs"][side])
            final = read(root / "expected/receipt.json")
            for index, descriptor in enumerate(journal["results"]):
                data = (root / "results" / f"{index}.json").read_bytes()
                self.assertEqual(descriptor, {"sha256": sha(data), "bytes": len(data)})
                child = json.loads(data)
                self.assertEqual(child["index"], index)
                self.assertEqual(
                    child["policy_sha256"], _checked_policy_sha256(load_recipe(root / "routing/derived-recipe.json"))
                )
                self.assertEqual(child["engine_sha256"], sha(_canonical(identity["engine"])))
                expected = compare(
                    root / "routing/derived-recipe.json",
                    root / "routing" / f"baseline-{index}.csv",
                    root / "routing" / f"candidate-{index}.csv",
                    sample_limit=0,
                )
                self.assertEqual(child["policy_sha256"], expected["policy_sha256"])
                self.assertNotEqual(child["policy_sha256"], identity["derived_recipe_sha256"])
                self.assertEqual(child["result"], {key: expected[key] for key in child["result"]})
                self.assertEqual(
                    child["inputs"], {side: final["partitions"][index][side] for side in ("baseline", "candidate")}
                )
            manifest = (root / "expected/manifest.json").read_bytes()
            self.assertEqual(journal["published_manifest_sha256"], sha(manifest))
            snapshot_bytes = sum(identity["inputs"][side]["bytes"] for side in ("baseline", "candidate"))
            all_routing_bytes = sum(item["bytes"] for item in journal["routing"]["files"].values())
            expected_staged = (
                all_routing_bytes
                if plan["partition_plan_version"] == 2
                else all_routing_bytes - snapshot_bytes - (root / "routing/derived-recipe.json").stat().st_size
            )
            self.assertEqual(final["staged_bytes"], expected_staged)

    def test_final_references_match_ordinary_discovery_including_both_legacy_orders(self):
        for profile in PROFILES:
            root = ROOT / profile
            journal = read(root / "journals/ready.json")
            recipe = read(root / "recipe.json")
            recipe["columns"] = {name: recipe["columns"][name] for name in journal["identity"]["columns"]}
            with tempfile.TemporaryDirectory() as temporary:
                temp = Path(temporary)
                (temp / "recipe.json").write_text(json.dumps(recipe), encoding="utf-8")
                with patch.object(
                    discovery, "_execution_context", return_value=journal["identity"]["normalization_runtime"]
                ):
                    discovery.discover(
                        root / "plan.json",
                        temp / "recipe.json",
                        root / "baseline.csv",
                        root / "candidate.csv",
                        temp / "output",
                    )
                    for path in (root / "expected").iterdir():
                        self.assertEqual(
                            (temp / "output" / path.name).read_bytes(), path.read_bytes(), (profile, path.name)
                        )
            self.assertEqual(discovery.verify(root / "expected")["verification"], "integrity-only")
        self.assertNotEqual(
            read(ROOT / "range-original/journals/ready.json")["identity"]["columns"],
            read(ROOT / "range-reordered/journals/ready.json")["identity"]["columns"],
        )

    def test_structural_negatives_and_future_semantic_obligations(self):
        for case in read(ROOT / "schema-negative.json"):
            with self.subTest(case=case["case"]):
                self.assertFalse(Draft202012Validator(load_schema(case["schema"])).is_valid(case["value"]))
        semantic = read(ROOT / "semantic-negative.json")
        self.assertGreaterEqual(len(semantic), 10)
        for case in semantic:
            with self.subTest(case=case["case"]):
                Draft202012Validator(load_schema(case["schema"])).validate(case["value"])
        self.assertTrue((ROOT / "truncated-session.next").read_bytes().startswith(b'{"partition_session_version":'))
        for name in ("truncated-session.next", "duplicate-session.raw", "nonfinite-session.raw"):
            with self.assertRaises(ParisonError):
                discovery._parse_json((ROOT / name).read_bytes())

    def test_primary_journal_authority_vectors_and_incomplete_child_obligation(self):
        cases = read(ROOT / "recovery-cases.json")
        for case in cases:
            if case["decision"] == "use-primary-discard-next":
                primary = read(ROOT / case["primary"])
                Draft202012Validator(load_schema(NAMES[0])).validate(primary)
                self.assertEqual(primary["state"], "comparing")
            elif case["decision"] == "reject":
                self.assertTrue(case["primary"] is None or case["primary"].endswith((".raw", ".next")))
            else:
                journal = read(ROOT / case["primary"])
                self.assertIsNone(journal["results"][case["child_slot"]])
                with self.assertRaises(ParisonError):
                    discovery._parse_json((ROOT / case["child"]).read_bytes())
        children = [read(path) for path in (ROOT / "hash-inconclusive/results").glob("*.json")]
        self.assertTrue(any(not child["result"]["complete"] for child in children))
        # Future reuse must reject incomplete children despite valid structure.

    def test_closed_assurance_and_query_response_constraints(self):
        validator = Draft202012Validator(load_schema(NAMES[2]))
        original = read(ROOT / "hash/responses/resume.json")
        for name, value in (
            ("execution_assurance", "exact-source-backed"),
            ("execution_assurance", "fresh-exact"),
            ("source_path", "private/source.csv"),
            ("sensitive_retained", False),
        ):
            record = {**original, name: value}
            self.assertFalse(validator.is_valid(record))
        preview = read(ROOT / "hash/responses/preview.json")
        for name, value in (("reused_partitions", 1), ("summary", original["summary"]), ("state", "abandoned")):
            self.assertFalse(validator.is_valid({**preview, name: value}))

    def test_coherently_forged_child_is_not_authenticated_by_schema_or_hash(self):
        forged = read(ROOT / "coherent-forgery.json")
        child = forged["child"]
        Draft202012Validator(load_schema(forged["schema"])).validate(child)
        data = _canonical(child) + b"\n"
        self.assertEqual(forged["descriptor"], {"sha256": sha(data), "bytes": len(data)})
        root = ROOT / "hash"
        index = child["index"]
        fresh = compare(
            root / "routing/derived-recipe.json",
            root / "routing" / f"baseline-{index}.csv",
            root / "routing" / f"candidate-{index}.csv",
            sample_limit=0,
        )
        self.assertEqual(child["policy_sha256"], fresh["policy_sha256"])
        self.assertNotEqual(child["result"], {key: fresh[key] for key in child["result"]})
        self.assertTrue(discovery._consistent_counts(child["result"]["counts"], child["result"]["field_counts"], True))
        self.assertEqual(forged["assurance"], "reused-integrity-checked")
        self.assertIs(forged["exact_replay_matches"], False)

    def test_wire_gate_does_not_enable_retained_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "output"
            root = ROOT / "hash"
            args = [
                "discover",
                "--plan",
                str(root / "plan.json"),
                "--recipe",
                str(root / "recipe.json"),
                "--baseline",
                str(root / "baseline.csv"),
                "--candidate",
                str(root / "candidate.csv"),
                "--output",
                str(out),
                "--workspace",
                str(Path(temporary) / "retained"),
            ]
            for command in (["session", "preview", "private"], args):
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                    discovery.main(command)
                self.assertEqual(caught.exception.code, 2)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
