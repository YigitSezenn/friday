import re
import unittest
from pathlib import Path

HUD = Path(__file__).resolve().parent.parent / "ui" / "hud"


class HudStructureTests(unittest.TestCase):
    def setUp(self):
        self.html = (HUD / "index.html").read_text(encoding="utf-8")
        self.i18n = (HUD / "i18n.js").read_text(encoding="utf-8")

    def test_every_settings_tab_has_a_pane(self):
        tabs = set(re.findall(r'class="stab" data-tab="([^"]+)"', self.html))
        panes = set(re.findall(r'class="pane(?: on)?" data-pane="([^"]+)"', self.html))
        self.assertEqual(tabs, panes)
        self.assertIn("izinler", tabs)

    def test_every_tab_label_key_exists_in_every_language(self):
        keys = set(re.findall(r'class="stab"[^>]*data-i18n="([^"]+)"', self.html))
        packs = self.i18n.count("tabAbout:")
        for key in keys:
            self.assertEqual(self.i18n.count(f"{key}:"), packs, key)


class PermissionTests(unittest.TestCase):
    def test_registry_value_mapping(self):
        from jarvis.permissions import state_from_value

        self.assertEqual(state_from_value("Allow"), "granted")
        self.assertEqual(state_from_value("deny"), "denied")
        self.assertEqual(state_from_value(None), "unknown")

    def test_unknown_kind_and_non_windows_are_safe(self):
        from jarvis.permissions import permission_state, settings_uri, snapshot

        self.assertEqual(permission_state("nope"), "unknown")
        self.assertEqual(settings_uri("nope"), "")
        self.assertEqual(set(snapshot()), {"microphone", "webcam"})
        self.assertTrue(settings_uri("webcam").startswith("ms-settings:"))


if __name__ == "__main__":
    unittest.main()
