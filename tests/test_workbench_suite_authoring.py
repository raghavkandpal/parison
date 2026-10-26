"""Destination-relative suite-v2 authoring and publication gates."""

import errno
import http.client
import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from parison.core import ParisonError, load_suite
from parison.workbench_host import create_workbench_server
from parison.workbench_suite_authoring import export_suite_draft, review_suite_draft

EXAMPLES = Path(__file__).parents[1] / "examples/0.15"


class SuiteAuthoring(unittest.TestCase):
    def test_workbench_routes_review_and_export(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("payout-aggregate.recipe.json", "payout-keyed.recipe.json", "processor.csv", "ledger.csv"):
                shutil.copy2(EXAMPLES / name, root / name)
            draft = json.loads((EXAMPLES / "payout-suite.json").read_text())
            server, _ = create_workbench_server(root, "authoring-capability")
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            connection = http.client.HTTPConnection(*server.server_address)

            def post(route, value):
                connection.request(
                    "POST",
                    route,
                    body=json.dumps(value),
                    headers={
                        "Content-Type": "application/json",
                        "Origin": f"http://127.0.0.1:{server.server_port}",
                        "X-Parison-Session": "authoring-capability",
                    },
                )
                response = connection.getresponse()
                return response.status, response.read()

            try:
                request = {"destination": "draft.json", "draft": draft}
                status, body = post("/api/suite-draft-review", request)
                self.assertEqual(status, 200)
                reviewed = json.loads(body)
                self.assertTrue(reviewed["unapproved"])
                self.assertFalse((root / "draft.json").exists())
                self.assertEqual(post("/api/suite-draft-export", {**request, "review_id": "0" * 64})[0], 422)
                status, body = post("/api/suite-draft-export", {**request, "review_id": reviewed["review_id"]})
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["suite_policy_sha256"], reviewed["suite_policy_sha256"])
                self.assertTrue((root / "draft.json").is_file())
            finally:
                connection.close()
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_relocated_review_and_unapproved_export(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("payout-aggregate.recipe.json", "payout-keyed.recipe.json", "processor.csv", "ledger.csv"):
                shutil.copy2(EXAMPLES / name, root / name)
            for source, target in (
                ("multiset.recipe.json", "multiset.recipe.json"),
                ("baseline.csv", "multiset-baseline.csv"),
                ("candidate.jsonl", "multiset-candidate.jsonl"),
            ):
                shutil.copy2(Path(__file__).parents[1] / "examples/0.8" / source, root / target)
            (root / "suites").mkdir()
            draft = json.loads((EXAMPLES / "payout-suite.json").read_text())
            draft["cases"].reverse()
            draft["cases"].append(
                {
                    "id": "multiset-check",
                    "recipe": "multiset.recipe.json",
                    "baseline": "multiset-baseline.csv",
                    "candidate": "multiset-candidate.jsonl",
                    "tags": ["critical"],
                }
            )
            for case in draft["cases"]:
                for key in ("recipe", "baseline", "candidate"):
                    case[key] = "../" + case[key]
            draft["defaults"] = {"limits": {"max_rows": 1000}}
            draft["cases"][0]["execution"] = {"engine": "sqlite", "max_temp_bytes": 1000000}
            draft["cases"][0]["limits"] = {"max_input_bytes": 1000000}
            draft["cases"][0]["expected_policy_sha256"] = load_suite(EXAMPLES / "payout-suite.json")["cases"][1][
                "policy_sha256"
            ]
            with patch("parison.suites.run_suite", side_effect=AssertionError("authoring executed")):
                reviewed = review_suite_draft(root, "suites/draft.json", draft)
                self.assertEqual(
                    reviewed["case_ids"], ["transaction-parity", "category-conservation", "multiset-check"]
                )
                exported = export_suite_draft(root, "suites/draft.json", draft, reviewed["review_id"])
            self.assertTrue(exported["unapproved"])
            self.assertEqual(
                load_suite(root / "suites/draft.json")["suite_policy_sha256"], reviewed["suite_policy_sha256"]
            )
            with self.assertRaises(ParisonError):
                export_suite_draft(root, "suites/draft.json", draft, reviewed["review_id"])
            draft["cases"][0]["expected_policy_sha256"] = "0" * 64
            with self.assertRaises(ParisonError):
                review_suite_draft(root, "suites/invalid.json", draft)

    def test_reference_change_invalidates_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("payout-aggregate.recipe.json", "payout-keyed.recipe.json", "processor.csv", "ledger.csv"):
                shutil.copy2(EXAMPLES / name, root / name)
            draft = json.loads((EXAMPLES / "payout-suite.json").read_text())
            reviewed = review_suite_draft(root, "draft.json", draft)
            source = root / "processor.csv"
            source.write_bytes(source.read_bytes() + b"\n")
            with self.assertRaisesRegex(ParisonError, "changed after review"):
                export_suite_draft(root, "draft.json", draft, reviewed["review_id"])
            self.assertFalse((root / "draft.json").exists())

    def test_traversal_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("payout-aggregate.recipe.json", "payout-keyed.recipe.json", "processor.csv", "ledger.csv"):
                shutil.copy2(EXAMPLES / name, root / name)
            draft = json.loads((EXAMPLES / "payout-suite.json").read_text())
            draft["cases"][0]["recipe"] = "../outside.json"
            with self.assertRaisesRegex(ParisonError, "leaves the workspace"):
                review_suite_draft(root, "draft.json", draft)
            draft["cases"][0]["recipe"] = "linked.json"
            (root / "linked.json").symlink_to(root / "payout-aggregate.recipe.json")
            with self.assertRaisesRegex(ParisonError, "symlink"):
                review_suite_draft(root, "draft.json", draft)

    def test_hostile_text_and_staging_errors_leave_no_draft(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("payout-aggregate.recipe.json", "payout-keyed.recipe.json", "processor.csv", "ledger.csv"):
                shutil.copy2(EXAMPLES / name, root / name)
            draft = json.loads((EXAMPLES / "payout-suite.json").read_text())
            draft["cases"][0]["description"] = "\ud800"
            with self.assertRaisesRegex(ParisonError, "UTF-8"):
                review_suite_draft(root, "draft.json", draft)
            draft["cases"][0].pop("description")
            with patch("parison.workbench_suite_authoring.os.fsync", side_effect=OSError(errno.ENOSPC, "full")):
                with self.assertRaisesRegex(ParisonError, "stage suite draft"):
                    review_suite_draft(root, "draft.json", draft)
            self.assertEqual(sorted(path.name for path in root.glob(".draft.json-*")), [])
            reviewed = review_suite_draft(root, "draft.json", draft)
            with patch("parison.workbench_suite_authoring.os.link", side_effect=OSError(errno.EPERM, "denied")):
                with self.assertRaisesRegex(ParisonError, "publish suite draft"):
                    export_suite_draft(root, "draft.json", draft, reviewed["review_id"])
            self.assertFalse((root / "draft.json").exists())
            self.assertEqual(sorted(path.name for path in root.glob(".draft.json-*")), [])
