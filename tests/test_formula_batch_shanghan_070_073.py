import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BATCH_PATH = ROOT / "data" / "curated_batches" / "shanghan_070_073.json"

EXPECTED_FORMULAS = {
    "shanghan:白虎汤",
    "shanghan:炙甘草汤",
    "shanghan:大承气汤",
    "shanghan:小承气汤",
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


class ShanghanBatch070073Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modules = json.loads(BATCH_PATH.read_text(encoding="utf-8"))

    def test_exact_formula_set(self):
        self.assertEqual(set(self.modules), EXPECTED_FORMULAS)
        self.assertTrue(all(key.startswith("shanghan:") for key in self.modules))

    def test_complete_module_structure(self):
        for key, module in self.modules.items():
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
                self.assertEqual(module["review_level"], "完整")
                self.assertEqual(module["usage_status"], "reviewed")
                self.assertTrue(module["usage_plain"])
                self.assertTrue(module["why"])
                self.assertGreaterEqual(len(module["symptoms"]), 6)
                self.assertGreaterEqual(len(module["overview"]["paragraphs"]), 5)
                self.assertGreaterEqual(len(module["overview"]["key_points"]), 6)
                self.assertGreaterEqual(len(module["six_channel"]["original"]), 2)
                self.assertGreaterEqual(
                    len(module["six_channel"]["annotations"]), 3
                )
                self.assertGreaterEqual(
                    len(module["six_channel"]["annotation_original"]), 3
                )
                self.assertGreaterEqual(len(module["rationale"]["full_text"]), 250)
                self.assertGreaterEqual(len(module["annotations"]), 3)
                self.assertGreaterEqual(len(module["page_reading"]), 2)
                self.assertGreaterEqual(len(module["proofreading"]), 3)
                for row in module["symptoms"]:
                    self.assertEqual(set(row), {"name", "source", "page"})
                    self.assertIsInstance(row["page"], int)
                for row in module["annotations"]:
                    self.assertEqual(set(row), {"heading", "text", "source_page"})
                    self.assertIsInstance(row["source_page"], int)
                for row in module["page_reading"]:
                    self.assertEqual(
                        set(row), {"page", "title", "kind", "text", "annotation"}
                    )
                    self.assertIsInstance(row["page"], int)

    def test_six_channel_identity_and_explicit_duplicates(self):
        self.assertEqual(
            self.modules["shanghan:白虎汤"]["six_channel"]["id"],
            "yangming",
        )
        self.assertEqual(
            self.modules["shanghan:炙甘草汤"]["six_channel"]["id"],
            "taiyang",
        )
        self.assertIn(
            "里虚",
            self.modules["shanghan:炙甘草汤"]["six_channel"]["name"],
        )
        for key in ("shanghan:大承气汤", "shanghan:小承气汤"):
            self.assertEqual(self.modules[key]["six_channel"]["id"], "yangming")
            self.assertEqual(self.modules[key]["six_channel"]["name"], "阳明病")

        baihu = self.modules["shanghan:白虎汤"]
        self.assertIn("厥阴", baihu["six_channel"]["summary"])
        self.assertIn("脉滑而厥", " ".join(baihu["six_channel"]["original"]))
        self.assertIn(197, baihu["six_channel"]["source_pages"])

        dachengqi = self.modules["shanghan:大承气汤"]
        self.assertIn("少阴篇", dachengqi["six_channel"]["summary"])
        self.assertIn("自利清水", " ".join(dachengqi["six_channel"]["original"]))
        self.assertIn(187, dachengqi["six_channel"]["source_pages"])
        self.assertIn(188, dachengqi["six_channel"]["source_pages"])

    def test_doses_and_classical_decoctions_are_preserved(self):
        expected = {
            "shanghan:白虎汤": (
                "知母（六两）",
                "石膏（一斤碎）",
                "甘草（二两炙）",
                "粳米（六合）",
                "以水一斗",
                "煮米熟",
                "温服一升",
                "日三服",
            ),
            "shanghan:炙甘草汤": (
                "甘草（四两炙）",
                "生地黄（一斤）",
                "大枣（三十枚擘）",
                "阿胶（二两）",
                "清酒七升",
                "水八升",
                "先煮八味",
                "纳胶烊消尽",
            ),
            "shanghan:大承气汤": (
                "厚朴（半斤炙去皮）",
                "枳实（五枚炙）",
                "芒硝（三合）",
                "大黄（四两酒洗）",
                "先煮二物",
                "纳大黄",
                "纳芒硝",
                "得下余勿服",
            ),
            "shanghan:小承气汤": (
                "大黄（四两）",
                "厚朴（二两炙去皮）",
                "枳实（三枚大者炙）",
                "以水四升",
                "煮取一升二合",
                "初服汤当更衣",
                "若更衣者。勿服之",
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

    def test_rendered_pages_cover_all_key_source_pages(self):
        expected_pages = {
            "shanghan:白虎汤": {128, 197},
            "shanghan:炙甘草汤": {128, 129, 130},
            "shanghan:大承气汤": {141, 142, 143, 187, 188},
            "shanghan:小承气汤": {141, 142, 143},
        }
        valid_pages = {
            128,
            129,
            130,
            141,
            142,
            143,
            187,
            188,
            197,
        }
        for key, module in self.modules.items():
            actual = {row["page"] for row in module["page_reading"]}
            with self.subTest(formula=key):
                self.assertTrue(expected_pages[key].issubset(actual))
                self.assertTrue(actual.issubset(valid_pages))

    def test_ancient_modern_and_organized_steps_are_separate(self):
        for key, module in self.modules.items():
            with self.subTest(formula=key):
                usage = module["usage_modern"]
                self.assertNotEqual(
                    module["usage_original"]["text"],
                    usage["source_text"],
                )
                self.assertTrue(usage["summary"])
                self.assertTrue(usage["source_text"])
                self.assertGreaterEqual(len(usage["steps"]), 5)
                self.assertGreaterEqual(len(usage["cautions"]), 5)
                self.assertTrue(usage["source_pages"])

        baihu = self.modules["shanghan:白虎汤"]
        self.assertIn("石膏可以用到一两", baihu["usage_modern"]["source_text"])
        self.assertIn("两茶匙", baihu["usage_modern"]["source_text"])

        zhigancao = self.modules["shanghan:炙甘草汤"]
        self.assertIn("三碗酒四碗水", zhigancao["usage_modern"]["source_text"])
        self.assertIn("一碗撒一钱阿胶", zhigancao["usage_modern"]["source_text"])

        dachengqi = self.modules["shanghan:大承气汤"]
        self.assertIn("十碗煮成五碗", dachengqi["usage_modern"]["source_text"])
        self.assertIn("微煮一二沸", dachengqi["usage_modern"]["source_text"])

        xiaochengqi = self.modules["shanghan:小承气汤"]
        self.assertIn("没有结硬块", xiaochengqi["usage_modern"]["source_text"])
        self.assertIn("少与小承气汤", xiaochengqi["usage_modern"]["source_text"])

    def test_baihu_textual_conflicts_are_explicit(self):
        module = self.modules["shanghan:白虎汤"]
        formula = module["formula_original"]
        self.assertIn("表有热。里有寒", formula["text"])
        self.assertIn("甘草（二两炙）", formula["text"])
        self.assertIn("倪书页128作“表有寒，里有热”", formula["note"])
        self.assertIn("甘草未标炙", formula["note"])
        self.assertIn("一斗二升", formula["note"])
        self.assertIn("表有寒，里有热", module["page_reading"][0]["text"])
        self.assertIn("表有热、里有寒", module["proofreading"][2]["note"])

    def test_zhigancao_liquor_ratio_and_pulse_definitions(self):
        module = self.modules["shanghan:炙甘草汤"]
        usage = module["usage_original"]["text"]
        self.assertIn("清酒七升", usage)
        self.assertIn("水八升", usage)
        self.assertIn("先煮八味", usage)
        self.assertIn("取三升", usage)
        self.assertIn("纳胶烊消尽", usage)

        pulse_text = " ".join(module["six_channel"]["original"])
        self.assertIn("时一止复来者，名曰结", pulse_text)
        self.assertIn("不能自还，因而复动者，名曰代阴也", pulse_text)
        self.assertIn("三十枚", module["formula_original"]["text"])
        self.assertIn("十二枚", module["formula_original"]["note"])
        self.assertIn("二两洗", module["formula_original"]["note"])

    def test_chengqi_differences_and_small_formula_wine_conflict(self):
        da = self.modules["shanghan:大承气汤"]
        xiao = self.modules["shanghan:小承气汤"]

        self.assertIn("芒硝（三合）", da["formula_original"]["text"])
        self.assertIn("先煮二物", da["usage_original"]["text"])
        self.assertIn("纳大黄", da["usage_original"]["text"])
        self.assertIn("纳芒硝", da["usage_original"]["text"])
        self.assertIn("得下余勿服", da["usage_original"]["text"])

        self.assertNotIn("芒硝（", xiao["formula_original"]["text"])
        self.assertIn("大黄（四两）", xiao["formula_original"]["text"])
        self.assertIn("以水四升", xiao["usage_original"]["text"])
        self.assertIn("三味同", " ".join(xiao["usage_modern"]["steps"]))
        self.assertIn("方剂排印作“大黄四两酒洗”", xiao["formula_original"]["note"])
        self.assertIn("直接冲突", xiao["proofreading"][2]["note"])
        self.assertIn(
            "小承气汤的大黄没有用酒洗",
            xiao["usage_modern"]["source_text"],
        )

        self.assertIn("满而实", da["usage_modern"]["source_text"])
        self.assertIn("没有结硬块", xiao["usage_modern"]["source_text"])

    def test_high_risk_and_emergency_boundaries_are_preserved(self):
        combined = {
            key: json.dumps(module, ensure_ascii=False)
            for key, module in self.modules.items()
        }
        for key, text in combined.items():
            with self.subTest(formula=key):
                self.assertIn("急诊", text)
                self.assertTrue(
                    any(
                        phrase in text
                        for phrase in (
                            "不得自行",
                            "不应自行",
                            "不能自行",
                            "无专业辨证不得",
                        )
                    )
                )

        self.assertIn("意识改变", combined["shanghan:白虎汤"])
        self.assertIn("心律", combined["shanghan:炙甘草汤"])
        self.assertIn("酒精", combined["shanghan:炙甘草汤"])
        self.assertIn("肠梗阻", combined["shanghan:大承气汤"])
        self.assertIn("得下余勿服", combined["shanghan:大承气汤"])
        self.assertIn("更衣者，勿服之", combined["shanghan:小承气汤"])

    def test_no_placeholder_or_unresolved_scope_notes(self):
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
