import unittest

from parison.workbench_page import PAGE


class WorkbenchPageTests(unittest.TestCase):
    def test_refined_ui_contract(self):
        page = PAGE.decode()

        self.assertIn("--canvas:#f4f6f9", page)
        self.assertIn(".editor-footer{align-items:stretch;flex-direction:column}", page)
        self.assertNotIn('class="eyebrow"', page)
        self.assertNotIn("@media(pointer:coarse)", page)
        self.assertIn("tbody th{width:34%}", page)
        self.assertIn("#history-view table{table-layout:fixed}", page)
        self.assertNotIn("}th{width:34%", page)
        for activity in ("run", "history", "investigate", "compare"):
            self.assertIn(f'data-view="{activity}"', page)
            self.assertIn(f'id="{activity}-view"', page)


if __name__ == "__main__":
    unittest.main()
