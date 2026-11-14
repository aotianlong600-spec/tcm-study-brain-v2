from __future__ import annotations

import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AcupunctureWebUiTest(unittest.TestCase):
    def test_module_tab_order_and_default_acupuncture_home(self):
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")

        tabs = re.findall(r'<button class="module-tab[^"]*"[^>]*>(.*?)</button>', html)
        self.assertEqual(tabs, ["针灸", "神农本草", "黄帝内经", "经方"])
        self.assertIn('<button class="module-tab active" data-view="acupuncture"', html)
        self.assertIn('<section id="acupuncture-view" class="module-view active">', html)
        self.assertIn('id="neijing-view"', html)
        self.assertIn('view: "acupuncture"', app_js)

    def test_acupuncture_tab_dual_dimensions_and_layers_present(self):
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        acup_js = (ROOT / "web" / "acupuncture.js").read_text(encoding="utf-8")
        app_js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "web" / "style.css").read_text(encoding="utf-8")

        self.assertIn('data-view="acupuncture"', html)
        self.assertIn('id="acupuncture-view"', html)
        self.assertIn('data-acup-dim="book"', html)
        self.assertIn('data-acup-dim="knowledge"', html)
        self.assertIn('data-acup-dim="diagnose"', html)
        self.assertIn('src="/acupuncture.js"', html)

        self.assertIn("#/acupuncture/", app_js)
        self.assertIn("window.acupunctureUI", app_js)

        for key in ("source_quote", "ni_teaching", "other_annotations", "collation_notes", "organizer_summary"):
            self.assertIn(key, acup_js)
        self.assertIn("尚待考证", acup_js)
        self.assertIn("/api/acupuncture/source-pages/", acup_js)
        self.assertIn("/api/acupuncture/diagnose", acup_js)

        self.assertIn(".acup-dim-tab.active", css)
        self.assertIn(".acup-safety-banner", css)
        self.assertIn(".acup-guide-box", css)


if __name__ == "__main__":
    unittest.main()
