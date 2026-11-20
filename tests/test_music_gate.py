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
