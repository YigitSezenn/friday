"""Alkış sayar: 2 alkış = aç/uyandır, 3 alkış = kapat. Yalnızca ses seviyesine bakar; ses kaydedilmez, hiçbir yere gönderilmez."""

from __future__ import annotations


class ClapDetector:
    BASE_LOUD = 0.20  # %100 hassasiyette bir alkışın ulaşması gereken seviye (0-1)
    RATIO = 5.0  # ortam gürültüsünün en az bu kadar katı olmalı
    MIN_GAP = 0.12  # aynı alkışın kuyruğu ikinci alkış sayılmaz
    SETTLE = 0.7  # son alkıştan sonra bu kadar sessizlik: sayı kesinleşir
    COOLDOWN = 2.0
    MAX_CLAPS = 3  # daha fazlası alkış değil gürültü/kalabalık sayılır

    def __init__(self, sensitivity: float = 1.0) -> None:
        self.floor = 0.0
        self.prev = 0.0
        self.claps: list[float] = []
        self.quiet_until = 0.0
        self.loud = self.BASE_LOUD
        self.set_sensitivity(sensitivity)

    def set_sensitivity(self, sensitivity: float) -> None:
        """1.0 = varsayılan; 2.0 = iki kat hassas (yarı şiddette alkış yeter), 0.5 = yarı hassas."""
        self.loud = self.BASE_LOUD / min(max(float(sensitivity or 1.0), 0.5), 2.0)

    def feed(self, level: float, now: float) -> int:
        """Alkış sayısı kesinleşince 2 ya da 3 döner, aksi halde 0."""
        onset = level >= max(self.loud, self.floor * self.RATIO) and self.prev < level * 0.5
        if level < self.loud:
            self.floor = self.floor * 0.95 + level * 0.05
        self.prev = level
        if now < self.quiet_until:
            self.claps = []
            return 0
        if onset and not (self.claps and now - self.claps[-1] < self.MIN_GAP):
            self.claps.append(now)
            if len(self.claps) > self.MAX_CLAPS:
                self.claps = []
                self.quiet_until = now + self.COOLDOWN
            return 0
        if self.claps and now - self.claps[-1] >= self.SETTLE:
            count, self.claps = len(self.claps), []
            if count >= 2:
                self.quiet_until = now + self.COOLDOWN
                return count
        return 0
