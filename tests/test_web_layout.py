from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class WebLayoutTest(unittest.TestCase):
    def test_desktop_panels_scroll_independently(self):
        css = (ROOT / "web" / "style.css").read_text(encoding="utf-8")
        app_js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn(".workspace {", css)
        self.assertIn("height: calc(100vh - 322px);", css)
        self.assertIn("max-height: 680px;", css)
        self.assertIn(".entity-list { flex: 1 1 auto; min-height: 0; overflow: auto;", css)
        self.assertIn(".detail-panel { height: 100%; overflow: auto;", css)
        self.assertIn("panel.scrollTo({ top: Math.max(0, top), behavior: \"smooth\" });", app_js)

    def test_mobile_layout_returns_to_page_flow(self):
        css = (ROOT / "web" / "style.css").read_text(encoding="utf-8")
        self.assertIn(
            ".workspace { display: flex; flex-direction: column; height: auto; min-height: 0; }",
            css,
        )
        self.assertIn(".detail-panel { height: auto; min-height: 360px; overflow: visible; }", css)


if __name__ == "__main__":
    unittest.main()
