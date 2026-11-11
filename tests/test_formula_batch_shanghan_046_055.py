import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "data" / "curated_batches" / "shanghan_046_055.json"

EXPECTED = [
    "shanghan:抵当丸",
    "shanghan:大陷胸丸",
    "shanghan:大陷胸汤",
    "shanghan:小陷胸汤",
    "shanghan:文蛤散",
    "shanghan:白散",
    "shanghan:柴胡桂枝汤",
    "shanghan:柴胡桂枝干姜汤",
    "shanghan:半夏泻心汤",
    "shanghan:十枣汤",
]

ALIASES = {"白术": ("白术", "白朮"), "豆豉": ("豆豉", "豉")}
TOXIC = {
    "shanghan:抵当丸": ("水蛭", "虻虫"),
    "shanghan:大陷胸丸": ("甘遂",),
    "shanghan:大陷胸汤": ("甘遂",),
    "shanghan:白散": ("巴豆",),
    "shanghan:十枣汤": ("芫花", "甘遂", "大戟"),
}


class Shanghan046055BatchTest(unittest.TestCase):
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
                self.assertEqual(module["review_status"], "reviewed")
                self.assertEqual(module["usage_status"], "reviewed")
                self.assertGreaterEqual(len(module["overview"]["paragraphs"]), 4)
                self.assertGreaterEqual(len(module["symptoms"]), 3)
                self.assertGreaterEqual(len(module["six_channel"]["original"]), 1)
                self.assertGreaterEqual(len(module["six_channel"]["annotations"]), 1)
                self.assertGreaterEqual(len(module["page_reading"]), 1)
                self.assertGreaterEqual(len(module["proofreading"]), 2)
                self.assertGreaterEqual(len(module["usage_modern"]["steps"]), 4)
                self.assertGreaterEqual(len(module["usage_modern"]["cautions"]), 4)
                self.assertGreaterEqual(len(module["rationale"]["full_text"]), 200)

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
                self.assertTrue(all(isinstance(row["page"], int) for row in module["page_reading"]))
                self.assertTrue(module["formula_original"]["source_pages"])
                self.assertTrue(module["usage_original"]["source_pages"])
                self.assertTrue(module["six_channel"]["proof_note"])

    def test_no_placeholder_language(self):
        text = json.dumps(self.modules, ensure_ascii=False)
        for forbidden in ("TODO", "TBD", "本地文件夹未找到", "当前没有把", "冒充"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
