import unittest
from types import SimpleNamespace as P

from jarvis.gesture import PinchDrag, pinch_ratio


def hand(thumb=(0.5, 0.5), index=(0.5, 0.5)):
    pts = [P(x=0.5, y=0.9) for _ in range(21)]
    pts[0] = P(x=0.5, y=0.9)
    pts[9] = P(x=0.5, y=0.5)  # el boyu 0.4
    pts[4], pts[8] = P(x=thumb[0], y=thumb[1]), P(x=index[0], y=index[1])
    return pts


def pinched(x, y):
    return hand((x - 0.01, y), (x + 0.01, y))


def open_hand(x, y):
    return hand((x - 0.15, y), (x + 0.15, y))


class FakeWin:
    def __init__(self, movable=True):
        self.moves, self._movable = [], movable

    def foreground(self): return 7
    def movable(self, hwnd): return self._movable
    def rect(self, hwnd): return (100, 100, 700, 500)
    def screen(self): return (1920, 1080)
    def move(self, hwnd, x, y): self.moves.append((hwnd, x, y))


class PinchTests(unittest.TestCase):
    def test_ratio(self):
        self.assertLess(pinch_ratio(pinched(0.5, 0.5)), 0.1)
        self.assertGreater(pinch_ratio(open_hand(0.5, 0.5)), 0.6)

    def test_open_hand_moves_nothing(self):
        win = FakeWin(); drag = PinchDrag(win)
        for i in range(5):
            drag.update(open_hand(0.5 + i * 0.05, 0.5), i * 0.05)
        self.assertEqual(win.moves, [])

    def test_pinch_and_move_drags_window_then_release_stops(self):
        win = FakeWin(); drag = PinchDrag(win)
        drag.update(pinched(0.5, 0.5), 0.0)
        self.assertTrue(drag.grabbing)
        for i in range(1, 12):
            drag.update(pinched(0.5 + i * 0.02, 0.5), i * 0.05)
        self.assertGreater(win.moves[-1][1], 100)
        self.assertAlmostEqual(win.moves[-1][2], 100, delta=2)
        drag.update(open_hand(0.7, 0.5), 1.0)
        self.assertFalse(drag.grabbing)
        count = len(win.moves)
        drag.update(open_hand(0.9, 0.5), 1.1)
        self.assertEqual(len(win.moves), count)

    def test_unmovable_window_is_never_grabbed(self):
        win = FakeWin(movable=False); drag = PinchDrag(win)
        drag.update(pinched(0.5, 0.5), 0.0); drag.update(pinched(0.9, 0.5), 0.1)
        self.assertFalse(drag.grabbing); self.assertEqual(win.moves, [])

    def test_window_stays_on_screen(self):
        win = FakeWin(); drag = PinchDrag(win)
        drag.update(pinched(0.1, 0.5), 0.0)
        for i in range(1, 40):
            drag.update(pinched(0.1 + i * 0.1, 0.5 + i * 0.1), i * 0.05)
        _hwnd, x, y = win.moves[-1]
        self.assertLessEqual(x, 1820); self.assertLessEqual(y, 1040)

    def test_hand_lost_briefly_keeps_grab_then_releases(self):
        win = FakeWin(); drag = PinchDrag(win)
        drag.update(pinched(0.5, 0.5), 0.0)
        drag.update(None, 0.2); self.assertTrue(drag.grabbing)
        drag.update(None, 0.9); self.assertFalse(drag.grabbing)


if __name__ == "__main__":
    unittest.main()
