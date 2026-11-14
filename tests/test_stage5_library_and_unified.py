from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

from fastapi.testclient import TestClient

from ai import grounded_study
from app.main import app
from etl.library.validate import validate_all


ROOT = Path(__file__).resolve().parents[1]


class Stage5LibraryAndUnifiedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_library_etl_validator_passes_with_all_17_books(self):
        res = validate_all()
        self.assertTrue(res["valid"], res.get("errors"))
        self.assertEqual(res["books"], 17)
        self.assertEqual(res["indexed_books"], 15)
        self.assertEqual(res["scan_only_books"], 2)
        self.assertGreaterEqual(res["syndromes"], 20)
        self.assertGreaterEqual(res["linked_pages"], 1500)

    def test_scan_only_books_never_fabricate_text_and_render_real_pngs(self):
        for book_id, expected_pages in (("xu-lingtai-collection-pdf", 434), ("huangdi-waijing-pdf", 85)):
            meta = self.client.get(f"/api/library/books/{book_id}")
            self.assertEqual(meta.status_code, 200)
            payload = meta.json()
            self.assertEqual(payload["search_index_status"], "scan_browse_only")
            self.assertEqual(payload["total_units"], expected_pages)
            self.assertEqual(payload["text_units"], 0)
            self.assertTrue(payload["has_image_viewer"])

            pg = self.client.get(f"/api/library/books/{book_id}/pages/1").json()
            self.assertEqual(pg["body_text"], "")
            self.assertEqual(pg["entity_links"], [])

            img = self.client.get(f"/api/library/books/{book_id}/pages/1/image")
            self.assertEqual(img.status_code, 200)
            self.assertTrue(img.content.startswith(b"\x89PNG"))

            # Searching directly in that scan-only book must return 0 hits
            sr = self.client.get(f"/api/library/search?q=伤寒&book_id={book_id}").json()
            self.assertEqual(sr["total"], 0)

    def test_newly_digitized_books_searchable_and_linked(self):
        # Verify Hantang Formulas HT-series, Hantang Cases, Xuezhenglun, Shishimilu, Otsuka, Wang Rulin
        checks = [
            ("ni-hantang-formulas-pdf", 235, "HT-"),
            ("ni-hantang-articles-cases-pdf", 383, "伤寒"),
            ("ni-hantang-clinic-notes-pdf", 35, "经方"),
            ("tang-rongchuan-xuezhenglun-pdf", 170, "血证论"),
            ("chen-shiduo-shishimilu-txt", None, "陈士铎"),
            ("shanghan-juyi-book-txt", None, "太阳"),
            ("otsuka-shanghan-docx", 9, "太陽"),
            ("wang-rulin-zhengyinfanglun-doc", 22, "證因方論"),
        ]
        for bid, expected_units, query in checks:
            b = self.client.get(f"/api/library/books/{bid}").json()
            self.assertEqual(b["search_index_status"], "indexed", bid)
            if expected_units is not None:
                self.assertEqual(b["total_units"], expected_units, bid)
            res = self.client.get(f"/api/library/search?q={query}&book_id={bid}").json()
            self.assertGreater(res["total"], 0, f"Expected hits for {query} in {bid}")

    def test_bidirectional_entity_and_book_linkage(self):
        # Entity -> Library backlinks
        el = self.client.get("/api/library/entity-links/shanghan:桂枝汤").json()
        self.assertGreater(el["library_ref_count"], 5)
        self.assertTrue(any("太阳表虚" in s["title"] for s in el["related_syndromes"]))

        # Book page -> clickable module entities
        pg = self.client.get("/api/library/books/tang-rongchuan-xuezhenglun-pdf/pages/2").json()
        self.assertTrue(pg["body_text"])
        self.assertIsNotNone(pg["image_url"])
        self.assertGreaterEqual(len(pg["entity_links"]), 1)

    def test_stage5a_unified_diagnose_spans_all_four_pillars(self):
        res = self.client.get("/api/stage5/diagnose?q=胸痹 短气 心痛彻背")
        self.assertEqual(res.status_code, 200)
        d = res.json()
        self.assertTrue(any(c["id"] == "syndrome:xiongbi-xintong" for c in d["syndrome_clusters"]))
        self.assertGreater(len(d["formulas"]["matched_formulas"]), 0)
        self.assertGreater(len(d["acupuncture"]["matched_points"]), 0)
        self.assertGreater(len(d["library_hits"]), 0)

    def test_stage5b_grounding_eval_cases(self):
        eval_cases = json.loads((ROOT / "evaluation" / "grounding_eval_cases.json").read_text(encoding="utf-8"))["cases"]
        for case in eval_cases:
            res = grounded_study.ground_study_query(case["query"])
            sb = res["safety_boundary"]
            self.assertEqual(sb["triggered"], case["expect_safety_triggered"], case["id"])
            if "expect_safety_mode" in case:
                self.assertEqual(sb["mode"], case["expect_safety_mode"], case["id"])
            if "expect_min_citations" in case:
                self.assertGreaterEqual(len(res["verified_citations"]), case["expect_min_citations"], case["id"])
            if "expect_min_pillars" in case:
                self.assertGreaterEqual(len(res["four_pillar_links"]), case["expect_min_pillars"], case["id"])
            for sid in case.get("expect_syndrome_ids", []):
                self.assertTrue(any(s["id"] == sid for s in res["matched_syndromes"]), f"{case['id']} missing {sid}")
            for scan_id in case.get("forbid_scan_books_cited", []):
                self.assertFalse(any(c["book_id"] == scan_id for c in res["verified_citations"]), f"{case['id']} cited scan {scan_id}")
            # Verify every single citation truly carries verified=True and sha
            for cite in res["verified_citations"]:
                self.assertTrue(cite["verified"])
                self.assertEqual(len(cite["text_sha256"]), 64)
            if case.get("expect_must_mention_scan_gap"):
                joined_gaps = " ".join(res["insufficiencies_and_gaps"])
                self.assertIn("徐灵胎", joined_gaps)

    def test_web_ui_has_standalone_library_and_stage5_without_breaking_core_tabs(self):
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "web" / "library_stage5.js").read_text(encoding="utf-8")
        tabs = re.findall(r'<button class="module-tab[^"]*"[^>]*>(.*?)</button>', html)
        self.assertEqual(tabs, ["针灸", "神农本草", "黄帝内经", "经方"])
        self.assertIn('data-stage5-view="library"', html)
        self.assertIn('data-stage5-view="stage5"', html)
        self.assertIn('id="library-view"', html)
        self.assertIn('id="stage5-view"', html)
        self.assertIn("/library_stage5.js", html)
        self.assertIn("/api/library/books", js)
        self.assertIn("/api/stage5/diagnose", js)
        self.assertIn("/api/stage5/compose", js)
        self.assertIn("/api/stage5/ground", js)

    def test_stage5_compose_dynamic_compound_formulas_and_pulse_differentiation(self):
        # Empty initial compose request must return empty query/regimens without pre-filling symptoms
        empty_res = self.client.get("/api/stage5/compose")
        self.assertEqual(empty_res.status_code, 200)
        empty_data = empty_res.json()
        self.assertEqual(empty_data["query"], "")
        self.assertEqual(empty_data["recognized_symptoms"], [])
        self.assertEqual(empty_data["recognized_pulses"], [])
        self.assertEqual(empty_data["compound_regimens"], [])
        self.assertGreaterEqual(len(empty_data["pulse_options"]), 12)
        self.assertGreaterEqual(len(empty_data["quick_symptom_pills"]), 18)

        js_src = (ROOT / "web" / "library_stage5.js").read_text(encoding="utf-8")
        self.assertIn("s5Pulses: []", js_src)
        self.assertIn("renderComposeEmpty", js_src)
        self.assertNotIn("const defaultQ =", js_src)

        # Case 1:身冷脚冷眩晕 + 腹痛大便干痛经 + 脉沉微细涩 -> 真武汤 合 当归芍药散 & 排除大承气汤
        c1 = self.client.get(
            "/api/stage5/compose?q=身冷，脚冷，眩晕，习惯性便秘，腹痛，大便干，痛经&pulse=沉 微细 涩"
        )
        self.assertEqual(c1.status_code, 200)
        d1 = c1.json()
        top1_names = set(d1["compound_regimens"][0]["formula_names"])
        self.assertEqual(top1_names, {"当归芍药散", "真武汤"})
        self.assertTrue(any(p["name"] == "大承气汤" for p in d1["excluded_pitfalls"]))
        acup1_names = {p["name"] for p in d1["acupoint_protocol"]["primary"] + d1["acupoint_protocol"]["adjuncts"]}
        self.assertTrue({"三阴交", "关元", "太溪"}.issubset(acup1_names))
        self.assertTrue(d1["ai_ready_case_packet"]["ready_for_llm"])

        # Case 2: 改见 但头汗出 + 小便不利 + 往来寒热 + 脉沉弦微细 -> 动态切换为 真武汤 合 柴胡桂枝干姜汤
        c2 = self.client.get(
            "/api/stage5/compose?q=身冷，脚冷，眩晕，但头汗出，小便不利，往来寒热&pulse=沉 弦 微细"
        )
        self.assertEqual(c2.status_code, 200)
        d2 = c2.json()
        top2_names = set(d2["compound_regimens"][0]["formula_names"])
        self.assertEqual(top2_names, {"柴胡桂枝干姜汤", "真武汤"})
        self.assertIn("但头汗出", d2["recognized_symptoms"])
        self.assertNotIn("有汗", d2["recognized_symptoms"])
        acup2_names = {p["name"] for p in d2["acupoint_protocol"]["primary"] + d2["acupoint_protocol"]["adjuncts"]}
        self.assertTrue({"期门", "阳陵泉", "关元"}.issubset(acup2_names))

        # Case 3: Expanded patterns check (半夏泻心汤 & 肾气丸)
        c3 = self.client.get("/api/stage5/compose?q=心下痞，呕吐&pulse=滑")
        self.assertEqual(c3.status_code, 200)
        self.assertEqual(c3.json()["candidate_formulas"][0]["name"], "半夏泻心汤")

        c4 = self.client.get("/api/stage5/compose?q=夜尿多，身冷，耳鸣&pulse=沉")
        self.assertEqual(c4.status_code, 200)
        self.assertEqual(c4.json()["candidate_formulas"][0]["name"], "肾气丸")

    def test_library_pdf_extraction_cleanliness_and_precision_search(self):
        # 1. 伤寒论 p.32 coordinate-ordered integrity & left-margin stamp removal
        p32 = self.client.get("/api/library/books/ni-shanghan-pdf/pages/32").json()
        self.assertIn("增「桂」令汗出亡阳故也", p32["body_text"])
        self.assertIn("葛根汤方", p32["body_text"])
        self.assertNotIn("觀\n其\n脈\n證", p32["body_text"])
        sh_meta = self.client.get("/api/library/books/ni-shanghan-pdf").json()
        self.assertGreaterEqual(len(sh_meta["chapters"]), 3)
        self.assertTrue(all(len(c["title"]) <= 28 for c in sh_meta["chapters"]))

        # 2. 金匮要略叠字去重
        p10 = self.client.get("/api/library/books/ni-jinkui-pdf/pages/10").json()
        self.assertNotIn("倪倪倪倪", p10["body_text"])
        self.assertIn("续伤寒篇", p10["body_text"])

        # 3. 汉唐方剂双栏顺序独立可读
        hf10 = self.client.get("/api/library/books/ni-hantang-formulas-pdf/pages/10").json()
        self.assertIn("乳汁不能正常下行了", hf10["body_text"])

        # 4. 整词/去引号/去换行检索精度（无 1298 条双元组噪音膨胀）
        s_ch = self.client.get("/api/library/search?q=柴胡桂枝干姜汤").json()
        self.assertFalse(s_ch["fallback_used"])
        self.assertEqual(s_ch["exact_total"], s_ch["total"])
        self.assertLess(s_ch["total"], 25)
        self.assertTrue(any(it["book_id"] == "ni-shanghan-pdf" and it["page_no"] == 107 for it in s_ch["items"]))

        # 5. 去书名/引号匹配：增桂令汗出亡阳 精准命中 增「桂」令汗出亡阳故也 (p.32)
        s_br = self.client.get("/api/library/search?q=增桂令汗出亡阳").json()
        self.assertFalse(s_br["fallback_used"])
        self.assertGreaterEqual(s_br["exact_total"], 1)
        self.assertTrue(any(it["book_id"] == "ni-shanghan-pdf" and it["page_no"] == 32 for it in s_br["items"]))

        # 6. 异体/错位注音折合检索（臓->脏、ㄧ->一）
        s_var = self.client.get("/api/library/search?q=五脏").json()
        self.assertGreater(s_var["exact_total"], 10)
        s_case = self.client.get("/api/library/search?q=一般&book_id=ni-hantang-articles-cases-pdf").json()
        self.assertGreater(s_case["exact_total"], 10)


    def test_stage5_compose_full_corpus_entries_clues_and_followup_questions(self) -> None:
        empty = self.client.get("/api/stage5/compose").json()
        self.assertEqual(empty["query"], "")
        self.assertGreaterEqual(len(empty["clinical_entry_cards"]), 12)
        for card in empty["clinical_entry_cards"]:
            self.assertTrue(card["id"].startswith("entry:"))
            self.assertTrue(card["tokens"])
            self.assertTrue(card["default_query"])

        rhinitis = self.client.get("/api/stage5/compose", params={"q": "过敏性鼻炎 鼻塞"}).json()
        self.assertTrue(rhinitis["matched_condition_patterns"])
        cond_names = [c["condition_name"] for c in rhinitis["matched_condition_patterns"]]
        self.assertTrue(any("鼻" in nm for nm in cond_names), f"Expected nasal condition pattern, got {cond_names}")
        pri_pts = [p["name"] for p in rhinitis["acupoint_protocol"]["primary"]]
        self.assertTrue(pri_pts, "Non-atom disease like 过敏性鼻炎 should still return acupuncture points")
        self.assertEqual(rhinitis["matched_jingfang_clues"], [])

        gallstone = self.client.get("/api/stage5/compose", params={"q": "胆结石 黄疸", "pulse": "弦"}).json()
        clue_names = [c["name"] for c in gallstone["matched_jingfang_clues"]]
        self.assertIn("茵陈五苓散", clue_names)
        self.assertTrue(any(c["why_summary"] for c in gallstone["matched_jingfang_clues"]))
        self.assertTrue(gallstone["followup_questions"])
        fu_tokens = {f.get("token", "") for f in gallstone["followup_questions"]}
        self.assertFalse(fu_tokens & set(gallstone["recognized_symptoms"]))

        hemostasis = self.client.get("/api/stage5/compose", params={"q": "痔疮 便血"}).json()
        self.assertEqual(hemostasis["matched_jingfang_clues"][0]["name"], "黄土汤")

        migraine = self.client.get("/api/stage5/compose", params={"q": "偏头痛 呕吐", "pulse": "弦 细"}).json()
        mig_names = [c["name"] for c in migraine["matched_jingfang_clues"]]
        self.assertIn("小柴胡汤", mig_names)
        xch = next(c for c in migraine["matched_jingfang_clues"] if c["name"] == "小柴胡汤")
        self.assertTrue(xch["modifications"], "Expected linked modifications on 小柴胡汤")
        self.assertIn("acupoint_protocol", migraine)
        self.assertTrue(migraine["acupoint_protocol"]["primary"])


if __name__ == "__main__":
    unittest.main()
