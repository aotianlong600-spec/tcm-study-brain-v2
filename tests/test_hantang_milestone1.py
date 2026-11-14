from __future__ import annotations

import json
import unittest
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from app.main import app
from app.static_dispatch import dispatch_api


class HantangMilestone1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_overview_completeness_and_epistemic_isolation(self):
        ov_resp = self.client.get("/api/hantang/overview")
        self.assertEqual(ov_resp.status_code, 200)
        ov = ov_resp.json()

        self.assertEqual(ov["formula_count"], 91)
        self.assertEqual(ov["missing_numbers"], [55, 56, 57, 58, 75, 76, 86, 91, 94])
        self.assertEqual(len(ov["categories"]), 7)
        self.assertEqual(sum(c["count"] for c in ov["categories"]), 91)
        self.assertEqual(len(ov["du_spine_diagnostics"]), 5)
        self.assertEqual(len(ov["special_palpation_points"]), 6)
        self.assertEqual(len(ov["western_history_rules"]), 7)
        self.assertEqual(len(ov["clinical_redlines"]), 10)
        self.assertEqual(len(ov["cases_index"]), 12)

        notice = ov["epistemic_notice"]
        self.assertIn("严禁", notice)
        self.assertIn("倪海厦", notice)
        self.assertIn("紫极", notice)

        list_resp = self.client.get("/api/hantang/formulas")
        self.assertEqual(list_resp.status_code, 200)
        items = list_resp.json()["items"]
        self.assertEqual(len(items), 91)
        nums = [x["num"] for x in items]
        self.assertEqual(len(set(nums)), 91)
        self.assertTrue(set(nums).isdisjoint(set(ov["missing_numbers"])))

        partial_items = [x for x in items if x["ni_original"]["is_partial_disclosure"]]
        self.assertGreaterEqual(len(partial_items), 85)
        for item in items:
            self.assertTrue(item["ni_original"]["indications"])
            self.assertTrue(item["ni_original"]["partial_herbs"])
            self.assertTrue(item["ziji_note"]["commentary"])
            self.assertIn("source_anchor", item)

    def test_all_132_hantang_source_anchors_resolve_http_200_via_locate(self):
        ov = self.client.get("/api/hantang/overview").json()
        items = self.client.get("/api/hantang/formulas").json()["items"]

        anchors = []
        for f in items:
            anchors.append((f["ht_number"], f["source_anchor"]))
        for sec in ("du_spine_diagnostics", "special_palpation_points", "western_history_rules", "clinical_redlines", "cases_index"):
            for obj in ov[sec]:
                anchors.append((obj.get("id", sec), obj["anchor"]))
        anchors.append(("prognosis", ov["prognosis_and_recovery_criteria"]["anchor"]))

        self.assertEqual(len(anchors), 132)
        for label, anc in anchors:
            params = {
                "book_id": anc["book_id"],
                "page_no": int(anc.get("page_no") or 0),
                "q": anc.get("q", ""),
                "before": 1,
                "after": 2,
            }
            resp = self.client.get("/api/library/locate", params=params)
            self.assertEqual(resp.status_code, 200, f"Locate failed for {label}: {anc}")
            payload = resp.json()
            self.assertTrue(payload.get("pages"), f"Empty pages for {label}: {anc}")

    def test_hantang_linked_classics_and_acupoints_exist(self):
        items = self.client.get("/api/hantang/formulas").json()["items"]
        formula_cache = {}
        point_cache = {}

        # Verify every Du spine acupoint link resolves
        ov = self.client.get("/api/hantang/overview").json()
        for d in ov["du_spine_diagnostics"]:
            pid = d.get("acupoint_id")
            self.assertTrue(pid, f"Missing acupoint_id on {d['id']}")
            r = self.client.get(f"/api/acupuncture/points/{pid}")
            self.assertEqual(r.status_code, 200, f"Invalid acupoint {pid}")

        # Verify all linked classic formulas & acupoints across all 91 HT items resolve
        checked_f = set()
        checked_p = set()
        for it in items:
            for c in it["ziji_note"]["linked_classical_formulas"]:
                checked_f.add(c["id"])
            for p in it["ziji_note"]["linked_acupoints"]:
                checked_p.add(p["id"])

        for fid in checked_f:
            if fid not in formula_cache:
                formula_cache[fid] = self.client.get(f"/api/formulas/{fid}").status_code
            self.assertEqual(formula_cache[fid], 200, f"Broken classic formula link: {fid}")

        for pid in checked_p:
            if pid not in point_cache:
                point_cache[pid] = self.client.get(f"/api/acupuncture/points/{pid}").status_code
            self.assertEqual(point_cache[pid], 200, f"Broken acupoint link: {pid}")

        self.assertGreater(len(checked_f), 30)
        self.assertGreater(len(checked_p), 30)

    def test_fastapi_and_static_dispatch_parity(self):
        urls = [
            "/api/hantang/overview",
            "/api/hantang/formulas",
            "/api/hantang/formulas?category=gynecology&safety=standard",
            "/api/hantang/formulas?q=HT-40",
            "/api/hantang/formulas/hantang:ht-01",
            "/api/hantang/formulas/HT-84",
            "/api/hantang/match?q=心脏术后",
            "/api/stage5/compose?" + urlencode({"q": "胆切除术后，右胁隐痛"}),
        ]
        for url in urls:
            r_fast = self.client.get(url)
            s_stat, b_stat = dispatch_api(url)
            self.assertEqual(r_fast.status_code, 200, url)
            self.assertEqual(s_stat, 200, url)
            self.assertEqual(
                json.loads(json.dumps(r_fast.json(), ensure_ascii=False)),
                json.loads(json.dumps(b_stat, ensure_ascii=False)),
                f"Parity mismatch on {url}",
            )

        # Missing formula HT-55 -> 404 on both
        self.assertEqual(self.client.get("/api/hantang/formulas/HT-55").status_code, 404)
        self.assertEqual(dispatch_api("/api/hantang/formulas/HT-55")[0], 404)

    def test_stage5_compose_hantang_matching_and_pitfall_dedup(self):
        # 1. Heart surgery: triggers west:heart-bypass-stent, HT-40, keeps excluded_pitfalls schema clean
        r1 = self.client.get("/api/stage5/compose", params={"q": "心脏术后，恶寒发热无汗", "pulse": "浮紧"}).json()
        ht1 = r1["hantang_context"]
        self.assertTrue(any(w["id"] == "west:heart-bypass-stent" for w in ht1["western_history_guidance"]))
        self.assertTrue(any(f["ht_number"] == "HT-40" for f in ht1["hantang_formulas"]))
        self.assertIn("HT-40", r1["ai_ready_case_packet"]["hantang_hints"]["matched_ht_numbers"])
        self.assertTrue(r1["excluded_pitfalls"])
        for ex in r1["excluded_pitfalls"]:
            parts = ex["why_excluded"].split("；")
            self.assertEqual(len(parts), len(set(parts)), f"Duplicate reasons on {ex['name']}: {ex['why_excluded']}")

        # 2. Cholecystectomy: surfaces HT-84
        r2 = self.client.get("/api/stage5/compose", params={"q": "胆切除术后，右胁隐痛，胆怯"}).json()
        ht2 = r2["hantang_context"]
        self.assertTrue(any(w["id"] == "west:cholecystectomy" for w in ht2["western_history_guidance"]))
        self.assertTrue(any(f["ht_number"] == "HT-84" for f in ht2["hantang_formulas"]))

        # 3. 5th thoracic vertebra tenderness + SLE -> du:t5-shendao + ht-rl-1 + HT-2
        r3 = self.client.get("/api/stage5/compose", params={"q": "第5椎压痛，红斑狼疮，失眠手足冷"}).json()
        ht3 = r3["hantang_context"]
        self.assertTrue(any(d["id"] == "du:t5-shendao" for d in ht3["du_spine_guides"]))
        self.assertTrue(any(rl["id"] == "ht-rl-1" for rl in ht3["ht_redlines"]))
        self.assertTrue(any(f["ht_number"] == "HT-2" for f in ht3["hantang_formulas"]))


if __name__ == "__main__":
    unittest.main()
