import json
import unittest
from pathlib import Path

from etl.review_ledger import (
    load_source_catalog,
    validate_record_provenance,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "source-evidence.schema.json"


class ProvenanceLedgerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = load_source_catalog()
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.sample_pages = {
            "ni-acupuncture-v2-20100703:p042": {
                "page_id": "ni-acupuncture-v2-20100703:p042",
                "source_id": "ni-acupuncture-v2-20100703",
                "pdf_page": 42,
                "printed_page": 42,
                "body_text": "中府如果直刺，容易扎到肺。云门是肺的募穴，这两个穴道靠肺很近。",
                "raw_text": "中府如果直刺，容易扎到肺。云门是肺的募穴，这两个穴道靠肺很近。",
                "footnotes": [],
            }
        }

    def test_schema_defines_orthogonal_statuses_and_content_layers(self):
        defs = self.schema["definitions"]
        self.assertEqual(defs["reviewStatus"]["enum"], ["pending", "needs_changes", "approved", "rejected"])
        self.assertEqual(defs["riskLevel"]["enum"], ["standard", "high_risk", "emergency"])
        self.assertIn("collation_notes", defs["contentLayers"]["required"])

    def test_valid_record_passes_and_fabricated_citation_fails(self):
        valid = {
            "id": "acupoint:中府",
            "record_type": "acupoint",
            "canonical_name": "中府",
            "aliases": [],
            "summary": "手太阴肺经第一穴",
            "source_spans": [
                {
                    "span_id": "sp-1",
                    "source_id": "ni-acupuncture-v2-20100703",
                    "page_id": "ni-acupuncture-v2-20100703:p042",
                    "pdf_page": 42,
                    "printed_page": 42,
                    "quote": "中府如果直刺，容易扎到肺",
                }
            ],
            "content_layers": {
                "source_quote": ["中府如果直刺，容易扎到肺。"],
                "ni_teaching": ["扁鹊针灸手法是一针透两穴。"],
                "other_annotations": [],
                "collation_notes": [],
                "organizer_summary": ["中府透云门，避肺防气胸。"],
            },
            "open_questions": [],
            "generation_status": "manual",
            "evidence_status": "verified",
            "review_status": "approved",
            "risk_level": "high_risk",
            "safety_warning": "紧邻胸膜肺尖，切忌直刺过深。",
            "version": "1.0",
        }
        self.assertEqual(validate_record_provenance(valid, self.sources, self.sample_pages), [])

        fake_quote = json.loads(json.dumps(valid))
        fake_quote["source_spans"][0]["quote"] = "本页完全不存在的捏造引文"
        errors = validate_record_provenance(fake_quote, self.sources, self.sample_pages)
        self.assertTrue(any("quote not found" in err for err in errors))

        missing_page = json.loads(json.dumps(valid))
        missing_page["source_spans"][0]["page_id"] = "ni-acupuncture-v2-20100703:p999"
        errors2 = validate_record_provenance(missing_page, self.sources, self.sample_pages)
        self.assertTrue(any("unknown page_id" in err for err in errors2))

        missing_warning = json.loads(json.dumps(valid))
        missing_warning["safety_warning"] = ""
        errors3 = validate_record_provenance(missing_warning, self.sources, self.sample_pages)
        self.assertTrue(any("safety_warning" in err for err in errors3))

        auto_approved = json.loads(json.dumps(valid))
        auto_approved["generation_status"] = "auto"
        errors4 = validate_record_provenance(auto_approved, self.sources, self.sample_pages)
        self.assertTrue(any("auto-generated" in err for err in errors4))


if __name__ == "__main__":
    unittest.main()
