"""Masaüstü komutları: masaüstünü göster, pencereleri küçült, ekranı kilitle, ekran görüntüsü."""

from __future__ import annotations

import time
from pathlib import Path

VK_LWIN = 0x5B
VK_SHIFT = 0x10
VK_D = 0x44
VK_M = 0x4D
VK_TAB = 0x09
VK_UP = 0x26
VK_DOWN = 0x28
VK_SNAPSHOT = 0x2C

# Eylem -> (tuşlar, söylenecek yanıt). Hepsi geri alınabilir; kapatma ve kilit dışında yıkıcı iş yoktur.
KEYS = {
    "show_desktop": ((VK_LWIN, VK_D), "Masaüstü gösterildi."),
    "minimize_all": ((VK_LWIN, VK_M), "Pencereler küçültüldü."),
    "restore_all": ((VK_LWIN, VK_SHIFT, VK_M), "Pencereler geri getirildi."),
    "task_view": ((VK_LWIN, VK_TAB), "Görev görünümü açıldı."),
    "maximize": ((VK_LWIN, VK_UP), "Pencere büyütüldü."),
    "minimize": ((VK_LWIN, VK_DOWN), "Pencere küçültüldü."),
}
ALIASES = {
    "masaustu": "show_desktop", "masaüstü": "show_desktop", "desktop": "show_desktop",
    "hepsini kucult": "minimize_all", "hepsini küçült": "minimize_all",
    "geri getir": "restore_all", "restore": "restore_all",
    "gorev gorunumu": "task_view", "görev görünümü": "task_view",
    "buyut": "maximize", "büyüt": "maximize", "kucult": "minimize", "küçült": "minimize",
    "kilitle": "lock", "ekrani kilitle": "lock", "ekranı kilitle": "lock",
    "ekran goruntusu": "screenshot", "ekran görüntüsü": "screenshot",
}
ACTIONS = tuple(KEYS) + ("lock", "screenshot")


def _canonical(action: str) -> str:
    value = str(action or "").strip().lower()
    return ALIASES.get(value, value)


def screenshot_path(base: Path | None = None) -> Path:
    folder = base or (Path.home() / "Pictures" / "FRIDAY")
    return folder / f"ekran-{time.strftime('%Y%m%d-%H%M%S')}.png"


def run(action: str) -> str:
    from jarvis import win32

    name = _canonical(action)
    if name not in ACTIONS:
        return "Bilinmeyen masaüstü komutu. Şunlar var: " + ", ".join(ACTIONS) + "."
    if not win32.available():
        return "Bu komut yalnızca Windows'ta çalışır."
    if name == "lock":
        import ctypes

        ctypes.windll.user32.LockWorkStation()
        return "Ekran kilitlendi."
    if name == "screenshot":
        try:
            import mss
            from mss import tools as mss_tools

            target = screenshot_path()
            target.parent.mkdir(parents=True, exist_ok=True)
            with mss.mss() as grabber:
                shot = grabber.grab(grabber.monitors[0])
                mss_tools.to_png(shot.rgb, shot.size, output=str(target))
            return f"Ekran görüntüsü kaydedildi: {target.name} (Resimler/FRIDAY)."
        except Exception as exc:
            return f"Ekran görüntüsü alınamadı: {exc}"
    keys, answer = KEYS[name]
    win32.press_keys(*keys)
    return answer
