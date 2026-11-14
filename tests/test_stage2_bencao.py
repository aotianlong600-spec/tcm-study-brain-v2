import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from etl.bencao.validate import run_validation


ROOT = Path(__file__).resolve().parent.parent


class Stage2BencaoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_etl_validator_passes_with_zero_errors(self) -> None:
        report = run_validation()
        self.assertTrue(report["valid"], msg=f"Validation errors: {report['errors']}")
        self.assertEqual(report["error_count"], 0)
        stats = report["stats"]
        self.assertEqual(stats["pages"], 154)
        self.assertEqual(stats["entries"], 385)
        self.assertEqual(stats["main"], 357)
        self.assertEqual(stats["ch3"], 28)
        self.assertEqual(stats["curated_deep"], 78)
        self.assertEqual(stats["comparisons"], 38)
        self.assertGreaterEqual(stats["entries_with_formulas"], 140)
        self.assertGreaterEqual(stats["emergency_or_high_risk"], 100)

    def test_overview_preserves_legacy_351_while_exposing_stage2_385_complete(self) -> None:
        ov_resp = self.client.get("/api/overview")
        self.assertEqual(ov_resp.status_code, 200)
        ov = ov_resp.json()
        # Preserve Stage 4 / Stage 1 invariants
        self.assertEqual(ov["herbs"], 351)
        self.assertEqual(ov["modules"]["herbs"], "complete")
        bc = ov["bencao_summary"]
        self.assertEqual(bc["edition_total"], 385)
        self.assertEqual(bc["main_classic_total"], 357)
        self.assertEqual(bc["chapter3_supplement_count"], 28)
        self.assertEqual(bc["newly_recovered_count"], 34)
        self.assertEqual(bc["comparisons_count"], 38)

        bc_ov = self.client.get("/api/bencao/overview")
        self.assertEqual(bc_ov.status_code, 200)
        self.assertEqual(bc_ov.json()["total_pdf_pages"], 154)
        self.assertEqual(bc_ov.json()["blank_pdf_pages"], [2, 3])
        self.assertEqual(len(bc_ov.json()["prompt_chips"]), 8)

    def test_recovered_6_main_and_28_ch3_entries_are_discoverable(self) -> None:
        resp = self.client.get("/api/bencao/entries", params={"recovered_only": "true", "page_size": 50})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total"], 34)
        names = {item["name"] for item in data["items"]}
        for recovered_main in ("青石赤石黄石白石黑石脂等", "赤芝黑芝青芝白芝黄芝紫芝", "榆皮", "蟹", "大豆黄卷", "粉钖"):
            self.assertIn(recovered_main, names)

        ch3_resp = self.client.get("/api/bencao/entries", params={"grade": "增补经方药", "page_size": 50})
        self.assertEqual(ch3_resp.status_code, 200)
        self.assertEqual(ch3_resp.json()["total"], 28)

        # Verify 白芷 coexists in main classic AND ch3 without collision
        main_bz = self.client.get("/api/bencao/entries/bencao:白芷")
        ch3_bz = self.client.get("/api/bencao/entries/bencao:ch3-白芷")
        self.assertEqual(main_bz.status_code, 200)
        self.assertEqual(ch3_bz.status_code, 200)
        self.assertEqual(main_bz.json()["kind"], "main")
        self.assertEqual(ch3_bz.json()["kind"], "ch3")
        self.assertTrue(main_bz.json()["classic_original"]["in_shennong_classic"])
        self.assertFalse(ch3_bz.json()["classic_original"]["in_shennong_classic"])

    def test_strict_layer_separation_and_open_questions_unfabricated(self) -> None:
        ch3_douchi = self.client.get("/api/bencao/entries/bencao:ch3-豆豉").json()
        self.assertFalse(ch3_douchi["classic_original"]["in_shennong_classic"])
        self.assertIn("第三章", ch3_douchi["classic_original"]["text"])
        self.assertTrue(ch3_douchi["ni_haixia_annotations"]["chapter3_pithy_summary"] or ch3_douchi["ni_haixia_annotations"]["why_it_works"])

        # Open question preserved on ch3-蒴翟细叶 without fabrication
        sz = self.client.get("/api/bencao/entries/bencao:ch3-蒴翟细叶").json()
        self.assertTrue(sz["open_questions"])
        self.assertIn("现无资料可查", sz["open_questions"][0])

        # Classic-only unannotated items retain open_questions
        classic_only = self.client.get("/api/bencao/entries", params={"review_status": "classic_only", "page_size": 10}).json()
        self.assertGreaterEqual(classic_only["total"], 75)
        sample = self.client.get(f"/api/bencao/entries/{classic_only['items'][0]['id']}").json()
        self.assertTrue(sample["open_questions"])
        self.assertTrue(sample["classic_original"]["in_shennong_classic"])

    def test_controversies_not_merged_and_high_risk_flags_preserved(self) -> None:
        fenxi = self.client.get("/api/bencao/entries/bencao:粉钖").json()
        self.assertTrue(fenxi["identity_controversies"])
        topics = " ".join(c["topic"] + c["summary"] for c in fenxi["identity_controversies"])
        self.assertIn("白粉", topics)
        self.assertEqual(fenxi["properties"]["risk_level"], "emergency")

        fuzi = self.client.get("/api/bencao/entries/bencao:附子").json()
        self.assertEqual(fuzi["properties"]["risk_level"], "emergency")
        self.assertTrue(fuzi["comparisons_detailed"])
        self.assertTrue(fuzi["formula_usages"])

    def test_chapters_general_theory_and_38_comparisons(self) -> None:
        chaps = self.client.get("/api/bencao/chapters").json()
        self.assertEqual(chaps["total"], 8)

        gen = self.client.get("/api/bencao/chapters/ch2-general").json()
        self.assertEqual(len(gen["rules"]), 13)

        upper = self.client.get("/api/bencao/chapters/juan1-upper").json()
        self.assertEqual(upper["entry_count"], 142)

        comps = self.client.get("/api/bencao/comparisons").json()
        self.assertEqual(comps["total"], 38)
        one_comp = self.client.get("/api/bencao/comparisons/comp-guizhi-rougui")
        self.assertEqual(one_comp.status_code, 200)
        self.assertGreaterEqual(len(one_comp.json()["herbs_meta"]), 2)

    def test_diagnose_endpoint_and_source_page_images(self) -> None:
        diag_warm = self.client.get("/api/bencao/diagnose", params={"q": "心中懊憹 失眠烦躁"}).json()
        self.assertGreaterEqual(diag_warm["total"], 3)
        top_names = [it["name"] for it in diag_warm["items"][:5]]
        self.assertTrue(any(n in top_names for n in ("栀子", "黄连", "豆豉")))
        self.assertTrue(diag_warm["items"][0]["why_recommended"])

        diag_cold = self.client.get("/api/bencao/diagnose", params={"q": "四肢厥逆 脉微欲绝 里寒"}).json()
        self.assertTrue(diag_cold["safety_alerts"])
        self.assertTrue(diag_cold["related_comparisons"])

        pages = self.client.get("/api/bencao/pages", params={"q": "神农本草经"}).json()
        self.assertGreaterEqual(pages["total"], 1)

        pg19 = self.client.get("/api/bencao/source-pages/19").json()
        self.assertEqual(pg19["pdf_page"], 19)
        self.assertIn("text_sha256", pg19)
        self.assertTrue(pg19["linked_herbs"])

        img_resp = self.client.get("/api/bencao/source-pages/19/image")
        self.assertEqual(img_resp.status_code, 200)
        self.assertEqual(img_resp.headers["content-type"], "image/png")
        self.assertTrue(img_resp.content.startswith(b"\x89PNG"))

    def test_bidirectional_formula_herb_links_with_dose_and_processing(self) -> None:
        # Formula -> Herb
        gz_formula = self.client.get("/api/formulas/shanghan:桂枝汤").json()
        ing_map = {ing["name"]: ing for ing in gz_formula["ingredients"]}
        self.assertEqual(ing_map["桂枝"]["herb_id"], "bencao:牡桂")
        self.assertIn("herb_controversy", ing_map["桂枝"])

        zhizi_formula = self.client.get("/api/formulas/shanghan:栀子豉汤").json()
        zz_map = {ing["name"]: ing for ing in zhizi_formula["ingredients"]}
        self.assertEqual(zz_map["豆豉"]["herb_id"], "bencao:ch3-豆豉")

        # Herb -> Formula with exact dose/processing
        douchi = self.client.get("/api/bencao/entries/bencao:ch3-豆豉").json()
        dc_fids = {u["formula_id"]: u for u in douchi["formula_usages"]}
        self.assertIn("shanghan:栀子豉汤", dc_fids)
        self.assertEqual(dc_fids["shanghan:栀子豉汤"]["dose"], "四合")

        shizhi = self.client.get("/api/bencao/entries/bencao:青石赤石黄石白石黑石脂等").json()
        sz_fids = {u["formula_id"] for u in shizhi["formula_usages"]}
        self.assertIn("shanghan:赤石脂禹余粮汤", sz_fids)
        self.assertIn("shanghan:桃花汤", sz_fids)

        zaoxintu = self.client.get("/api/bencao/entries/bencao:ch3-灶心土").json()
        self.assertIn("jinkui:黄土汤", {u["formula_id"] for u in zaoxintu["formula_usages"]})

        yitang = self.client.get("/api/bencao/entries/bencao:ch3-饴糖").json()
        self.assertIn("shanghan:小建中汤", {u["formula_id"] for u in yitang["formula_usages"]})

        # Legacy /api/herbs endpoint backward-compatibility for recovered items
        legacy_douchi = self.client.get("/api/herbs/bencao:ch3-豆豉")
        self.assertEqual(legacy_douchi.status_code, 200)
        self.assertIn("bencao_entry", legacy_douchi.json())

    def test_stage2_ui_wiring_present_and_legacy_selectors_guarded(self) -> None:
        index_html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        bencao_js = (ROOT / "web" / "bencao.js").read_text(encoding="utf-8")

        self.assertIn('<script src="/bencao.js"></script>', index_html)
        for dom_id in ('id="herbs-view"', 'id="bc-dim-switch"', 'id="bc-list"', 'id="bc-detail"', 'id="bc-honesty-note"'):
            self.assertIn(dom_id, index_html)
        self.assertIn("window.bencaoUI", app_js)
        self.assertNotIn('$("#herb-query").addEventListener', app_js)
        self.assertNotIn('$("#herb-list").addEventListener', app_js)
        for dim in ('"diagnose"', '"catalog"', '"theory"', '"comparisons"', '"pages"'):
            self.assertIn(dim, bencao_js)
        self.assertIn("/api/bencao/source-pages/", bencao_js)


if __name__ == "__main__":
    unittest.main()
