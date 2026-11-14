"""Regression tests for Milestone 4 Route A optimizations and Stage 5 parity."""

from __future__ import annotations

import json
from pathlib import Path
import unittest
from urllib.parse import quote

from fastapi.testclient import TestClient

from ai.grounded_study import ground_study_query
from app.formula_diagnose import SYNONYM_GROUPS as DIAGNOSE_SYNONYM_GROUPS
from app.main import app
from app.static_dispatch import dispatch_json
from app.syndrome_composer import PATTERN_ATOMS, compose_differentiation
from app.syndrome_rules import are_formulas_redundant_siblings
from retrieval.index import search_all_knowledge, search_library_pages
from retrieval.tcm_synonyms import (
    FORMULA_SYNONYM_GROUPS,
    expand_clinical_synonyms,
    expand_ortho_variants,
)


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


class Milestone4RouteATest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_shared_synonyms_and_classical_orthographic_expansion(self) -> None:
        self.assertIs(DIAGNOSE_SYNONYM_GROUPS, FORMULA_SYNONYM_GROUPS)
        self.assertIn("四逆汤", expand_ortho_variants("回逆汤"))
        self.assertIn("真武汤", expand_ortho_variants("玄武汤"))
        self.assertIn("桅子大黄汤", expand_ortho_variants("栀子大黄汤"))
        self.assertIn("黄耆建中汤", expand_ortho_variants("黄芪建中汤"))

        syns = expand_clinical_synonyms(["拉肚子"])
        flat = {tok for grp in syns for tok in grp}
        self.assertTrue({"拉肚子", "腹泻", "下利"} <= flat)

    def test_library_multistage_retrieval_bencao_and_hantang_indexing(self) -> None:
        huini = search_library_pages("回逆汤")
        self.assertTrue(huini.get("items"), "回逆汤 should expand to 四逆汤 library pages")

        xuanwu = search_library_pages("玄武汤")
        self.assertTrue(xuanwu.get("items"), "玄武汤 should expand to 真武汤 library pages")

        diarrhea = search_library_pages("拉肚子")
        self.assertTrue(diarrhea.get("items"), "拉肚子 should retrieve 下利/泄泻 pages via Stage-2 synonyms")

        plum_pit = search_library_pages("梅核气")
        self.assertTrue(plum_pit.get("items"), "梅核气 should retrieve classical pages")

        missing = search_library_pages("不存在的故事测试词8899")
        self.assertEqual(missing.get("total", 0), 0)
        self.assertEqual(missing.get("items", []), [])

        ht_hits = search_all_knowledge("白带丸", limit=12)
        self.assertTrue(any(h.get("module") == "hantang" for h in ht_hits))

        bc_hits = search_all_knowledge("麻黄", limit=12)
        bc_mahuang = next((h for h in bc_hits if h.get("entity_id") == "bencao:麻黄"), None)
        self.assertIsNotNone(bc_mahuang)
        self.assertTrue(bc_mahuang.get("summary"), "Bencao structured entity should have non-empty summary")

    def test_context_aware_herb_cross_links_rescued(self) -> None:
        cross = json.loads((ROOT / "data" / "library" / "cross_links.json").read_text(encoding="utf-8"))
        entities = cross.get("entity_refs", {})
        for eid in ("bencao:甘草", "bencao:大枣", "bencao:干姜", "bencao:ch3-小麦"):
            self.assertIn(eid, entities, f"{eid} should be context-linked in cross_links.json")
            self.assertGreaterEqual(len(entities[eid]), 1)

    def test_dynamic_cluster_counts_and_frontend_contract(self) -> None:
        ground = ground_study_query("小柴胡汤")
        layers_txt = json.dumps(ground, ensure_ascii=False)
        for school in ("唐容川", "陈士铎", "徐灵胎", "丹波元珍", "大冢敬节", "汪汝麟", "黄帝外经"):
            self.assertIn(school, layers_txt)

        ground_gap = ground_study_query("不存在证候群边界测试9911")
        gap_txt = json.dumps(ground_gap, ensure_ascii=False)
        self.assertIn("31 大跨书证候群", gap_txt)

        html_src = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="s5-tab-syndromes"', html_src)
        self.assertIn("31 大跨书证候群图谱", html_src)

        js_src = (ROOT / "web" / "library_stage5.js").read_text(encoding="utf-8")
        for needle in (
            "syncSyndromeTabCount",
            "updateSyndromeTabCount",
            "badge-hantang",
            'module === "hantang"',
            "文献缺口边界",
        ):
            self.assertIn(needle, js_src)
        self.assertNotIn("影印未OCR边界", js_src)

    def test_expanded_pattern_atoms_integrity_and_siblings(self) -> None:
        self.assertGreaterEqual(len(PATTERN_ATOMS), 190)

        sh = json.loads((ROOT / "data" / "formulas.json").read_text(encoding="utf-8"))
        jk_raw = json.loads((ROOT / "data" / "jinkui_formulas.json").read_text(encoding="utf-8"))
        jk = jk_raw if isinstance(jk_raw, list) else jk_raw.get("items", jk_raw.get("formulas", []))
        valid_fids = {f["id"] for f in sh + jk}
        valid_ap = {
            a["id"]
            for a in json.loads((ROOT / "data" / "acupuncture" / "acupoints.json").read_text(encoding="utf-8")).get(
                "items", []
            )
        }

        seen_atoms: set[str] = set()
        for atom in PATTERN_ATOMS:
            self.assertNotIn(atom["atom_id"], seen_atoms)
            seen_atoms.add(atom["atom_id"])
            self.assertIn(atom["formula_id"], valid_fids)
            self.assertIn(atom["polarity"], VALID_POLARITIES)
            for pt in atom.get("acupoints", []):
                self.assertIn(pt["id"], valid_ap)

        self.assertTrue(are_formulas_redundant_siblings("shanghan:黄芩汤", "jinkui:黄芩汤"))
        self.assertTrue(are_formulas_redundant_siblings("jinkui:大乌头煎", "jinkui:乌头桂枝汤"))
        self.assertTrue(are_formulas_redundant_siblings("shanghan:半夏泻心汤", "shanghan:生姜泻心汤"))

    def test_expanded_compose_accuracy_and_new_redlines(self) -> None:
        plum = compose_differentiation("梅核气 胸满 咽中如有炙脔", "弦 滑")
        self.assertIn("梅核气", plum["recognized_symptoms"])
        self.assertEqual(plum["candidate_formulas"][0]["name"], "半夏厚朴汤")

        cramp = compose_differentiation("脚挛急 腹痛", "弦")
        self.assertIn("脚挛急", cramp["recognized_symptoms"])
        self.assertEqual(cramp["candidate_formulas"][0]["name"], "芍药甘草汤")

        preg = compose_differentiation("怀孕呕吐 妊娠恶阻 大便干 少腹急结 寒疝", "滑")
        self.assertIn("妊娠恶阻", preg["recognized_symptoms"])
        preg_cands = [c["name"] for c in preg["candidate_formulas"]]
        preg_excl = {e["name"] for e in preg["excluded_pitfalls"]}
        self.assertIn("干姜人参半夏丸", preg_cands[:2])
        self.assertIn("redline:pregnancy-contraindication", {r["id"] for r in preg["classical_redlines"]})
        self.assertTrue({"大承气汤", "抵当汤", "大乌头煎", "大黄甘草汤"}.issubset(preg_excl))
        for bad in ("大承气汤", "大乌头煎", "下瘀血汤", "大黄甘草汤"):
            self.assertNotIn(bad, preg_cands)

        hernia = compose_differentiation("寒疝 绕脐痛 脚冷 身冷", "沉 紧")
        self.assertIn("寒疝腹痛", hernia["recognized_symptoms"])
        h_cands = [c["name"] for c in hernia["candidate_formulas"]]
        h_excl = {e["name"] for e in hernia["excluded_pitfalls"]}
        self.assertIn("大乌头煎", h_cands[:2])
        self.assertIn("redline:hanshan-futong", {r["id"] for r in hernia["classical_redlines"]})
        self.assertIn("大承气汤", h_excl)

    def test_api_and_static_dispatch_parity(self) -> None:
        syn_api = self.client.get("/api/stage5/syndromes").json()
        syn_static = json.loads(dispatch_json("/api/stage5/syndromes"))["body"]
        self.assertEqual(syn_api["total"], 31)
        self.assertEqual(syn_api["total"], syn_static["total"])

        q = quote("梅核气 胸满")
        p = quote("弦 滑")
        cmp_api = self.client.get(f"/api/stage5/compose?q={q}&pulse={p}").json()
        cmp_static = json.loads(dispatch_json(f"/api/stage5/compose?q={q}&pulse={p}"))["body"]
        self.assertEqual(
            [c["formula_id"] for c in cmp_api["candidate_formulas"]],
            [c["formula_id"] for c in cmp_static["candidate_formulas"]],
        )


if __name__ == "__main__":
    unittest.main()
