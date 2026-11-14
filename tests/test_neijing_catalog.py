import unittest

from fastapi.testclient import TestClient

from app.main import app


class NeijingCatalogApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_overview_and_neijing_overview(self):
        ov = self.client.get("/api/overview").json()
        self.assertEqual(ov["modules"]["neijing"], "partial")
        self.assertIn("neijing_summary", ov)
        nj_ov = self.client.get("/api/neijing/overview").json()
        self.assertFalse(nj_ov["edition_inventory"]["lingshu_included"])
        self.assertEqual(nj_ov["stats"]["total_chapters"], 74)
        self.assertGreaterEqual(nj_ov["stats"]["approved_chapters"], 24)
        self.assertEqual(len(nj_ov["submodules"]), 6)

    def test_chapters_and_chapter_detail_routes(self):
        res = self.client.get("/api/neijing/chapters").json()
        self.assertEqual(res["total"], 74)
        ch5 = self.client.get("/api/neijing/chapters/nj:suwen:05").json()
        self.assertEqual(ch5["id"], "nj:suwen:05")
        self.assertEqual(ch5["passage"]["review_status"], "approved")
        self.assertTrue(ch5["passage"]["content_layers"]["source_quote"])
        self.assertTrue(ch5["passage"]["content_layers"]["ni_teaching"])
        self.assertTrue(ch5["related_concepts"])
        self.assertEqual(self.client.get("/api/neijing/chapters/nj:suwen:999").status_code, 404)

    def test_concepts_and_cross_module_resolution(self):
        res = self.client.get("/api/neijing/concepts?submodule=bian_zheng").json()
        self.assertGreaterEqual(res["total"], 3)
        c = self.client.get("/api/neijing/concepts/concept:nj:yin-yang-biao-li-han-re").json()
        self.assertTrue(c["differentiation_rules"])
        self.assertTrue(c["historical_boundary_note"])
        peer_mods = {lk["peer"]["module"] for lk in c["classic_links"]}
        self.assertIn("formulas", peer_mods)
        self.assertIn("acupuncture", peer_mods)
        self.assertEqual(self.client.get("/api/neijing/concepts/concept:nj:missing").status_code, 404)

    def test_pages_search_and_rendered_source_image(self):
        search = self.client.get("/api/neijing/pages?q=标本").json()
        self.assertGreaterEqual(search["total"], 1)
        page = self.client.get("/api/neijing/source-pages/ni-neijing-vol2-pdf/121").json()
        self.assertEqual(page["printed_page"], 268)
        self.assertIn("标本", page["body_text"])
        img = self.client.get(page["image_url"])
        self.assertEqual(img.status_code, 200)
        self.assertEqual(img.headers["content-type"], "image/png")
        self.assertGreater(len(img.content), 10000)


if __name__ == "__main__":
    unittest.main()
