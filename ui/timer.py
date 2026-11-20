"""Zamanlayıcı ve kronometre: durum Python'da, HUD ve sesli komut aynı sayacı görür."""

from __future__ import annotations

import threading
import time




class TimerMixin:
    @property
    def timer(self):
        from jarvis.timer import TimerState

        state = self.__dict__.get("_timer")
        if state is None:
            state = self.__dict__["_timer"] = TimerState()
            threading.Thread(target=self._timer_loop, name="friday-timer", daemon=True).start()
        return state

    def timer_push(self) -> None:
        self._call("timer", self.timer.snapshot(time.time()))

    def timer_set(self, seconds: int, label: str = "") -> None:
        self.timer.set(seconds, label, time.time())
        self.timer_push()

    def timer_add(self, seconds: int) -> bool:
        running = self.timer.add(seconds, time.time())
        self.timer_push()
        return running

    def timer_cancel(self) -> bool:
        active = self.timer.cancel()
        self.timer_push()
        return active

    def timer_watch(self, action: str) -> float:
        elapsed = self.timer.watch(action, time.time())
        self.timer_push()
        return elapsed

    def _timer_loop(self) -> None:
        while not self._closed:
            time.sleep(0.25)
            label = self.timer.due(time.time())
            if label is not None:
                self._timer_fire(label)

    def _timer_fire(self, label: str) -> None:
        from jarvis import sounds

        self.timer_push()
        self._call("timerDone", label)
        self.write_log("SYS: Süre doldu" + (f": {label}" if label else "."))
        if not sounds.play("alarm", loop=True):
            try:
                import winsound

                for _ in range(3):
                    winsound.Beep(880, 220)
                    winsound.Beep(660, 220)
            except (ImportError, RuntimeError):
                pass
        else:
            # Alarm en çok 20 sn çalar; kullanıcı ekrandaki uyarıyı kapatırsa hemen susar.
            threading.Timer(20, lambda: sounds.stop("alarm")).start()
        speak = getattr(self, "speak_note", None)
        if callable(speak):
            what = f"'{label}' zamanlayıcısı" if label else "Zamanlayıcı"
            speak(f"{what} doldu. Kullanıcıya kısaca ve net haber ver.")
