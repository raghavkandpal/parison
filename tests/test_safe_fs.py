import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from parison._safe_fs import check_output_parent, rename_no_replace
from parison.core import ParisonError


class SafeFilesystemTests(unittest.TestCase):
    def test_atomic_publication_never_replaces_a_raced_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, target = root / "stage", root / "target"
            source.mkdir()
            (source / "new").write_text("new", encoding="utf-8")
            target.mkdir()
            (target / "existing").write_text("existing", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                rename_no_replace(source, target)

            self.assertEqual((target / "existing").read_text(encoding="utf-8"), "existing")
            self.assertTrue(source.is_dir())

    def test_windows_fallback_preserves_rename_no_replace_contract(self):
        source, target = Path("stage"), Path("target")
        with (
            patch("parison._safe_fs.sys.platform", "win32"),
            patch("parison._safe_fs.os.rename", side_effect=FileExistsError("raced")) as rename,
            self.assertRaises(FileExistsError),
        ):
            rename_no_replace(source, target)
        rename.assert_called_once_with(source, target)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are unavailable")
    def test_output_parent_rejects_symlink_components(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            real = root / "real"
            real.mkdir()
            linked = root / "linked"
            linked.symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(ParisonError, "output parent is unsafe"):
                check_output_parent(linked / "child")


if __name__ == "__main__":
    unittest.main()
