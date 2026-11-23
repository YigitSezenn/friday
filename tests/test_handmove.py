import unittest
from unittest import mock

from tools.actions import confirm, handmove
from tools.actions.webcam import WebcamStreamer


class FakeMover:
    closed = False

    def __init__(self, on_status=None):
        pass

    def on_frame(self, frame):
        pass

    def close(self):
        FakeMover.closed = True


class FakeCam(WebcamStreamer):
    def start(self):
        self._active = True
        return "ok"


def run(cam, action="start", yes=False, ready=True, ensure=lambda: ""):
    return handmove.hand_control(action, yes, cam, None, make_mover=FakeMover, model_ready=lambda: ready, ensure_model=ensure)


class HandControlTests(unittest.TestCase):
    def setUp(self):
        FakeMover.closed = False

    def test_asks_first_and_names_camera_privacy_and_download(self):
        cam = FakeCam()
        out = run(cam, ready=False)
        self.assertIn("ONAY GEREKLİ", out)
        self.assertIn("Gemini'ye gönderilmez", out)
        self.assertIn("8 MB", out)
        self.assertIsNone(cam.frame_hook)
        self.assertFalse(cam.is_active)

    def test_confirm_without_prior_ask_or_yes_does_not_start(self):
        cam = FakeCam()
        self.assertIn("ONAY GEREKLİ", run(cam, yes=True))
        self.assertIsNone(cam.frame_hook)

    def test_start_after_user_yes_is_local_only(self):
        cam = FakeCam()
        run(cam)
        confirm.note_user_said("evet aç")
        with mock.patch.object(confirm, "MIN_WAIT", 0):
            out = run(cam, yes=True)
        self.assertIn("El kontrolü açık", out)
        self.assertTrue(cam.local_only)
        self.assertIsNotNone(cam.frame_hook)

    def test_model_download_failure_keeps_camera_off(self):
        cam = FakeCam()
        run(cam)
        confirm.note_user_said("evet")
        with mock.patch.object(confirm, "MIN_WAIT", 0):
            out = run(cam, yes=True, ensure=lambda: "El takip modeli indirilemedi")
        self.assertIn("indirilemedi", out)
        self.assertFalse(cam.is_active)

    def test_stop_clears_hook_closes_mover_and_restores_streaming(self):
        cam = FakeCam()
        cam.frame_hook, cam.local_only = FakeMover().on_frame, True
        self.assertIn("kapatıldı", run(cam, "stop"))
        self.assertIsNone(cam.frame_hook)
        self.assertFalse(cam.local_only)
        self.assertTrue(FakeMover.closed)

    def test_plain_webcam_stop_also_ends_hand_control(self):
        cam = FakeCam()
        cam.frame_hook, cam.local_only = FakeMover().on_frame, True
        cam.stop()
        self.assertIsNone(cam.frame_hook)


if __name__ == "__main__":
    unittest.main()


class PaddedTrackerTests(unittest.TestCase):
    def test_points_are_mapped_back_from_padded_frame(self):
        import numpy as np
        from types import SimpleNamespace as P

        from jarvis import handtrack

        seen = {}

        class FakeMp:
            class ImageFormat: SRGB = 1
            class Image:
                def __init__(self, image_format, data): seen["shape"] = data.shape

        class FakeLandmarker:
            def detect_for_video(self, image, ms):
                # genişletilmiş karenin tam ortası = asıl karenin ortası
                return P(hand_landmarks=[[P(x=0.5, y=0.5), P(x=0.0, y=0.0)]])

        tracker = object.__new__(handtrack.HandTracker)
        tracker._mp, tracker._landmarker, tracker._last_ms = FakeMp, FakeLandmarker(), 0
        points = tracker.points(np.zeros((100, 200, 3), dtype=np.uint8))
        self.assertEqual(seen["shape"], (140, 280, 3))
        self.assertAlmostEqual(points[0].x, 0.5); self.assertAlmostEqual(points[0].y, 0.5)
        self.assertLess(points[1].x, 0); self.assertLess(points[1].y, 0)  # kadraj dışı = negatif


class StandingPermissionTests(unittest.TestCase):
    def setUp(self):
        FakeMover.closed = False

    def test_saved_permission_skips_the_voice_confirmation(self):
        from unittest import mock

        with mock.patch.object(handmove, "_allowed", return_value=True):
            self.assertIn("açık", run(FakeCam(), "start", yes=False))

    def test_without_saved_permission_it_still_asks(self):
        from unittest import mock

        with mock.patch.object(handmove, "_allowed", return_value=False):
            self.assertIn("ONAY", run(FakeCam(), "start", yes=False).upper())

    def test_permission_defaults_off_and_is_a_saved_setting(self):
        from jarvis import config

        self.assertIs(config.DEFAULT_CONFIG["hand_allowed"], False)
