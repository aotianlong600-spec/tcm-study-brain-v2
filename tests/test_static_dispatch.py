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
            "/api/stage5/overview",
            "/api/stage5/compose",
            "/api/stage5/compose?q=胆结石+黄疸&pulse=弦",
            "/api/stage5/ground?q=桂枝汤",
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
