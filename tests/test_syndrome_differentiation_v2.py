"""Regression tests for multi-school clinical syndrome differentiation rules & safety redlines."""

from __future__ import annotations

from pathlib import Path
import unittest

from fastapi.testclient import TestClient

from app.formula_diagnose import diagnose_formulas
from app.main import app
from app.syndrome_composer import PATTERN_ATOMS, compose_differentiation
from app.syndrome_rules import are_formulas_redundant_siblings


ROOT = Path(__file__).resolve().parents[1]


class SyndromeDifferentiationV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_all_atoms_have_explicit_polarity_and_no_bad_compound_pairs(self) -> None:
        valid_polarities = {
            "yang_def_cold",
            "heat_excess",
            "warm_exterior",
            "yin_def_heat",
            "half_interior",
            "blood_stasis",
            "balanced",
        }
        self.assertGreaterEqual(len(PATTERN_ATOMS), 80)
        for atom in PATTERN_ATOMS:
            pol = atom.get("polarity")
            self.assertIn(pol, valid_polarities, f"Missing/invalid polarity on {atom['atom_id']}: {pol}")

        # Mixed cold + heat edge queries must never produce antagonistic or sibling compound pairs
        for q, p in [
            ("身冷 下利清谷 高热 口渴", "沉 数"),
            ("大热 口渴 喜冷饮", "洪大"),
            ("皮肤干燥 口渴 便溏", "缓"),
        ]:
            res = compose_differentiation(q, p)
            for reg in res["compound_regimens"]:
                fids = reg["formula_ids"]
                if len(fids) == 2:
                    self.assertFalse(
                        are_formulas_redundant_siblings(fids[0], fids[1]),
                        f"Redundant sibling compound formed: {fids}",
                    )

    def test_yin_deficiency_hemoptysis_blocks_sweat_and_jianzhong(self) -> None:
        res = compose_differentiation("吐血 咳嗽 骨蒸 盗汗 手掌烦热", "数 微细")
        syms = set(res["recognized_symptoms"])
        self.assertIn("骨蒸盗汗", syms)
        self.assertIn("失血", syms)
        self.assertNotIn("有汗", syms)

        cand_names = {c["name"] for c in res["candidate_formulas"]}
        excluded_names = {e["name"] for e in res["excluded_pitfalls"]}
        for forbidden in ("麻黄汤", "麻黄杏仁甘草石膏汤", "小建中汤"):
            self.assertNotIn(forbidden, cand_names)
            self.assertIn(forbidden, excluded_names)

        redline_ids = {r["id"] for r in res["classical_redlines"]}
        self.assertIn("redline:yin-xulao-tuxue", redline_ids)
        self.assertTrue(cand_names & {"百合地黄汤", "泻心汤（三黄）", "黄连阿胶汤"})

    def test_menstrual_exterior_locks_xiaochaihu_and_qimen(self) -> None:
        res = compose_differentiation("发热 恶寒 头痛 月经适来 经痛", "浮 弦")
        self.assertEqual(res["candidate_formulas"][0]["name"], "小柴胡汤")
        excluded = {e["name"] for e in res["excluded_pitfalls"]}
        self.assertTrue({"麻黄汤", "桂枝汤", "大承气汤"}.issubset(excluded))
        primary_pts = {p["name"] for p in res["acupoint_protocol"]["primary"]}
        self.assertIn("期门", primary_pts)
        self.assertIn("redline:jingqi-chaihu", {r["id"] for r in res["classical_redlines"]})

    def test_heat_jue_vs_cold_jue_disambiguation(self) -> None:
        hot = compose_differentiation("四肢厥冷 腹痛 脉滑 口渴 小便深黄", "滑 数")
        self.assertIn("热厥", hot["recognized_symptoms"])
        self.assertNotIn("脚冷", hot["recognized_symptoms"])
        hot_top = {c["name"] for c in hot["candidate_formulas"][:3]}
        self.assertTrue(hot_top & {"大承气汤", "白虎汤"})
        hot_excl = {e["name"] for e in hot["excluded_pitfalls"]}
        self.assertIn("真武汤", hot_excl)
        self.assertIn("redline:rejue-vs-hanjue", {r["id"] for r in hot["classical_redlines"]})

        cold = compose_differentiation("身冷 四肢厥冷 下利清谷 脉微细", "微细 沉")
        self.assertIn("脚冷", cold["recognized_symptoms"])
        self.assertNotIn("热厥", cold["recognized_symptoms"])
        self.assertTrue({c["name"] for c in cold["candidate_formulas"][:3]} & {"通脉四逆汤", "四逆汤", "白通汤"})

    def test_daiyang_false_heat_true_cold_blocks_purging(self) -> None:
        res = compose_differentiation("下利清谷 四肢厥冷 面赤如妆 身反不恶寒 脉微细", "微细 沉")
        self.assertEqual(res["candidate_formulas"][0]["name"], "通脉四逆汤")
        excluded = {e["name"] for e in res["excluded_pitfalls"]}
        self.assertIn("白虎加人参汤", excluded)
        self.assertIn("redline:daiyang-geyang", {r["id"] for r in res["classical_redlines"]})

    def test_shaoyin_urgent_purgation_and_first_interior_then_exterior(self) -> None:
        urgent = compose_differentiation("自利清水 口燥咽干 腹胀痛拒按", "微细 沉")
        self.assertIn("自利清水热", urgent["recognized_symptoms"])
        self.assertNotIn("下利清谷", urgent["recognized_symptoms"])
        self.assertEqual(urgent["candidate_formulas"][0]["name"], "大承气汤")
        self.assertTrue({"理中丸", "桃花汤"}.issubset({e["name"] for e in urgent["excluded_pitfalls"]}))
        self.assertIn("redline:shaoyin-jixia", {r["id"] for r in urgent["classical_redlines"]})

        xianli = compose_differentiation("发热 身冷 恶寒 无汗 下利清谷 脉微细", "微细 沉")
        top3 = {c["name"] for c in xianli["candidate_formulas"][:3]}
        self.assertTrue(top3 & {"通脉四逆汤", "四逆汤", "白通汤"})
        excl = {e["name"] for e in xianli["excluded_pitfalls"]}
        self.assertTrue({"麻黄汤", "桂枝汤", "葛根汤"}.issubset(excl))
        self.assertIn("redline:xianli-houbiao", {r["id"] for r in xianli["classical_redlines"]})

    def test_zangjie_emergency_blocks_daxianxiong(self) -> None:
        res = compose_differentiation("心下硬痛 舌白厚湿 饮食如故 不渴", "沉 紧")
        cand_names = {c["name"] for c in res["candidate_formulas"]}
        excluded_names = {e["name"] for e in res["excluded_pitfalls"]}
        self.assertNotIn("大陷胸汤", cand_names)
        self.assertNotIn("小陷胸汤", cand_names)
        self.assertIn("大陷胸汤", excluded_names)
        red = next((r for r in res["classical_redlines"] if r["id"] == "redline:zangjie-jinxia"), None)
        self.assertIsNotNone(red)
        self.assertEqual(red["severity"], "emergency")

    def test_shaoyin_sore_throat_urinary_and_skin_dry_inner_damp(self) -> None:
        throat = compose_differentiation("咽喉肿痛 下利 脉微细", "微细")
        throat_top = {c["name"] for c in throat["candidate_formulas"][:3]}
        self.assertTrue({"半夏散及汤", "猪肤汤"}.issubset(throat_top))
        self.assertIn("redline:shaoyin-yantong", {r["id"] for r in throat["classical_redlines"]})

        urine = compose_differentiation("小便刺痛 尿血 尿黄", "数")
        urine_top = {c["name"] for c in urine["candidate_formulas"][:3]}
        self.assertTrue(urine_top & {"赤豆当归散", "猪苓汤"})
        urine_excl = {e["name"] for e in urine["excluded_pitfalls"]}
        self.assertTrue({"葛根黄芩黄连汤", "白头翁汤"}.issubset(urine_excl))
        urine_reds = {r["id"] for r in urine["classical_redlines"]}
        self.assertIn("redline:relin-niaoxue", urine_reds)
        self.assertNotIn("redline:yin-xulao-tuxue", urine_reds)

        skin = compose_differentiation("皮肤干燥 瘙痒 口渴 便溏", "缓")
        skin_cand = {c["name"] for c in skin["candidate_formulas"]}
        self.assertNotIn("白虎汤", skin_cand)
        self.assertNotIn("白虎加人参汤", skin_cand)
        self.assertIn("redline:skin-dry-inner-damp", {r["id"] for r in skin["classical_redlines"]})

    def test_heart_surgery_blocks_mahuang_and_dyspnea_recognition(self) -> None:
        heart_op = compose_differentiation("心脏术后 恶寒 无汗 身痛", "浮 紧")
        cands = {c["name"] for c in heart_op["candidate_formulas"]}
        excl = {e["name"] for e in heart_op["excluded_pitfalls"]}
        for mh in ("麻黄汤", "葛根汤", "大青龙汤", "小青龙汤"):
            self.assertNotIn(mh, cands)
            self.assertIn(mh, excl)
        self.assertIn("redline:heart-surgery-no-mahuang", {r["id"] for r in heart_op["classical_redlines"]})

        chuan = compose_differentiation("喘 短气 抬肩 痰鸣 身冷", "沉 紧")
        chuan_top = {c["name"] for c in chuan["candidate_formulas"][:3]}
        self.assertTrue({"射干麻黄汤", "小青龙汤"}.issubset(chuan_top))

    def test_formula_diagnose_safety_and_stage5_web_contract(self) -> None:
        head_sweat = diagnose_formulas("但头汗出 身冷 眩晕")
        self.assertNotIn("有汗（自汗/恶风/桂枝汤类趋势）", head_sweat.get("query_signals", []))

        bleed = diagnose_formulas("吐血 骨蒸盗汗")
        self.assertTrue(any("亡血家" in a or "阴虚吐血" in a for a in bleed["safety_alerts"]))

        zangjie = diagnose_formulas("心下硬痛 饮食如故 苔白滑")
        self.assertTrue(any("脏结" in a for a in zangjie["safety_alerts"]))

        api_res = self.client.get("/api/stage5/compose", params={"q": "吐血 骨蒸 盗汗", "pulse": "数 微细"})
        self.assertEqual(api_res.status_code, 200)
        payload = api_res.json()
        self.assertIn("classical_redlines", payload)
        self.assertIn("classical_redlines", payload["ai_ready_case_packet"])
        self.assertGreaterEqual(len(payload["classical_redlines"]), 1)

        syndromes = self.client.get("/api/stage5/syndromes").json()
        self.assertGreaterEqual(syndromes["total"], 26)
        self.assertGreaterEqual(len(syndromes["items"]), 26)

        js = (ROOT / "web" / "library_stage5.js").read_text(encoding="utf-8")
        self.assertIn("classical_redlines", js)
        self.assertIn("s5-redline-section", js)


if __name__ == "__main__":
    unittest.main()
