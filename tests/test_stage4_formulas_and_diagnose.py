import json
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


ROOT = Path(__file__).resolve().parent.parent


class Stage4FormulasAndDiagnoseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_ui_no_unannotated_processing_placeholder_and_decoction_follows_composition(self) -> None:
        app_js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        stage4_js = (ROOT / "web" / "formulas_stage4.js").read_text(encoding="utf-8")
        index_html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")

        self.assertNotIn("未注炮制", app_js)
        self.assertNotIn("未注炮制", stage4_js)
        self.assertIn('/formulas_stage4.js', index_html)
        self.assertIn('id="s4-mode-strip"', index_html)
        self.assertIn('id="s4-left-host"', index_html)

        # Verify layout order inside renderCuratedFormulaDetail
        curated_start = app_js.index("function renderCuratedFormulaDetail")
        curated_end = app_js.index("function renderSourceModal") if "function renderSourceModal" in app_js else app_js.index("function renderFormulaDetail")
        curated_block = app_js[curated_start:curated_end]
        pos_comp = curated_block.index("1. 药物与剂量")
        pos_dec = curated_block.index("2. 熬煮法与煎服规范")
        pos_symp = curated_block.index("3. 相关症状与辨证线索")
        pos_over = curated_block.index("overview-block")
        pos_mod = curated_block.index("renderModificationsSection(item)")
        self.assertLess(pos_comp, pos_dec)
        self.assertLess(pos_dec, pos_symp)
        self.assertLess(pos_symp, pos_over)
        self.assertLess(pos_over, pos_mod)

        # Verify layout order inside renderFormulaDetail
        detail_start = app_js.index("function renderFormulaDetail")
        detail_end = app_js.index("function renderHerbDetail")
        detail_block = app_js[detail_start:detail_end]
        d_comp = detail_block.index("1. 药物与剂量 · 原文组成")
        d_dec = detail_block.index("2. 熬煮法与煎服")
        d_why = detail_block.index("3. 为什么用 · 方义与主治")
        d_mod = detail_block.index("renderModificationsSection(item)")
        self.assertLess(d_comp, d_dec)
        self.assertLess(d_dec, d_why)
        self.assertLess(d_why, d_mod)

    def test_overview_keeps_prior_module_gates_and_reports_stage4_complete(self) -> None:
        resp = self.client.get("/api/overview")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["modules"]["acupuncture"], "complete")
        self.assertEqual(data["modules"]["neijing"], "partial")
        self.assertEqual(data["modules"]["six_channels"], "complete")
        self.assertEqual(data["modules"]["jinkui"], "complete")
        self.assertEqual(data["modules"]["diagnosis"], "ready")
        self.assertEqual(data["formula_summary"]["formula_count"], 299)
        self.assertEqual(data["formula_summary"]["reviewed_count"], 299)
        self.assertEqual(data["formula_summary"]["jinkui_chapters_count"], 20)
        self.assertEqual(data["formula_summary"]["modifications_count"], 108)
        self.assertEqual(data["formula_summary"]["variants_count"], 42)
        self.assertEqual(data["formula_summary"]["acupuncture_links_count"], 27)

    def test_diagnose_route_works_and_discriminates_syndromes(self) -> None:
        cases = [
            ("心烦喜呕 往来寒热", ["shanghan:小柴胡汤"]),
            ("项背强几几 无汗", ["shanghan:葛根汤"]),
            ("少腹肿痞", ["jinkui:大黄牡丹汤"]),
            ("热入血室", ["shanghan:小柴胡汤"]),
            ("寒多不用水", ["shanghan:理中丸", "jinkui:理中丸"]),
            ("下血 先便后血", ["jinkui:黄土汤"]),
        ]
        for query, expected_top_ids in cases:
            resp = self.client.get("/api/formulas/diagnose", params={"q": query})
            self.assertEqual(resp.status_code, 200, msg=f"query={query}")
            payload = resp.json()
            ids = [row["id"] for row in payload["matched_formulas"]]
            self.assertTrue(ids, msg=f"No formulas matched for {query}")
            self.assertIn(ids[0], expected_top_ids, msg=f"query={query} got top={ids[:3]}")

        # Sweating polarity discrimination: 项背强几几 有汗 vs 无汗
        sweat = self.client.get("/api/formulas/diagnose", params={"q": "项背强几几 有汗"}).json()
        sweat_top2 = [row["id"] for row in sweat["matched_formulas"][:2]]
        self.assertTrue(
            any(fid in sweat_top2 for fid in ("jinkui:栝篓桂枝汤", "shanghan:桂枝加葛根汤")),
            msg=f"Expected sweating formula in top 2, got {sweat_top2}",
        )

        # Chest painful obstruction
        xiongbi = self.client.get("/api/formulas/diagnose", params={"q": "胸痹 短气"}).json()
        xb_top4 = [row["id"] for row in xiongbi["matched_formulas"][:4]]
        self.assertIn("jinkui:栝蒌薤白白酒汤", xb_top4)

        # Acute appendicitis triggers safety alert
        appendicitis = self.client.get("/api/formulas/diagnose", params={"q": "少腹肿痞"}).json()
        self.assertTrue(appendicitis["safety_alerts"])

    def test_jinkui_chapters_six_channels_modifications_variants_and_acup_links(self) -> None:
        jk = self.client.get("/api/jinkui-chapters")
        self.assertEqual(jk.status_code, 200)
        jk_data = jk.json()
        self.assertEqual(jk_data["total"], 20)
        self.assertEqual(len(jk_data["items"]), 20)
        self.assertEqual(sum(ch["formula_count"] for ch in jk_data["items"]), 186)

        jk18 = self.client.get("/api/jinkui-chapters/jk-ch-18")
        self.assertEqual(jk18.status_code, 200)
        self.assertTrue(jk18.json()["formulas"])

        mods = self.client.get("/api/formula-modifications")
        self.assertEqual(mods.status_code, 200)
        self.assertEqual(mods.json()["total"], 108)

        variants = self.client.get("/api/formula-variants")
        self.assertEqual(variants.status_code, 200)
        vdata = variants.json()
        self.assertEqual(vdata["total"], 42)
        self.assertEqual(vdata["exact_same_count"], 15)
        self.assertEqual(vdata["diff_count"], 27)

        acups = self.client.get("/api/formula-acupuncture-links")
        self.assertEqual(acups.status_code, 200)
        self.assertEqual(acups.json()["total"], 27)

        # Enriched formula detail includes cross-book variant & acupuncture links
        lizhong = self.client.get("/api/formulas/shanghan:理中丸")
        self.assertEqual(lizhong.status_code, 200)
        lz_data = lizhong.json()
        self.assertIsNotNone(lz_data["cross_book_variant"])
        self.assertEqual(lz_data["cross_book_variant"]["peer_formula"]["id"], "jinkui:理中丸")

        xch = self.client.get("/api/formulas/shanghan:小柴胡汤").json()
        self.assertTrue(xch["modifications"]["as_base"])
        self.assertTrue(xch["acupuncture_relations"])

    def test_formula_modules_all_299_reviewed(self) -> None:
        modules = json.loads((ROOT / "data" / "formula_modules.json").read_text(encoding="utf-8"))
        self.assertEqual(len(modules), 299)
        reviewed = sum(1 for row in modules.values() if row.get("review_status") == "reviewed")
        self.assertEqual(reviewed, 299)


if __name__ == "__main__":
    unittest.main()
