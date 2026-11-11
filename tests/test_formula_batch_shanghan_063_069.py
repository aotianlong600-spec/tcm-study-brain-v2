import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BATCH_PATH = ROOT / "data" / "curated_batches" / "shanghan_063_069.json"
FORMULAS_PATH = ROOT / "data" / "formulas.json"

EXPECTED_FORMULAS = [
    "shanghan:瓜蒂散",
    "shanghan:黄芩汤",
    "shanghan:黄芩加半夏生姜汤",
    "shanghan:黄连汤",
    "shanghan:桂枝附子汤",
    "shanghan:白术附子汤",
    "shanghan:甘草附子汤",
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


class Shanghan063069BatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modules = json.loads(BATCH_PATH.read_text(encoding="utf-8"))
        cls.catalog = json.loads(FORMULAS_PATH.read_text(encoding="utf-8"))
        cls.catalog_ids = {formula["id"] for formula in cls.catalog}

    def assert_formula(self, formula_id):
        module = self.modules[formula_id]
        self.assertEqual(set(module), REQUIRED_FIELDS)
        self.assertEqual(module["review_status"], "reviewed")
        self.assertEqual(module["review_level"], "完整")
        self.assertEqual(module["usage_status"], "reviewed")
        self.assertTrue(module["usage_plain"])
        self.assertGreaterEqual(len(module["symptoms"]), 4)
        self.assertEqual(len(module["overview"]["paragraphs"]), 5)
        self.assertGreaterEqual(len(module["overview"]["key_points"]), 5)
        six_channel = module["six_channel"]
        self.assertEqual(
            (six_channel["id"], six_channel["name"]), ("taiyang", "太阳病")
        )
        self.assertGreaterEqual(len(six_channel["original"]), 3)
        self.assertGreaterEqual(len(six_channel["annotations"]), 3)
        self.assertGreaterEqual(len(six_channel["annotation_original"]), 3)
        self.assertTrue(six_channel["source_pages"])
        self.assertTrue(six_channel["proof_note"])
        self.assertGreaterEqual(len(module["usage_modern"]["steps"]), 5)
        self.assertGreaterEqual(len(module["usage_modern"]["cautions"]), 5)
        self.assertGreaterEqual(len(module["annotations"]), 3)
        self.assertGreaterEqual(len(module["proofreading"]), 3)
        self.assertGreaterEqual(len(module["page_reading"]), 1)
        self.assertGreaterEqual(len(module["rationale"]["full_text"]), 400)
        self.assertTrue(module["editorial_note"])

    def test_exact_formula_set_and_catalog_membership(self):
        self.assertEqual(list(self.modules), EXPECTED_FORMULAS)
        self.assertTrue(set(self.modules).issubset(self.catalog_ids))

    def test_gua_di_san_is_fully_reviewed(self):
        formula_id = "shanghan:瓜蒂散"
        self.assert_formula(formula_id)
        module = self.modules[formula_id]
        pages = {row["page"] for row in module["page_reading"]}
        self.assertTrue({120, 121, 198}.issubset(pages))
        original = module["formula_original"]["text"]
        usage = module["usage_original"]["text"]
        for needle in (
            "瓜蒂（一分熬黄）",
            "赤小豆（一分",
            "香豉一合",
            "热汤七合",
            "一钱匕",
            "少少加",
            "得快吐乃止",
            "诸亡血虚家",
            "不可与瓜蒂散",
        ):
            self.assertIn(needle, original + usage)
        combined = json.dumps(module, ensure_ascii=False)
        for needle in ("催吐", "亡血虚家", "半钱匕", "各六铢", "胃出血"):
            self.assertIn(needle, combined)

    def test_huang_qin_tang_is_fully_reviewed(self):
        formula_id = "shanghan:黄芩汤"
        self.assert_formula(formula_id)
        module = self.modules[formula_id]
        pages = {row["page"] for row in module["page_reading"]}
        self.assertTrue({124, 125}.issubset(pages))
        text = (
            module["formula_original"]["text"]
            + "\n"
            + module["usage_original"]["text"]
        )
        for needle in (
            "黄芩（三两",
            "芍药（二两）",
            "甘草（二两炙）",
            "大枣（十二枚擘）",
            "以水一斗",
            "煮取三升",
            "温服一升",
            "日再",
            "夜一服",
        ):
            self.assertIn(needle, text)
        combined = json.dumps(module, ensure_ascii=False)
        for needle in ("玉函", "作二两", "半夏半升", "生姜三两", "热利腹痛"):
            self.assertIn(needle, combined)

    def test_huang_qin_jia_ban_xia_sheng_jiang_tang_is_fully_reviewed(self):
        formula_id = "shanghan:黄芩加半夏生姜汤"
        self.assert_formula(formula_id)
        module = self.modules[formula_id]
        pages = {row["page"] for row in module["page_reading"]}
        self.assertTrue({124, 125}.issubset(pages))
        text = module["formula_original"]["text"]
        for needle in (
            "半夏（半升洗）",
            "生姜（一两半",
            "一方三两",
            "上六味",
            "若呕者",
        ):
            self.assertIn(needle, text)
        combined = json.dumps(module, ensure_ascii=False)
        for needle in ("生姜一两半", "生姜三两", "止呕", "生半夏", "不得自行"):
            self.assertIn(needle, combined)

    def test_huang_lian_tang_is_fully_reviewed(self):
        formula_id = "shanghan:黄连汤"
        self.assert_formula(formula_id)
        module = self.modules[formula_id]
        pages = {row["page"] for row in module["page_reading"]}
        self.assertTrue({125, 126}.issubset(pages))
        text = (
            module["formula_original"]["text"]
            + "\n"
            + module["usage_original"]["text"]
        )
        for needle in (
            "黄连（三两",
            "甘草（三两炙",
            "干姜（三两",
            "桂枝（三两去皮",
            "人参（二两",
            "大枣（十二枚擘）",
            "半夏（半升洗",
            "昼三夜二",
        ):
            self.assertIn(needle, text)
        combined = json.dumps(module, ensure_ascii=False)
        for needle in ("干姜二两", "人参三两", "上热下寒", "生半夏", "妊娠慎用"):
            self.assertIn(needle, combined)

    def test_gui_zhi_fu_zi_tang_is_fully_reviewed(self):
        formula_id = "shanghan:桂枝附子汤"
        self.assert_formula(formula_id)
        module = self.modules[formula_id]
        pages = {row["page"] for row in module["page_reading"]}
        self.assertTrue({126}.issubset(pages))
        text = (
            module["formula_original"]["text"]
            + "\n"
            + module["usage_original"]["text"]
        )
        for needle in (
            "桂枝（四两去皮）",
            "附子（三枚炮去皮破",
            "生姜（三两切）",
            "大枣（十二枚擘）",
            "甘草（二两炙）",
            "以水六升",
            "煮取二升",
            "分温三服",
        ):
            self.assertIn(needle, text)
        combined = json.dumps(module, ensure_ascii=False)
        for needle in ("附子二枚", "钱本作二枚", "炮附子", "心律失常", "不得自行"):
            self.assertIn(needle, combined)

    def test_bai_zhu_fu_zi_tang_is_fully_reviewed(self):
        formula_id = "shanghan:白术附子汤"
        self.assert_formula(formula_id)
        module = self.modules[formula_id]
        pages = {row["page"] for row in module["page_reading"]}
        self.assertTrue({126, 127}.issubset(pages))
        text = (
            module["formula_original"]["text"]
            + "\n"
            + module["usage_original"]["text"]
        )
        for needle in (
            "附子（三枚炮去皮破）",
            "白术（四两）",
            "生姜（三两切",
            "甘草（二两炙",
            "大枣（十二枚擘",
            "其人身如痹",
            "如冒状",
            "虚弱家及产妇",
            "宜减服之",
        ):
            self.assertIn(needle, text)
        combined = json.dumps(module, ensure_ascii=False)
        for needle in ("大便溏", "大便硬", "小便自利", "附子一枚", "白术二两", "妊娠慎用"):
            self.assertIn(needle, combined)

    def test_gan_cao_fu_zi_tang_is_fully_reviewed(self):
        formula_id = "shanghan:甘草附子汤"
        self.assert_formula(formula_id)
        module = self.modules[formula_id]
        pages = {row["page"] for row in module["page_reading"]}
        self.assertTrue({127, 128}.issubset(pages))
        text = (
            module["formula_original"]["text"]
            + "\n"
            + module["usage_original"]["text"]
        )
        for needle in (
            "白术（二两",
            "桂枝（四两去皮）",
            "附子（二枚炮去皮",
            "甘草（二两炙",
            "以水六升",
            "煮取二升",
            "温服一升",
            "日三服",
            "六七合",
        ):
            self.assertIn(needle, text)
        combined = json.dumps(module, ensure_ascii=False)
        for needle in ("煮取三升", "玉函", "白术三两", "甘草三两", "炮附子", "不得自行"):
            self.assertIn(needle, combined)

    def test_no_placeholder_language(self):
        text = json.dumps(self.modules, ensure_ascii=False)
        for forbidden in (
            "本地文件夹未找到",
            "本地未找到",
            "当前没有把",
            "冒充",
            "TODO",
            "TBD",
            "待整理",
            "候选原文",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
