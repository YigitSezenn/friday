import re
import unittest
from pathlib import Path

HUD = Path(__file__).resolve().parents[1] / "ui" / "hud"


class HudLayoutTests(unittest.TestCase):
    def setUp(self):
        self.html = (HUD / "index.html").read_text(encoding="utf-8")

    def test_window_buttons_live_in_topbar(self):
        topbar = re.search(r'<div id="topbar">(.*?)\n</div>', self.html, re.S).group(1)
        self.assertIn('id="min"', topbar)
        self.assertIn('id="quit"', topbar)

    def test_fx_assets_exist_and_are_linked(self):
        for name in ("hud-fx.css", "hud-fx.js"):
            self.assertTrue((HUD / name).is_file(), name)
            self.assertIn(name, self.html)

    def test_reduced_motion_is_respected(self):
        self.assertIn("prefers-reduced-motion", (HUD / "hud-fx.css").read_text(encoding="utf-8"))
        self.assertIn("prefers-reduced-motion", (HUD / "hud-fx.js").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
