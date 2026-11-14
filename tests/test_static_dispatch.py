from __future__ import annotations

import json
import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.static_dispatch import dispatch_api, dispatch_json


class StaticDispatchParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_key_routes_match_fastapi_responses(self) -> None:
        urls = [
            "/api/overview",
            "/api/formulas?book=伤寒论&page=1&page_size=12",
            "/api/formulas/diagnose?q=小便不利+渴",
            "/api/formulas/shanghan%3A%E6%A1%82%E6%9E%9D%E6%B1%A4",
            "/api/herbs?q=附子",
            "/api/six-channels",
            "/api/jinkui-chapters",
            "/api/acupuncture/overview",
            "/api/acupuncture/diagnose?q=偏头痛+呕吐",
            "/api/acupuncture/points/acupoint%3Ali04%3A%E5%90%88%E8%B0%B7",
            "/api/neijing/overview",
            "/api/neijing/diagnose?q=失眠",
            "/api/bencao/overview",
            "/api/bencao/diagnose?q=寒热",
            "/api/library/overview",
            "/api/library/search?q=柴胡桂枝干姜汤",
            "/api/library/books/ni-shanghan-pdf/context?page_no=32&before=2&after=3",
            "/api/stage5/overview",
            "/api/stage5/compose",
            "/api/stage5/compose?q=胆结石+黄疸&pulse=弦",
            "/api/stage5/compose?q=%E5%BF%83%E6%82%B8+%E8%88%8C%E7%BA%A2%E5%B0%91%E8%8B%94&pulse=%E7%BB%93%E4%BB%A3",
            "/api/stage5/compose?q=%E5%8F%B3%E4%B8%8B%E8%85%B9%E7%97%9B+%E5%B0%8F%E4%BE%BF%E8%87%AA%E5%88%A9",
            "/api/stage5/ground?q=桂枝汤",
            "/api/library/locate?book_hint=%E4%BC%A4%E5%AF%92%E8%AE%BA%E8%BE%91%E4%B9%89&line=295&q=%E6%A1%82%E6%9E%9D%E6%B1%A4",
            "/api/library/locate?book_hint=%E9%87%91%E5%8C%AE%E8%A6%81%E7%95%A5&page_no=103&q=%E6%A1%82%E6%9E%9D%E8%8A%8D%E8%8D%AF%E7%9F%A5%E6%AF%8D%E6%B1%A4",
        ]
        for url in urls:
            # Also verify subpath prefix handling (/tcm-study-brain-v2/api/...)
            api_resp = self.client.get(url)
            self.assertEqual(api_resp.status_code, 200, url)
            env = json.loads(dispatch_json(f"/tcm-study-brain-v2{url}"))
            self.assertEqual(env["status"], 200, url)
            self.assertEqual(env["body"], api_resp.json(), f"Mismatch on {url}")

        envelope = json.loads(dispatch_json("/api/health"))
        self.assertEqual(envelope["status"], 200)
        self.assertEqual(envelope["body"]["status"], "ok")

    def test_404_and_pdf_source_resolution(self) -> None:
        st404, body404 = dispatch_api("/api/formulas/not_existing_formula")
        self.assertEqual(st404, 404)
        self.assertIn("detail", body404)

        st_ctx404, body_ctx404 = dispatch_api("/api/library/books/not_existing_book/context?page_no=1")
        self.assertEqual(st_ctx404, 404)
        self.assertIn("detail", body_ctx404)

        st_loc404, body_loc404 = dispatch_api("/api/library/locate?q=%E4%B8%8D%E5%AD%98%E5%9C%A8%E7%9A%84%E6%95%85%E4%BA%8B%E6%B5%8B%E8%AF%95%E8%AF%8D8899")
        self.assertEqual(st_loc404, 404)
        self.assertIn("detail", body_loc404)

        for img_url in (
            "/api/acupuncture/source-pages/42/image",
            "/api/bencao/source-pages/19/image",
            "/api/neijing/source-pages/ni-neijing-vol1-pdf/12/image",
            "/api/library/books/huangdi-waijing-pdf/pages/1/image",
        ):
            st, meta = dispatch_api(f"/api/__pdf-source?url={img_url}")
            self.assertEqual(st, 200, img_url)
            self.assertTrue(meta["relative_path"].endswith(".pdf"))
            self.assertGreaterEqual(meta["pdf_page"], 1)


if __name__ == "__main__":
    unittest.main()
