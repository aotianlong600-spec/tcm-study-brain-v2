from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
BATCH_PATH = ROOT / "data" / "curated_batches" / "jinkui_001_007.json"


class JinkuiBatch001007Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not BATCH_PATH.exists():
            raise unittest.SkipTest("jinkui batch is deferred until the Shanghan milestone")
        cls.batch = json.loads(BATCH_PATH.read_text(encoding="utf-8"))

    def test_batch_has_expected_formulas_in_source_order(self):
        self.assertEqual(
            list(self.batch),
            [
                "jinkui:理中丸",
                "jinkui:通脉四逆加猪胆汁汤",
                "jinkui:栝篓桂枝汤",
                "jinkui:葛根汤",
                "jinkui:大承气汤",
                "jinkui:麻黄加术汤",
                "jinkui:麻黄杏仁薏苡甘草汤",
            ],
        )

    def test_each_formula_is_a_complete_reviewed_module(self):
        required = {
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
        for key, module in self.batch.items():
            with self.subTest(formula=key):
                self.assertTrue(required.issubset(module))
                self.assertEqual(module["review_status"], "reviewed")
                self.assertEqual(module["review_level"], "完整")
                self.assertEqual(module["usage_status"], "reviewed")
                self.assertGreaterEqual(len(module["symptoms"]), 5)
                self.assertGreaterEqual(len(module["overview"]["paragraphs"]), 4)
                self.assertGreaterEqual(len(module["overview"]["key_points"]), 5)
                self.assertGreaterEqual(len(module["six_channel"]["original"]), 1)
                self.assertGreaterEqual(len(module["six_channel"]["annotations"]), 2)
                self.assertGreaterEqual(len(module["page_reading"]), 2)
                self.assertGreaterEqual(len(module["usage_modern"]["steps"]), 4)
                self.assertGreaterEqual(len(module["usage_modern"]["cautions"]), 2)
                self.assertGreaterEqual(len(module["rationale"]["full_text"]), 250)
                self.assertGreaterEqual(len(module["annotations"]), 3)
                self.assertGreaterEqual(len(module["proofreading"]), 2)
                for section in ("overview", "six_channel", "formula_original", "usage_original", "usage_modern", "rationale"):
                    self.assertIsInstance(module[section], dict)

    def test_original_doses_and_decoctions_survive(self):
        expected = {
            "jinkui:理中丸": [
                "人参 甘草 白术 干姜各三两",
                "如鸡子黄大",
                "用水八升，煮取三升",
                "服汤后如食顷，饮热粥一升许",
            ],
            "jinkui:通脉四逆加猪胆汁汤": [
                "甘草二两，炙",
                "干姜三两，强人可四两",
                "附子大者一枚，生",
                "猪胆汁半合",
                "以水三升，煮取一升二合",
            ],
            "jinkui:栝篓桂枝汤": [
                "栝蒌根二两",
                "桂枝三两",
                "芍药三两",
                "甘草二两",
                "以水九升，煮取三升",
            ],
            "jinkui:葛根汤": [
                "葛根四两",
                "麻黄三两，去节",
                "桂枝二两",
                "甘草二两，炙",
                "芍药二两",
                "先煮麻黄葛根",
            ],
            "jinkui:大承气汤": [
                "厚朴半斤，炙，去皮",
                "大黄四两，酒洗",
                "枳实五枚，炙",
                "芒硝三合",
                "先煮枳朴",
                "得下利，余勿服",
            ],
            "jinkui:麻黄加术汤": [
                "麻黄三两，去节",
                "桂枝二两",
                "甘草一两",
                "白术四两",
                "杏仁七十个，去皮尖",
                "覆取微汗",
            ],
            "jinkui:麻黄杏仁薏苡甘草汤": [
                "麻黄半两",
                "杏仁十个，去皮尖",
                "薏苡半两",
                "甘草一两，炙",
                "每服四钱匕",
                "有微汗，避风",
            ],
        }
        for key, phrases in expected.items():
            with self.subTest(formula=key):
                source = self.batch[key]["formula_original"]["text"] + "\n" + self.batch[key]["usage_original"]["text"]
                for phrase in phrases:
                    self.assertIn(phrase, source)

    def test_pages_and_video_transcripts_are_explicit(self):
        expected_book_pages = {
            "jinkui:理中丸": {11, 12, 418},
            "jinkui:通脉四逆加猪胆汁汤": {13},
            "jinkui:栝篓桂枝汤": {43, 44},
            "jinkui:葛根汤": {45, 46},
            "jinkui:大承气汤": {47, 48},
            "jinkui:麻黄加术汤": {55, 56},
            "jinkui:麻黄杏仁薏苡甘草汤": {56, 57},
        }
        for key, pages in expected_book_pages.items():
            with self.subTest(formula=key):
                module = self.batch[key]
                self.assertTrue(pages.issubset(set(module["six_channel"]["source_pages"])))
                proof_titles = " ".join(row["title"] for row in module["proofreading"])
                proof_notes = " ".join(row["note"] for row in module["proofreading"])
                self.assertIn("倪海厦注金匮要略", proof_titles)
                self.assertIn("视频同步文稿", proof_titles)
                self.assertIn("页", proof_notes)
                self.assertTrue(all(row["page"] for row in module["page_reading"]))

    def test_version_differences_are_not_silently_normalized(self):
        textual = {
            key: json.dumps(module, ensure_ascii=False)
            for key, module in self.batch.items()
        }
        self.assertIn("栝篓", textual["jinkui:栝篓桂枝汤"])
        self.assertIn("栝蒌", textual["jinkui:栝篓桂枝汤"])
        self.assertIn("减三升", textual["jinkui:葛根汤"])
        self.assertIn("减二升", textual["jinkui:葛根汤"])
        self.assertIn("桂技", textual["jinkui:麻黄加术汤"])
        self.assertIn("桂枝", textual["jinkui:麻黄加术汤"])
        self.assertIn("薏苡仁", textual["jinkui:麻黄杏仁薏苡甘草汤"])
        self.assertIn("强人可四两", textual["jinkui:通脉四逆加猪胆汁汤"])
        self.assertIn("甘草未标炙", textual["jinkui:理中丸"])
        self.assertIn("倪注解释作炙甘草", textual["jinkui:理中丸"])

    def test_missing_formula_notice_is_not_fabricated(self):
        serialized = json.dumps(self.batch, ensure_ascii=False)
        for forbidden in (
            "本地文件夹未找到",
            "本地未找到",
            "当前没有把《金匮要略》文稿冒充伤寒论文稿",
            "伤寒独立视频同步文稿缺失",
        ):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
