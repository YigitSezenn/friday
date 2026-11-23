import unittest
from types import SimpleNamespace as P

from jarvis.gesture import HOLD, HandGestures, pinch_ratio, ratios

TIPS = {"move": 8, "resize": 12, "maximize": 16, "minimize": 20}


def hand(close=None, at=(0.5, 0.5)):
    """El noktaları: `close` verilen parmak başparmağa kıstırılmış, diğerleri açık."""
    pts = [P(x=0.5, y=0.9) for _ in range(21)]
    pts[9] = P(x=0.5, y=0.5)  # el boyu 0.4
    pts[4] = P(x=at[0], y=at[1])
    for index, (name, tip) in enumerate(TIPS.items()):
        far = 0.25 + 0.06 * index
        pts[tip] = P(x=at[0] + (0.01 if name == close else far), y=at[1])
    return pts


class FakeWin:
    def __init__(self, controllable=True, maximized=False):
        self.moves, self.sizes, self.shown, self.closed, self.tabs = [], [], [], [], []
        self._controllable, self._maximized = controllable, maximized

    def foreground(self): return 7
    def controllable(self, hwnd): return self._controllable
    def maximized(self, hwnd): return self._maximized
    def rect(self, hwnd): return (100, 100, 700, 500)
    def screen(self): return (1920, 1080)
    def move(self, hwnd, x, y): self.moves.append((hwnd, x, y))
    def resize(self, hwnd, w, h): self.sizes.append((hwnd, w, h))
    def show(self, hwnd, cmd): self.shown.append(cmd)
    def close(self, hwnd): self.closed.append(hwnd)
    def close_tab(self, hwnd): self.tabs.append(hwnd)


def grab(g, name, at=(0.5, 0.5)):
    g.update(hand(name, at), -0.1); g.update(hand(name, at), 0.0)  # başlamak için art arda iki kare gerekir


def drive(g, frames, step=0.05, start=0.0):
    for i, pts in enumerate(frames):
        g.update(pts, start + i * step)


class RatioTests(unittest.TestCase):
    def test_ratio(self):
        self.assertLess(pinch_ratio(hand("move")), 0.1)
        self.assertGreater(pinch_ratio(hand()), 0.4)
        self.assertEqual(set(ratios(hand())), set(TIPS))


class MoveResizeTests(unittest.TestCase):
    def test_open_hand_does_nothing(self):
        win = FakeWin(); g = HandGestures(win)
        drive(g, [hand(None, (0.5 + i * 0.05, 0.5)) for i in range(5)])
        self.assertEqual((win.moves, win.sizes, win.shown), ([], [], []))

    def test_index_pinch_moves_then_release_stops(self):
        win = FakeWin(); g = HandGestures(win)
        grab(g, "move", (0.5, 0.5))
        self.assertTrue(g.grabbing)
        drive(g, [hand("move", (0.5 + i * 0.02, 0.5)) for i in range(1, 12)], start=0.05)
        self.assertGreater(win.moves[-1][1], 100)
        self.assertAlmostEqual(win.moves[-1][2], 100, delta=2)
        self.assertEqual(win.sizes, [])
        g.update(hand(None, (0.7, 0.5)), 1.0)
        self.assertTrue(g.grabbing)  # tek karelik açılma bırakmaz
        g.update(hand(None, (0.7, 0.5)), 1.05)
        self.assertFalse(g.grabbing)
        count = len(win.moves); g.update(hand(None, (0.9, 0.5)), 1.1)
        self.assertEqual(len(win.moves), count)

    def test_middle_pinch_resizes_not_moves(self):
        win = FakeWin(); g = HandGestures(win)
        grab(g, "resize", (0.5, 0.5))
        drive(g, [hand("resize", (0.5 + i * 0.02, 0.5 + i * 0.02)) for i in range(1, 12)], start=0.05)
        self.assertEqual(win.moves, [])
        _h, w, h = win.sizes[-1]
        self.assertGreater(w, 600); self.assertGreater(h, 400)

    def test_resize_has_minimum_size(self):
        win = FakeWin(); g = HandGestures(win)
        grab(g, "resize", (0.9, 0.9))
        drive(g, [hand("resize", (0.9 - i * 0.05, 0.9 - i * 0.05)) for i in range(1, 15)], start=0.05)
        _h, w, h = win.sizes[-1]
        self.assertGreaterEqual(w, 320); self.assertGreaterEqual(h, 200)

    def test_window_stays_on_screen(self):
        win = FakeWin(); g = HandGestures(win)
        grab(g, "move", (0.1, 0.5))
        drive(g, [hand("move", (0.1 + i * 0.1, 0.5 + i * 0.1)) for i in range(1, 40)], start=0.05)
        _h, x, y = win.moves[-1]
        self.assertLessEqual(x, 1820); self.assertLessEqual(y, 1040)

    def test_uncontrollable_or_maximized_window_is_not_grabbed(self):
        for win in (FakeWin(controllable=False), FakeWin(maximized=True)):
            g = HandGestures(win)
            grab(g, "move"); g.update(hand("move", (0.9, 0.5)), 0.1)
            self.assertFalse(g.grabbing); self.assertEqual(win.moves, [])

    def test_hand_lost_briefly_keeps_grab_then_releases(self):
        win = FakeWin(); g = HandGestures(win)
        grab(g, "move")
        g.update(None, 0.2); self.assertTrue(g.grabbing)
        g.update(None, 0.9); self.assertFalse(g.grabbing)


