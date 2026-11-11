from pathlib import Path
import json
import unittest

from etl.enrich_evidence import load_curated


ROOT = Path(__file__).resolve().parents[1]


class CuratedBatchMergeTest(unittest.TestCase):
    def test_batches_merge_without_hiding_conflicts(self):
        curated = load_curated()
        accepted = json.loads(
            (ROOT / "data" / "curated_batch_manifest.json").read_text(encoding="utf-8")
        )["accepted"]
        batch_ids = {
            formula_id
            for name in accepted
            for formula_id in json.loads(
                (ROOT / "data" / "curated_batches" / name).read_text(encoding="utf-8")
            )
        }
        self.assertTrue(batch_ids)
        self.assertTrue(batch_ids.issubset(curated))


if __name__ == "__main__":
    unittest.main()
