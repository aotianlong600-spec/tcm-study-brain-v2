import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BATCH_PATH = ROOT / "data" / "curated_batches" / "shanghan_100_106.json"

EXPECTED_FORMULAS = {
    "shanghan:乌梅丸",
    "shanghan:当归四逆汤",
    "shanghan:当归四逆加吴茱萸生姜汤",
    "shanghan:麻黄升麻汤",
    "shanghan:干姜黄连黄芩人参汤",
    "shanghan:白头翁汤",
    "shanghan:四逆加人参汤",
}

REQUIRED_FIELDS = {
    "review_status",
    "review_level",
    "usage_status",
    "usage_plain",
    "why",
    "symptoms",
    "overview",
    "six_channel",
    "formula_original",
    "usage_original",
    "usage_modern",
    "rationale",
    "annotations",
    "page_reading",
    "proofreading",
    "editorial_note",
}


class Shanghan100106BatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modules = json.loads(BATCH_PATH.read_text(encoding="utf-8"))

    def test_exact_formula_set(self):
        self.assertEqual(set(self.modules), EXPECTED_FORMULAS)
        self.assertTrue(all(key.startswith("shanghan:") for key in self.modules))
        self.assertNotIn("shanghan:四逆加人参汤", {"jinkui:四逆加人参汤"})

    def test_complete_module_structure(self):
        for key, module in self.modules.items():
            with self.subTest(formula=key):
                self.assertEqual(set(module), REQUIRED_FIELDS)
                self.assertEqual(module["review_status"], "reviewed")
                self.assertEqual(module["review_level"], "完整")
                self.assertEqual(module["usage_status"], "reviewed")
                self.assertTrue(module["usage_plain"])
                self.assertTrue(module["why"])
                self.assertGreaterEqual(len(module["symptoms"]), 4)
                self.assertGreaterEqual(len(module["overview"]["paragraphs"]), 5)
                self.assertGreaterEqual(len(module["overview"]["key_points"]), 5)
                self.assertGreaterEqual(len(module["rationale"]["full_text"]), 250)
                self.assertGreaterEqual(len(module["annotations"]), 3)
                self.assertGreaterEqual(len(module["proofreading"]), 3)

    def test_six_channel_and_formula_identity(self):
        for key, module in self.modules.items():
            six_channel = module["six_channel"]
            with self.subTest(formula=key):
                self.assertEqual(six_channel["id"], "jueyin")
                self.assertGreaterEqual(len(six_channel["original"]), 3)
                self.assertGreaterEqual(len(six_channel["annotations"]), 3)
                self.assertGreaterEqual(len(six_channel["annotation_original"]), 3)
                self.assertTrue(six_channel["proof_note"])
                self.assertTrue(six_channel["source_pages"])

        sini = self.modules["shanghan:四逆加人参汤"]
        self.assertEqual(sini["six_channel"]["id"], "jueyin")
        self.assertIn("霍乱", sini["six_channel"]["name"])
        self.assertIn("不属于厥阴本证", sini["six_channel"]["summary"])

    def test_doses_and_classical_usage_are_preserved(self):
        expected = {
            "shanghan:乌梅丸": (
                "乌梅（三百枚）",
                "黄连（十六两）",
                "附子（六两炮",
                "苦酒渍乌梅一宿",
                "五斗米下",
                "先食饮服十丸",
                "稍加至二十丸",
            ),
            "shanghan:当归四逆汤": (
                "当归（三两）",
                "细辛（三两）",
                "大枣（二十五枚",
                "以水八升",
                "温服一升",
                "日三服",
            ),
            "shanghan:当归四逆加吴茱萸生姜汤": (
                "吴茱萸（二升）",
                "生姜（半斤",
                "甘草（二两炙）",
                "清酒六升",
                "温分五服",
            ),
            "shanghan:麻黄升麻汤": (
                "麻黄（二两半",
                "升麻（一两一分）",
                "葳蕤（十八铢）",
                "上十四味",
                "先煮麻黄",
                "分温三服",
            ),
            "shanghan:干姜黄连黄芩人参汤": (
                "干姜",
                "黄连",
                "黄芩",
                "人参（各三两）",
                "以水六升",
                "分温再服",
            ),
            "shanghan:白头翁汤": (
                "白头翁（二两）",
                "黄柏（三两）",
                "以水七升",
                "温服一升",
                "不愈更服一升",
            ),
            "shanghan:四逆加人参汤": (
                "甘草（二两炙）",
                "附子（一枚生",
                "干姜（一两半）",
                "人参（一两）",
                "以水三升",
                "分温再服",
            ),
        }
        for key, needles in expected.items():
            module = self.modules[key]
            text = (
                module["formula_original"]["text"]
                + module["usage_original"]["text"]
            )
            with self.subTest(formula=key):
                for needle in needles:
                    self.assertIn(needle, text)

    def test_page_reading_is_direct_and_page_mapped(self):
        expected_pages = {
            "shanghan:乌梅丸": {193, 194},
            "shanghan:当归四逆汤": {197},
            "shanghan:当归四逆加吴茱萸生姜汤": {197, 198},
            "shanghan:麻黄升麻汤": {199, 200},
            "shanghan:干姜黄连黄芩人参汤": {200, 201},
            "shanghan:白头翁汤": {203, 204},
            "shanghan:四逆加人参汤": {48, 205, 207},
        }
        valid_pages = {48, 193, 194, 197, 198, 199, 200, 201, 203, 204, 205, 207}
        for key, module in self.modules.items():
            pages = {row["page"] for row in module["page_reading"]}
            with self.subTest(formula=key):
                self.assertTrue(expected_pages[key].issubset(pages))
                for item in module["page_reading"]:
                    self.assertIn(item["page"], valid_pages)
                    self.assertTrue(item["title"])
                    self.assertTrue(item["kind"])
                    self.assertTrue(item["text"])
                    self.assertTrue(item["annotation"])

    def test_modern_usage_has_source_steps_and_cautions(self):
        for key, module in self.modules.items():
            usage = module["usage_modern"]
            with self.subTest(formula=key):
                self.assertTrue(usage["summary"])
                self.assertTrue(usage["source_text"])
                self.assertGreaterEqual(len(usage["steps"]), 5)
                self.assertGreaterEqual(len(usage["cautions"]), 5)
                self.assertTrue(usage["source_pages"])

    def test_textual_conflicts_are_explicit(self):
        wumei = self.modules["shanghan:乌梅丸"]
        self.assertIn("黄连（十六两）", wumei["formula_original"]["text"])
        self.assertIn("五斗米下", wumei["formula_original"]["text"])
        self.assertIn("黄连一斤", wumei["usage_modern"]["source_text"])
        self.assertIn("五升米", wumei["usage_modern"]["source_text"])
        self.assertIn("五升", wumei["proofreading"][1]["note"])

        danggui = self.modules["shanghan:当归四逆汤"]
        self.assertIn("玉函", danggui["formula_original"]["note"])
        self.assertIn("一法十二枚", danggui["formula_original"]["note"])

        add_wu = self.modules["shanghan:当归四逆加吴茱萸生姜汤"]
        self.assertIn("甘草（二两炙）", add_wu["formula_original"]["text"])
        self.assertIn("九味组成", add_wu["formula_original"]["note"])
        self.assertNotIn("composition_raw", add_wu["formula_original"]["note"])
        self.assertIn("九味", add_wu["usage_modern"]["source_text"])
        self.assertIn("漏甘草", add_wu["proofreading"][2]["title"])

        mahuang = self.modules["shanghan:麻黄升麻汤"]
        self.assertIn("菖蒲", mahuang["formula_original"]["note"])
        self.assertIn("麦门冬", mahuang["formula_original"]["note"])
        self.assertIn("疑非仲景", mahuang["formula_original"]["note"])
        self.assertIn("外台", mahuang["formula_original"]["note"])

        ganjiang = self.modules["shanghan:干姜黄连黄芩人参汤"]
        self.assertIn("阙文", ganjiang["formula_original"]["note"])
        self.assertIn("寒下", ganjiang["formula_original"]["note"])
        self.assertIn(
            "干姜，黄连，黄芩，人参各三两",
            ganjiang["usage_modern"]["source_text"],
        )

        baitou = self.modules["shanghan:白头翁汤"]
        self.assertIn("白头翁（二两）", baitou["formula_original"]["text"])
        self.assertIn("并作三两", baitou["formula_original"]["note"])
        self.assertIn("欲饮水", baitou["formula_original"]["text"])

        sini = self.modules["shanghan:四逆加人参汤"]
        self.assertIn("一作□", sini["formula_original"]["note"])
        self.assertIn("人参一两为主", sini["formula_original"]["note"])
        self.assertIn("作三两", sini["formula_original"]["note"])
        self.assertIn("亡阳", sini["rationale"]["full_text"])
        self.assertIn("不在倪书这册PDF的完整方页", sini["formula_original"]["note"])
        self.assertIn("未列", sini["proofreading"][1]["note"])

    def test_high_risk_warnings_are_preserved(self):
        combined = {
            key: json.dumps(module, ensure_ascii=False)
            for key, module in self.modules.items()
        }
        self_use_warnings = (
            "不得自行",
            "不应自行",
            "不能自行",
            "不能按条文自行",
            "不能按网页自配",
        )

        def assert_self_use_warning(key):
            self.assertTrue(
                any(phrase in combined[key] for phrase in self_use_warnings),
                f"{key} is missing an explicit self-use warning",
            )

        for key in ("shanghan:乌梅丸", "shanghan:四逆加人参汤"):
            self.assertIn("附子", combined[key])
            assert_self_use_warning(key)

        self.assertIn("细辛", combined["shanghan:乌梅丸"])
        self.assertIn("细辛", combined["shanghan:当归四逆汤"])
        self.assertIn("细辛", combined["shanghan:当归四逆加吴茱萸生姜汤"])
        self.assertIn("吴茱萸", combined["shanghan:当归四逆加吴茱萸生姜汤"])
        self.assertIn("清酒", combined["shanghan:当归四逆加吴茱萸生姜汤"])
        self.assertIn("麻黄", combined["shanghan:麻黄升麻汤"])
        self.assertIn("唾脓血", combined["shanghan:麻黄升麻汤"])
        self.assertIn("入口即吐", combined["shanghan:干姜黄连黄芩人参汤"])
        self.assertIn("脱水", combined["shanghan:白头翁汤"])
        self.assertIn("血便", combined["shanghan:白头翁汤"])
        self.assertIn("急诊", combined["shanghan:四逆加人参汤"])

    def test_sini_add_is_independent_from_jinkui(self):
        sini = self.modules["shanghan:四逆加人参汤"]
        boundary_text = " ".join(
            [sini["usage_modern"]["summary"]]
            + sini["usage_modern"]["steps"]
            + sini["usage_modern"]["cautions"]
            + [sini["editorial_note"]]
        )
        self.assertIn("shanghan:四逆加人参汤", boundary_text)
        self.assertIn("jinkui:四逆加人参汤", boundary_text)
        self.assertIn("独立", boundary_text)
        self.assertIn("独立", sini["proofreading"][2]["note"])
        self.assertIn("辨霍乱病脉证并治", " ".join(sini["six_channel"]["original"]))
        self.assertIn("霍乱", sini["six_channel"]["name"])

    def test_no_placeholder_or_scope_notes(self):
        text = json.dumps(self.modules, ensure_ascii=False)
        for forbidden in (
            "本地文件夹未找到",
            "当前没有把",
            "冒充",
            "TODO",
            "TBD",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
