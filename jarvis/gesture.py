"""El hareketiyle pencere taşıma: başparmak ve işaret parmağını birleştirip (tutma) sürükle, aç (bırak).

Saf mantık: el noktaları (0-1 aralığında x, y) ve pencere işlemleri dışarıdan verilir, kamera/Windows gerekmez.
"""

from __future__ import annotations

import math

WRIST, THUMB_TIP, INDEX_TIP, MIDDLE_MCP = 0, 4, 8, 9
GRAB_BELOW = 0.30  # parmak uçları el boyunun %30'undan yakınsa tut
RELEASE_ABOVE = 0.50  # %50'den açılınca bırak (titremeyi önler)
GAIN = 1.6  # küçük el hareketi ekranın büyük kısmını gezsin
SMOOTH = 0.5
LOST_GRACE = 0.5  # el kısa süre kaybolursa bırakma


def _dist(a, b) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def pinch_ratio(points) -> float:
    size = _dist(points[WRIST], points[MIDDLE_MCP]) or 1e-6
    return _dist(points[THUMB_TIP], points[INDEX_TIP]) / size


class PinchDrag:
    """`win`: foreground() -> hwnd, movable(hwnd), rect(hwnd), move(hwnd, x, y), screen() -> (w, h)."""

    def __init__(self, win) -> None:
        self.win = win
        self.hwnd = 0
        self.start_hand = (0.0, 0.0)
        self.start_pos = (0, 0)
        self.size = (0, 0)
        self.pos = (0.0, 0.0)
        self.last_seen = 0.0

    @property
    def grabbing(self) -> bool:
        return bool(self.hwnd)

    def release(self) -> None:
        self.hwnd = 0

    def update(self, points, now: float) -> None:
        if not points:
            if self.grabbing and now - self.last_seen > LOST_GRACE:
                self.release()
            return
        self.last_seen = now
        ratio = pinch_ratio(points)
        hand = ((points[THUMB_TIP].x + points[INDEX_TIP].x) / 2, (points[THUMB_TIP].y + points[INDEX_TIP].y) / 2)
        if not self.grabbing:
            if ratio < GRAB_BELOW:
                hwnd = self.win.foreground()
                rect = self.win.rect(hwnd) if hwnd and self.win.movable(hwnd) else None
                if rect:
                    self.hwnd, self.start_hand = hwnd, hand
                    self.start_pos = (rect[0], rect[1])
                    self.size = (rect[2] - rect[0], rect[3] - rect[1])
                    self.pos = (float(rect[0]), float(rect[1]))
            return
        if ratio > RELEASE_ABOVE:
            self.release()
            return
        screen_w, screen_h = self.win.screen()
        goal_x = self.start_pos[0] + (hand[0] - self.start_hand[0]) * screen_w * GAIN
        goal_y = self.start_pos[1] + (hand[1] - self.start_hand[1]) * screen_h * GAIN
        # Başlık çubuğu her zaman ekranda kalsın.
        goal_x = min(max(goal_x, 100 - self.size[0]), screen_w - 100)
        goal_y = min(max(goal_y, 0), screen_h - 40)
        self.pos = (self.pos[0] + (goal_x - self.pos[0]) * SMOOTH, self.pos[1] + (goal_y - self.pos[1]) * SMOOTH)
        self.win.move(self.hwnd, round(self.pos[0]), round(self.pos[1]))
