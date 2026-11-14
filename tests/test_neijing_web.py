from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class NeijingWebUiTest(unittest.TestCase):
    def test_neijing_view_replaces_placeholder_and_preserves_nav_order(self):
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("第三阶段建设模块 · 待接入", html)
        for id_attr in (
            'id="neijing-view"',
            'data-nj-dim="concepts"',
            'data-nj-dim="chapters"',
            'data-nj-dim="pages"',
            'data-nj-sub="yin_yang_wu_xing"',
            'data-nj-sub="zang_xiang"',
            'data-nj-sub="bing_yin_bing_ji"',
            'data-nj-sub="zhen_fa"',
            'data-nj-sub="bian_zheng"',
            'data-nj-sub="yang_sheng"',
            '<script src="/neijing.js"></script>',
        ):
            self.assertIn(id_attr, html)

    def test_neijing_js_and_app_js_wiring(self):
        nj_js = (ROOT / "web" / "neijing.js").read_text(encoding="utf-8")
        app_js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("window.neijingUI", nj_js)
        self.assertIn("/api/neijing/concepts", nj_js)
        self.assertIn("/api/neijing/chapters", nj_js)
        self.assertIn("/api/neijing/source-pages/", nj_js)
        self.assertIn("window.neijingUI", app_js)
        self.assertIn("#/neijing/", app_js)


if __name__ == "__main__":
    unittest.main()
