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
        self.assertEqual(res["indexed_books"], 17)
        self.assertEqual(res["scan_only_books"], 0)
        self.assertGreaterEqual(res["syndromes"], 20)
        self.assertGreaterEqual(res["linked_pages"], 1500)

    def test_ocr_indexed_books_preserve_blank_pages_and_render_real_pngs(self):
        cases = (
            ("xu-lingtai-collection-pdf", 434, 412, 15, 374, "慎疾刍言", "慎疾刍言"),
            ("huangdi-waijing-pdf", 85, 85, None, 76, "阴寒格阳", "命门"),
        )
        for book_id, expected_pages, expected_text_units, blank_pno, content_pno, must_contain, search_q in cases:
            meta = self.client.get(f"/api/library/books/{book_id}")
            self.assertEqual(meta.status_code, 200)
            payload = meta.json()
            self.assertEqual(payload["search_index_status"], "indexed")
            self.assertEqual(payload["total_units"], expected_pages)
            self.assertEqual(payload["text_units"], expected_text_units)
            self.assertTrue(payload["has_image_viewer"])

            if blank_pno is not None:
                blank_pg = self.client.get(f"/api/library/books/{book_id}/pages/{blank_pno}").json()
                self.assertEqual(blank_pg["body_text"], "")
                self.assertEqual(blank_pg["ocr_status"], "blank_page")

            pg = self.client.get(f"/api/library/books/{book_id}/pages/{content_pno}").json()
            self.assertIn(must_contain, pg["body_text"])

            img = self.client.get(f"/api/library/books/{book_id}/pages/{content_pno}/image")
            self.assertEqual(img.status_code, 200)
            self.assertTrue(img.content.startswith(b"\x89PNG"))

            sr = self.client.get(f"/api/library/search?q={search_q}&book_id={book_id}").json()
            self.assertGreater(sr["total"], 0)
            self.assertEqual(sr["scan_only_notice"], [])

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
            for req_id in case.get("expect_require_cited_book_ids", []):
                self.assertTrue(any(c["book_id"] == req_id for c in res["verified_citations"]), f"{case['id']} missing cited {req_id}")
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
        self.assertGreaterEqual(len(sh_meta["chapters"]), 5)
        self.assertTrue(all(len(c["title"]) <= 28 for c in sh_meta["chapters"]))
        jk_meta = self.client.get("/api/library/books/ni-jinkui-pdf").json()
        self.assertGreaterEqual(len(jk_meta["chapters"]), 5)
        self.assertTrue(all(len(c["title"]) <= 28 for c in jk_meta["chapters"]))

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

    def test_library_context_continuous_reading_and_frontend_hooks(self) -> None:
        # 1. Indexed PDF windowed context
        resp = self.client.get("/api/library/books/ni-shanghan-pdf/context?page_no=32&before=2&after=3")
        self.assertEqual(resp.status_code, 200)
        ctx = resp.json()
        self.assertEqual(ctx["target_page"], 32)
        self.assertEqual(ctx["start_page"], 30)
        self.assertEqual(ctx["end_page"], 35)
        self.assertTrue(ctx["has_prev_chunk"])
        self.assertTrue(ctx["has_next_chunk"])
        self.assertEqual([p["page_no"] for p in ctx["pages"]], [30, 31, 32, 33, 34, 35])
        target_blk = next(p for p in ctx["pages"] if p["page_no"] == 32)
        self.assertIn("葛根汤方", target_blk["body_text"])
        self.assertTrue(target_blk["text_sha256"])

        # 2. Text-only book boundary at start page
        txt_ctx = self.client.get("/api/library/books/chen-shiduo-shishimilu-txt/context?page_no=1&before=2&after=4").json()
        self.assertEqual(txt_ctx["start_page"], 1)
        self.assertFalse(txt_ctx["has_prev_chunk"])
        self.assertFalse(txt_ctx["pages"][0]["has_image_viewer"])

        # 3. OCR-indexed scan volume returns real OCR text on content pages, stays empty on blank pages, and serves PNGs
        ocr_ctx = self.client.get("/api/library/books/xu-lingtai-collection-pdf/context?page_no=16&before=1&after=1").json()
        self.assertEqual(len(ocr_ctx["pages"]), 3)
        for pg in ocr_ctx["pages"]:
            self.assertEqual(pg["search_index_status"], "indexed")
            self.assertIn("/image", pg["image_url"])
        blank_p15 = next(p for p in ocr_ctx["pages"] if p["page_no"] == 15)
        self.assertEqual(blank_p15["body_text"], "")
        content_p16 = next(p for p in ocr_ctx["pages"] if p["page_no"] == 16)
        self.assertIn("难经", content_p16["body_text"])

        # 4. Unknown book returns 404
        self.assertEqual(self.client.get("/api/library/books/nonexistent/context?page_no=1").status_code, 404)

        # 5. Frontend continuous reader + search-back hooks exist
        js = (ROOT / "web" / "library_stage5.js").read_text(encoding="utf-8")
        for token in (
            "/context?",
            "lib-continuous-stream",
            "loadContextDirection",
            "data-lib-layout",
            "is-continuation",
            "lib-synced-scan-pane",
            "lib-back-to-search-btn",
        ):
            self.assertIn(token, js)

    def test_stage5_compose_expanded_syndromes_tongue_inquiry_and_safety(self) -> None:
        empty = self.client.get("/api/stage5/compose").json()
        self.assertGreaterEqual(len(empty["tongue_options"]), 6)
        self.assertGreaterEqual(len(empty["inquiry_pills"]), 12)

        # 1. 炙甘草汤 (脉结代 + 舌红少苔)
        zgct = self.client.get("/api/stage5/compose", params={"q": "心悸 失眠 舌红少苔", "pulse": "结代"}).json()
        self.assertIn("舌红少苔", zgct["recognized_tongues"])
        self.assertEqual(zgct["candidate_formulas"][0]["name"], "炙甘草汤")
        self.assertTrue(zgct["triage_summary"]["headline"])
        self.assertTrue(zgct["triage_summary"]["tongue_notes"])
        self.assertTrue(zgct["decoction_and_safety"])

        # 2. 麻黄汤 (太阳伤寒表实 + 麻黄先煮注意)
        mht = self.client.get("/api/stage5/compose", params={"q": "发热 无汗 恶寒 身痛 咳嗽", "pulse": "浮 紧"}).json()
        self.assertEqual(mht["candidate_formulas"][0]["name"], "麻黄汤")
        self.assertTrue(any("麻黄" in note for note in mht["decoction_and_safety"]))

        # 3. 白虎汤 (阳明经证洪大渴)
        bht = self.client.get("/api/stage5/compose", params={"q": "高热 大汗 口渴 喜冷饮", "pulse": "洪大"}).json()
        self.assertEqual(bht["candidate_formulas"][0]["name"], "白虎汤")

        # 4. 桃核承气汤 (蓄血小便自利少腹急结)
        thcq = self.client.get("/api/stage5/compose", params={"q": "少腹急结 如狂 小便自利", "pulse": "沉 涩"}).json()
        self.assertEqual(thcq["candidate_formulas"][0]["name"], "桃核承气汤")

        # 5. 大黄牡丹汤 (肠痈右下腹痛)
        dhmd = self.client.get("/api/stage5/compose", params={"q": "右下腹痛 发热 脉数"}).json()
        self.assertEqual(dhmd["candidate_formulas"][0]["name"], "大黄牡丹汤")

        # 6. Polarity exclusion: never auto-pair 大承气汤 with 四逆汤/白通汤
        mixed = self.client.get(
            "/api/stage5/compose",
            params={"q": "高热 腹满拒按 大便闭 身冷 脚冷 下利清谷", "pulse": "洪大 微细"},
        ).json()
        for reg in mixed["compound_regimens"]:
            fnames = set(reg["formula_names"])
            self.assertFalse(
                {"大承气汤", "四逆汤"}.issubset(fnames) or {"白虎汤", "四逆汤"}.issubset(fnames),
                f"Antagonistic pair leaked into compound regimen: {fnames}",
            )

        # 7. Frontend compose hooks for new triage/tongue/inquiry/decoction features
        js = (ROOT / "web" / "library_stage5.js").read_text(encoding="utf-8")
        for token in ("tongue_options", "inquiry_pills", "triage_summary", "decoction_and_safety"):
            self.assertIn(token, js)

    def test_library_locate_endpoint_and_context_drawer_hooks(self) -> None:
        # 1. Shanghan Juyi line-based lookup
        juyi = self.client.get(
            "/api/library/locate",
            params={"book_hint": "伤寒论辑义", "line": 295, "q": "桂枝汤"},
        )
        self.assertEqual(juyi.status_code, 200)
        jb = juyi.json()
        self.assertEqual(jb["resolved_book_id"], "shanghan-juyi-book-txt")
        self.assertGreaterEqual(jb["resolved_page_no"], 1)
        self.assertTrue(jb["pages"])
        self.assertLessEqual(jb["start_page"], jb["resolved_page_no"])
        self.assertGreaterEqual(jb["end_page"], jb["resolved_page_no"])

        # 2. Jinkui page + quote verification
        jk = self.client.get(
            "/api/library/locate",
            params={"book_hint": "金匮要略", "page_no": 103, "q": "桂枝芍药知母汤"},
        )
        self.assertEqual(jk.status_code, 200)
        jkb = jk.json()
        self.assertEqual(jkb["resolved_book_id"], "ni-jinkui-pdf")
        self.assertEqual(jkb["resolved_page_no"], 103)
        self.assertTrue(jkb["pages"])

        # 3. Quote-only global lookup
        qonly = self.client.get("/api/library/locate", params={"q": "先便后血"})
        self.assertEqual(qonly.status_code, 200)
        qb = qonly.json()
        self.assertGreaterEqual(qb["resolved_page_no"], 1)
        self.assertTrue(qb["pages"])

        # 3b. 2-char acupoint & alias locator + chapters/matched_pages index payload
        zf = self.client.get(
            "/api/library/locate",
            params={"book_id": "acupuncture-pdf", "page_no": 39, "q": "中府"},
        )
        self.assertEqual(zf.status_code, 200)
        zfb = zf.json()
        self.assertEqual(zfb["resolved_book_id"], "ni-acupuncture-v2-20100703")
        zf_active = next(p for p in zfb["pages"] if p["page_no"] == zfb["resolved_page_no"])
        self.assertIn("中府", zf_active["body_text"])
        self.assertGreaterEqual(len(zfb.get("chapters", [])), 5)
        self.assertTrue(zfb.get("matched_pages"))

        # 3c. Blank-page / cover-page skip for 2-char herb query
        bc = self.client.get(
            "/api/library/locate",
            params={"book_id": "ni-bencao-pdf", "page_no": 2, "q": "甘草"},
        )
        self.assertEqual(bc.status_code, 200)
        bcb = bc.json()
        self.assertEqual(bcb["resolved_book_id"], "ni-bencao-pdf")
        bc_active = next(p for p in bcb["pages"] if p["page_no"] == bcb["resolved_page_no"])
        self.assertIn("甘草", bc_active["body_text"])

        # 3d. Section/clause book_hint + page_no fallback (e.g. 太阳病条文 p.17 项背强几几 & unrecognized hint)
        xb = self.client.get(
            "/api/library/locate",
            params={"book_hint": "太阳病条文", "page_no": 17, "q": "项背强几几"},
        )
        self.assertEqual(xb.status_code, 200)
        xbb = xb.json()
        self.assertEqual(xbb["resolved_book_id"], "ni-shanghan-pdf")
        self.assertEqual(xbb["resolved_page_no"], 17)
        xb_active = next(p for p in xbb["pages"] if p["page_no"] == 17)
        self.assertIn("项背强几几", xb_active["body_text"])

        xb_raw = self.client.get(
            "/api/library/locate",
            params={"book_hint": "未命名章节提示", "page_no": 17, "q": "项背强几几"},
        )
        self.assertEqual(xb_raw.status_code, 200)
        self.assertEqual(xb_raw.json()["resolved_book_id"], "ni-shanghan-pdf")
        self.assertEqual(xb_raw.json()["resolved_page_no"], 17)

        # 4. 404 when neither book nor quote exists
        miss = self.client.get("/api/library/locate", params={"q": "不存在的故事测试词8899"})
        self.assertEqual(miss.status_code, 404)

        # 5. HTML, CSS & JS context drawer + clickable index + locator hooks across all modules
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        for token in ("ctx-drawer-backdrop", "ctx-reader-drawer"):
            self.assertIn(token, html)

        css = (ROOT / "web" / "style.css").read_text(encoding="utf-8")
        self.assertIn("grid-template-rows: minmax(0, 1fr);", css)
        self.assertIn(".workspace.lib-workspace", css)

        lib_js = (ROOT / "web" / "library_stage5.js").read_text(encoding="utf-8")
        for token in (
            "/api/library/locate",
            "openContextDrawer",
            "jumpCtxToPage",
            "searchInsideCtxBook",
            "ctx-index-pane",
            "ctx-toggle-index",
            "#bc-detail",
            "#nj-detail",
            "#six-detail",
            "data-ctx-loc",
        ):
            self.assertIn(token, lib_js)

        for mod_file in ("app.js", "bencao.js", "neijing.js", "acupuncture.js", "formulas_stage4.js"):
            src = (ROOT / "web" / mod_file).read_text(encoding="utf-8")
            self.assertIn("data-ctx-loc", src, f"Missing data-ctx-loc in {mod_file}")


if __name__ == "__main__":
    unittest.main()
