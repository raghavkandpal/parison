"""Pin released identities that the opt-in dataset v2 bindings must preserve."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from parison.inputs import _source_digest, _source_paths


class DatasetBindingFeasibility(unittest.TestCase):
    def test_two_workbook_selections_share_physical_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "shared.xlsx"
            workbook = Workbook()
            workbook.active.append(["id", "value"])
            workbook.active.append(["1", 10])
            workbook.active.append(["2", 20])
            workbook.save(path)
            workbook.close()
            first = f"xlsx:{path}#Sheet!A1:B2"
            second = f"xlsx:{path}#Sheet!A1:B3"
            self.assertEqual(_source_paths(first), (path,))
            self.assertEqual(_source_paths(second), (path,))
            self.assertEqual(_source_digest(first), hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(_source_digest(first), _source_digest(second))

    def test_partition_identity_binds_names_and_preserves_single_member_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            member = root / "a.csv"
            content = b"id,value\n1,10\n"
            member.write_bytes(content)
            expected = hashlib.sha256(b"a.csv\0" + hashlib.sha256(content).digest()).hexdigest()
            self.assertEqual(_source_digest(root), expected)
            self.assertNotEqual(_source_digest(root), _source_digest(member))
            member.rename(root / "b.csv")
            self.assertNotEqual(_source_digest(root), expected)
            (root / ".hidden.csv").write_bytes(b"not selected")
            self.assertEqual(_source_paths(root), (root / "b.csv",))

    def test_json_selection_is_not_bound_by_physical_digest(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "shared.json"
            path.write_bytes(b'{"left":[{"id":1}],"right":[{"id":2}]}')
            self.assertEqual(_source_digest(f"json:{path}#/left"), _source_digest(f"json:{path}#/right"))

    def test_partition_identity_binds_content_and_membership_in_name_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            # Create in reverse order to distinguish enumeration from creation order.
            (root / "b.csv").write_bytes(b"id\n2\n")
            (root / "a.csv").write_bytes(b"id\n1\n")
            expected = hashlib.sha256(
                b"a.csv\0" + hashlib.sha256(b"id\n1\n").digest() + b"b.csv\0" + hashlib.sha256(b"id\n2\n").digest()
            ).hexdigest()
            self.assertEqual(_source_digest(root), expected)
            (root / "b.csv").write_bytes(b"id\n3\n")
            changed = _source_digest(root)
            self.assertNotEqual(changed, expected)
            (root / "c.csv").write_bytes(b"id\n4\n")
            self.assertNotEqual(_source_digest(root), changed)
