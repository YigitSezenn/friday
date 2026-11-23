"""El hareketiyle pencere denetimi. Başparmağı bir parmağa kıstırmak (tutma) hareketi seçer:

  işaret parmağı  → pencereyi taşı (kıstırıp sürükle, aç: bırak)
  orta parmak     → pencereyi boyutlandır (kıstırıp sürükle, aç: bırak)
  yüzük parmağı   → büyüt / eski boyuta getir (0,4 sn kıstırıp tut)
  serçe parmağı   → küçült (0,4 sn kıstırıp tut)
  işaret+orta birlikte → sekmeyi kapat (1 sn tut; Ctrl+W)
  yumruk (dört parmak da kıstırılmış) → pencereyi kapat (1,5 sn tut; kaydedilmemiş işi uygulama sorar)

Saf mantık: el noktaları (0-1 aralığında x, y) ve pencere işlemleri dışarıdan verilir, kamera/Windows gerekmez.
"""

from __future__ import annotations

import math

WRIST, THUMB_TIP, MIDDLE_MCP = 0, 4, 9
FOLDED_BELOW = 1.3  # tam yumruk: dört parmak ucu da bileğe el boyunun 1,3 katından yakın (kıvrık)
EDGE = 0.03  # el noktası kadraj kenarına bu kadar yakınsa uyar
TIPS = {"move": 8, "resize": 12, "maximize": 16, "minimize": 20}
GRAB_BELOW = 0.30  # parmak uçları el boyunun %30'undan yakınsa tut
# yüzük ve serçe daha kısa/zor: eşikleri gevşek
GRAB = {"move": 0.30, "resize": 0.30, "maximize": 0.38, "minimize": 0.48}
OTHERS_ABOVE = 0.45  # diğer parmaklar açık olmalı (yumruk hareket sayılmaz)
RELEASE_ABOVE = 0.50  # %50'den açılınca bırak (titremeyi önler)
GAIN = 1.6  # küçük el hareketi ekranın büyük kısmını gezsin
SMOOTH = 0.5
LOST_GRACE = 0.5  # el kısa süre kaybolursa bırakma
HOLD = 0.4
CLOSE_HOLD = 1.5
TAB_HOLD = 1.0
START_FRAMES = 2  # algılama tek karelik yanlışla başlamasın
RELEASE_FRAMES = 2  # tek karelik kayıp bırakmasın
DEADZONE = 3  # piksel; titreme pencereyi oynatmasın
COOLDOWN = 1.5
MIN_SIZE = (320, 200)
DEFAULTS = {"move": True, "resize": True, "maximize": True, "minimize": True, "close": True, "tab": True, "speed": 1.0}
LABELS = {"move": "taşıyor", "resize": "boyutlandırıyor", "maximize": "büyütüyor", "minimize": "küçültüyor", "close": "kapatıyor", "tab": "sekmeyi kapatıyor"}


def _dist(a, b) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def _at_edge(points) -> bool:
    return any(p.x < EDGE or p.x > 1 - EDGE or p.y < EDGE or p.y > 1 - EDGE for p in points)


def ratios(points) -> dict[str, float]:
    size = _dist(points[WRIST], points[MIDDLE_MCP]) or 1e-6
    return {name: _dist(points[THUMB_TIP], points[tip]) / size for name, tip in TIPS.items()}


def pinch_ratio(points) -> float:
    return ratios(points)["move"]


