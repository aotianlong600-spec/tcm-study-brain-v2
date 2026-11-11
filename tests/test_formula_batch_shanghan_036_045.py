import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "data" / "curated_batches" / "shanghan_036_045.json"

EXPECTED = [
    "shanghan:小柴胡汤",
    "shanghan:小建中汤",
    "shanghan:大柴胡汤",
    "shanghan:柴胡加芒硝汤",
    "shanghan:桃核承气汤",
    "shanghan:柴胡加龙骨牡蛎汤",
    "shanghan:桂枝去芍药加蜀漆牡蛎龙骨救逆汤",
    "shanghan:桂枝加桂汤",
    "shanghan:桂枝甘草龙骨牡蛎汤",
    "shanghan:抵当汤",
]

ALIASES = {"饴糖": ("饴糖", "胶饴"), "白术": ("白术", "白朮")}
TOXIC = {
    "shanghan:柴胡加龙骨牡蛎汤": ("铅丹",),
    "shanghan:桂枝去芍药加蜀漆牡蛎龙骨救逆汤": ("蜀漆",),
    "shanghan:抵当汤": ("水蛭", "虻虫"),
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
PAGE_EXPECTATIONS = {
    "shanghan:小柴胡汤": {69, 70, 73},
    "shanghan:小建中汤": {75, 76},
    "shanghan:大柴胡汤": {76, 77},
    "shanghan:柴胡加芒硝汤": {77, 78},
    "shanghan:桃核承气汤": {79, 80},
    "shanghan:柴胡加龙骨牡蛎汤": {80, 81},
    "shanghan:桂枝去芍药加蜀漆牡蛎龙骨救逆汤": {83, 84},
    "shanghan:桂枝加桂汤": {86, 87},
    "shanghan:桂枝甘草龙骨牡蛎汤": {87, 88},
    "shanghan:抵当汤": {91, 92, 93},
}
ORIGINAL_NEEDLES = {
    "shanghan:小柴胡汤": ("往来寒热", "胸胁苦满", "去滓再煎", "若咳者"),
    "shanghan:小建中汤": ("阳脉涩", "腹中急痛", "胶饴（一升）", "呕家不可用建中汤"),
    "shanghan:大柴胡汤": ("呕不止", "心下急", "大黄", "去滓再煎"),
    "shanghan:柴胡加芒硝汤": ("胸胁满而呕", "日晡所发潮热", "芒硝（二两", "分温再服"),
    "shanghan:桃核承气汤": ("热结膀胱", "其人如狂", "少腹急结", "当微利"),
    "shanghan:柴胡加龙骨牡蛎汤": ("胸满烦惊", "小便不利", "一身尽重", "铅丹（一两半"),
    "shanghan:桂枝去芍药加蜀漆牡蛎龙骨救逆汤": (
        "火迫劫之",
        "惊狂",
        "先煮蜀漆",
        "蜀漆（三两洗去腥",
    ),
    "shanghan:桂枝加桂汤": ("气从少腹上冲心", "桂枝（五两去皮）", "泄奔豚气"),
    "shanghan:桂枝甘草龙骨牡蛎汤": ("火逆下之", "因烧针烦躁", "温服八合"),
    "shanghan:抵当汤": ("脉微而沉", "其人发狂", "少腹当硬满", "不下更服"),
}
VERSION_NEEDLES = {
    "shanghan:小柴胡汤": ("八两", "十三枚"),
    "shanghan:小建中汤": ("作三两", "十一枚"),
    "shanghan:大柴胡汤": ("一方加大黄二两", "八味"),
    "shanghan:柴胡加芒硝汤": ("大枣四枚", "大枣十二枚"),
    "shanghan:桃核承气汤": ("千金翼作一两",),
    "shanghan:柴胡加龙骨牡蛎汤": ("十一味", "十二味", "无黄芩"),
    "shanghan:桂枝去芍药加蜀漆牡蛎龙骨救逆汤": ("右为末", "上七味"),
    "shanghan:桂枝加桂汤": ("肉桂五分至八分", "生姜二两"),
    "shanghan:桂枝甘草龙骨牡蛎汤": ("茯苓四两", "桂苓甘草龙骨牡蛎汤", "四味", "五味"),
    "shanghan:抵当汤": ("二十三个", "二两破六片"),
}


class Shanghan036045BatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modules = json.loads(BATCH.read_text(encoding="utf-8"))
        cls.catalog = {
            row["id"]: row
            for row in json.loads((ROOT / "data" / "formulas.json").read_text(encoding="utf-8"))
        }

    def test_exact_formula_set(self):
        self.assertEqual(list(self.modules), EXPECTED)

    def test_complete_module_structure(self):
        for key, module in self.modules.items():
            with self.subTest(formula=key):
                self.assertEqual(set(module), REQUIRED_FIELDS)
                self.assertEqual(module["review_status"], "reviewed")
                self.assertEqual(module["review_level"], "完整")
                self.assertEqual(module["usage_status"], "reviewed")
                self.assertGreaterEqual(len(module["overview"]["paragraphs"]), 5)
                self.assertGreaterEqual(len(module["overview"]["key_points"]), 5)
                self.assertGreaterEqual(len(module["symptoms"]), 4)
                self.assertGreaterEqual(len(module["six_channel"]["original"]), 2)
                self.assertGreaterEqual(len(module["six_channel"]["annotations"]), 2)
                self.assertGreaterEqual(len(module["six_channel"]["annotation_original"]), 2)
                self.assertGreaterEqual(len(module["page_reading"]), 2)
                self.assertGreaterEqual(len(module["proofreading"]), 4)
                self.assertGreaterEqual(len(module["usage_modern"]["steps"]), 5)
                self.assertGreaterEqual(len(module["usage_modern"]["cautions"]), 5)
                self.assertGreaterEqual(len(module["rationale"]["full_text"]), 400)

    def test_catalog_names_and_doses_are_preserved(self):
        for key, module in self.modules.items():
            text = module["formula_original"]["text"] + module["usage_original"]["text"]
            for ingredient in self.catalog[key]["ingredients"]:
                names = ALIASES.get(ingredient["name"], (ingredient["name"],))
                with self.subTest(formula=key, ingredient=ingredient["name"]):
                    self.assertTrue(any(name in text for name in names))
                    if ingredient.get("dose"):
                        self.assertIn(ingredient["dose"], text)

    def test_high_risk_boundaries(self):
        for key, terms in TOXIC.items():
            text = json.dumps(self.modules[key], ensure_ascii=False)
            with self.subTest(formula=key):
                for term in terms:
                    self.assertIn(term, text)
                self.assertRegex(text, r"毒|风险|急诊|不得自行|不应自行|不能自行")

    def test_pages_and_sources_are_explicit(self):
        for key, module in self.modules.items():
            with self.subTest(formula=key):
                actual_pages = {row["page"] for row in module["page_reading"]}
                self.assertTrue(
                    all(isinstance(row["page"], int) for row in module["page_reading"])
                )
                self.assertTrue(PAGE_EXPECTATIONS[key].issubset(actual_pages))
                self.assertTrue(set(module["six_channel"]["source_pages"]).issubset(actual_pages))
                self.assertTrue(module["formula_original"]["source_pages"])
                self.assertTrue(module["usage_original"]["source_pages"])

    def test_formula_specific_original_and_version_boundaries(self):
        for key, needles in ORIGINAL_NEEDLES.items():
            module = self.modules[key]
            text = (
                module["formula_original"]["text"]
                + "\n"
                + module["usage_original"]["text"]
            )
            for needle in needles:
                with self.subTest(formula=key, needle=needle):
                    self.assertIn(needle, text)
        for key, needles in VERSION_NEEDLES.items():
            text = json.dumps(self.modules[key], ensure_ascii=False)
            for needle in needles:
                with self.subTest(formula=key, version_needle=needle):
                    self.assertIn(needle, text)
                self.assertTrue(module["six_channel"]["proof_note"])

    def test_no_placeholder_language(self):
        text = json.dumps(self.modules, ensure_ascii=False)
        for forbidden in ("TODO", "TBD", "本地文件夹未找到", "当前没有把", "冒充"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
