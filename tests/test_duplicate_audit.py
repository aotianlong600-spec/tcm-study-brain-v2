import unittest

from scripts.audit_duplicate_formulas import audit


class DuplicateAuditTest(unittest.TestCase):
    def test_shanghan_has_no_exact_duplicate_entries(self):
        result = audit()
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["within_shanghan_name_duplicates"], {})
        self.assertEqual(result["within_shanghan_exact_composition_duplicates"], [])

    def test_cross_book_overlap_is_reported_not_deleted(self):
        result = audit()
        self.assertEqual(result["book_records"], 299)
        self.assertEqual(result["unique_normalized_names"], 257)
        self.assertEqual(result["cross_book_same_name"], 42)
        self.assertEqual(len(result["cross_book_groups"]), 42)


if __name__ == "__main__":
    unittest.main()
