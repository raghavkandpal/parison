import unittest

from parison.workbench_page import PAGE


class WorkbenchPageTests(unittest.TestCase):
    def test_refined_ui_contract(self):
        page = PAGE.decode()

        self.assertIn("--canvas:#f4f6f9", page)
        self.assertIn(".editor-footer{align-items:stretch;flex-direction:column}", page)
        self.assertNotIn('class="eyebrow"', page)
        self.assertNotIn("@media(pointer:coarse)", page)


if __name__ == "__main__":
    unittest.main()
