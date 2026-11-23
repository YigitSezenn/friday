import unittest

from tools.actions.windowctl import window_control


class FakeUi:
    def __init__(self): self.sizes = []
    def camera_size(self, size): self.sizes.append(size)


class FakeWin:
    def __init__(self, hwnd=5, ok=True):
        self.calls, self.hwnd, self.ok = [], hwnd, ok
    def available(self): return True
    def target_window(self): return self.hwnd
    def show_window(self, hwnd, cmd): self.calls.append(("show", hwnd, cmd)); return self.ok
    def close_window(self, hwnd): self.calls.append(("close", hwnd)); return self.ok
    def close_tab(self, hwnd): self.calls.append(("tab", hwnd)); return self.ok


class CameraTests(unittest.TestCase):
    def test_camera_sizes(self):
        ui = FakeUi()
        for action, size in (("fullscreen", 2), ("tam ekran", 2), ("large", 1), ("küçült", 0)):
            window_control(action, "camera", ui)
            self.assertEqual(ui.sizes[-1], size)

    def test_unknown_camera_action_changes_nothing(self):
        ui = FakeUi(); window_control("zıpla", "kamera", ui)
        self.assertEqual(ui.sizes, [])


class WindowTests(unittest.TestCase):
    def test_actions_reach_the_target_window(self):
        win = FakeWin()
        for action in ("küçült", "büyüt", "restore", "kapat", "sekmeyi kapat"):
            window_control(action, "window", None, win=win)
        self.assertEqual(win.calls, [("show", 5, 6), ("show", 5, 3), ("show", 5, 9), ("close", 5), ("tab", 5)])

    def test_no_target_or_failure_is_reported(self):
        self.assertIn("bulamadım", window_control("minimize", "window", None, win=FakeWin(hwnd=0)))
        self.assertIn("ulaşamadım", window_control("minimize", "window", None, win=FakeWin(ok=False)))


if __name__ == "__main__":
    unittest.main()
