from pathlib import Path
import json
import unittest

from fastapi.testclient import TestClient

from app.main import app


ROOT = Path(__file__).resolve().parents[1]


class FormulaCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_overview_is_local_and_bounded(self):
        data = self.client.get("/api/overview").json()
        self.assertEqual(data["formulas"], 299)
        self.assertEqual(data["herbs"], 351)
        self.assertEqual(data["by_book"], {"伤寒论": 113, "金匮要略": 186})
        self.assertEqual(data["source_pending"], 1)
        self.assertEqual(data["modules"]["acupuncture"], "not_imported")

    def test_formula_detail_keeps_dose_and_source(self):
        data = self.client.get("/api/formulas/shanghan%3A%E6%A1%82%E6%9E%9D%E6%B1%A4").json()
        self.assertEqual(data["name"], "桂枝汤")
        self.assertEqual(data["expected_count"], 5)
        self.assertEqual(data["source"]["line"], 295)
        self.assertTrue(all(row["dose"] for row in data["ingredients"]))
        self.assertEqual(data["evidence"]["review_level"], "完整")
        self.assertEqual(data["evidence"]["six_channel"]["name"], "太阳病")
        self.assertGreaterEqual(len(data["evidence"]["six_channel"]["original"]), 3)
        self.assertGreaterEqual(len(data["evidence"]["usage_modern"]["steps"]), 5)
        self.assertGreaterEqual(len(data["evidence"]["symptoms"]), 8)
        self.assertGreaterEqual(len(data["evidence"]["page_reading"]), 5)

    def test_formula_to_herb_link(self):
        data = self.client.get("/api/formulas/shanghan%3A%E6%A1%82%E6%9E%9D%E6%B1%A4").json()
        self.assertTrue(any(row.get("herb_id") == "bencao:牡桂" for row in data["ingredients"]))
        self.assertEqual(data["evidence"]["review_status"], "reviewed")
        self.assertIn("有汗、恶风", data["evidence"]["why"])

    def test_herb_detail_has_formula_links(self):
        data = self.client.get("/api/herbs/bencao%3A%E7%89%A1%E6%A1%82").json()
        self.assertEqual(data["name"], "牡桂")
        self.assertTrue(any(item["name"] == "桂枝汤" for item in data["formulas"]))

    def test_search_and_filter(self):
        data = self.client.get("/api/formulas?q=桂枝&type=汤&page_size=60").json()
        self.assertGreater(data["total"], 0)
        self.assertTrue(all(item["name"] for item in data["items"]))
        self.assertTrue(all(item["type"] == "汤" for item in data["items"]))

    def test_source_variant_is_flagged(self):
        data = self.client.get("/api/overview").json()
        self.assertEqual(data["by_status"]["variant"], 4)
        self.assertEqual(data["by_status"]["missing"], 1)

    def test_six_channel_module_starts_with_taiyang(self):
        data = self.client.get("/api/six-channels").json()
        self.assertEqual(len(data["items"]), 6)
        taiyang = self.client.get("/api/six-channels/taiyang").json()
        self.assertEqual(taiyang["name"], "太阳病")
        self.assertEqual(taiyang["status"], "reviewed")
        self.assertGreaterEqual(len(taiyang["original"]), 3)
        self.assertGreaterEqual(len(taiyang["annotations"]), 3)
        self.assertIn("shanghan:桂枝汤", taiyang["related_formula_ids"])

    def test_jinkui_is_present_and_marked(self):
        data = self.client.get("/api/formulas?book=金匮要略&page_size=60").json()
        self.assertEqual(data["total"], 186)
        detail = self.client.get("/api/formulas/jinkui%3A%E5%9B%9B%E9%80%86%E5%8A%A0%E4%BA%BA%E5%8F%82%E6%B1%A4").json()
        self.assertEqual(detail["name"], "四逆加人参汤")
        self.assertEqual(detail["evidence"]["review_status"], "reviewed")
        self.assertIn("视频同步文稿", detail["evidence"]["usage_note"])
        jinkui = json.loads((ROOT / "data" / "jinkui_formulas.json").read_text(encoding="utf-8"))
        self.assertEqual(sum(1 for item in jinkui if any(not row["dose"] for row in item["ingredients"])), 0)
        self.assertEqual(sum(1 for item in jinkui if item["status"] == "complete"), 168)
        self.assertEqual(sum(1 for item in jinkui if item["status"] == "unchecked"), 17)


if __name__ == "__main__":
    unittest.main()
