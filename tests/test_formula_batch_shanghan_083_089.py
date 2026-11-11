import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BATCH_PATH = ROOT / "data" / "curated_batches" / "shanghan_083_089.json"
FORMULAS_PATH = ROOT / "data" / "formulas.json"

EXPECTED_FORMULAS = [
    "shanghan:桂枝加芍药汤",
    "shanghan:桂枝加大黄汤",
    "shanghan:麻黄附子细辛汤",
    "shanghan:麻黄附子甘草汤",
    "shanghan:黄连阿胶汤",
    "shanghan:附子汤",
    "shanghan:桃花汤",
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


class Shanghan083089BatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modules = json.loads(BATCH_PATH.read_text(encoding="utf-8"))
        cls.catalog = json.loads(FORMULAS_PATH.read_text(encoding="utf-8"))
        cls.catalog_ids = {formula["id"] for formula in cls.catalog}

    def test_exact_formula_set_and_catalog_membership(self):
        self.assertEqual(list(self.modules), EXPECTED_FORMULAS)
        self.assertEqual(set(self.modules), set(EXPECTED_FORMULAS))
        self.assertTrue(set(self.modules).issubset(self.catalog_ids))

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
        expected_channel = {
            "shanghan:桂枝加芍药汤": ("taiyin", "太阴病"),
            "shanghan:桂枝加大黄汤": ("taiyin", "太阴病"),
            "shanghan:麻黄附子细辛汤": ("shaoyin", "少阴病"),
            "shanghan:麻黄附子甘草汤": ("shaoyin", "少阴病"),
            "shanghan:黄连阿胶汤": ("shaoyin", "少阴病"),
            "shanghan:附子汤": ("shaoyin", "少阴病"),
            "shanghan:桃花汤": ("shaoyin", "少阴病"),
        }
        for key, module in self.modules.items():
            six_channel = module["six_channel"]
            with self.subTest(formula=key):
                self.assertEqual(
                    (six_channel["id"], six_channel["name"]), expected_channel[key]
                )
                self.assertTrue(six_channel["summary"])
                self.assertTrue(six_channel["proof_note"])
                self.assertTrue(six_channel["source_pages"])
                for row in six_channel["annotation_original"]:
                    self.assertIsInstance(row["page"], int)
                    self.assertTrue(row["text"])

    def test_page_reading_is_direct_and_page_mapped(self):
        expected_pages = {
            "shanghan:桂枝加芍药汤": {170},
            "shanghan:桂枝加大黄汤": {170},
            "shanghan:麻黄附子细辛汤": {177},
            "shanghan:麻黄附子甘草汤": {178},
            "shanghan:黄连阿胶汤": {178, 179},
            "shanghan:附子汤": {179, 180},
            "shanghan:桃花汤": {180, 181},
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
                    self.assertTrue(170 <= row["page"] <= 181)
                    self.assertTrue(row["title"])
                    self.assertTrue(row["kind"])
                    self.assertTrue(row["text"])
                    self.assertTrue(row["annotation"])

    def test_original_doses_and_decoction_layers_survive(self):
        expected = {
            "shanghan:桂枝加芍药汤": (
                "桂枝（三两去皮）",
                "芍药（六两）",
                "甘草（二两炙）",
                "大枣（十二枚擘）",
                "生姜（二两切）",
                "以水七升",
                "温分三服",
            ),
            "shanghan:桂枝加大黄汤": (
                "大黄（二两）",
                "芍药（六两）",
                "生姜（三两切）",
                "甘草（二两炙）",
                "大枣（十二枚擘）",
                "温服一升",
                "日三服",
            ),
            "shanghan:麻黄附子细辛汤": (
                "麻黄（二两去节）",
                "细辛（二两）",
                "附子（一枚炮去皮破八片）",
                "以水一斗",
                "减二升",
                "日三服",
            ),
            "shanghan:麻黄附子甘草汤": (
                "麻黄（二两去节）",
                "甘草（二两炙）",
                "附子（一枚炮去皮破八片）",
                "先煮麻黄一两沸",
                "微发汗",
                "日三服",
            ),
            "shanghan:黄连阿胶汤": (
                "黄连（四两）",
                "黄芩（二两）",
                "鸡子黄（三枚）",
                "阿胶（三两一云三挺）",
                "以水六升",
                "纳胶烊尽",
                "小冷",
                "纳鸡子黄",
                "温服七合",
            ),
            "shanghan:附子汤": (
                "附子（二枚炮去皮破八片）",
                "茯苓（三两）",
                "人参（二两）",
                "白术（四两）",
                "芍药（三两）",
                "以水八升",
                "日三服",
            ),
            "shanghan:桃花汤": (
                "赤石脂（一斤一半全用一半筛末）",
                "干姜（一两）",
                "粳米（一升）",
                "以水七升",
                "纳赤石脂末方寸匕",
                "若一服愈",
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

    def test_version_differences_are_not_silently_normalized(self):
        texts = {
            key: json.dumps(module, ensure_ascii=False)
            for key, module in self.modules.items()
        }

        for needle in ("生姜二两", "大枣十二枚", "生姜三两", "大枣二枚"):
            self.assertIn(needle, texts["shanghan:桂枝加芍药汤"])

        for needle in ("大黄二两", "芍药六两", "大黄一两", "芍药三两"):
            self.assertIn(needle, texts["shanghan:桂枝加大黄汤"])

        self.assertIn("水一斗", texts["shanghan:麻黄附子细辛汤"])
        self.assertIn("水一升", texts["shanghan:麻黄附子细辛汤"])
        self.assertIn("去节", texts["shanghan:麻黄附子细辛汤"])
        self.assertIn("去筛", texts["shanghan:麻黄附子细辛汤"])
        self.assertIn("无里证", texts["shanghan:麻黄附子甘草汤"])

        for needle in (
            "黄芩二两",
            "黄芩一两",
            "鸡子黄三枚",
            "鸡子黄二枚",
            "阿胶三两",
            "阿胶二两",
            "水六升",
            "水五升",
        ):
            self.assertIn(needle, texts["shanghan:黄连阿胶汤"])

        self.assertIn("日三服", texts["shanghan:附子汤"])
        self.assertIn("日二服", texts["shanghan:附子汤"])
        self.assertIn("炮字", texts["shanghan:附子汤"])

        self.assertIn("水七升", texts["shanghan:桃花汤"])
        self.assertIn("水半升", texts["shanghan:桃花汤"])
        self.assertIn("疑", texts["shanghan:桃花汤"])

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

        def assert_self_use_warning(key):
            self.assertTrue(
                any(phrase in texts[key] for phrase in self_use_warnings),
                f"{key} is missing an explicit self-use warning",
            )

        for key in ("shanghan:桂枝加芍药汤", "shanghan:桂枝加大黄汤"):
            self.assertIn("急腹症", texts[key])
            assert_self_use_warning(key)
            self.assertIn("妊娠慎用", texts[key])

        for key in ("shanghan:麻黄附子细辛汤", "shanghan:麻黄附子甘草汤"):
            self.assertIn("麻黄", texts[key])
            self.assertIn("附子", texts[key])
            assert_self_use_warning(key)
            self.assertIn("心律失常", texts[key])
            self.assertIn("妊娠慎用", texts[key])

        self.assertIn("生鸡子黄", self.modules["shanghan:黄连阿胶汤"]["editorial_note"])
        self.assertIn("沙门菌", texts["shanghan:黄连阿胶汤"])
        self.assertIn("阿胶", texts["shanghan:黄连阿胶汤"])
        self.assertIn("妊娠慎用", texts["shanghan:黄连阿胶汤"])

        self.assertIn("炮附子", texts["shanghan:附子汤"])
        assert_self_use_warning("shanghan:附子汤")
        self.assertIn("妊娠慎用", texts["shanghan:附子汤"])

        self.assertIn("便脓血", texts["shanghan:桃花汤"])
        self.assertIn("急诊", texts["shanghan:桃花汤"])
        assert_self_use_warning("shanghan:桃花汤")
        self.assertIn("妊娠慎用", texts["shanghan:桃花汤"])

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
