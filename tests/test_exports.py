import csv
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ExportFilesTest(unittest.TestCase):
    def test_formula_csv_covers_all_records_with_doses(self):
        with (ROOT / "exports" / "formulas_with_doses.csv").open(
            encoding="utf-8-sig"
        ) as handle:
            rows = list(
                csv.DictReader(handle)
            )
        self.assertEqual(len(rows), 299)
        self.assertTrue(all(row["ingredients_with_doses"] for row in rows))
        self.assertEqual(
            sum(row["ingredients_with_doses"] == "原方缺" for row in rows),
            1,
        )

    def test_book_inventory_covers_local_source_files(self):
        files = [
            path
            for path in (ROOT / "books" / "ni-haixia-medicine").rglob("*")
            if path.is_file()
        ]
        inventory = (ROOT / "books" / "README.md").read_text(encoding="utf-8")
        self.assertEqual(len(files), 17)
        self.assertTrue(all(path.name in inventory for path in files))

    def test_dose_markdown_contains_both_books(self):
        text = (ROOT / "docs" / "formula-dosage-index.md").read_text(encoding="utf-8")
        self.assertIn("## 伤寒论", text)
        self.assertIn("## 金匮要略", text)
        self.assertIn("桂枝汤", text)


if __name__ == "__main__":
    unittest.main()
