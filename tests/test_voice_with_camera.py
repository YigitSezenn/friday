import asyncio
import threading
import time
import types
import unittest

from jarvis.live import JarvisLive as Live


class FakeWebcam:
    is_active = True

    def __init__(self): self.n = 0
    def get_latest_frame(self):
        self.n += 1
        return b"frame-%d" % self.n


class SlowUi:
    """evaluate_js arayüz iş parçacığı meşgulken uzun sürer."""

    def __init__(self, seconds): self.seconds, self.calls = seconds, 0
    def update_webcam_preview(self, frame):
        self.calls += 1
        threading.Event().wait(self.seconds)  # time.sleep başka testlerde taklit edilebilir


class PreviewDoesNotBlockTheEventLoop(unittest.TestCase):
    def run_preview(self, ui, duration=1.0):
        stub = types.SimpleNamespace(webcam=FakeWebcam(), ui=ui)
        lags = []

        async def ticker():  # mikrofon okuma/gönderme gibi: olay döngüsü hep zamanında dönmeli
            last = time.monotonic()
            while True:
                await asyncio.sleep(0.02)
                now = time.monotonic()
                lags.append(now - last - 0.02)
                last = now

        async def main():
            tasks = [asyncio.create_task(ticker()), asyncio.create_task(Live._preview_webcam(stub))]
            await asyncio.sleep(duration)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

        asyncio.run(main())
        return max(lags), ui.calls

    def test_slow_ui_does_not_stall_the_audio_loop(self):
        worst, calls = self.run_preview(SlowUi(0.3))
        self.assertLess(worst, 0.1)  # eski kod: ~0,3 sn'lik durmalar
        self.assertGreaterEqual(calls, 2)

    def test_preview_frames_do_not_pile_up_behind_a_slow_ui(self):
        _, calls = self.run_preview(SlowUi(0.4), duration=1.0)
        self.assertLessEqual(calls, 3)

    def test_fast_ui_gets_new_frames_at_about_ten_per_second(self):
        _, calls = self.run_preview(SlowUi(0.0), duration=1.0)
        self.assertTrue(6 <= calls <= 12, calls)


if __name__ == "__main__":
    unittest.main()


class ModelFallbackTests(unittest.TestCase):
    def setUp(self):
        import jarvis.live as live
        self.live = live
        live._model_override = None

    def tearDown(self):
        self.live._model_override = None

    def stub(self, silent):
        logs = []
        return types.SimpleNamespace(_silent_stalls=silent, ui=types.SimpleNamespace(write_log=logs.append)), logs

    def test_one_silent_round_keeps_the_model_two_switch_down_the_chain(self):
        from jarvis.config import FALLBACK_LIVE_MODELS
        first, _ = self.stub(1)
        Live._maybe_fallback_model(first)
        self.assertEqual(self.live.current_live_model(), "models/gemini-3.8-live")
        second, logs = self.stub(2)
        Live._maybe_fallback_model(second)
        self.assertEqual(self.live.current_live_model(), FALLBACK_LIVE_MODELS[0])
        self.assertEqual((len(logs), second._silent_stalls), (1, 0))
        third, _ = self.stub(2)
        Live._maybe_fallback_model(third)
        self.assertEqual(self.live.current_live_model(), FALLBACK_LIVE_MODELS[1])
        last, _ = self.stub(2)
        Live._maybe_fallback_model(last)
        self.assertEqual(self.live.current_live_model(), FALLBACK_LIVE_MODELS[1])  # zincirin sonu: kalır

    def test_next_fallback_walks_the_chain_and_ends(self):
        from jarvis.config import FALLBACK_LIVE_MODELS
        self.assertEqual(self.live.next_fallback("models/gemini-3.8-live"), FALLBACK_LIVE_MODELS[0])
        self.assertEqual(self.live.next_fallback(FALLBACK_LIVE_MODELS[0]), FALLBACK_LIVE_MODELS[1])
        self.assertIsNone(self.live.next_fallback(FALLBACK_LIVE_MODELS[1]))

    def test_fallback_model_gets_no_language_codes(self):
        from jarvis.language import live_speech_code
        self.assertIsNone(live_speech_code("models/gemini-3.1-flash-live-preview"))
        self.assertIsNone(live_speech_code("models/gemini-2.5-flash-native-audio-preview-12-2025"))
        self.assertIsNotNone(live_speech_code("models/gemini-3.8-live"))
