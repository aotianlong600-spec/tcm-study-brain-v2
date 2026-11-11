import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BATCH_PATH = ROOT / "data" / "curated_batches" / "shanghan_056_062.json"
FORMULAS_PATH = ROOT / "data" / "formulas.json"

EXPECTED_FORMULAS = [
    "shanghan:大黄黄连泻心汤",
    "shanghan:附子泻心汤",
    "shanghan:生姜泻心汤",
    "shanghan:甘草泻心汤",
    "shanghan:赤石脂禹余粮汤",
    "shanghan:旋覆代赭石汤",
    "shanghan:桂枝人参汤",
]

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


class Shanghan056062BatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not BATCH_PATH.exists():
            raise unittest.SkipTest("batch is still being produced")
        cls.modules = json.loads(BATCH_PATH.read_text(encoding="utf-8"))
        if set(cls.modules) != set(EXPECTED_FORMULAS):
            raise unittest.SkipTest("batch checkpoint is incomplete")
        cls.catalog = json.loads(FORMULAS_PATH.read_text(encoding="utf-8"))
        cls.catalog_ids = {formula["id"] for formula in cls.catalog}

    def test_exact_formula_set_and_catalog_order(self):
        self.assertEqual(list(self.modules), EXPECTED_FORMULAS)
        self.assertEqual(set(self.modules), set(EXPECTED_FORMULAS))
        self.assertTrue(set(self.modules).issubset(self.catalog_ids))

        catalog_order = [
            formula["id"]
            for formula in self.catalog
            if formula["id"] in set(EXPECTED_FORMULAS)
        ]
        self.assertEqual(catalog_order, EXPECTED_FORMULAS)

    def test_complete_module_structure(self):
        for key, module in self.modules.items():
            with self.subTest(formula=key):
                self.assertEqual(set(module), REQUIRED_FIELDS)
                self.assertEqual(module["review_status"], "reviewed")
                self.assertEqual(module["review_level"], "完整")
                self.assertEqual(module["usage_status"], "reviewed")
                self.assertTrue(module["usage_plain"])
                self.assertGreaterEqual(len(module["symptoms"]), 5)
                self.assertEqual(len(module["overview"]["paragraphs"]), 5)
                self.assertGreaterEqual(len(module["overview"]["key_points"]), 5)
                self.assertGreaterEqual(len(module["six_channel"]["original"]), 3)
                self.assertGreaterEqual(len(module["six_channel"]["annotations"]), 3)
                self.assertGreaterEqual(
                    len(module["six_channel"]["annotation_original"]), 3
                )
                self.assertGreaterEqual(len(module["page_reading"]), 1)
                self.assertGreaterEqual(len(module["annotations"]), 3)
                self.assertGreaterEqual(len(module["proofreading"]), 3)
                self.assertGreaterEqual(len(module["usage_modern"]["steps"]), 5)
                self.assertGreaterEqual(len(module["usage_modern"]["cautions"]), 5)
                self.assertGreaterEqual(len(module["rationale"]["full_text"]), 400)
                self.assertTrue(module["editorial_note"])

    def test_six_channel_identity_and_page_basis(self):
        for key, module in self.modules.items():
            six_channel = module["six_channel"]
            with self.subTest(formula=key):
                self.assertEqual(six_channel["id"], "taiyang")
                self.assertEqual(six_channel["name"], "太阳病")
                self.assertTrue(six_channel["summary"])
                self.assertTrue(six_channel["proof_note"])
                self.assertTrue(six_channel["source_pages"])
                for row in six_channel["annotation_original"]:
                    self.assertIsInstance(row["page"], int)
                    self.assertTrue(row["text"])

    def test_page_reading_is_direct_and_page_mapped(self):
        expected_pages = {
            "shanghan:大黄黄连泻心汤": {113, 114},
            "shanghan:附子泻心汤": {115},
            "shanghan:生姜泻心汤": {115, 116},
            "shanghan:甘草泻心汤": {116, 117},
            "shanghan:赤石脂禹余粮汤": {117, 118},
            "shanghan:旋覆代赭石汤": {118, 119},
            "shanghan:桂枝人参汤": {119, 120},
        }
        for key, module in self.modules.items():
            pages = {row["page"] for row in module["page_reading"]}
            with self.subTest(formula=key):
                self.assertTrue(expected_pages[key].issubset(pages))
                self.assertTrue(
                    expected_pages[key].issubset(
                        set(module["six_channel"]["source_pages"])
                    )
                )
                for row in module["page_reading"]:
                    self.assertIsInstance(row["page"], int)
                    self.assertTrue(113 <= row["page"] <= 120)
                    self.assertTrue(row["title"])
                    self.assertTrue(row["kind"])
                    self.assertTrue(row["text"])
                    self.assertTrue(row["annotation"])

    def test_original_doses_and_decoction_layers_survive(self):
        expected = {
            "shanghan:大黄黄连泻心汤": (
                "大黄（二两）",
                "黄连（一两）",
                "麻沸汤二升",
                "渍之",
                "须臾",
                "分温再服",
            ),
            "shanghan:附子泻心汤": (
                "大黄（二两）",
                "黄连（一两）",
                "黄芩（一两）",
                "附子（二枚炮去皮破别煮取汁）",
                "麻沸汤二升",
                "纳附子汁",
            ),
            "shanghan:生姜泻心汤": (
                "生姜（四两切）",
                "甘草（三两炙）",
                "人参（三两）",
                "干姜（一两）",
                "黄芩（三两）",
                "半夏（半升洗）",
                "黄连（一两）",
                "大枣（十二枚擘）",
                "再煎取三升",
            ),
            "shanghan:甘草泻心汤": (
                "甘草（四两炙）",
                "黄芩（三两）",
                "干姜（三两",
                "大枣（十二枚擘）",
                "半夏（半升洗",
                "黄连（一两）",
                "再煎取三升",
            ),
            "shanghan:赤石脂禹余粮汤": (
                "赤石脂（一斤碎）",
                "太一禹余粮（一斤碎",
                "以水六升",
                "煮取二升",
                "分温三服",
            ),
            "shanghan:旋覆代赭石汤": (
                "旋复花（三两）",
                "人参（二两）",
                "生姜（五两",
                "大枣（十二枚擘）",
                "甘草（三两炙）",
                "半夏（半升洗）",
                "代赭（一两",
                "再煎取三升",
            ),
            "shanghan:桂枝人参汤": (
                "桂枝（四两别切",
                "甘草（四两炙）",
                "白术（三两）",
                "人参（三两）",
                "干姜（三两）",
                "以水九升",
                "先煮四味",
                "纳桂",
                "日再",
                "夜一服",
            ),
        }
        for key, needles in expected.items():
            text = (
                self.modules[key]["formula_original"]["text"]
                + "\n"
                + self.modules[key]["usage_original"]["text"]
            )
            with self.subTest(formula=key):
                for needle in needles:
                    self.assertIn(needle, text)

    def test_same_herbs_have_distinct_doses_and_processing(self):
        texts = {
            key: json.dumps(module, ensure_ascii=False)
            for key, module in self.modules.items()
        }

        self.assertIn("诸本皆二味", texts["shanghan:大黄黄连泻心汤"])
        self.assertIn("黄芩", texts["shanghan:大黄黄连泻心汤"])
        self.assertIn("不是", texts["shanghan:大黄黄连泻心汤"])

        for needle in (
            "黄连二两",
            "黄连（一两）",
            "附子一枚",
            "附子（二枚",
            "别煮取汁",
            "渍",
        ):
            self.assertIn(needle, texts["shanghan:附子泻心汤"])

        for needle in (
            "甘草三两",
            "甘草四两",
            "干姜一两",
            "干姜三两",
            "人参三两",
            "脱落",
        ):
            combined = (
                texts["shanghan:生姜泻心汤"] + texts["shanghan:甘草泻心汤"]
            )
            self.assertIn(needle, combined)

        self.assertIn("半夏", texts["shanghan:生姜泻心汤"])
        self.assertIn("洗", texts["shanghan:生姜泻心汤"])
        self.assertIn("半夏", texts["shanghan:甘草泻心汤"])
        self.assertIn("洗", texts["shanghan:甘草泻心汤"])

    def test_textual_variants_are_explicit(self):
        texts = {
            key: json.dumps(module, ensure_ascii=False)
            for key, module in self.modules.items()
        }

        self.assertIn("林亿", texts["shanghan:大黄黄连泻心汤"])
        self.assertIn("推测", texts["shanghan:大黄黄连泻心汤"])
        self.assertIn("黄芩", texts["shanghan:大黄黄连泻心汤"])

        self.assertIn("成本", texts["shanghan:附子泻心汤"])
        self.assertIn("作一枚", texts["shanghan:附子泻心汤"])
        self.assertIn("大黄二两", texts["shanghan:附子泻心汤"])
        self.assertIn("黄连二两", texts["shanghan:附子泻心汤"])

        self.assertIn("外台", texts["shanghan:甘草泻心汤"])
        self.assertIn("干姜", texts["shanghan:甘草泻心汤"])
        self.assertIn("人参", texts["shanghan:甘草泻心汤"])

        self.assertIn("太一禹余粮", texts["shanghan:赤石脂禹余粮汤"])
        self.assertIn("禹余粮", texts["shanghan:赤石脂禹余粮汤"])

        self.assertIn("旋覆代赭石汤", texts["shanghan:旋覆代赭石汤"])
        self.assertIn("旋复代赭汤", texts["shanghan:旋覆代赭石汤"])
        self.assertIn("代赭石", texts["shanghan:旋覆代赭石汤"])

        self.assertIn("别切", texts["shanghan:桂枝人参汤"])
        self.assertIn("去皮", texts["shanghan:桂枝人参汤"])
        self.assertIn("后下", texts["shanghan:桂枝人参汤"])

    def test_high_risk_warnings_are_explicit(self):
        texts = {
            key: json.dumps(module, ensure_ascii=False)
            for key, module in self.modules.items()
        }
        self_use_warnings = (
            "不得自行",
            "不应自行",
            "不能自行",
            "不能按条文自行",
        )
        emergency_actions = ("急诊", "立即就医", "急救")

        def assert_self_use_warning(key):
            self.assertTrue(
                any(phrase in texts[key] for phrase in self_use_warnings),
                f"{key} is missing an explicit self-use warning",
            )

        def assert_emergency_action(key):
            self.assertTrue(
                any(phrase in texts[key] for phrase in emergency_actions),
                f"{key} is missing an emergency-action warning",
            )

        for key in EXPECTED_FORMULAS:
            self.assertIn("妊娠慎用", texts[key])
            assert_self_use_warning(key)

        self.assertIn("乌头", texts["shanghan:附子泻心汤"])
        self.assertIn("心律失常", texts["shanghan:附子泻心汤"])

        for key in ("shanghan:生姜泻心汤", "shanghan:甘草泻心汤"):
            self.assertIn("半夏", texts[key])
            self.assertIn("生半夏", texts[key])

        for phrase in ("矿物药", "矿物来源", "重金属", "杂质", "微生物", "肠梗阻"):
            self.assertIn(phrase, texts["shanghan:赤石脂禹余粮汤"])
        assert_emergency_action("shanghan:赤石脂禹余粮汤")

        self.assertIn("代赭石", texts["shanghan:旋覆代赭石汤"])
        self.assertIn("矿物", texts["shanghan:旋覆代赭石汤"])
        assert_emergency_action("shanghan:旋覆代赭石汤")

        self.assertIn("下利", texts["shanghan:桂枝人参汤"])
        assert_emergency_action("shanghan:桂枝人参汤")

    def test_no_placeholder_or_scope_notes(self):
        text = json.dumps(self.modules, ensure_ascii=False)
        for forbidden in (
            "本地文件夹未找到",
            "本地未找到",
            "当前没有把",
            "冒充",
            "TODO",
            "TBD",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
