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
