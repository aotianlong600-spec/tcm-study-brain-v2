import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "data" / "curated_batches" / "shanghan_107_112.json"

EXPECTED = [
    "shanghan:理中丸",
    "shanghan:通脉四逆加猪胆汁汤",
    "shanghan:烧裈散",
    "shanghan:枳实栀子豉汤",
    "shanghan:牡蛎泽泻散",
    "shanghan:竹叶石膏汤",
]


class Shanghan107112BatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modules = json.loads(BATCH.read_text(encoding="utf-8"))

    def test_exact_formula_set(self):
        self.assertEqual(list(self.modules), EXPECTED)

    def test_complete_reviewed_modules(self):
        for key, module in self.modules.items():
            with self.subTest(formula=key):
                self.assertEqual(module["review_status"], "reviewed")
                self.assertEqual(module["usage_status"], "reviewed")
                self.assertGreaterEqual(len(module["overview"]["paragraphs"]), 5)
                self.assertGreaterEqual(len(module["symptoms"]), 3)
                self.assertGreaterEqual(len(module["page_reading"]), 1)
                self.assertGreaterEqual(len(module["proofreading"]), 2)
                self.assertGreaterEqual(len(module["usage_modern"]["steps"]), 5)
                self.assertGreaterEqual(len(module["usage_modern"]["cautions"]), 4)
                self.assertGreaterEqual(len(module["rationale"]["full_text"]), 200)

    def test_original_doses_and_usage_are_preserved(self):
        expected = {
            "shanghan:理中丸": ["人参", "干姜", "甘草（炙）", "白术（各三两）", "用水八升"],
            "shanghan:通脉四逆加猪胆汁汤": ["甘草（二两炙）", "干姜（三两", "猪胆汁（半合）", "附子（大者一枚生"],
            "shanghan:烧裈散": ["妇人中裈近隐处", "水服方寸匕", "日三服"],
            "shanghan:枳实栀子豉汤": ["枳实（三枚炙）", "栀子（十四个擘）", "豉（一升绵裹）", "清浆水七升", "下豉"],
            "shanghan:牡蛎泽泻散": ["牡蛎（熬）", "泽泻", "蜀漆", "葶苈子", "商陆根", "海藻", "栝蒌根", "各等分"],
            "shanghan:竹叶石膏汤": ["竹叶（二把）", "石膏（一斤）", "人参（二两）", "粳米（半升）", "纳粳米"],
        }
        for key, needles in expected.items():
            text = self.modules[key]["formula_original"]["text"] + self.modules[key]["usage_original"]["text"]
            with self.subTest(formula=key):
                for needle in needles:
                    self.assertIn(needle, text)

    def test_no_ni_pdf_page_is_fabricated(self):
        for key in (
            "shanghan:理中丸",
            "shanghan:通脉四逆加猪胆汁汤",
            "shanghan:烧裈散",
            "shanghan:枳实栀子豉汤",
            "shanghan:牡蛎泽泻散",
            "shanghan:竹叶石膏汤",
        ):
            module_text = json.dumps(self.modules[key], ensure_ascii=False)
            self.assertIn("末篇", module_text)
            self.assertIn("辑义", module_text)

    def test_high_risk_warnings_are_explicit(self):
        combined = {
            key: json.dumps(module, ensure_ascii=False)
            for key, module in self.modules.items()
        }
        self.assertIn("生附子", combined["shanghan:通脉四逆加猪胆汁汤"])
        self.assertIn("禁止", combined["shanghan:烧裈散"])
        self.assertIn("商陆", combined["shanghan:牡蛎泽泻散"])
        self.assertIn("蜀漆", combined["shanghan:牡蛎泽泻散"])
        self.assertIn("生半夏", combined["shanghan:竹叶石膏汤"])
        self.assertIn("急诊", combined["shanghan:竹叶石膏汤"])
        self.assertIn("不是基础四味之一", combined["shanghan:理中丸"])

    def test_same_name_boundaries_are_documented(self):
        lizhong = self.modules["shanghan:理中丸"]
        self.assertIn("霍乱", lizhong["six_channel"]["name"])
        self.assertIn("理中", lizhong["formula_original"]["text"])
        zhuye = self.modules["shanghan:竹叶石膏汤"]
        self.assertIn("白虎汤", zhuye["rationale"]["full_text"])


if __name__ == "__main__":
    unittest.main()
