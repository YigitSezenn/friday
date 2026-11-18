"""Pencere yaşam döngüsü: kapanış, tepsi, küçültme, güncelleme, kaldırma."""

from __future__ import annotations

import time




class WindowMixin:
    def _on_closing(self) -> bool:
        from jarvis.taskbar import installer_is_running

        if self._quitting or installer_is_running():
            return True
        # Pencere kapanmadan önce kapanış animasyonu/sesi oynar; close() sonunda kapatır.
        self.begin_farewell()
        return False

    def _minimize_after_close(self) -> None:
        time.sleep(0.12)
        self.minimize_to_taskbar()

    def _ensure_tray(self) -> None:
        if getattr(self, "_tray", None) is not None or self._smoke:
            return
        from jarvis.tray import FridayTray

        self._tray = FridayTray(self.restore_from_taskbar, self.quit_app)
        self._tray.start()

    def quit_app(self) -> None:
        if self._quitting:
            return
        self.begin_farewell()

    def minimize_to_taskbar(self) -> None:
        window = self._window
        if window is None or self._quitting or self._closed or getattr(self, "_hiding", False):
            return
        self._hiding = True
        self._ensure_tray()
        ready = self._tray.wait_ready() if getattr(self, "_tray", None) is not None else False
        if not ready:
            self._hiding = False
            self.write_log("ERR: Tepsi simgesi açılamadı.")
            return
        try:
            window.hide()
        except Exception:
            try:
                window.minimize()
            except Exception:
                pass
        self._hiding = False

    def restore_from_taskbar(self) -> bool:
        window = self._window
        if window is None or self._quitting or self._closed or self._smoke:
            return False
        try:
            window.show()
            window.restore()
            if not getattr(window, "fullscreen", False):
                window.toggle_fullscreen()
            return True
        except Exception:
            return False

    def _check_update(self) -> None:
        from jarvis import __version__
        from jarvis.updater import available_update

        try:
            newer = available_update(__version__)
        except Exception:
            return
        if newer:
            self._update_version = newer
            self._call("updateOffer", newer)

    def install_update(self) -> None:
        import os
        import tempfile

        from jarvis.updater import download_installer

        self.write_log("SYS: Güncelleme indiriliyor.")
        dest = os.path.join(tempfile.gettempdir(), "FRIDAY-Kurulum-yeni.exe")
        try:
            download_installer(dest)
        except Exception:
            self.write_log("ERR: Güncelleme indirilemedi.")
            return
        try:
            os.startfile(dest)  # type: ignore[attr-defined]
        except Exception:
            self.write_log("ERR: Kurulum açılamadı.")
            return
        self.write_log("SYS: Kurulum açıldı.")

    def request_uninstall(self) -> None:
        from jarvis.uninstall import installed_uninstaller, launch_uninstaller

        if not launch_uninstaller(installed_uninstaller()):
            self.write_log("ERR: Kaldırma yalnız kurulmuş FRIDAY için. Kaynak klasörü ve başka klasörler silinmedi.")
            return
        self._quitting = True
        self.close()

    def close(self) -> None:
        self._quitting = True
        self._closed = True
        tray = getattr(self, "_tray", None)
        if tray is not None:
            tray.stop()
        window = self._window
        if window is not None:
            try:
                window.destroy()
            except Exception:
                pass

    def open_settings(self) -> None:
        self._js("document.getElementById('ov-settings').hidden = false")

    def open_phone(self) -> None:
        if self.phone_opener:
            self.phone_opener()

    def wait_for_api_key(self) -> None:
        return
