from __future__ import annotations

import json
from pathlib import Path
import unittest

from etl.acupuncture.validate import validate_all


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "acupuncture"


class AcupunctureBatchesAndCompiledTest(unittest.TestCase):
    def test_validate_accepted_and_compiled_zero_errors(self):
        count, errors = validate_all(accepted_only=True, check_compiled=True)
        self.assertEqual(count, 11)
        self.assertEqual(errors, [])

    def test_full_book_meridian_points_techniques_and_conditions_shape(self):
        meridians = json.loads((DATA_DIR / "meridians.json").read_text(encoding="utf-8"))
        acupoints = json.loads((DATA_DIR / "acupoints.json").read_text(encoding="utf-8"))
        techniques = json.loads((DATA_DIR / "techniques.json").read_text(encoding="utf-8"))
        conditions = json.loads((DATA_DIR / "conditions.json").read_text(encoding="utf-8"))
        relations = json.loads((DATA_DIR / "relations.json").read_text(encoding="utf-8"))

        self.assertEqual(meridians["stats"]["total"], 15)
        self.assertEqual(meridians["stats"]["approved"], 15)
        self.assertEqual(acupoints["stats"]["total"], 387)
        self.assertEqual(acupoints["stats"]["approved"], 385)
        self.assertEqual(techniques["stats"]["total"], 86)
        self.assertEqual(techniques["stats"]["approved"], 86)
        self.assertEqual(conditions["stats"]["total"], 34)
        self.assertEqual(conditions["stats"]["approved"], 34)
        self.assertEqual(relations["stats"]["total"], 1364)

        pending_points = {pt["id"] for pt in acupoints["items"] if pt["review_status"] == "pending"}
        self.assertEqual(pending_points, {"acupoint:st21:梁门", "acupoint:lv12:急脉"})

        lu_points = [pt for pt in acupoints["items"] if pt.get("meridian_id") == "meridian:lu"]
        self.assertEqual(len(lu_points), 11)
        for pt in lu_points:
            self.assertEqual(pt["review_status"], "approved")
            self.assertEqual(pt["risk_level"], "high_risk")
            self.assertTrue(pt["open_questions"])

        brain = next(c for c in conditions["items"] if c["id"] == "cond:ch6:头部与脑瘤治症")
        self.assertEqual(brain["risk_level"], "emergency")
        self.assertEqual(len(brain["sub_patterns"]), 7)
        self.assertTrue(any("全蝎" in json.dumps(brain, ensure_ascii=False) for _ in [1]))

        ghost = next(c for c in conditions["items"] if c["id"] == "cond:ch6:s296")
        self.assertEqual(ghost["review_status"], "approved")
        self.assertTrue(ghost["open_questions"])


if __name__ == "__main__":
    unittest.main()