class HoldGestureTests(unittest.TestCase):
    def test_ring_hold_maximizes_then_restores(self):
        win = FakeWin(); g = HandGestures(win)
        drive(g, [hand("maximize")] * 15)  # 0,7 sn
        self.assertEqual(win.shown, [3])
        drive(g, [hand(None)] * 3, start=1.0)  # bırak
        win._maximized = True
        drive(g, [hand("maximize")] * 15, start=3.0)
        self.assertEqual(win.shown, [3, 9])

    def test_pinky_hold_minimizes(self):
        win = FakeWin(); g = HandGestures(win)
        drive(g, [hand("minimize")] * 15)
        self.assertEqual(win.shown, [6])

    def test_short_touch_does_nothing_and_holding_fires_once(self):
        win = FakeWin(); g = HandGestures(win)
        drive(g, [hand("minimize")] * 5)  # 0,25 sn
        self.assertEqual(win.shown, [])
        drive(g, [hand("minimize")] * 60, start=1.0)  # uzun tutma: tek tetik
        self.assertEqual(win.shown, [6])

    def test_fist_like_hand_is_ignored(self):
        win = FakeWin(); g = HandGestures(win)
        pts = hand("move")
        for tip in (12, 16, 20):
            pts[tip] = P(x=0.5, y=0.5)  # hepsi başparmağa yakın
        drive(g, [pts] * 20)
        self.assertEqual((win.moves, win.shown), ([], []))

    def test_disabled_gesture_is_off_and_speed_scales(self):
        win = FakeWin(); g = HandGestures(win, lambda: {"minimize": False, "speed": 1.0})
        drive(g, [hand("minimize")] * 15)
        self.assertEqual(win.shown, [])
        slow, fast = FakeWin(), FakeWin()
        for win, speed in ((slow, 0.5), (fast, 2.0)):
            g = HandGestures(win, lambda s=speed: {"speed": s})
            grab(g, "move", (0.3, 0.5))
            drive(g, [hand("move", (0.35, 0.5))] * 8, start=0.05)
        self.assertGreater(fast.moves[-1][1], slow.moves[-1][1])

    def test_status_callback_reports_changes_only(self):
        said = []; win = FakeWin(); g = HandGestures(win, None, said.append)
        grab(g, "move"); g.update(hand("move", (0.6, 0.5)), 0.05); g.update(hand(None), 0.1); g.update(hand(None), 0.15)
        self.assertEqual(said, ["taşıyor", "hazır"])


class StabilityTests(unittest.TestCase):
    def test_single_frame_pinch_does_not_start_drag(self):
        win = FakeWin(); g = HandGestures(win)
        g.update(hand("move"), 0.0); g.update(hand(None), 0.05)
        self.assertFalse(g.grabbing)

    def test_tiny_jitter_does_not_move_window(self):
        win = FakeWin(); g = HandGestures(win)
        grab(g, "move")
        drive(g, [hand("move", (0.5 + (i % 2) * 0.0005, 0.5)) for i in range(10)], start=0.05)
        self.assertEqual(win.moves, [])


