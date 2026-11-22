"""Çift alkışı tanır. Yalnızca ses seviyesine bakar; ses kaydedilmez, hiçbir yere gönderilmez."""

from __future__ import annotations


class ClapDetector:
    LOUD = 0.35  # alkış ortamdan belirgin yüksek ve ani olmalı
    RATIO = 6.0
    MIN_GAP = 0.12  # aynı alkışın kuyruğu ikinci alkış sayılmaz
    MAX_GAP = 0.9
    COOLDOWN = 2.0

    def __init__(self) -> None:
        self.floor = 0.0
        self.prev = 0.0
        self.first: float | None = None
        self.quiet_until = 0.0

    def feed(self, level: float, now: float) -> bool:
        onset = level >= max(self.LOUD, self.floor * self.RATIO) and self.prev < level * 0.5
        if level < self.LOUD:
            self.floor = self.floor * 0.95 + level * 0.05
        self.prev = level
        if now < self.quiet_until:
            return False
        if self.first is not None and now - self.first > self.MAX_GAP:
            self.first = None
        if not onset:
            return False
        if self.first is None:
            self.first = now
            return False
        if now - self.first < self.MIN_GAP:
            return False
        self.first = None
        self.quiet_until = now + self.COOLDOWN
        return True
