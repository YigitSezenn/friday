"""Mikrofon parçasını modele vermeden önce süzer.

Yankı engelleme açıkken yakalama Windows Voice Capture DSP'sinden gelir (hoparlör
yankısı silinmiş). Asistan konuşurken BargeGate, ortam gürültüsünü ve kalan yankı
izini düşürür; kullanıcının sesi geçince o parçalar gönderilir. Kapalıyken düz
mikrofon kullanılır ve asistan konuşurken mikrofon susar.
"""

from __future__ import annotations

import os
import time

from jarvis.audio.barge import BargeGate, peak
from jarvis.config import get_app_config_value

SPEAKER_RATE = 24000
RECENT = (0.15, 0.6)
FLOOR_RATIO = 0.15
FLOOR_CAP = 0.12
DUCK = 0.35
_SLOTS = 128


def aec_wanted() -> bool:
    if os.environ.get("JARVIS_NO_AEC") == "1":
        return False
    return bool(get_app_config_value("aec_enabled", True))


class CaptureFilter:
    def __init__(self) -> None:
        self.gate = BargeGate()
        self.played = 0
        self.ducked = False
        self._played_at = [-1e9] * _SLOTS
        self._played_peak = [0.0] * _SLOTS
        self._played_i = 0

    def note_playback(self, pcm: bytes, now: float | None = None) -> None:
        if not pcm:
            return
        moment = time.monotonic() if now is None else now
        self.played += len(pcm) // 2
        level = peak(pcm)
        index = self._played_i % _SLOTS
        self._played_at[index] = moment
        self._played_peak[index] = level
        self._played_i += 1

    def warm(self) -> bool:
        return self.played >= SPEAKER_RATE

    def echo_floor(self, now: float | None = None) -> float:
        moment = time.monotonic() if now is None else now
        low, high = RECENT
        heard = [
            level
            for stamp, level in zip(self._played_at, self._played_peak)
            if low <= moment - stamp <= high
        ]
        return min(FLOOR_CAP, FLOOR_RATIO * (max(heard) if heard else 0.0))

    def apply(self, pcm: bytes, *, speaking: bool, echo_cancelled: bool, now: float | None = None) -> list[bytes]:
        moment = time.monotonic() if now is None else now
        if not echo_cancelled:
            self.ducked = False
            self.gate.end()
            return [] if speaking or not pcm else [pcm]
        level = peak(pcm)
        if not speaking:
            was_open = self.gate.is_open
            self.gate.end()
            self.gate.listen(level)
            if was_open:
                self.ducked = False
            return [pcm] if pcm else []
        was_open = self.gate.is_open
        pieces = self.gate.feed(pcm, level, moment, self.warm(), self.echo_floor(moment))
        self.ducked = self.gate.is_open
        if was_open and not self.gate.is_open:
            self.ducked = False
        return [piece for piece in pieces if piece]


def chunks_for_model(pcm: bytes, *, speaking: bool, echo_cancelled: bool, filt: CaptureFilter, now: float | None = None) -> list[bytes]:
    """Yakalama yolunun modele koyduğu parçalar. Ham mikrofon değil, filtrenin çıktısı."""
    return filt.apply(pcm, speaking=speaking, echo_cancelled=echo_cancelled, now=now)