class HandGestures:
    """`win`: foreground(), controllable(h), movable(h), rect(h), move(h,x,y), resize(h,w,h), show(h,cmd), maximized(h), screen()."""

    def __init__(self, win, options=None, on_status=None) -> None:
        self.win = win
        self.options = options or (lambda: DEFAULTS)
        self.on_status = on_status or (lambda text: None)
        self.mode = ""  # taşıma / boyutlandırma sürerken
        self.hwnd = 0
        self.start_hand = (0.0, 0.0)
        self.start_rect = (0, 0, 0, 0)
        self.pos = (0.0, 0.0)
        self.hold = ""
        self.hold_since = 0.0
        self.seen = 0  # art arda kaç karede aynı hareket görüldü
        self.candidate = ""
        self.opened = 0  # art arda kaç karede el açık görüldü (bırakma)
        self.armed = True
        self.cool_until = 0.0
        self.last_seen = 0.0
        self._status = ""

    @property
    def grabbing(self) -> bool:
        return bool(self.mode)

    def _say(self, text: str) -> None:
        if text != self._status:
            self._status = text
            self.on_status(text)

    def release(self) -> None:
        self.mode, self.hwnd, self.hold, self.candidate, self.seen, self.opened = "", 0, "", "", 0, 0
        self._say("hazır")

    def _enabled(self, name: str) -> bool:
        return bool(self.options().get(name, True))

    @staticmethod
    def _fist(points) -> bool:
        """Parmaklar yalnızca başparmağa değmesin, avuca da kıvrılmış olsun (tam yumruk)."""
        if points is None:
            return False
        size = _dist(points[WRIST], points[MIDDLE_MCP]) or 1e-6
        return all(_dist(points[WRIST], points[tip]) / size < FOLDED_BELOW for tip in (8, 12, 16, 20))

    def _pick(self, found: dict[str, float], points=None) -> str:
        close = [name for name, value in found.items() if value < GRAB[name]]
        if len(close) == len(found):
            return "close" if self._fist(points) else ""
        if sorted(close) == ["move", "resize"] and found["maximize"] > OTHERS_ABOVE and found["minimize"] > OTHERS_ABOVE:
            return "tab"
        if len(close) != 1:
            return ""
        others = [value for name, value in found.items() if name != close[0]]
        return close[0] if all(value > OTHERS_ABOVE for value in others) else ""

    def update(self, points, now: float) -> None:
        if not points:
            if (self.grabbing or self.hold) and now - self.last_seen > LOST_GRACE:
                self.release()
            elif not self.grabbing and not self.hold:
                self._say("el görünmüyor")
            return
        self.last_seen = now
        found = ratios(points)
        hand = ((points[THUMB_TIP].x + points[TIPS["move"]].x) / 2, (points[THUMB_TIP].y + points[TIPS["move"]].y) / 2)
        if self.mode:
            self._drag(points, found, now)
            return
        active = self._pick(found, points)
        self.seen = self.seen + 1 if active and active == self.candidate else 1
        self.candidate = active
        if not active:
            self.hold, self.armed = "", True
            self._say("el kadrajın kenarında" if _at_edge(points) else "hazır")
            return
        if not self._enabled(active):
            self._say("hazır")
            return
        if active in ("move", "resize"):
            if self.seen >= START_FRAMES:
                self._start_drag(active, points)
            return
        # büyüt / küçült: tutup bekle
        if not self.armed or now < self.cool_until:
            return
        if self.hold != active:
            self.hold, self.hold_since = active, now
            self._say(LABELS[active] + "… tut")
        elif now - self.hold_since >= {"close": CLOSE_HOLD, "tab": TAB_HOLD}.get(active, HOLD):
            self._fire(active)
            self.cool_until, self.hold, self.armed = now + COOLDOWN, "", False

    def _target(self):
        hwnd = self.win.foreground()
        return hwnd if hwnd and self.win.controllable(hwnd) else 0

    def _fire(self, name: str) -> None:
        hwnd = self._target()
        if not hwnd:
            return
        if name == "tab":
            self.win.close_tab(hwnd)
        elif name == "close":
            self.win.close(hwnd)
        elif name == "minimize":
            self.win.show(hwnd, 6)
        else:
            self.win.show(hwnd, 9 if self.win.maximized(hwnd) else 3)
        self._say(LABELS[name])

    def _start_drag(self, name: str, points) -> None:
        hwnd = self._target()
        if not hwnd or self.win.maximized(hwnd):
            return  # tam ekran pencere taşınmaz/boyutlanmaz; önce eski boyuta getir
        rect = self.win.rect(hwnd)
        if not rect:
            return
        self.mode, self.hwnd = name, hwnd
        self.start_hand = (points[THUMB_TIP].x, points[THUMB_TIP].y)
        self.start_rect = rect
        self.pos = (float(rect[0]), float(rect[1])) if name == "move" else (float(rect[2] - rect[0]), float(rect[3] - rect[1]))
        self._say(LABELS[name])

    def _drag(self, points, found: dict[str, float], now: float) -> None:
        self.opened = self.opened + 1 if found[self.mode] > RELEASE_ABOVE else 0
        if self.opened >= RELEASE_FRAMES:
            self.release()
            return
        if self.opened:
            return  # tek karelik açılma: pencereyi olduğu yerde tut
        screen_w, screen_h = self.win.screen()
        speed = GAIN * float(self.options().get("speed", 1.0) or 1.0)
        dx = (points[THUMB_TIP].x - self.start_hand[0]) * screen_w * speed
        dy = (points[THUMB_TIP].y - self.start_hand[1]) * screen_h * speed
        left, top, right, bottom = self.start_rect
        width, height = right - left, bottom - top
        if self.mode == "move":
            goal = (min(max(left + dx, 100 - width), screen_w - 100), min(max(top + dy, 0), screen_h - 40))  # başlık çubuğu ekranda kalsın
        else:
            goal = (min(max(width + dx, MIN_SIZE[0]), screen_w), min(max(height + dy, MIN_SIZE[1]), screen_h))
        if abs(goal[0] - self.pos[0]) < DEADZONE and abs(goal[1] - self.pos[1]) < DEADZONE:
            return
        self.pos = (self.pos[0] + (goal[0] - self.pos[0]) * SMOOTH, self.pos[1] + (goal[1] - self.pos[1]) * SMOOTH)
        if self.mode == "move":
            self.win.move(self.hwnd, round(self.pos[0]), round(self.pos[1]))
        else:
            self.win.resize(self.hwnd, round(self.pos[0]), round(self.pos[1]))
