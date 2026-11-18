import unittest
import wave

from jarvis import sounds
from jarvis.config import DEFAULT_CONFIG


class SoundAssetsTest(unittest.TestCase):
    def test_wavs_exist_and_are_valid(self):
        for name, low, high in (("startup", 3, 10), ("shutdown", 3, 10), ("success", 0.2, 2), ("ambient", 10, 60)):
            file = sounds.path(name)
            self.assertIsNotNone(file, name)
            with wave.open(str(file)) as w:
                self.assertEqual(w.getnchannels(), 2)
                self.assertEqual(w.getframerate(), 44100)
                seconds = w.getnframes() / w.getframerate()
            self.assertTrue(low <= seconds <= high, f"{name} {seconds}")

    def test_music_off_by_default_and_effects_on(self):
        self.assertFalse(DEFAULT_CONFIG["music"])
        self.assertTrue(DEFAULT_CONFIG["effects"])

    def test_play_is_safe_without_windows(self):
        import sys

        if sys.platform != "win32":
            self.assertFalse(sounds.play("startup"))
        self.assertFalse(sounds.play("yok-boyle-ses"))


if __name__ == "__main__":
    unittest.main()
