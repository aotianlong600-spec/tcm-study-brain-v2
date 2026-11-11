import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BATCH_PATH = ROOT / "data" / "curated_batches" / "shanghan_090_096.json"

EXPECTED_FORMULAS = {
    "shanghan:猪肤汤",
    "shanghan:甘草汤",
    "shanghan:桔梗汤",
    "shanghan:苦酒汤",
    "shanghan:半夏散及汤",
    "shanghan:白通汤",
    "shanghan:白通加猪胆汁汤",
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


class Shanghan090096BatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modules = json.loads(BATCH_PATH.read_text(encoding="utf-8"))

    def test_exact_formula_set(self):
        self.assertEqual(set(self.modules), EXPECTED_FORMULAS)

    def test_complete_module_structure(self):
        for key, module in self.modules.items():
            with self.subTest(formula=key):
                self.assertEqual(set(module), REQUIRED_FIELDS)
                self.assertEqual(module["review_status"], "reviewed")
                self.assertEqual(module["review_level"], "完整")
                self.assertEqual(module["usage_status"], "reviewed")
                self.assertTrue(module["usage_plain"])
                self.assertGreaterEqual(len(module["symptoms"]), 1)
                self.assertGreaterEqual(len(module["overview"]["paragraphs"]), 4)
                self.assertGreaterEqual(len(module["overview"]["key_points"]), 5)
                self.assertGreaterEqual(len(module["rationale"]["full_text"]), 200)
                self.assertGreaterEqual(len(module["annotations"]), 3)
                self.assertGreaterEqual(len(module["proofreading"]), 3)

    def test_six_channel_has_original_and_annotation(self):
        for key, module in self.modules.items():
            with self.subTest(formula=key):
                six_channel = module["six_channel"]
                self.assertEqual(six_channel["id"], "shaoyin")
                self.assertEqual(six_channel["name"], "少阴病")
                self.assertGreaterEqual(len(six_channel["original"]), 3)
                self.assertGreaterEqual(len(six_channel["annotations"]), 3)
                self.assertGreaterEqual(len(six_channel["annotation_original"]), 3)
                self.assertTrue(six_channel["proof_note"])
                self.assertTrue(six_channel["source_pages"])

    def test_doses_and_classical_usage_are_preserved(self):
        expected = {
            "shanghan:猪肤汤": ("猪肤（一斤）", "白蜜一升", "白粉五合", "温分六服"),
            "shanghan:甘草汤": ("甘草（二两）", "温服七合", "日二服"),
            "shanghan:桔梗汤": ("桔梗（一两）", "甘草（二两）", "温分再服"),
            "shanghan:苦酒汤": (
                "半夏（洗破如枣核十四枚）",
                "鸡子（一枚",
                "令三沸",
                "少少含咽之",
            ),
            "shanghan:半夏散及汤": (
                "等分",
                "白饮和服方寸匕",
                "日三服",
                "两方寸匕",
                "半夏有毒",
            ),
            "shanghan:白通汤": (
                "葱白（四茎）",
                "干姜（一两）",
                "附子（一枚生",
                "分温再服",
            ),
            "shanghan:白通加猪胆汁汤": (
                "人尿（五合）",
                "猪胆汁（一合）",
                "上五味",
                "脉暴出者死",
                "微续者生",
            ),
        }
        for key, needles in expected.items():
            text = self.modules[key]["formula_original"]["text"] + self.modules[key][
                "usage_original"
            ]["text"]
            with self.subTest(formula=key):
                for needle in needles:
                    self.assertIn(needle, text)

    def test_page_reading_is_direct_and_page_mapped(self):
        expected_pages = {
            "shanghan:猪肤汤": {181, 182},
            "shanghan:甘草汤": {182},
            "shanghan:桔梗汤": {182},
            "shanghan:苦酒汤": {182, 183},
            "shanghan:半夏散及汤": {183},
            "shanghan:白通汤": {183, 184},
            "shanghan:白通加猪胆汁汤": {184},
        }
        for key, module in self.modules.items():
            pages = {row["page"] for row in module["page_reading"]}
            with self.subTest(formula=key):
                self.assertTrue(expected_pages[key].issubset(pages))
                for item in module["page_reading"]:
                    self.assertIsInstance(item["page"], int)
                    self.assertTrue(181 <= item["page"] <= 184)
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
                self.assertGreaterEqual(len(usage["cautions"]), 4)
                self.assertTrue(usage["source_pages"])

    def test_textual_conflicts_are_explicit(self):
        pig_skin = self.modules["shanghan:猪肤汤"]
        self.assertIn("白粉五合", pig_skin["formula_original"]["text"])
        self.assertIn("米粉", pig_skin["usage_modern"]["source_text"])
        self.assertIn("猪肤取材", pig_skin["proofreading"][2]["title"])

        licorice = self.modules["shanghan:甘草汤"]
        self.assertIn("日二服", licorice["formula_original"]["text"])
        self.assertIn("日一服", licorice["usage_modern"]["source_text"])
        self.assertIn("外台", licorice["proofreading"][0]["note"])

        bitter_wine = self.modules["shanghan:苦酒汤"]
        self.assertIn("鸡子（一枚", bitter_wine["formula_original"]["text"])
        self.assertIn("鸡子十枚", bitter_wine["usage_modern"]["source_text"])
        self.assertIn("十枚", bitter_wine["proofreading"][1]["note"])

        pinellia = self.modules["shanghan:半夏散及汤"]
        self.assertIn("白饮和服方寸匕", pinellia["formula_original"]["text"])
        self.assertIn("七寸匕", pinellia["usage_modern"]["source_text"])
        self.assertIn("七寸匕", pinellia["proofreading"][1]["note"])

        baitong_bile = self.modules["shanghan:白通加猪胆汁汤"]
        self.assertIn("上五味", baitong_bile["formula_original"]["text"])
        self.assertIn("右三味", baitong_bile["usage_modern"]["source_text"])
        self.assertIn("并非", baitong_bile["formula_original"]["note"])

    def test_high_risk_warnings_are_preserved(self):
        combined = {
            key: json.dumps(module, ensure_ascii=False)
            for key, module in self.modules.items()
        }
        for key in ("shanghan:苦酒汤", "shanghan:半夏散及汤"):
            self.assertIn("生半夏", combined[key])
        self.assertIn("生鸡子", combined["shanghan:苦酒汤"])
        self.assertIn("不得自行", combined["shanghan:半夏散及汤"])

        for key in ("shanghan:白通汤", "shanghan:白通加猪胆汁汤"):
            self.assertIn("生附子", combined[key])
            self.assertIn("不得自行", combined[key])
            self.assertIn("急诊", combined[key])

        self.assertIn("人尿", combined["shanghan:白通加猪胆汁汤"])
        self.assertIn("猪胆汁", combined["shanghan:白通加猪胆汁汤"])

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
