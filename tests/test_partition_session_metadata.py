"""Private semantic bindings grant neither file integrity nor reuse authority."""

import copy
import json
import unittest
from pathlib import Path

from parison import partition_sessions as sessions
from parison.core import ParisonError

ROOT = Path(__file__).parent / "fixtures/partition_session"
PROFILES = ("range-original", "range-reordered", "hash", "hash-pass", "hash-inconclusive")


def read(path):
    return json.loads(path.read_bytes())


class SessionMetadata(unittest.TestCase):
    def test_frozen_states_derived_policies_and_children(self):
        for profile in PROFILES:
            root = ROOT / profile
            plan = read(root / "plan.json")
            for path in (root / "journals").glob("*.json"):
                with self.subTest(profile=profile, state=path.stem):
                    sessions._journal(read(path), plan)
            journal = read(root / "journals/ready.json")
            recipe = sessions._derived((root / "routing/derived-recipe.json").read_bytes(), journal, plan)
            for index in range(len(journal["results"])):
                sessions._checkpoint(read(root / f"results/{index}.json"), index, journal, recipe)

    def test_semantic_negatives_with_recorded_identity_context(self):
        root = ROOT / "hash"
        plan = read(root / "plan.json")
        journal = read(root / "journals/ready.json")
        data = (root / "routing/derived-recipe.json").read_bytes()
        recipe = sessions._derived(data, journal, plan)
        for case in read(ROOT / "semantic-negative.json"):
            # Package/runtime/layout changes are resume admission failures, not
            # malformed recorded identity: preview cannot assert current eligibility.
            if case["case"] in {"wrong package binding", "foreign runtime before source IO"}:
                continue
            with self.subTest(case=case["case"]), self.assertRaises(ParisonError):
                value = case["value"]
                if case["schema"] == "partition-session-v1":
                    sessions._journal(value, plan)
                    sessions._derived(data, value, plan)
                else:
                    sessions._checkpoint(value, 0, journal, recipe)

    def test_exact_tokens_and_state_bindings(self):
        root = ROOT / "hash"
        plan = read(root / "plan.json")
        original = read(root / "journals/ready.json")
        mutations = (
            lambda j: j.update(partition_session_version=True),
            lambda j: j.update(max_session_bytes=100000.0),
            lambda j: j.update(state="routed"),
            lambda j: j.update(state="comparing"),
            lambda j: j.update(routing=None),
            lambda j: j["identity"].update(columns=["id", "amount", "tenant"]),
            lambda j: j["routing"]["receipt"]["route_rows"].update(baseline=3.0),
            lambda j: j["results"][0].update(bytes=755.0),
            lambda j: j["routing"]["receipt"]["partitions"][0].update(bucket=False),
            lambda j: j["routing"]["files"]["baseline-0.csv"].update(bytes=33),
        )
        for mutate in mutations:
            value = copy.deepcopy(original)
            mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(ParisonError):
                sessions._journal(value, plan)

    def test_foreign_well_formed_identity_is_readable_not_reusable(self):
        root = ROOT / "hash"
        journal = read(root / "journals/ready.json")
        journal["identity"]["engine"]["package_sha256"] = "a" * 64
        journal["identity"]["normalization_runtime"]["python_version"] = "3.11.1"
        sessions._journal(journal, read(root / "plan.json"))

    def test_canonical_derived_bytes_and_original_policy(self):
        root = ROOT / "hash"
        journal = read(root / "journals/ready.json")
        plan = read(root / "plan.json")
        data = (root / "routing/derived-recipe.json").read_bytes()
        for changed in (data + b"\n", data.replace(b'"expected_empty":true', b'"expected_empty":false')):
            with self.assertRaises(ParisonError):
                sessions._derived(changed, journal, plan)
        journal["identity"]["policy_sha256"] = "a" * 64
        with self.assertRaises(ParisonError):
            sessions._derived(data, journal, plan)

    def test_structural_negative_vectors(self):
        root = ROOT / "hash"
        journal = read(root / "journals/ready.json")
        plan = read(root / "plan.json")
        recipe = sessions._derived((root / "routing/derived-recipe.json").read_bytes(), journal, plan)
        for case in read(ROOT / "schema-negative.json"):
            if case["schema"] == "partition-session-result-v1":
                continue
            with self.subTest(case=case["case"]), self.assertRaises(ParisonError):
                if case["schema"] == "partition-session-v1":
                    sessions._journal(case["value"], plan)
                else:
                    sessions._checkpoint(case["value"], 0, journal, recipe)

    def test_committed_bytes_are_strict_bounded_canonical_lf(self):
        valid = (ROOT / "hash/journals/ready.json").read_bytes()
        self.assertEqual(sessions._metadata(valid), json.loads(valid))
        for data in (
            valid[:-1],
            valid + b"\n",
            b'{"x":1,"x":2}\n',
            b'{"x":NaN}\n',
            b"{}\r\n",
            b"[]\n",
            b'"secret"\n',
            b" " * 1048577,
            b"\xff",
        ):
            with (
                self.subTest(data=data[:20]),
                self.assertRaisesRegex(ParisonError, "^invalid partition session metadata$"),
            ):
                sessions._metadata(data)

    def test_coherent_forgery_remains_unsigned_integrity_only(self):
        root = ROOT / "hash"
        journal = read(root / "journals/ready.json")
        recipe = sessions._derived(
            (root / "routing/derived-recipe.json").read_bytes(), journal, read(root / "plan.json")
        )
        forged = read(ROOT / "coherent-forgery.json")
        child = forged["child"]
        sessions._checkpoint(child, child["index"], journal, recipe)
        self.assertFalse(forged["exact_replay_matches"])
        self.assertEqual(forged["assurance"], "reused-integrity-checked")

    def test_float_and_boolean_child_tokens_are_not_integer_counts(self):
        root = ROOT / "hash"
        journal = read(root / "journals/ready.json")
        recipe = sessions._derived(
            (root / "routing/derived-recipe.json").read_bytes(), journal, read(root / "plan.json")
        )
        for token in (1.0, True):
            for path in (
                ("index",),
                ("partition_checkpoint_version",),
                ("result", "counts", "baseline"),
                ("result", "discrepancy_count"),
                ("inputs", "baseline", "rows"),
            ):
                child = read(root / "results/0.json")
                target = child
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = token
                with self.subTest(path=path, token=token), self.assertRaises(ParisonError):
                    sessions._checkpoint(child, 0, journal, recipe)

    def test_abandoning_retains_ready_descriptor_invariants(self):
        root = ROOT / "hash"
        journal = read(root / "journals/ready.json")
        journal["state"] = "abandoning"
        journal["results"][0] = None
        with self.assertRaises(ParisonError):
            sessions._journal(journal, read(root / "plan.json"))
