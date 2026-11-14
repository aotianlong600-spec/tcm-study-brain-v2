import copy
import json
from pathlib import Path
import unittest

from etl.neijing.validate import load_external_target_ids, validate_all, validate_batch_payload
from etl.review_ledger import load_pages_index, load_source_catalog


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "neijing"


class NeijingBatchesAndCompiledTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.passages = json.loads((DATA_DIR / "passages.json").read_text(encoding="utf-8"))
        cls.concepts = json.loads((DATA_DIR / "concepts.json").read_text(encoding="utf-8"))
        cls.relations = json.loads((DATA_DIR / "relations.json").read_text(encoding="utf-8"))

    def test_validate_accepted_and_compiled_zero_errors(self):
        count, errors = validate_all(accepted_only=True, check_compiled=True)
        self.assertEqual(count, 7)
        self.assertEqual(errors, [])

    def test_all_six_doctrine_submodules_and_cross_module_links_present(self):
        self.assertEqual(self.passages["stats"]["total"], 74)
        self.assertEqual(self.passages["stats"]["approved"], 74)
        self.assertEqual(self.passages["stats"]["pending"], 0)
        self.assertEqual(self.concepts["stats"]["approved"], 34)
        by_sub = self.concepts["stats"]["by_submodule"]
        for key in (
            "yin_yang_wu_xing",
            "zang_xiang",
            "bing_yin_bing_ji",
            "zhen_fa",
            "bian_zheng",
            "yang_sheng",
        ):
            self.assertGreaterEqual(by_sub.get(key, 0), 5, key)
        by_target = self.relations["stats"]["by_target_module"]
        for mod in ("neijing", "acupuncture", "six_channels", "formulas", "jinkui_formulas", "herbs"):
            self.assertGreaterEqual(by_target.get(mod, 0), 10, mod)

    def test_fabricated_quote_or_dangling_cross_link_fails_validation(self):
        batch = json.loads((DATA_DIR / "review_batches" / "nj_thematic_concepts.json").read_text(encoding="utf-8"))
        broken = copy.deepcopy(batch)
        broken["concepts"][0]["source_spans"][0]["quote"] = "完全虚构的不存在内经原句"
        broken["concepts"][0]["classic_links"][0]["target_id"] = "shanghan:不存在的经方"
        errors = validate_batch_payload(
            broken,
            load_source_catalog(),
            load_pages_index(ROOT / "sources" / "neijing" / "pages.jsonl"),
            load_external_target_ids(),
        )
        self.assertTrue(any("not found verbatim" in e for e in errors))
        self.assertTrue(any("dangling" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
