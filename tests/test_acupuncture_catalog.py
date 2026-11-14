from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app.main import app


class AcupunctureCatalogApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_overview_reports_complete_acupuncture(self):
        ov = self.client.get("/api/overview").json()
        self.assertEqual(ov["modules"]["acupuncture"], "complete")
        self.assertEqual(ov["modules"]["conditions"], "complete")
        self.assertEqual(ov["formulas"], 299)
        self.assertEqual(ov["herbs"], 351)

        aov = self.client.get("/api/acupuncture/overview").json()
        self.assertEqual(aov["total_pages"], 216)
        self.assertEqual(aov["chapters"]["approved_sections"], 297)
        self.assertEqual(aov["meridians"]["approved"], 15)
        self.assertEqual(aov["acupoints"]["total"], 387)
        self.assertEqual(aov["acupoints"]["approved"], 385)
        self.assertEqual(aov["techniques"]["approved"], 86)
        self.assertEqual(aov["conditions"]["approved"], 34)

    def test_chapters_and_indexes_routes(self):
        ch = self.client.get("/api/acupuncture/chapters").json()
        self.assertEqual(len(ch["chapters"]), 6)

        ch4 = self.client.get("/api/acupuncture/chapters/ch4").json()
        self.assertEqual(ch4["id"], "ch4")
        self.assertEqual(ch4["approved_sections"], 217)

        idx = self.client.get("/api/acupuncture/indexes", params={"q": "太渊"}).json()
        self.assertGreaterEqual(idx["counts"]["acupoint_terms"], 1)
        self.assertEqual(idx["acupoint_terms"][0]["name"], "太渊")

        self.assertEqual(self.client.get("/api/acupuncture/chapters/ch99").status_code, 404)

    def test_diagnose_bianzheng_and_fuzzy_queries(self):
        stomach = self.client.get("/api/acupuncture/diagnose", params={"q": "胃痛 呕吐 胃寒"}).json()
        self.assertTrue(any("胃痛" in g["title"] for g in stomach["channel_guides"]))
        self.assertEqual(stomach["matched_patterns"][0]["condition_id"], "cond:ch6:s281")
        stomach_pts = {p["id"] for p in stomach["matched_points"]}
        self.assertTrue({"acupoint:sp04:公孙", "acupoint:pc06:内关"}.issubset(stomach_pts))

        gyn = self.client.get("/api/acupuncture/diagnose", params={"q": "痛经 血块"}).json()
        self.assertEqual(gyn["matched_patterns"][0]["condition_id"], "cond:ch6:s289")
        self.assertTrue(any("妇科" in g["title"] for g in gyn["channel_guides"]))

        goat = self.client.get("/api/acupuncture/diagnose", params={"q": "大便干结 便秘 羊屎"}).json()
        self.assertEqual(goat["matched_patterns"][0]["condition_id"], "cond:ch6:s285")
        self.assertTrue(any(p["id"] == "acupoint:ki06:照海" for p in goat["matched_points"]))

        knee = self.client.get("/api/acupuncture/diagnose", params={"q": "膝盖冷"}).json()
        knee_ids = [p["id"] for p in knee["matched_points"]]
        self.assertIn("acupoint:st33:阴市", knee_ids)
        self.assertIn("acupoint:st32:伏兔", knee_ids)

        preg = self.client.get("/api/acupuncture/diagnose", params={"q": "孕妇 合谷 胎位不正"}).json()
        self.assertTrue(preg["safety_alerts"])
        self.assertEqual(preg["matched_patterns"][0]["condition_id"], "cond:ch6:s290")

        yinling = self.client.get("/api/acupuncture/points", params={"q": "阴陵"}).json()
        self.assertTrue(any(p["id"] == "acupoint:sp09:阴陵泉" for p in yinling["items"]))

        ashi = self.client.get("/api/acupuncture/techniques", params={"q": "阿是"}).json()
        self.assertTrue(any(t["id"] == "tech:ashi_and_tianying_rule" for t in ashi["items"]))

    def test_meridian_point_technique_condition_bidirectional_routes(self):
        lu = self.client.get("/api/acupuncture/meridians/meridian:lu").json()
        self.assertEqual(lu["canonical_name"], "手太阴肺经")
        self.assertEqual(len(lu["resolved_acupoints"]), 11)
        self.assertEqual(lu["paired_meridian"]["id"], "meridian:li")
        self.assertGreater(len(lu["relations"]), 0)

        pts = self.client.get("/api/acupuncture/points", params={"meridian_id": "meridian:lu"}).json()
        self.assertEqual(pts["filtered"], 11)

        zf = self.client.get("/api/acupuncture/points/acupoint:lu01:中府").json()
        self.assertEqual(zf["meridian"]["id"], "meridian:lu")
        self.assertEqual(zf["risk_level"], "high_risk")
        self.assertTrue(any(r["peer"]["id"] == "cond:ch6:治鼻病" for r in zf["relations"]))

        tech = self.client.get("/api/acupuncture/techniques/tech:shu_mu_yuan_luo_hui_xi").json()
        self.assertEqual(tech["review_status"], "approved")
        self.assertGreaterEqual(len(tech["steps_or_rules"]), 3)

        head = self.client.get("/api/acupuncture/conditions/cond:ch6:头部与脑瘤治症").json()
        self.assertEqual(head["risk_level"], "emergency")
        self.assertEqual(len(head["sub_patterns"]), 7)

        nose = self.client.get("/api/acupuncture/conditions/cond:ch6:治鼻病").json()
        linked_ids = {p["id"] for pat in nose["sub_patterns"] for p in pat["resolved_points"]}
        self.assertTrue({"acupoint:lu01:中府", "acupoint:lu03:天府", "acupoint:lu09:太渊"}.issubset(linked_ids))

        self.assertEqual(self.client.get("/api/acupuncture/points/missing:pt").status_code, 404)

    def test_source_page_text_footnotes_and_rendered_image(self):
        page43 = self.client.get("/api/acupuncture/source-pages/43").json()
        self.assertEqual(page43["pdf_page"], 43)
        self.assertTrue(any("欠㰦" in fn for fn in page43["footnotes"]))

        img_res = self.client.get("/api/acupuncture/source-pages/42/image")
        self.assertEqual(img_res.status_code, 200)
        self.assertEqual(img_res.headers["content-type"], "image/png")
        self.assertTrue(img_res.content.startswith(b"\x89PNG"))

        self.assertEqual(self.client.get("/api/acupuncture/source-pages/999").status_code, 404)


if __name__ == "__main__":
    unittest.main()
