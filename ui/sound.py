"""Açılış/kapanış/onay sesleri, arka plan müziği ve kapanış vedası."""

from __future__ import annotations

import threading




class SoundMixin:
    def play_success_sfx(self) -> None:
        if not self.effects:
            return
        from jarvis import sounds

        if sounds.play("success", volume=400):
            return
        try:
            import winsound

            winsound.Beep(740, 80)
        except (ImportError, RuntimeError):
            pass

    def play_startup_sfx(self) -> None:
        if self._smoke or not self.effects:
            return
        from jarvis import sounds

        if not sounds.play("startup", volume=300):
            try:
                import winsound

                winsound.Beep(523, 80)
                winsound.Beep(784, 140)
            except (ImportError, RuntimeError):
                pass
        self.sync_music()

    def sync_music(self) -> None:
        """Arka plan müziği: yalnızca kendi ayarı açıksa döner (ses efektlerinden bağımsız)."""
        if self._smoke:
            return
        from jarvis import sounds

        if self.music and not self._quitting:
            sounds.play("ambient", loop=True, volume=260)
        else:
            sounds.stop("ambient")

    def play_close_sfx(self) -> None:
        """Kapanış sesini bitene kadar çalar (çağıran iş parçacığını bekletir)."""
        if not self.effects:
            return
        from jarvis import sounds

        sounds.stop("ambient")
        if sounds.play("shutdown", wait=True, volume=300):
            return
        try:
            import winsound

            winsound.Beep(523, 70)
            winsound.Beep(349, 160)
        except (ImportError, RuntimeError):
            pass

    def begin_farewell(self) -> None:
        """HUD'da kapanış animasyonu + kapanış sesi, sonra gerçek kapanış."""
        if self._quitting or self._farewell:
            return
        self._farewell = True

        def run() -> None:
            self._js("document.body.dataset.shutdown='1'")
            try:
                self.play_close_sfx()
            finally:
                self.close()

        threading.Thread(target=run, name="friday-farewell", daemon=True).start()
