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
        self.moves, self.sizes, self.shown, self.closed, self.tabs, self.switched = [], [], [], [], [], []
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
    def switch_tab(self, hwnd, forward): self.switched.append(forward)


def open_hand(x, y=0.5, curl=()):
    """Gerçekçi açık el: avuç merkezi (x, y); bilek aşağıda, dört parmak ucu yukarıda; başparmak yanda."""
    pts = [P(x=x, y=y + 0.4) for _ in range(21)]
    pts[9] = P(x=x, y=y)  # el boyu 0,4
    pts[4] = P(x=x - 0.25, y=y + 0.2)
    for i, tip in enumerate((8, 12, 16, 20)):
        pts[tip] = P(x=x - 0.12 + i * 0.08, y=y - 0.4)  # bilekten ~2,2 kat uzak
    for tip in curl:  # hareket bulanıklığı: bu parmak yarı kıvrık görünür (kıstırma değil)
        pts[tip] = P(x=x + 0.1, y=y + 0.1)
    return pts


def point_hand(x, y=0.5):
    """Yalnızca işaret parmağı açık; öteki üçü avuca kıvrık, başparmak yanda."""
    pts = open_hand(x, y)
    for i, tip in enumerate((12, 16, 20)):
        pts[tip] = P(x=x + i * 0.05, y=y + 0.1)
    return pts


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


class FistTabTests(unittest.TestCase):
    def fist(self):
        pts = hand("move")
        for tip in (12, 16, 20):
            pts[tip] = P(x=0.5, y=0.5)  # dört parmak ucu başparmakta ve avuçta
        return pts

    def test_fist_held_closes_tab_once(self):
        win = FakeWin(); g = HandGestures(win)
        drive(g, [self.fist()] * 60)
        self.assertEqual((win.tabs, win.closed, win.moves), ([7], [], []))

    def test_short_fist_and_disabled_do_nothing(self):
        win = FakeWin(); g = HandGestures(win)
        drive(g, [self.fist()] * 10)
        self.assertEqual(win.tabs, [])
        g = HandGestures(win, lambda: {"tab": False}); drive(g, [self.fist()] * 60)
        self.assertEqual(win.tabs, [])

    def test_extended_fingers_touching_are_not_a_fist(self):
        win = FakeWin(); g = HandGestures(win)
        pts = hand("move")
        for tip in (4, 8, 12, 16, 20):
            pts[tip] = P(x=0.5, y=0.1)  # birbirine değiyor ama bilekten uzakta
        drive(g, [pts] * 60)
        self.assertEqual(win.tabs, [])


class PointSwitchTests(unittest.TestCase):
    def flick(self, start, end, frames=5, y=0.5):
        return [point_hand(start + (end - start) * i / (frames - 1), y) for i in range(frames)]

    def test_index_flick_right_goes_forward_left_goes_back(self):
        win = FakeWin(); g = HandGestures(win)
        drive(g, self.flick(0.3, 0.6)); drive(g, self.flick(0.6, 0.3), start=2.0)
        self.assertEqual(win.switched, [True, False])

    def test_cooldown_prevents_double_switch(self):
        win = FakeWin(); g = HandGestures(win)
        drive(g, self.flick(0.2, 0.9, frames=12), step=0.02)
        self.assertEqual(len(win.switched), 1)

    def test_small_jitter_open_hand_and_disabled_do_not_switch(self):
        win = FakeWin(); g = HandGestures(win)
        drive(g, self.flick(0.5, 0.52))
        drive(g, [open_hand(0.3 + i * 0.06) for i in range(5)], start=3.0)
        g2 = HandGestures(win, lambda: {"switch": False}); drive(g2, self.flick(0.3, 0.6))
        self.assertEqual(win.switched, [])

    def test_pointing_hand_moving_right_does_not_close_window(self):
        win = FakeWin(); g = HandGestures(win)
        drive(g, [point_hand(0.2 + i * 0.1) for i in range(8)])
        self.assertEqual(win.closed, [])


class SwipeCloseTests(unittest.TestCase):
    def sweep(self, start=0.2, end=0.8, frames=8, y=0.5, step=0.05):
        out = []
        for i in range(frames):
            out.append(open_hand(start + (end - start) * i / (frames - 1), y))
        return out

    def test_open_hand_sweep_left_to_right_closes_window_once(self):
        win = FakeWin(); g = HandGestures(win)
        drive(g, self.sweep() + self.sweep(), start=0.0)
        self.assertEqual(win.closed, [7])

    def test_right_to_left_or_short_or_slow_does_not_close(self):
        for frames in (self.sweep(0.8, 0.2), self.sweep(0.4, 0.6)):
            win = FakeWin(); g = HandGestures(win); drive(g, frames)
            self.assertEqual(win.closed, [])
        win = FakeWin(); g = HandGestures(win); drive(g, self.sweep(frames=8), step=0.3)  # 2,1 sn: yavaş
        self.assertEqual(win.closed, [])

    def at(self, x, y=0.5, curl=()):
        return open_hand(x, y, curl)

    def test_fast_sparse_swipe_with_a_blurred_frame_and_a_dropout_still_closes(self):
        win = FakeWin(); g = HandGestures(win)
        g.update(self.at(0.25), 0.00)
        g.update(None, 0.08)  # hızlı harekette el kaybolur
        g.update(self.at(0.50, curl=(12, 16)), 0.16)  # bulanık, yarı kıvrık kare
        g.update(self.at(0.80), 0.28)
        self.assertEqual(win.closed, [7])

    def test_two_sample_jump_closes(self):
        win = FakeWin(); g = HandGestures(win)
        g.update(self.at(0.2), 0.0); g.update(self.at(0.62), 0.25)
        self.assertEqual(win.closed, [7])

    def test_diagonal_motion_does_not_close(self):
        win = FakeWin(); g = HandGestures(win)
        drive(g, [open_hand(0.2 + i * 0.08, 0.2 + i * 0.08) for i in range(8)])
        self.assertEqual(win.closed, [])

    def test_pinched_hand_moving_right_drags_instead_of_closing(self):
        win = FakeWin(); g = HandGestures(win)
        grab(g, "move")
        drive(g, [hand("move", (0.2 + i * 0.07, 0.5)) for i in range(8)], start=0.1)
        self.assertEqual(win.closed, [])

    def test_fist_does_nothing_and_close_can_be_disabled(self):
        win = FakeWin(); g = HandGestures(win)
        fist = hand("move")
        for tip in (12, 16, 20):
            fist[tip] = P(x=0.5, y=0.5)
        drive(g, [fist] * 80)
        self.assertEqual(win.closed, [])
        g = HandGestures(win, lambda: {"close": False}); drive(g, self.sweep())
        self.assertEqual(win.closed, [])


if __name__ == "__main__":
    unittest.main()


class HoldGraceTests(unittest.TestCase):
    def test_brief_dropout_does_not_reset_hold(self):
        win = FakeWin(); g = HandGestures(win)
        frames = [hand("minimize")] * 3 + [hand(None)] + [hand("minimize")] * 4  # ortada tek kare kayıp
        drive(g, frames)
        self.assertEqual(win.shown, [6])
