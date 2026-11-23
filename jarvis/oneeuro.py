"""1€ filtresi (Casiez, Roussel, Vogel; CHI 2012): yavaşken titremeyi bastırır, hızlıyken gecikmeyi azaltır.

Kesme frekansı hıza göre değişir: fc = mincutoff + beta * |hız|. Ayar yolu (yazarların önerisi):
önce beta=0 ile mincutoff'u yavaş harekette titreme kalmayana kadar düşür, sonra beta'yı hızlı harekette gecikme kalmayana kadar artır.
Zaman damgalarıyla çalışır; kare hızı değişse de aynı davranır.
"""

from __future__ import annotations

import math


def _alpha(cutoff: float, dt: float) -> float:
    tau = 1.0 / (2 * math.pi * cutoff)
    return 1.0 / (1.0 + tau / dt)


class OneEuro:
    def __init__(self, mincutoff: float = 1.0, beta: float = 0.0, dcutoff: float = 1.0) -> None:
        self.mincutoff, self.beta, self.dcutoff = mincutoff, beta, dcutoff
        self.reset()

    def reset(self) -> None:
        self.x = None
        self.dx = 0.0
        self.t = 0.0

    def __call__(self, value: float, now: float) -> float:
        if self.x is None:
            self.x, self.t = value, now
            return value
        dt = max(now - self.t, 1e-3)
        speed = (value - self.x) / dt
        self.dx += _alpha(self.dcutoff, dt) * (speed - self.dx)
        cutoff = self.mincutoff + self.beta * abs(self.dx)
        self.x += _alpha(cutoff, dt) * (value - self.x)
        self.t = now
        return self.x
