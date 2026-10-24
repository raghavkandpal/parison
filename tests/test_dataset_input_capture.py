"""Fresh suite capture binds actual selected sources and policy."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from parison.core import load_suite, select_suite_cases
from parison.manifesting import capture_suite_input_bindings

ROOT = Path(__file__).parents[1]


class SuiteInputCapture(unittest.TestCase):
    def test_selected_cases_capture_real_bytes_and_effective_policies(self):
        suite = load_suite(ROOT / "examples/0.15/payout-suite.json")
        selected = select_suite_cases(suite, ["transaction-parity"], None, None, None)
        record = capture_suite_input_bindings(suite, selected)
        self.assertEqual(record["binding_version"], 1)
        self.assertEqual(record["policy"], {"kind": "suite", "sha256": suite["suite_policy_sha256"]})
        self.assertEqual(
            [(item["id"], item["role"]) for item in record["bindings"]],
            [("transaction-parity", "baseline"), ("transaction-parity", "candidate")],
        )
        for item in record["bindings"]:
            case = selected[0]
            source = Path(case[item["role"]])
            self.assertEqual(item["source_kind"], "file")
            self.assertEqual(item["selection"], {"kind": "file"})
            self.assertEqual(item["source_sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(item["policy_sha256"], case["policy_sha256"])
        schema = json.loads((ROOT / "src/parison/schemas/input-bindings-v1.schema.json").read_text())
        Draft202012Validator(schema).validate(record)

    def test_recapture_detects_changed_input_bytes(self):
        suite = load_suite(ROOT / "examples/0.15/payout-suite.json")
        selected = select_suite_cases(suite, ["transaction-parity"], None, None, None)
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "input.csv"
            source.write_bytes(b"first")
            selected[0]["baseline"] = str(source)
            first = capture_suite_input_bindings(suite, selected)
            source.write_bytes(b"second")
            second = capture_suite_input_bindings(suite, selected)
        self.assertNotEqual(first, second)
        self.assertEqual(first["bindings"][1], second["bindings"][1])


if __name__ == "__main__":
    unittest.main()
