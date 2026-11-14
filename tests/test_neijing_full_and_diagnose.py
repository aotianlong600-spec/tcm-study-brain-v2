import json
from pathlib import Path
import unittest

from fastapi.testclient import TestClient

from app.main import app


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "neijing"
WEB_DIR = ROOT / "web"


class NeijingFullBookAndDiagnoseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.chapters = json.loads((DATA_DIR / "chapters.json").read_text(encoding="utf-8"))
        cls.passages = json.loads((DATA_DIR / "passages.json").read_text(encoding="utf-8"))
        cls.concepts = json.loads((DATA_DIR / "concepts.json").read_text(encoding="utf-8"))
        cls.relations = json.loads((DATA_DIR / "relations.json").read_text(encoding="utf-8"))

    def test_all_74_chapters_and_283_sections_approved_without_reversed_pages(self):
        self.assertEqual(self.chapters["stats"]["total_chapters"], 74)
        self.assertEqual(self.chapters["stats"]["approved_chapters"], 74)
        self.assertEqual(self.chapters["stats"]["total_sections"], 283)
        self.assertEqual(self.chapters["stats"]["approved_sections"], 283)
        self.assertEqual(self.passages["stats"]["approved"], 74)
        self.assertEqual(self.passages["stats"]["pending"], 0)
        ch_sec_counts = {c["id"]: len(c.get("sections", [])) for c in self.chapters["chapters"]}
        total_sec_notes = 0
        for p in self.passages["items"]:
            self.assertEqual(p["review_status"], "approved", p["id"])
            self.assertEqual(p["evidence_status"], "verified", p["id"])
            expected_secs = ch_sec_counts.get(p["chapter_id"], 0)
            self.assertEqual(len(p.get("section_notes", [])), expected_secs, p["id"])
            total_sec_notes += len(p.get("section_notes", []))
            for span in p.get("source_spans", []):
                self.assertTrue(span.get("quote_sha256"), p["id"])
        self.assertEqual(total_sec_notes, 283)
        for ch in self.chapters["chapters"]:
            self.assertLessEqual(ch["pdf_page_start"], ch["pdf_page_end"], ch["id"])

    def test_34_concepts_and_303_relations_approved(self):
        self.assertEqual(self.concepts["stats"]["approved"], 34)
        self.assertEqual(self.concepts["stats"]["pending"], 0)
        self.assertEqual(self.relations["stats"]["total"], 303)
        self.assertEqual(self.relations["stats"]["approved"], 303)

    def test_overview_keeps_honest_partial_and_reports_full_suwen_counts(self):
        res = self.client.get("/api/overview")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["modules"]["neijing"], "partial")
        nj_stats = body["neijing_summary"]["stats"]
        self.assertEqual(nj_stats["approved_chapters"], 74)
        self.assertEqual(nj_stats["total_chapters"], 74)
        self.assertEqual(nj_stats["approved_sections"], 283)
        self.assertEqual(nj_stats["total_concepts"], 34)
        self.assertEqual(nj_stats["total_relations"], 303)

    def test_diagnose_endpoint_reasoning_and_high_risk_banners(self):
        empty = self.client.get("/api/neijing/diagnose")
        self.assertEqual(empty.status_code, 200)
        eb = empty.json()
        self.assertGreaterEqual(len(eb["prompt_chips"]), 6)
        self.assertGreaterEqual(len(eb["concepts"]), 4)
        self.assertGreaterEqual(len(eb["chapters"]), 4)

        xiao_ke = self.client.get("/api/neijing/diagnose", params={"q": "消渴 脾瘅"})
        self.assertEqual(xiao_ke.status_code, 200)
        xk = xiao_ke.json()
        self.assertGreaterEqual(xk["matched_concepts_count"], 1)
        self.assertGreaterEqual(xk["matched_chapters_count"], 1)
        self.assertTrue(any("奇病" in ch["title"] or "脾瘅" in json.dumps(ch, ensure_ascii=False) for ch in xk["chapters"]))

        zhenzang = self.client.get("/api/neijing/diagnose", params={"q": "真脏脉"})
        self.assertEqual(zhenzang.status_code, 200)
        zz = zhenzang.json()
        self.assertTrue(zz["has_high_risk"])
        self.assertIn("急危", zz["safety_banner"])

        fengshui = self.client.get("/api/neijing/diagnose", params={"q": "水肿 风水 卧蚕"})
        self.assertEqual(fengshui.status_code, 200)
        fs = fengshui.json()
        self.assertGreaterEqual(fs["matched_concepts_count"], 1)
        jinkui_ids = {x["id"] for x in fs["cross_module_links"].get("jinkui_formulas", [])}
        self.assertTrue(bool(jinkui_ids), "Expected cross-module Jinkui formula links for 水肿/风水")

    def test_chapter_detail_returns_full_page_previews_and_prev_next_links(self):
        res = self.client.get("/api/neijing/chapters/nj:suwen:05")
        self.assertEqual(res.status_code, 200)
        ch = res.json()
        self.assertEqual(len(ch["pages_preview"]), 10)
        self.assertEqual(ch["prev_chapter"]["id"], "nj:suwen:04")
        self.assertEqual(ch["next_chapter"]["id"], "nj:suwen:06")
        self.assertGreaterEqual(len(ch["passage"]["section_notes"]), 4)

    def test_reverse_neijing_relations_on_all_sibling_modules(self):
        checks = [
            ("/api/formulas/shanghan%3A%E6%A1%82%E6%9E%9D%E6%B1%A4", "formulas"),
            ("/api/formulas/jinkui%3A%E9%98%B2%E5%B7%B1%E9%BB%84%E8%80%86%E6%B1%A4", "jinkui_formulas"),
            ("/api/herbs/bencao%3A%E9%99%84%E5%AD%90", "herbs"),
            ("/api/six-channels/taiyang", "six_channels"),
            ("/api/acupuncture/meridians/meridian%3Alu", "meridian"),
            ("/api/acupuncture/points/acupoint%3Aren04%3A%E5%85%B3%E5%85%83", "acupoint"),
            ("/api/acupuncture/techniques/tech%3Aheavenly_stems_meridians", "technique"),
            ("/api/acupuncture/conditions/cond%3Ach6%3As275", "condition"),
        ]
        for url, label in checks:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200, f"{label}: {url}")
            body = res.json()
            nj_rels = body.get("neijing_relations", [])
            self.assertGreaterEqual(len(nj_rels), 1, f"Expected neijing_relations on {label} ({url})")
            first = nj_rels[0]
            self.assertIn(first["target_kind"], ("concept", "chapter"))
            self.assertTrue(first["target_nav_id"])
            self.assertTrue(first["canonical_name"])

    def test_frontend_diagnose_section_notes_and_bidirectional_wiring(self):
        html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
        nj_js = (WEB_DIR / "neijing.js").read_text(encoding="utf-8")
        app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")
        acup_js = (WEB_DIR / "acupuncture.js").read_text(encoding="utf-8")

        self.assertIn('data-nj-dim="diagnose"', html)
        self.assertIn("/api/neijing/diagnose", nj_js)
        self.assertIn("section_notes", nj_js)
        self.assertIn("prev_chapter", nj_js)
        self.assertIn("openConcept", nj_js)
        self.assertIn("openChapter", nj_js)

        self.assertIn("neijing_relations", app_js)
        self.assertIn("data-nj-jump-concept", app_js)
        self.assertIn("data-nj-jump-chapter", app_js)
        self.assertIn("neijing_relations", acup_js)
        self.assertIn("renderNeijingLinks", acup_js)


if __name__ == "__main__":
    unittest.main()
