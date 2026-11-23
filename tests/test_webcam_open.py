import sys
import threading
import time
import types
import unittest
from unittest import mock

from tools.actions.webcam import WebcamStreamer


class FakeCap:
    def __init__(self, opens_after_calls, delay=0.0):
        self.opens_after_calls, self.delay = opens_after_calls, delay
        self.calls = 0

    def make(self, *args):
        self.calls += 1
        time.sleep(self.delay)
        cap = types.SimpleNamespace()
        ok = self.calls > self.opens_after_calls
        cap.isOpened = lambda: ok
        cap.release = lambda: None
        cap.set = lambda *a: True
        cap.read = lambda: (False, None)
        return cap


def fake_cv2(factory):
    return types.SimpleNamespace(VideoCapture=factory, CAP_DSHOW=700, CAP_PROP_FOURCC=6, CAP_PROP_FRAME_WIDTH=3,
                                 CAP_PROP_FRAME_HEIGHT=4, CAP_PROP_FPS=5, CAP_PROP_BUFFERSIZE=38,
                                 VideoWriter_fourcc=lambda *a: 0)


class WebcamOpenTests(unittest.TestCase):
    def start_with(self, cap, **limits):
        cam = WebcamStreamer()
        for name, value in limits.items():
            setattr(cam, name, value)
        with mock.patch.dict(sys.modules, {"cv2": fake_cv2(cap.make)}):
            status = cam.start()
            cam.stop()
        return status

    def test_slow_first_open_still_reports_ok(self):
        # eski kod yalnızca 1 sn bekleyip "açılamadı" diyordu
        self.assertEqual(self.start_with(FakeCap(0, delay=1.4)), "ok")

    def test_first_attempts_fail_then_camera_opens(self):
        self.assertEqual(self.start_with(FakeCap(2), OPEN_RETRY_DELAY=0.01), "ok")  # 1. tur: DSHOW+varsayılan başarısız

    def test_camera_that_never_opens_reports_missing(self):
        self.assertEqual(self.start_with(FakeCap(10**6), OPEN_RETRY_DELAY=0.01), "missing")


if __name__ == "__main__":
    unittest.main()
