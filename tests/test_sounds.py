from pathlib import Path
import unittest
import wave

from jarvis import sounds
from jarvis.config import DEFAULT_CONFIG


class SoundAssetsTest(unittest.TestCase):
    def test_wavs_exist_and_are_valid(self):
        for name, low, high in (("startup", 3, 10), ("shutdown", 3, 10), ("success", 0.2, 2), ("alarm", 1, 5), ("ambient", 10, 60)):
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


    def test_startup_sound_is_wired_into_boot(self):
        import inspect

        from ui.bridge import JarvisUI

        self.assertIn("self.play_startup_sfx()", inspect.getsource(JarvisUI._boot))

    def test_close_paths_use_farewell(self):
        import inspect

        from ui.bridge import JarvisUI

        self.assertIn("begin_farewell", inspect.getsource(JarvisUI._on_closing))
        self.assertIn("begin_farewell", inspect.getsource(JarvisUI.quit_app))


if __name__ == "__main__":
    unittest.main()


class LoopAndVolumeTests(unittest.TestCase):
    def test_loop_repeats_until_stopped(self):
        import threading
        import time
        from unittest import mock

        calls = []
        gate = threading.Semaphore(0)

        def fake_mci(command):
            calls.append(command)
            if command.startswith("play"):
                gate.release()
                time.sleep(0.02)  # "wait" ile çalma süresi
            return 0

        with mock.patch.object(sounds, "_mci", fake_mci), mock.patch.object(sounds.sys, "platform", "win32"):
            self.assertTrue(sounds.play("ambient", loop=True, volume=1000))
            self.assertTrue(gate.acquire(timeout=2))
            self.assertTrue(gate.acquire(timeout=2))  # ikinci tur: döngü çalışıyor
            sounds.stop("ambient")
            time.sleep(0.1)
            plays = len([c for c in calls if c.startswith("play")])
            time.sleep(0.1)
            self.assertEqual(plays, len([c for c in calls if c.startswith("play")]))
            self.assertTrue(all("repeat" not in c for c in calls))

    def test_volume_scales_samples(self):
        import array
        import os
        import tempfile
        import wave

        with tempfile.TemporaryDirectory() as tmp:
            os.environ["JARVIS_DATA_DIR"] = tmp
            try:
                src = Path(tmp) / "x.wav"
                with wave.open(str(src), "wb") as w:
                    w.setnchannels(1)
                    w.setsampwidth(2)
                    w.setframerate(8000)
                    w.writeframes(array.array("h", [10000, -10000]).tobytes())
                out = sounds._scaled(src, "x", 300)
                with wave.open(str(out), "rb") as w:
                    got = array.array("h")
                    got.frombytes(w.readframes(2))
                self.assertEqual(list(got), [3000, -3000])
                self.assertEqual(sounds._scaled(src, "x", 1000), src)
            finally:
                os.environ.pop("JARVIS_DATA_DIR", None)
