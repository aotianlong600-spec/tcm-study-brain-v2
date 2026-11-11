from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
BATCH_PATH = ROOT / "data" / "curated_batches" / "shanghan_076_082.json"

FORMULAS = {
    "shanghan:猪胆汁方",
    "shanghan:土瓜根方",
    "shanghan:茵陈蒿汤",
    "shanghan:吴茱萸汤",
    "shanghan:麻子仁丸",
    "shanghan:栀子蘗皮汤",
    "shanghan:麻黄连轺赤小豆汤",
}

TOP_LEVEL_KEYS = {
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


class ShanghanBatch076082Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.batch = json.loads(BATCH_PATH.read_text(encoding="utf-8"))

    def test_batch_covers_exact_formula_set(self):
        self.assertEqual(set(self.batch), FORMULAS)

    def test_modules_match_curated_structure(self):
        for key, module in self.batch.items():
            with self.subTest(formula=key):
                self.assertEqual(set(module), TOP_LEVEL_KEYS)
                self.assertEqual(
                    set(module["overview"]),
                    {"title", "paragraphs", "key_points"},
                )
                self.assertEqual(
                    set(module["six_channel"]),
                    {
                        "id",
                        "name",
                        "summary",
                        "original",
                        "annotations",
                        "annotation_original",
                        "source_pages",
                        "proof_note",
                    },
                )
                self.assertEqual(
                    set(module["formula_original"]),
                    {"title", "text", "source_pages", "note"},
                )
                self.assertEqual(
                    set(module["usage_original"]),
                    {"title", "summary", "text", "source_pages"},
                )
                self.assertEqual(
                    set(module["usage_modern"]),
                    {"summary", "source_text", "steps", "cautions", "source_pages"},
                )
                self.assertEqual(set(module["rationale"]), {"summary", "full_text"})
                self.assertEqual(module["review_status"], "reviewed")
                self.assertEqual(module["six_channel"]["id"], "yangming")
                self.assertEqual(module["six_channel"]["name"], "阳明病")
                self.assertGreaterEqual(len(module["overview"]["paragraphs"]), 3)
                self.assertGreaterEqual(len(module["symptoms"]), 5)
                self.assertGreaterEqual(len(module["page_reading"]), 1)
                self.assertGreaterEqual(len(module["proofreading"]), 2)
                for row in module["symptoms"]:
                    self.assertEqual(set(row), {"name", "source", "page"})
                for row in module["page_reading"]:
                    self.assertEqual(
                        set(row), {"page", "title", "kind", "text", "annotation"}
                    )
                for row in module["annotations"]:
                    self.assertEqual(set(row), {"heading", "text", "source_page"})

    def test_formula_doses_and_ancient_usage_are_explicit(self):
        expected = {
            "shanghan:猪胆汁方": (
                ["大猪胆", "一枚", "法醋", "灌谷道"],
                ["一食顷", "大便出"],
            ),
            "shanghan:土瓜根方": (["方缺"], ["方缺"]),
            "shanghan:茵陈蒿汤": (
                ["茵陈蒿", "六两", "大黄", "二两", "栀子", "十四枚"],
                ["一斗二升", "先煮茵陈", "分三服", "黄从小便去"],
            ),
            "shanghan:吴茱萸汤": (
                ["吴茱萸", "一升", "人参", "三两", "生姜", "六两", "大枣", "十二枚"],
                ["七升", "煮取二升", "温服七合", "日三服"],
            ),
            "shanghan:麻子仁丸": (
                [
                    "麻子仁",
                    "二升",
                    "芍药",
                    "半斤",
                    "枳实",
                    "大黄",
                    "一斤",
                    "厚朴",
                    "一尺",
                    "杏仁",
                    "一升",
                ],
                ["梧桐子大", "十丸", "日三服", "以知为度"],
            ),
            "shanghan:栀子蘗皮汤": (
                ["肥栀子", "十五个", "甘草", "一两", "黄柏", "二两"],
                ["四升", "一升半", "分温再服"],
            ),
            "shanghan:麻黄连轺赤小豆汤": (
                [
                    "麻黄",
                    "连轺",
                    "连翘根",
                    "杏仁",
                    "四十个",
                    "赤小豆",
                    "一升",
                    "生梓白皮",
                ],
                ["潦水一斗", "先煮麻黄再沸", "煮取三升", "半日服尽"],
            ),
        }
        for key, (formula_parts, usage_parts) in expected.items():
            with self.subTest(formula=key):
                formula_text = self.batch[key]["formula_original"]["text"]
                usage_text = self.batch[key]["usage_original"]["text"]
                for fragment in formula_parts:
                    self.assertIn(fragment, formula_text)
                for fragment in usage_parts:
                    self.assertIn(fragment, usage_text)

    def test_rendered_page_readings_cover_key_pages(self):
        expected_pages = {
            "shanghan:猪胆汁方": {152, 153},
            "shanghan:土瓜根方": {152},
            "shanghan:茵陈蒿汤": {153, 154, 161},
            "shanghan:吴茱萸汤": {156},
            "shanghan:麻子仁丸": {157, 158, 163},
            "shanghan:栀子蘗皮汤": {161, 162},
            "shanghan:麻黄连轺赤小豆汤": {162, 163},
        }
        for key, pages in expected_pages.items():
            with self.subTest(formula=key):
                actual = {row["page"] for row in self.batch[key]["page_reading"]}
                self.assertTrue(pages.issubset(actual))

    def test_missing_tuguagen_remains_missing(self):
        module = self.batch["shanghan:土瓜根方"]
        self.assertEqual(module["review_level"], "缺方")
        self.assertEqual(module["usage_status"], "missing")
        self.assertIn("方缺", module["formula_original"]["text"])
        self.assertIn("方缺", module["usage_original"]["text"])
        self.assertEqual(module["usage_modern"]["steps"], [])
        self.assertNotIn("土瓜根（", module["formula_original"]["text"])
        self.assertNotIn("捣汁", module["formula_original"]["text"])
        self.assertNotIn("捣汁", module["usage_original"]["text"])
        self.assertTrue(
            any("肘后" in note for note in module["usage_modern"]["cautions"])
        )

    def test_ancient_modern_and_variant_boundaries_are_separate(self):
        for key, module in self.batch.items():
            with self.subTest(formula=key):
                self.assertNotEqual(
                    module["usage_original"]["text"],
                    module["usage_modern"]["source_text"],
                )
                self.assertTrue(module["usage_modern"]["source_text"])
                if key != "shanghan:土瓜根方":
                    self.assertGreaterEqual(len(module["usage_modern"]["steps"]), 4)
                    self.assertGreaterEqual(len(module["usage_modern"]["cautions"]), 2)

        notes = {
            key: json.dumps(module, ensure_ascii=False)
            for key, module in self.batch.items()
        }
        self.assertIn("一斗", notes["shanghan:茵陈蒿汤"])
        self.assertIn("一斗二升", notes["shanghan:茵陈蒿汤"])
        self.assertIn("厚朴一斤", notes["shanghan:麻子仁丸"])
        self.assertIn("杏仁一斤", notes["shanghan:麻子仁丸"])
        self.assertIn("十四枚", notes["shanghan:栀子蘗皮汤"])
        self.assertIn("连翘", notes["shanghan:麻黄连轺赤小豆汤"])
        self.assertIn("潦水一升", notes["shanghan:麻黄连轺赤小豆汤"])
        self.assertIn("条方错配", notes["shanghan:栀子蘗皮汤"])
        self.assertIn("条方错配", notes["shanghan:麻黄连轺赤小豆汤"])

    def test_modern_book_text_and_safety_notes_are_preserved(self):
        zi_yin = self.batch["shanghan:茵陈蒿汤"]["usage_modern"]
        self.assertIn("先煮茵陈蒿", zi_yin["source_text"])
        self.assertIn("不可以随便加甘草", zi_yin["source_text"])

        wu_zhuyu = self.batch["shanghan:吴茱萸汤"]["usage_modern"]
        self.assertIn("吴茱萸用三钱", wu_zhuyu["source_text"])
        self.assertIn("呕酸", wu_zhuyu["source_text"])

        maziren = self.batch["shanghan:麻子仁丸"]["usage_modern"]
        self.assertIn("麻子仁二", maziren["source_text"])
        self.assertIn("攻破之剂", maziren["source_text"])
        self.assertIn("老人", "".join(maziren["cautions"]))

        zhizi = self.batch["shanghan:栀子蘗皮汤"]["usage_modern"]
        self.assertIn("栀子用二、三钱", zhizi["source_text"])
        self.assertIn("洗眼睛", zhizi["source_text"])

        mahuang = self.batch["shanghan:麻黄连轺赤小豆汤"]["usage_modern"]
        self.assertIn("桑白皮", mahuang["source_text"])
        self.assertIn("麻黄用二钱", mahuang["source_text"])
        self.assertTrue(any("麻黄" in row for row in mahuang["cautions"]))


if __name__ == "__main__":
    unittest.main()
