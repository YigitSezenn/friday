"""Asistan konuşurken söz kesme kapısı.

Yankısı silinmiş mikrofonda asistanın sesinden zayıf bir iz kalır. Bu iz modele giderse
asistan kendi yankısını kullanıcı sanır. Kapı, ancak ses ortamın ve bu izin belirgin
üstüne çıkınca (kullanıcı konuşuyor) açılır. Sürekli müzik ve uğultu kapıyı açık tutamaz.
"""

from __future__ import annotations

import array
from collections import deque

FLOOR = 0.05
RATIO = 3.0
HOLD_RATIO = 2.0
DECAY = 0.85
PREROLL = 6
HOLD = 0.8
LEARN = 4
START_RATIO = 1.5
SUSTAIN = 3
GRACE = 16
AMBIENT_N = 32
AMBIENT_PCT = 0.3
RESIDUAL_MIX = 0.1
RESIDUAL_CAP = 0.15


def peak(pcm: bytes) -> float:
    usable = pcm[: len(pcm) // 2 * 2]
    if not usable:
        return 0.0
    samples = array.array("h")
    samples.frombytes(usable)
    if not samples:
        return 0.0
    return max(abs(sample) for sample in samples) / 32768.0


class BargeGate:
    def __init__(self) -> None:
        self._quiet: deque[float] = deque(maxlen=AMBIENT_N)
        self.residual = 0.0
        self.end()

    def end(self) -> None:
        self.active = False
        self.env = 0.0
        self.base = FLOOR
        self.start = FLOOR
        self._grace = 0
        self._run = 0
        self.open_until = 0.0
        self._learn = 0
        self._pre: deque[bytes] = deque(maxlen=PREROLL)
        self._recent: deque[bool] = deque(maxlen=3)

    @property
    def is_open(self) -> bool:
        return self.open_until > 0

    @property
    def ambient(self) -> float:
        if not self._quiet:
            return 0.0
        ordered = sorted(self._quiet)
        index = min(len(ordered) - 1, int(len(ordered) * AMBIENT_PCT))
        return ordered[index]

    def listen(self, level: float) -> None:
        self._quiet.append(level)

    def feed(self, pcm: bytes, level: float, now: float, warm: bool, floor: float) -> list[bytes]:
        if not self.active:
            self.active = True
            self.env = max(self.ambient, self.residual)
            self.start = max(FLOOR, START_RATIO * self.env)
            self._learn = LEARN
        if self.open_until:
            if level > max(FLOOR, floor, HOLD_RATIO * self.base):
                self.open_until = now + HOLD
            if now <= self.open_until:
                return [pcm]
            self.open_until = 0.0
            self._recent.clear()
            self._grace = 0
            self._run = 0
        self._pre.append(pcm)
        if not warm or self._learn > 0:
            self._learn -= 1
            self._grace = GRACE
            self._run = 0
            self.env = max(level, self.env * DECAY)
            return []
        voiced = level > max(FLOOR, RATIO * self.env, floor)
        self._recent.append(voiced)
        sustained = False
        if self._grace > 0:
            self._grace -= 1
            self._run = self._run + 1 if level > max(RATIO * self.start, floor) else 0
            sustained = self._run >= SUSTAIN
            if sustained:
                self.env = min(self.env, self.start)
        if not voiced and not sustained:
            self.env = max(level, self.env * DECAY)
            self.residual += RESIDUAL_MIX * (min(level, RESIDUAL_CAP) - self.residual)
        if sum(self._recent) >= 2 or sustained:
            self.open_until = now + HOLD
            self.base = max(self.ambient, self.env)
            out = list(self._pre)
            self._pre.clear()
            self._recent.clear()
            return out
        return []
