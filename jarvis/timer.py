"""Zamanlayıcı ve kronometre durumu (saf mantık; saat dışarıdan verilir, böylece test edilir)."""
from __future__ import annotations

import threading


def parse_seconds(minutes=None, seconds=None) -> int:
    total = 0.0
    for value, scale in ((minutes, 60), (seconds, 1)):
        if value is None or str(value).strip() == "":
            continue
        total += float(str(value).replace(",", ".")) * scale
    return max(0, int(round(total)))


def clock(seconds: int) -> str:
    seconds = max(0, int(seconds))
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def spoken(seconds: int) -> str:
    seconds = max(0, int(seconds))
    minutes, secs = divmod(seconds, 60)
    parts = []
    if minutes:
        parts.append(f"{minutes} dakika")
    if secs or not parts:
        parts.append(f"{secs} saniye")
    return " ".join(parts)


class TimerState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.end = 0.0
        self.label = ""
        self.watch_start = 0.0
        self.watch_total = 0.0
        self.watch_running = False

    # ---- geri sayım ----
    def set(self, seconds: int, label: str, now: float) -> None:
        with self.lock:
            self.end = now + max(1, int(seconds))
            self.label = str(label or "").strip()

    def add(self, seconds: int, now: float) -> bool:
        """Çalışan sayaca süre ekler; yoksa yeni sayaç kurar. Negatif süre kısaltır."""
        with self.lock:
            if self.end > now:
                self.end = max(now + 1, self.end + seconds)
                return True
            if seconds > 0:
                self.end = now + seconds
                return False
            return False

    def cancel(self) -> bool:
        with self.lock:
            active = self.end > 0
            self.end = 0.0
            self.label = ""
            return active

    def remaining(self, now: float) -> int:
        with self.lock:
            return max(0, int(round(self.end - now))) if self.end else 0

    def due(self, now: float) -> str | None:
        """Süre dolduysa etiketi döner ve sayacı sıfırlar (bir kez tetiklenir)."""
        with self.lock:
            if self.end and now >= self.end:
                label = self.label
                self.end = 0.0
                self.label = ""
                return label or ""
            return None

    # ---- kronometre ----
    def watch(self, action: str, now: float) -> float:
        action = (action or "toggle").strip().casefold()
        with self.lock:
            if action in {"reset", "sifirla", "sıfırla"}:
                self.watch_running, self.watch_total, self.watch_start = False, 0.0, 0.0
            elif action in {"start", "baslat", "başlat"} or (action == "toggle" and not self.watch_running):
                if not self.watch_running:
                    self.watch_running, self.watch_start = True, now
            elif action in {"stop", "durdur"} or action == "toggle":
                if self.watch_running:
                    self.watch_total += now - self.watch_start
                    self.watch_running = False
            return self._elapsed(now)

    def _elapsed(self, now: float) -> float:
        return self.watch_total + (now - self.watch_start if self.watch_running else 0.0)

    def elapsed(self, now: float) -> float:
        with self.lock:
            return self._elapsed(now)

    def snapshot(self, now: float) -> dict:
        """HUD için: bitiş/başlangıç epoch ms olarak (tarayıcı kendi saatinden akıcı sayar)."""
        with self.lock:
            return {
                "end": int(self.end * 1000) if self.end > now else 0,
                "label": self.label,
                "watchStart": int((now - self._elapsed(now)) * 1000) if self.watch_running else 0,
                "watchTotal": int(self._elapsed(now) * 1000),
                "watchRunning": self.watch_running,
            }
