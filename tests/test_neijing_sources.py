import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PAGES_PATH = ROOT / "sources" / "neijing" / "pages.jsonl"
CHAPTERS_PATH = ROOT / "data" / "neijing" / "chapters.json"


class NeijingSourcesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = [
            json.loads(line)
            for line in PAGES_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        cls.chapters_data = json.loads(CHAPTERS_PATH.read_text(encoding="utf-8"))

    def test_pages_jsonl_covers_both_volumes_and_all_301_printed_pages(self):
        self.assertEqual(len(self.pages), 306)
        vol1 = [p for p in self.pages if p["source_id"] == "ni-neijing-vol1-pdf"]
        vol2 = [p for p in self.pages if p["source_id"] == "ni-neijing-vol2-pdf"]
        self.assertEqual(len(vol1), 152)
        self.assertEqual(len(vol2), 154)
        printed = sorted(p["printed_page"] for p in self.pages if p.get("printed_page") is not None)
        self.assertEqual(printed, list(range(1, 302)))
        self.assertEqual(len(set(p["page_id"] for p in self.pages)), 306)

    def test_edition_inventory_is_honest_about_suwen_only_and_missing_chapters(self):
        inv = self.chapters_data["edition_inventory"]
        self.assertFalse(inv["lingshu_included"])
        self.assertEqual(inv["toc_chapter_entries"], 74)
        self.assertEqual(inv["unique_suwen_numbers_included"], 72)
        self.assertEqual(inv["missing_suwen_count"], 9)
        self.assertEqual(
            [m["suwen_number"] for m in inv["missing_suwen_chapters"]],
            [51, 66, 67, 68, 69, 70, 71, 73, 74],
        )

    def test_chapter_and_section_ids_are_unique(self):
        chapters = self.chapters_data["chapters"]
        self.assertEqual(len(chapters), 74)
        cids = [c["id"] for c in chapters]
        self.assertEqual(len(set(cids)), 74)
        sids = [s["id"] for c in chapters for s in c.get("sections", [])]
        self.assertEqual(len(sids), 283)
        self.assertEqual(len(set(sids)), 283)


if __name__ == "__main__":
    unittest.main()
