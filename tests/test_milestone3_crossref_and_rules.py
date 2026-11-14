"""Milestone 3 regression tests: cross-school prose precision, TOC isolation, 90 atoms, 16 anchored redlines."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from fastapi.testclient import TestClient

from app.formula_diagnose import diagnose_formulas
from app.main import app
from app.static_dispatch import dispatch_json
from app.syndrome_composer import PATTERN_ATOMS, compose_differentiation
from app.syndrome_rules import REDLINE_ANCHOR_SPECS, resolve_redline_anchors
from etl.library.validate import validate_all
from retrieval.index import is_toc_or_frontmatter, search_library_pages


ROOT = Path(__file__).resolve().parents[1]
VALID_POLARITIES = {
    "yang_def_cold",
    "heat_excess",
    "warm_exterior",
    "yin_def_heat",
    "half_interior",
    "blood_stasis",
    "balanced",
}


class Milestone3CrossrefAndRulesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_search_downranks_toc_and_frontmatter(self) -> None:
        hits = search_library_pages("桂枝汤", limit=8)["items"]
        self.assertGreaterEqual(len(hits), 5)
        for h in hits[:4]:
            self.assertFalse(
                is_toc_or_frontmatter(h.get("section_title", ""), h.get("body_text", "")),
                f"Top search hit should be prose, not TOC/editorial: {h['book_id']} p.{h['page_no']} ({h.get('section_title')})",
            )

        explicit_toc = search_library_pages("伤寒类方 目录", book_id="xu-lingtai-collection-pdf", limit=5)["items"]
        self.assertTrue(any("目录" in (h.get("section_title") or "") for h in explicit_toc))

    def test_cross_links_multi_school_diversity_and_no_toc(self) -> None:
        cross = json.loads((ROOT / "data" / "library" / "cross_links.json").read_text(encoding="utf-8"))
        entity_refs = cross["entity_refs"]

        # Cache page lookup only for referenced books
        book_pages: dict[str, dict[int, dict]] = {}

        def _get_page(bid: str, pno: int) -> dict:
            if bid not in book_pages:
                path = ROOT / "sources" / "library" / f"{bid}.jsonl"
                book_pages[bid] = {
                    int(r["page_no"]): r
                    for r in (json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip())
                }
            return book_pages[bid][int(pno)]

        for eid in ("bencao:人参", "shanghan:桂枝汤", "shanghan:小柴胡汤"):
            refs = entity_refs.get(eid, [])
            self.assertGreaterEqual(len(refs), 8, f"Expected broad cross-school refs for {eid}")
            top10 = refs[:10]
            shelves = {r["shelf"] for r in top10}
            books = {r["book_id"] for r in top10}
            self.assertGreaterEqual(len(shelves), 2, f"Expected multi-shelf diversity in top10 of {eid}: {books}")
            self.assertGreaterEqual(len(books), 6, f"Expected >=6 distinct books in top10 of {eid}: {books}")
            for r in refs:
                row = _get_page(r["book_id"], r["page_no"])
                self.assertEqual(r["text_sha256"], row["text_sha256"])
                self.assertFalse(
                    is_toc_or_frontmatter(row.get("section_title", ""), row.get("body_text", "")),
                    f"TOC/frontmatter polluted entity_refs[{eid}]: {r['book_id']} p.{r['page_no']}",
                )
                self.assertTrue(r["snippet"].strip())

        guizhi_xu = [r for r in entity_refs["shanghan:桂枝汤"] if r["book_id"] == "xu-lingtai-collection-pdf"]
        self.assertTrue(guizhi_xu)
        self.assertNotIn(guizhi_xu[0]["page_no"], {179, 227, 228})

    def test_31_clusters_and_clean_library_refs(self) -> None:
        v = validate_all()
        self.assertTrue(v["valid"], v["errors"])
        self.assertEqual(v["syndromes"], 31)

        clusters = json.loads((ROOT / "data" / "relations" / "syndrome_clusters.json").read_text(encoding="utf-8"))["items"]
        by_id = {c["id"]: c for c in clusters}
        for new_id in (
            "syndrome:waihan-neihan-chuanzheng",
            "syndrome:baihe-yuhuo-xiehe",
            "syndrome:wuhan-shigao-jixu",
        ):
            self.assertIn(new_id, by_id)
            self.assertGreaterEqual(len(by_id[new_id]["library_refs"]), 3)

        waijing_books = {r["book_id"] for r in by_id["syndrome:waijing-mingmen-wuyu"]["library_refs"]}
        self.assertIn("huangdi-waijing-pdf", waijing_books)

        for c in clusters:
            for ref in c["library_refs"]:
                self.assertNotIn("目录", ref.get("section_title", ""), f"Cluster {c['id']} cited TOC: {ref}")

    def test_stage4_diagnose_fixes_and_alerts(self) -> None:
        night_sweat = diagnose_formulas("骨蒸盗汗 咳嗽 手掌烦热")
        self.assertNotIn("有汗（自汗/恶风/桂枝汤类趋势）", night_sweat.get("query_signals", []))

        shigao_warn = diagnose_formulas("高热 大渴 无汗")
        self.assertTrue(any("石膏" in a for a in shigao_warn["safety_alerts"]))

        xuchuan_warn = diagnose_formulas("虚喘 短气 不抬肩")
        self.assertTrue(any("不抬肩" in a for a in xuchuan_warn["safety_alerts"]))

    def test_90_atoms_and_new_differential_redlines(self) -> None:
        self.assertGreaterEqual(len(PATTERN_ATOMS), 90)
        for atom in PATTERN_ATOMS:
            self.assertIn(atom.get("polarity"), VALID_POLARITIES)

        # Redline 13: 大渴无汗禁单用白虎石膏
        res_sg = compose_differentiation("高热 大渴 无汗 恶寒", "浮 紧")
        sg_cands = {c["name"] for c in res_sg["candidate_formulas"]}
        sg_excl = {e["name"] for e in res_sg["excluded_pitfalls"]}
        self.assertNotIn("白虎汤", sg_cands)
        self.assertIn("白虎汤", sg_excl)
        self.assertIn("redline:wuhan-shigao-jixu", {r["id"] for r in res_sg["classical_redlines"]})

        # Redline 14: 背恶寒 口中和(附子汤) vs 口燥渴(白虎加人参汤)
        cold_back = compose_differentiation("背恶寒 口中和 身痛 脚冷", "沉 微细")
        self.assertEqual(cold_back["candidate_formulas"][0]["name"], "附子汤")
        self.assertNotIn("白虎汤", {c["name"] for c in cold_back["candidate_formulas"]})
        self.assertIn("白虎加人参汤", {e["name"] for e in cold_back["excluded_pitfalls"]})
        self.assertIn("redline:beiehan-kouzhonghe", {r["id"] for r in cold_back["classical_redlines"]})

        hot_back = compose_differentiation("背恶寒 口渴 大汗 发热", "洪大")
        self.assertEqual(hot_back["candidate_formulas"][0]["name"], "白虎加人参汤")
        self.assertIn("附子汤", {e["name"] for e in hot_back["excluded_pitfalls"]})

        # Redline 15: 阴黄 vs 女劳黑瘅
        yin_jaundice = compose_differentiation("黄疸 身冷 便溏", "迟 微细")
        self.assertIn("茵陈五苓散", {c["name"] for c in yin_jaundice["candidate_formulas"][:3]})
        self.assertNotIn("大承气汤", {c["name"] for c in yin_jaundice["candidate_formulas"]})
        self.assertIn("茵陈蒿汤", {e["name"] for e in yin_jaundice["excluded_pitfalls"]})
        self.assertIn("redline:hanhua-huangdan", {r["id"] for r in yin_jaundice["classical_redlines"]})

        # Redline 16: 远血(先便后血->黄土汤) vs 近血(先血后便->赤豆当归散)
        far_blood = compose_differentiation("先便后血 身冷 眩晕", "沉 微细")
        self.assertEqual(far_blood["candidate_formulas"][0]["name"], "黄土汤")
        self.assertIn("redline:yuxue-farre-yuanjin", {r["id"] for r in far_blood["classical_redlines"]})

        near_blood = compose_differentiation("先血后便 尿赤", "数")
        near_top = {c["name"] for c in near_blood["candidate_formulas"][:2]}
        self.assertIn("赤豆当归散", near_top)
        near_reds = {r["id"] for r in near_blood["classical_redlines"]}
        self.assertIn("redline:yuxue-farre-yuanjin", near_reds)
        self.assertNotIn("redline:yin-xulao-tuxue", near_reds)

        # Redline 12: 实喘抬肩 vs 虚喘短气不抬肩
        def_asthma = compose_differentiation("虚喘 短气 不抬肩 身冷", "微细 沉")
        self.assertEqual(def_asthma["candidate_formulas"][0]["name"], "甘草干姜汤")
        self.assertIn("麻黄汤", {e["name"] for e in def_asthma["excluded_pitfalls"]})
        self.assertIn("redline:xuchuan-bomen", {r["id"] for r in def_asthma["classical_redlines"]})

        shi_asthma = compose_differentiation("喘 短气 抬肩 痰鸣 身冷", "沉 紧")
        self.assertTrue({"射干麻黄汤", "小青龙汤"}.issubset({c["name"] for c in shi_asthma["candidate_formulas"][:3]}))
        self.assertIn("redline:xuchuan-bomen", {r["id"] for r in shi_asthma["classical_redlines"]})

    def test_all_16_redline_anchors_and_otsuka_fidelity(self) -> None:
        self.assertGreaterEqual(len(REDLINE_ANCHOR_SPECS), 16)
        page_cache: dict[str, dict[int, dict]] = {}
        for rid in REDLINE_ANCHOR_SPECS:
            anchors = resolve_redline_anchors(rid)
            self.assertGreaterEqual(len(anchors), 1, f"Redline {rid} missing resolved source_anchors")
            for a in anchors:
                bid = a["book_id"]
                if bid not in page_cache:
                    path = ROOT / "sources" / "library" / f"{bid}.jsonl"
                    page_cache[bid] = {
                        int(r["page_no"]): r
                        for r in (json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip())
                    }
                row = page_cache[bid][int(a["page_no"])]
                self.assertEqual(a["text_sha256"], row["text_sha256"])
                self.assertFalse(is_toc_or_frontmatter(row.get("section_title", ""), row.get("body_text", "")))

        zangjie = compose_differentiation("心下硬痛 舌白厚湿 饮食如故 不渴", "沉 紧")
        zj_rl = next(r for r in zangjie["classical_redlines"] if r["id"] == "redline:zangjie-jinxia")
        self.assertNotIn("大冢", zj_rl["schools_crossref"])
        self.assertTrue(zj_rl["source_anchors"])

    def test_static_dispatch_and_frontend_contract(self) -> None:
        for url in (
            "/api/stage5/compose?q=%E9%AB%98%E7%83%AD+%E5%A4%A7%E6%B8%B4+%E6%97%A0%E6%B1%97&pulse=%E6%B5%AE+%E7%B4%A7",
            "/api/library/entity-links/bencao%3A%E4%BA%BA%E5%8F%82",
            "/api/stage5/syndromes",
        ):
            api_res = self.client.get(url)
            self.assertEqual(api_res.status_code, 200, url)
            static_env = json.loads(dispatch_json(url))
            self.assertEqual(static_env["status"], 200, url)
            self.assertEqual(static_env["body"], api_res.json(), url)

        js = (ROOT / "web" / "library_stage5.js").read_text(encoding="utf-8")
        self.assertIn("source_anchors", js)
        self.assertIn("s5-redline-anchors", js)
        self.assertIn("XREF_SHELF_BADGES", js)
        self.assertIn(".slice(0, 10)", js)
        css = (ROOT / "web" / "style.css").read_text(encoding="utf-8")
        self.assertIn(".s5-redline-anchors", css)
        self.assertIn(".lib-xref-badge", css)


if __name__ == "__main__":
    unittest.main()
