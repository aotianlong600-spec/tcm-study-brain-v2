"""Milestone 2 regression tests for WinRT OCR digitized books:
  - xu-lingtai-collection-pdf (434 pages, 8 works + 1999 academic isolation)
  - huangdi-waijing-pdf (85 pages, 卷首概述 + 80 essays + archaic OCR search variants)
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from ai import grounded_study
from app import static_dispatch
from app.main import app
from etl.library.validate import validate_all


ROOT = Path(__file__).resolve().parents[1]


class Milestone2OcrBooksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_overview_stats_and_no_bogus_scan_gap(self) -> None:
        ov = self.client.get("/api/library/overview").json()
        stats = ov["stats"]
        self.assertEqual(stats["total_books"], 17)
        self.assertEqual(stats["indexed_books"], 17)
        self.assertEqual(stats["scan_only_books"], 0)
        v_res = validate_all()
        self.assertTrue(v_res["valid"], v_res["errors"])
        self.assertGreaterEqual(v_res["syndromes"], 28)

        res = grounded_study.ground_study_query("徐灵胎慎疾刍言与黄帝外经命门真火")
        joined_gaps = " ".join(res["insufficiencies_and_gaps"])
        self.assertNotIn("未生成虚假OCR文本", joined_gaps)
        self.assertNotIn("扫描影印保留卷（）", joined_gaps)

    def test_xu_lingtai_eight_books_boundaries_columns_and_blank_pages(self) -> None:
        toc = self.client.get("/api/library/books/xu-lingtai-collection-pdf").json()["chapters"]
        titles = " ".join(item["title"] for item in toc)
        for work in (
            "现代编注",
            "难经经释",
            "神农本草经百种录",
            "医贯砭",
            "医学源流论",
            "伤寒类方",
            "兰台轨范",
            "慎疾刍言",
            "洄溪医案",
            "著作辨考",
        ):
            self.assertIn(work, titles, f"Missing work landmark in Xu TOC: {work}")

        # Verify 2-column left-before-right ordering and CJK space cleanup on p.250
        p250 = self.client.get("/api/library/books/xu-lingtai-collection-pdf/pages/250").json()
        self.assertIn("大活络丹", p250["body_text"])
        self.assertIn("紫雪", p250["body_text"])
        self.assertLess(p250["body_text"].index("大活络丹"), p250["body_text"].index("紫雪"))
        self.assertNotIn("大 活 络 丹", p250["body_text"])

        # Verify 22 intentionally blank verso/divider pages stay blank (no fabrication)
        rows = [
            json.loads(line)
            for line in (ROOT / "sources" / "library" / "xu-lingtai-collection-pdf.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(len(rows), 434)
        blank_rows = [r for r in rows if r["ocr_status"] == "blank_page"]
        self.assertEqual(len(blank_rows), 22)
        self.assertTrue(all(r["body_text"] == "" and r["search_text"] == "" for r in blank_rows))

    def test_huangdi_waijing_80_essays_and_archaic_ocr_search(self) -> None:
        toc = self.client.get("/api/library/books/huangdi-waijing-pdf").json()["chapters"]
        essay_items = [item for item in toc if item["title"].endswith("篇")]
        self.assertEqual(len(essay_items), 80)

        p1 = self.client.get("/api/library/books/huangdi-waijing-pdf/pages/1").json()
        self.assertIn("卷首概述", p1["section_title"])
        p4 = self.client.get("/api/library/books/huangdi-waijing-pdf/pages/4").json()
        self.assertIn("阴阳颠倒篇", p4["body_text"])

        # Archaic glyph OCR variant ("亡汨亡阴篇" / "补泻阴汨篇") must match normal modern queries
        for query in ("亡阳", "补泻阴阳", "六气分门篇", "寒热舒肝"):
            sr = self.client.get(f"/api/library/search?q={query}&book_id=huangdi-waijing-pdf").json()
            self.assertGreater(sr["total"], 0, f"Expected search hits for {query} in Waijing")

    def test_subbook_locate_and_static_dispatch_parity(self) -> None:
        loc_sj = self.client.get("/api/library/locate", params={"book_hint": "慎疾刍言", "q": "五味子"}).json()
        self.assertEqual(loc_sj["resolved_book_id"], "xu-lingtai-collection-pdf")
        self.assertGreaterEqual(loc_sj["resolved_page_no"], 374)

        loc_wj = self.client.get("/api/library/locate", params={"book_hint": "外经微言", "q": "阴寒格阳"}).json()
        self.assertEqual(loc_wj["resolved_book_id"], "huangdi-waijing-pdf")
        self.assertEqual(loc_wj["resolved_page_no"], 76)

        st, static_ov = static_dispatch.dispatch_api("/api/library/overview")
        self.assertEqual(st, 200)
        static_stats = static_ov["stats"]
        self.assertEqual(static_stats["indexed_books"], 17)
        self.assertEqual(static_stats["scan_only_books"], 0)

        st2, static_sr = static_dispatch.dispatch_api("/api/library/search?q=洄溪医案&book_id=xu-lingtai-collection-pdf")
        self.assertEqual(st2, 200)
        self.assertGreater(static_sr["total"], 0)

    def test_concurrent_blank_and_adjacent_page_image_renders_succeed(self) -> None:
        cache_dir = ROOT / "data" / "library" / "page_images" / "xu-lingtai-collection-pdf"
        pages = [367, 368, 369, 370, 371, 372, 373, 374]
        for pno in pages:
            cached = cache_dir / f"page_{pno:04d}.png"
            if cached.exists():
                cached.unlink()

        def _fetch(pno: int):
            resp = self.client.get(f"/api/library/books/xu-lingtai-collection-pdf/pages/{pno}/image")
            return pno, resp.status_code, resp.headers.get("content-type", ""), resp.content[:8]

        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(_fetch, pages))

        for pno, status, ctype, sig in results:
            self.assertEqual(status, 200, f"Expected HTTP 200 for page {pno}, got {status}")
            self.assertIn("image/png", ctype)
            self.assertEqual(sig, b"\x89PNG\r\n\x1a\n", f"Invalid PNG header on page {pno}")


if __name__ == "__main__":
    unittest.main()
