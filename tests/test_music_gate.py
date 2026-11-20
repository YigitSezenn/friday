import unittest

from jarvis.heard import MicGate
from jarvis.intents import is_sleep, is_wake


class MicGateTests(unittest.TestCase):
    def test_steady_music_becomes_ambient(self):
        gate = MicGate()
        passed = [gate.passes(0.08) for _ in range(600)]
        self.assertTrue(passed[0])
        self.assertFalse(any(passed[-100:]), "sürekli müzik sonunda geçmemeli")

    def test_speech_over_music_passes(self):
        gate = MicGate()
        for _ in range(600):
            gate.passes(0.08)
        self.assertTrue(gate.passes(0.45))

    def test_quiet_room_blocks_hiss_and_passes_voice(self):
        gate = MicGate()
        for _ in range(50):
            self.assertFalse(gate.passes(0.005))
        self.assertTrue(gate.passes(0.2))

    def test_hangover_keeps_word_endings(self):
        gate = MicGate()
        gate.passes(0.3)
        self.assertTrue(gate.passes(0.005))


class IntentTests(unittest.TestCase):
    def test_sleep_phrases(self):
        for text in ("Uyu", "friday uyu lütfen", "Uyku moduna geç", "iyi geceler", "biraz dinlen"):
            self.assertTrue(is_sleep(text), text)

    def test_not_sleep(self):
        for text in ("uyumak istemiyorum", "Spotify'ı aç", "yarın sabah yedide uyandır", ""):
            self.assertFalse(is_sleep(text), text)

    def test_wake(self):
        self.assertTrue(is_wake("uyan"))
        self.assertFalse(is_wake("hava nasıl"))


if __name__ == "__main__":
    unittest.main()


class DesktopTests(unittest.TestCase):
    def test_aliases_and_unknown(self):
        from tools.actions import desktop

        self.assertEqual(desktop._canonical("Masaüstü"), "show_desktop")
        self.assertEqual(desktop._canonical("kilitle"), "lock")
        self.assertIn("Bilinmeyen", desktop.run("uç"))

    def test_tool_declared_and_handled(self):
        from tools.dispatch import TOOL_DECLARATIONS
        from tools.handlers import HANDLERS

        self.assertIn("desktop_action", HANDLERS)
        self.assertIn("desktop_action", [d["name"] for d in TOOL_DECLARATIONS])


class WeatherLocationTests(unittest.TestCase):
    def test_parse_ip_location(self):
        from tools.actions.weather import parse_ip_location

        good = parse_ip_location({"success": True, "city": "Kepez", "region": "Antalya", "latitude": 36.9, "longitude": 30.7})
        self.assertEqual(good["label"], "Kepez, Antalya")
        self.assertAlmostEqual(good["lat"], 36.9)
        self.assertEqual(parse_ip_location({"success": False}), {})
        self.assertEqual(parse_ip_location({"latitude": "x", "longitude": 1}), {})
        self.assertEqual(parse_ip_location({"latitude": 0, "longitude": 0}), {})
        same = parse_ip_location({"city": "Ankara", "region": "Ankara", "latitude": 39.9, "longitude": 32.8})
        self.assertEqual(same["label"], "Ankara")


class MemoryEntriesTests(unittest.TestCase):
    def test_list_entries_includes_flat_and_nested(self):
        from jarvis.memory_store import list_entries

        rows = list_entries({"kisisel": {"ad": {"value": "Yiğit"}, "yas": "20"}, "dil": "tr", "bos": {}, "x": ""})
        self.assertEqual(
            [(r["category"], r["key"], r["text"]) for r in rows],
            [("kisisel", "ad", "Yiğit"), ("kisisel", "yas", "20"), ("dil", "", "tr")],
        )

    def test_save_and_forget_roundtrip(self):
        import os
        import tempfile

        from jarvis.memory_store import delete_memory, list_entries, save_entry

        with tempfile.TemporaryDirectory() as tmp:
            os.environ["JARVIS_DATA_DIR"] = tmp
            try:
                self.assertIn("Kaydedildi", save_entry("kisisel", "ad", "Yiğit"))
                self.assertEqual(list_entries()[0]["text"], "Yiğit")
                self.assertIn("Anahtar", save_entry("kisisel", "", "x"))
                delete_memory(category="kisisel", key="ad")
                self.assertEqual(list_entries(), [])
            finally:
                os.environ.pop("JARVIS_DATA_DIR", None)


class WindowIntentTests(unittest.TestCase):
    def test_minimize_and_close_phrases(self):
        from jarvis.intents import is_close, is_minimize

        for text in ("küçül", "Kendini küçült lütfen", "pencereyi küçült"):
            self.assertTrue(is_minimize(text), text)
        for text in ("friday kapan", "kendini kapat", "uygulamayı kapat"):
            self.assertTrue(is_close(text), text)
        for text in ("sesi kapat", "ekranı kapat", "müziği küçült", "kapıyı kapat"):
            self.assertFalse(is_close(text) or is_minimize(text), text)

    def test_app_window_tool(self):
        from tools.dispatch import TOOL_DECLARATIONS
        from tools.handlers import HANDLERS

        self.assertIn("app_window", HANDLERS)
        self.assertIn("app_window", [d["name"] for d in TOOL_DECLARATIONS])


class DuplicateOpenTests(unittest.TestCase):
    def test_same_site_twice_opens_once(self):
        from tools.actions import browser

        browser._RECENT.clear()
        self.assertFalse(browser.recently_opened("https://www.youtube.com/watch?v=a", now=100.0))
        self.assertTrue(browser.recently_opened("https://youtube.com", now=102.0))
        self.assertFalse(browser.recently_opened("https://youtube.com", now=120.0))

    def test_home_open_cancelled_by_video(self):
        from unittest import mock
        from tools.actions import browser

        browser._RECENT.clear()
        browser._PENDING.clear()
        with mock.patch.object(browser.webbrowser, "open") as opened:
            browser.open_home_soon("https://www.youtube.com")
            browser.open_url("https://www.youtube.com/watch?v=abc")
            import time as _t
            _t.sleep(browser.WEAK_DELAY + 0.5)
        self.assertEqual(opened.call_count, 1)
        self.assertIn("watch", opened.call_args[0][0])
