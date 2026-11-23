"""El hareketiyle pencere denetimi. Başparmağı bir parmağa kıstırmak (tutma) hareketi seçer:

  işaret parmağı  → pencereyi taşı (kıstırıp sürükle, aç: bırak)
  orta parmak     → pencereyi boyutlandır (kıstırıp sürükle, aç: bırak)
  yüzük parmağı   → büyüt / eski boyuta getir (0,3 sn kıstırıp tut)
  serçe parmağı   → küçült (0,3 sn kıstırıp tut)
  işaret+orta birlikte → sekmeyi kapat (1 sn tut; Ctrl+W)
  açık elle soldan sağa hızlı salla → pencereyi kapat (kaydedilmemiş işi uygulama sorar)

Saf mantık: el noktaları (0-1 aralığında x, y) ve pencere işlemleri dışarıdan verilir, kamera/Windows gerekmez.
"""

from __future__ import annotations

import math

from jarvis.oneeuro import OneEuro

WRIST, THUMB_TIP, MIDDLE_MCP = 0, 4, 9
EDGE = 0.03  # el noktası kadraj kenarına bu kadar yakınsa uyar
TIPS = {"move": 8, "resize": 12, "maximize": 16, "minimize": 20}
GRAB_BELOW = 0.30  # parmak uçları el boyunun %30'undan yakınsa tut
# yüzük ve serçe daha kısa/zor: eşikleri gevşek
GRAB = {"move": 0.30, "resize": 0.30, "maximize": 0.38, "minimize": 0.55}
OTHERS_ABOVE = 0.45
MARGIN = 0.12  # seçilen parmak diğerlerinden en az bu kadar (el boyu oranı) daha yakın olmalı; diğerleri kıvrık olabilir  # diğer parmaklar açık olmalı (yumruk hareket sayılmaz)
RELEASE_ABOVE = 0.50  # %50'den açılınca bırak (titremeyi önler)
GAIN = 1.6  # küçük el hareketi ekranın büyük kısmını gezsin
# 1€ filtresi (bkz. oneeuro.py): yavaş harekette titreme bastırılır, hızlı harekette gecikme azalır. Birim: kare oranı/sn.
MINCUTOFF = 1.0
BETA = 8.0
LOST_GRACE = 0.5  # el kısa süre kaybolursa bırakma
HOLD = 0.3
HOLD_GRACE = 0.2  # tutma sırasında tek-iki karelik algı kaybı sayacı sıfırlamasın
SWIPE_DX = 0.35  # avuç merkezi bu kadar (kare genişliği oranı) sağa gitmeli
SWIPE_DY = 0.20  # ve en fazla bu kadar yukarı/aşağı kaymalı
SWIPE_WINDOW = 0.8  # saniye içinde
SWIPE_COOLDOWN = 2.0
TAB_HOLD = 1.0
START_FRAMES = 2  # algılama tek karelik yanlışla başlamasın
RELEASE_FRAMES = 2  # tek karelik kayıp bırakmasın
DEADZONE = 1  # piksel
COOLDOWN = 1.0
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
        self.filter_x, self.filter_y = OneEuro(MINCUTOFF, BETA), OneEuro(MINCUTOFF, BETA)
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
        self.hold_last = 0.0
        self.trail = []  # açık elin (zaman, x, y) izi: sallama algılamak için
        self.swipe_cool = 0.0
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

    def _pick(self, found: dict[str, float], points=None) -> str:
        close = [name for name, value in found.items() if value < GRAB[name]]
        if len(close) == len(found):
            return ""
        if not close:
            return ""
        if sorted(close) == ["move", "resize"] and all(found[n] > max(found["move"], found["resize"]) + MARGIN for n in ("maximize", "minimize")):
            return "tab"
        best = min(close, key=lambda name: found[name])
        # Diğer parmaklar açık ya da kıvrık olabilir; yeter ki seçilen parmak belirgin biçimde daha yakın olsun.
        clear = all(value > found[best] + MARGIN for name, value in found.items() if name != best)
        return best if clear else ""

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
            self.trail = []
            self._drag(points, found, now)
            return
        self._swipe(points, found, now)
        active = self._pick(found, points)
        self.seen = self.seen + 1 if active and active == self.candidate else 1
        self.candidate = active
        if not active and self.hold and now - self.hold_last <= HOLD_GRACE:
            return
        if active and active == self.hold:
            self.hold_last = now
        if not active:
            self.hold, self.armed = "", True
            self._say("el kadrajın kenarında" if _at_edge(points) else "hazır")
            return
        if not self._enabled(active):
            self._say("hazır")
            return
        if active in ("move", "resize"):
            if self.seen >= START_FRAMES:
                self._start_drag(active, points, now)
            return
        # büyüt / küçült: tutup bekle
        if not self.armed or now < self.cool_until:
            return
        if self.hold != active:
            self.hold, self.hold_since, self.hold_last = active, now, now
            self._say(LABELS[active] + "… tut")
        elif now - self.hold_since >= {"tab": TAB_HOLD}.get(active, HOLD):
            self._fire(active)
            self.cool_until, self.hold, self.armed = now + COOLDOWN, "", False

    def _swipe(self, points, found: dict[str, float], now: float) -> None:
        """Açık el (hiçbir parmak kıstırılmamış) soldan sağa hızlıca gidince pencereyi kapatır."""
        if not self._enabled("close") or now < self.swipe_cool or any(value < GRAB[name] for name, value in found.items()):
            self.trail = []  # kapalı ya da kıstırma var (taşıma/yumruk): sallama sayılmaz
            return
        if sum(value > OTHERS_ABOVE for value in found.values()) < 2:
            return  # hızlı harekette bulanık/kıvrık kare: izi silme, bu kareyi atla
        center = points[MIDDLE_MCP]
        self.trail = [t for t in self.trail if now - t[0] <= SWIPE_WINDOW] + [(now, center.x, center.y)]
        if center.x - min(t[1] for t in self.trail) >= SWIPE_DX and max(t[2] for t in self.trail) - min(t[2] for t in self.trail) <= SWIPE_DY:
            self.trail, self.swipe_cool = [], now + SWIPE_COOLDOWN
            self._fire("close")

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

    def _start_drag(self, name: str, points, now: float) -> None:
        hwnd = self._target()
        if not hwnd or self.win.maximized(hwnd):
            return  # tam ekran pencere taşınmaz/boyutlanmaz; önce eski boyuta getir
        rect = self.win.rect(hwnd)
        if not rect:
            return
        self.mode, self.hwnd = name, hwnd
        self.filter_x.reset(); self.filter_y.reset()
        self.start_hand = (self.filter_x(points[THUMB_TIP].x, now), self.filter_y(points[THUMB_TIP].y, now))
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
        hand_x, hand_y = self.filter_x(points[THUMB_TIP].x, now), self.filter_y(points[THUMB_TIP].y, now)
        dx = (hand_x - self.start_hand[0]) * screen_w * speed
        dy = (hand_y - self.start_hand[1]) * screen_h * speed
        left, top, right, bottom = self.start_rect
        width, height = right - left, bottom - top
        if self.mode == "move":
            goal = (min(max(left + dx, 100 - width), screen_w - 100), min(max(top + dy, 0), screen_h - 40))  # başlık çubuğu ekranda kalsın
        else:
            goal = (min(max(width + dx, MIN_SIZE[0]), screen_w), min(max(height + dy, MIN_SIZE[1]), screen_h))
        if abs(goal[0] - self.pos[0]) < DEADZONE and abs(goal[1] - self.pos[1]) < DEADZONE:
            return
        self.pos = goal
        if self.mode == "move":
            self.win.move(self.hwnd, round(self.pos[0]), round(self.pos[1]))
        else:
            self.win.resize(self.hwnd, round(self.pos[0]), round(self.pos[1]))
