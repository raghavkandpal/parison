"""Collection-v2 acquisition ordering, metadata admission and atomic cleanup."""

import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from parison import postgres_collection as collection
from parison.core import ParisonError
from parison.source_collection import verify_postgres_collection
from tests import test_postgres_collection_acquisition as acquisition

FIXTURE = Path(__file__).parent / "fixtures" / "postgres_representation"


class RepresentationCapture(unittest.TestCase):
    def setUp(self):
        # Reuse the existing fake driver and COPY stream, without inheriting its tests.
        self.harness = acquisition.CollectionAcquisition()
        self.harness.setUp()
        self.addCleanup(self.harness.doCleanups)
        self.harness.plan = json.loads((FIXTURE / "capture-plan.json").read_bytes())
        self.save()
        self.inventory = json.loads((FIXTURE / "candidate" / "representation.json").read_bytes())["tables"]

    def save(self):
        self.harness.plan_path.write_text(json.dumps(self.harness.plan))

    def export(self):
        return collection.export_postgres_collection(self.harness.plan_path, self.harness.output)

    def assert_clean(self):
        self.assertFalse(self.harness.output.exists())
        self.assertFalse(list(self.harness.root.glob(".output-*")))

    def test_metadata_admitted_after_all_locks_before_copy(self):
        events = []

        def capture(cursor, children, qualified):
            self.assertEqual(len([s for s in cursor.statements if s.startswith("LOCK TABLE")]), 2)
            self.assertEqual(set(children), set(qualified))
            self.assertEqual(events, [])
            events.append("metadata")
            self.assertNotIn("max_representation_bytes", children["orders"]["limits"])
            return copy.deepcopy(self.inventory)

        def acquire(*args):
            self.assertTrue(events)
            events.append("copy")
            return self.harness.acquire(*args)

        with (
            patch.object(collection, "_capture_inventory", side_effect=capture),
            patch.object(collection, "_acquire_table", side_effect=acquire),
        ):
            summary = self.export()
        self.assertEqual(events, ["metadata", "copy", "copy"])
        self.assertEqual(summary["postgres_collection_summary_version"], 2)
        self.assertEqual(summary, verify_postgres_collection(self.harness.output))
        metadata = json.loads((self.harness.output / "representation.json").read_bytes())
        self.assertEqual(metadata["tables"], self.inventory)
        self.assertEqual(metadata["transaction"]["snapshot"], "1:2:")

    def test_invalid_or_over_budget_metadata_never_reaches_copy(self):
        for label in ("budget", "normalization", "column-cap", "catalog-error", "interrupt"):
            with self.subTest(label=label):
                self.harness.plan = json.loads((FIXTURE / "capture-plan.json").read_bytes())
                inventory = copy.deepcopy(self.inventory)
                if label == "budget":
                    self.harness.plan["limits"]["max_representation_bytes"] = 1
                if label == "normalization":
                    inventory["orders"]["columns"][0]["numeric"]["precision"] = 64
                if label == "column-cap":
                    inventory["orders"]["columns"] *= 51
                self.save()
                failure = (
                    acquisition.DriverError("private catalog") if label == "catalog-error" else KeyboardInterrupt()
                )
                options = (
                    {"side_effect": failure} if label in {"catalog-error", "interrupt"} else {"return_value": inventory}
                )
                with (
                    patch.object(collection, "_capture_inventory", **options),
                    patch.object(collection, "_acquire_table") as acquire,
                ):
                    with self.assertRaises(KeyboardInterrupt if label == "interrupt" else ParisonError):
                        self.export()
                    acquire.assert_not_called()
                self.assert_clean()

    def test_capture_matrix_does_not_follow_csv_matrix_implicitly(self):
        def later_version(*args):
            source, snapshot = self.harness.qualify(*args)
            return {**source, "server_version_num": 180007}, snapshot

        with (
            patch.object(collection, "_qualify_table", side_effect=later_version),
            patch.object(collection, "_capture_inventory") as capture,
        ):
            with self.assertRaises(ParisonError):
                self.export()
            capture.assert_not_called()
        self.assert_clean()

    def test_bounded_catalog_fetch_and_version_classification(self):
        class Cursor:
            def execute(self, *args):
                pass

            def fetchmany(self, count):
                self.count = count
                return [("value",)] * 3

        cursor = Cursor()
        with self.assertRaises(ParisonError):
            collection._capture_rows(cursor, "query", (), "name", 2)
        self.assertEqual(cursor.count, 3)
        self.assertEqual(
            collection._provider_version(None, "libc", "C", "C"), {"state": "not-versioned", "value": None}
        )
        for provider in ("icu", "builtin"):
            self.assertEqual(
                collection._provider_version(None, provider, "C", "C"), {"state": "unknown", "value": None}
            )
        self.assertEqual(collection._provider_version("1", "builtin", None, None), {"state": "known", "value": "1"})

    def test_v1_writer_never_collects_representation(self):
        self.harness.plan = json.loads((FIXTURE.parent / "postgres_collection" / "plan.json").read_bytes())
        self.save()
        with patch.object(collection, "_capture_inventory") as capture:
            summary = self.export()
        capture.assert_not_called()
        self.assertEqual(summary["postgres_collection_summary_version"], 1)
        self.assertFalse((self.harness.output / "representation.json").exists())


if __name__ == "__main__":
    unittest.main()
