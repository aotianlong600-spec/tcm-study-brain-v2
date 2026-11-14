import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "source_catalog.json"
MANIFEST_PATH = ROOT / "data" / "source_manifest.json"


class SourceCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        cls.by_id = {item["source_id"]: item for item in cls.catalog["sources"]}

    def test_catalog_covers_all_books_and_legacy_manifest_is_untouched(self):
        self.assertGreaterEqual(self.catalog["total_sources"], 23)
        self.assertEqual(len(self.by_id), len(self.catalog["sources"]))
        legacy = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertEqual(len(legacy["sources"]), 6)
        book_files = [
            p.relative_to(ROOT).as_posix()
            for p in (ROOT / "books" / "ni-haixia-medicine").rglob("*")
            if p.is_file()
        ]
        catalog_paths = {item["relative_path"] for item in self.catalog["sources"]}
        self.assertTrue(set(book_files).issubset(catalog_paths))

    def test_every_source_exists_and_sha256_matches(self):
        for item in self.catalog["sources"]:
            target = ROOT / item["relative_path"]
            self.assertTrue(target.is_file(), f"missing file: {item['relative_path']}")
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            self.assertEqual(item["sha256"], digest, item["source_id"])

    def test_acupuncture_source_is_marked_collated_transcript(self):
        acup = self.by_id["ni-acupuncture-v2-20100703"]
        self.assertEqual(acup["source_type"], "collated_transcript")
        self.assertEqual(acup["total_pages"], 216)
        self.assertEqual(acup["text_layer_status"], "clean_digital")
        self.assertIn("V2-20100703", acup["edition"])


if __name__ == "__main__":
    unittest.main()
