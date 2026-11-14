from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PAGES_PATH = ROOT / "sources" / "acupuncture" / "pages.jsonl"
CHAPTERS_PATH = ROOT / "data" / "acupuncture" / "chapters.json"
INDEXES_PATH = ROOT / "data" / "acupuncture" / "book_indexes.json"


class AcupunctureSourcesTest(unittest.TestCase):
    def test_pages_jsonl_integrity(self):
        with PAGES_PATH.open(encoding="utf-8") as handle:
            rows = [json.loads(line) for line in handle if line.strip()]
        self.assertEqual(len(rows), 216)
        footnote_pages = 0
        for row in rows:
            pdf_page = row["pdf_page"]
            if pdf_page >= 2:
                self.assertEqual(row["printed_page"], pdf_page)
                self.assertGreater(len(row["body_text"].strip()), 10)
            if row.get("footnotes"):
                footnote_pages += 1
        self.assertEqual(footnote_pages, 20)
        p43 = rows[42]
        self.assertEqual(p43["pdf_page"], 43)
        self.assertTrue(any("欠㰦" in fn for fn in p43["footnotes"]))

    def test_chapters_and_indexes_denominator(self):
        chapters = json.loads(CHAPTERS_PATH.read_text(encoding="utf-8"))
        indexes = json.loads(INDEXES_PATH.read_text(encoding="utf-8"))
        self.assertEqual(chapters["stats"]["total_chapters"], 6)
        self.assertEqual(chapters["stats"]["total_sections"], 297)
        self.assertEqual(chapters["stats"]["approved_sections"], 297)
        self.assertEqual(len(chapters["chapters"]), 6)
        self.assertEqual(chapters["chapters"][3]["total_sections"], 217)
        self.assertEqual(chapters["chapters"][5]["total_sections"], 34)
        self.assertEqual(indexes["stats"]["indexed_acupoint_terms"], 378)
        self.assertEqual(indexes["stats"]["indexed_condition_terms"], 274)


if __name__ == "__main__":
    unittest.main()
