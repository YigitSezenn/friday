"""Konuşma turunu kapatır. Sessizlik uzayınca model yanıt vermeye geçer."""

from __future__ import annotations

from jarvis.audio.barge import peak


class TurnGate:
    def __init__(self, speech: float = 0.02, silence_s: float = 0.7) -> None:
        self.speech = speech
        self.silence_s = silence_s
        self.open = False
        self.quiet_at: float | None = None

    def feed(self, pcm: bytes, now: float) -> tuple[list[str], list[str]]:
        level = peak(pcm)
        before: list[str] = []
        after: list[str] = []
        if level >= self.speech:
            self.quiet_at = None
            if not self.open:
                self.open = True
                before.append("start")
        elif self.open:
            if self.quiet_at is None:
                self.quiet_at = now
            elif now - self.quiet_at >= self.silence_s:
                self.open = False
                self.quiet_at = None
                after.append("end")
        return before, after
