from pathlib import Path
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
        self.assertEqual(data["formulas"], 112)
        self.assertEqual(data["herbs"], 351)
        self.assertEqual(data["source_pending"], 1)
        self.assertEqual(data["modules"]["acupuncture"], "not_imported")

    def test_formula_detail_keeps_dose_and_source(self):
        data = self.client.get("/api/formulas/shanghan%3A%E6%A1%82%E6%9E%9D%E6%B1%A4").json()
        self.assertEqual(data["name"], "桂枝汤")
        self.assertEqual(data["expected_count"], 5)
        self.assertEqual(data["source"]["line"], 295)
        self.assertTrue(all(row["dose"] for row in data["ingredients"]))

    def test_formula_to_herb_link(self):
        data = self.client.get("/api/formulas/shanghan%3A%E6%A1%82%E6%9E%9D%E6%B1%A4").json()
        self.assertTrue(any(row.get("herb_id") == "bencao:牡桂" for row in data["ingredients"]))

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
        self.assertIn("桂枝加葛根汤", data["source_variants"])


if __name__ == "__main__":
    unittest.main()