class CurledFingersTests(unittest.TestCase):
    def test_pinky_pinch_works_while_other_fingers_are_curled(self):
        win = FakeWin(); g = HandGestures(win)
        pts = hand("minimize")
        for tip in (8, 12, 16):
            pts[tip] = P(x=0.5 + 0.2, y=0.5)  # kıvrık: başparmağa orta yakınlıkta (oran 0,5)
        drive(g, [pts] * 12)
        self.assertEqual(win.shown, [6])

    def test_two_equally_close_fingers_are_ambiguous(self):
        win = FakeWin(); g = HandGestures(win)
        pts = hand("maximize"); pts[20] = P(x=0.5 + 0.01, y=0.5)  # yüzük ve serçe aynı yakınlıkta
        drive(g, [pts] * 20)
        self.assertEqual(win.shown, [])


class TabGestureTests(unittest.TestCase):
    def two(self):
        pts = hand("move")
        pts[12] = P(x=0.51, y=0.5)  # orta parmak da başparmakta
        return pts

    def test_index_plus_middle_held_closes_tab_once(self):
        win = FakeWin(); g = HandGestures(win)
        drive(g, [self.two()] * 60)
        self.assertEqual((win.tabs, win.closed, win.moves), ([7], [], []))

    def test_short_touch_and_disabled_do_nothing(self):
        win = FakeWin(); g = HandGestures(win)
        drive(g, [self.two()] * 10)
        self.assertEqual(win.tabs, [])
        g = HandGestures(win, lambda: {"tab": False}); drive(g, [self.two()] * 60)
        self.assertEqual(win.tabs, [])


class FingerAndFistTests(unittest.TestCase):
    def test_pinky_and_ring_trigger_with_looser_pinch(self):
        for name, shown in (("minimize", 6), ("maximize", 3)):
            win = FakeWin(); g = HandGestures(win)
            pts = hand(name)
            tip = {"minimize": 20, "maximize": 16}[name]
            pts[tip] = P(x=0.5 + {"minimize": 0.17, "maximize": 0.14}[name], y=0.5)  # el boyunun %35-43'ü: eskiden tetiklenmezdi
            drive(g, [pts] * 12)
            self.assertEqual(win.shown, [shown])

    def test_open_hand_edge_status(self):
        said = []; g = HandGestures(FakeWin(), None, said.append)
        pts = hand(None); pts[0] = P(x=0.01, y=0.9)
        g.update(pts, 0.0); g.update(hand(None), 0.1)
        self.assertEqual(said, ["el kadrajın kenarında", "hazır"])

    def test_fingers_touching_thumb_but_not_folded_is_not_a_fist(self):
        win = FakeWin(); g = HandGestures(win)
        pts = hand("move")
        for tip in (4, 8, 12, 16, 20):
            pts[tip] = P(x=0.5, y=0.1)  # hepsi birbirine değiyor ama bilekten uzakta: uzatılmış, kıvrık değil
        drive(g, [pts] * 80)
        self.assertEqual(win.closed, [])


class CloseGestureTests(unittest.TestCase):
    def fist(self):
        pts = hand("move")
        for tip in (12, 16, 20):
            pts[tip] = P(x=0.5, y=0.5)
        return pts

    def test_fist_held_closes_window_once(self):
        win = FakeWin(); g = HandGestures(win)
        drive(g, [self.fist()] * 80)  # 4 sn
        self.assertEqual(win.closed, [7])

    def test_short_fist_does_not_close(self):
        win = FakeWin(); g = HandGestures(win)
        drive(g, [self.fist()] * 20)  # 1 sn
        self.assertEqual(win.closed, [])

    def test_close_can_be_disabled(self):
        win = FakeWin(); g = HandGestures(win, lambda: {"close": False})
        drive(g, [self.fist()] * 80)
        self.assertEqual(win.closed, [])


if __name__ == "__main__":
    unittest.main()


class HoldGraceTests(unittest.TestCase):
    def test_brief_dropout_does_not_reset_hold(self):
        win = FakeWin(); g = HandGestures(win)
        frames = [hand("minimize")] * 3 + [hand(None)] + [hand("minimize")] * 4  # ortada tek kare kayıp
        drive(g, frames)
        self.assertEqual(win.shown, [6])
