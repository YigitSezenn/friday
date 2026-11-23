"""Sesle pencere denetimi: öndeki başka pencere ve kamera önizlemesi."""

from __future__ import annotations

CAMERA_SIZES = {"small": 0, "large": 1, "fullscreen": 2}
CAMERA_WORDS = {"kucult": "small", "small": "small", "normal": "large", "buyut": "large", "large": "large",
                "tam ekran": "fullscreen", "tam_ekran": "fullscreen", "fullscreen": "fullscreen"}
WINDOW_SHOW = {"minimize": 6, "maximize": 3, "restore": 9}
WINDOW_WORDS = {"kucult": "minimize", "minimize": "minimize", "buyut": "maximize", "maximize": "maximize", "tam ekran": "maximize",
                "restore": "restore", "eski boyut": "restore", "kapat": "close", "close": "close",
                "sekmeyi kapat": "close_tab", "close_tab": "close_tab"}
DONE = {"minimize": "Pencere küçültüldü.", "maximize": "Pencere büyütüldü.", "restore": "Pencere eski boyutuna döndü.",
        "close": "Pencere kapatılıyor.", "close_tab": "Sekme kapatılıyor."}


def _fold(text: str) -> str:
    return text.translate(str.maketrans("ıİşŞğĞüÜöÖçÇ", "iissgguuooCC".lower())).lower().strip()


def window_control(action: str, target: str = "window", ui=None, *, win=None) -> str:
    action, target = _fold(action), _fold(target) or "window"
    if target in {"camera", "kamera"}:
        size = CAMERA_WORDS.get(action)
        if size is None:
            return "Kamera için tam ekran, büyüt ya da küçült diyebilirsin."
        if ui is None or not hasattr(ui, "camera_size"):
            return "Kamera önizlemesi şu an kullanılamıyor."
        ui.camera_size(CAMERA_SIZES[size])
        return {"small": "Kamera küçüldü.", "large": "Kamera büyüdü.", "fullscreen": "Kamera tam ekran."}[size]
    name = WINDOW_WORDS.get(action)
    if name is None:
        return "Pencere için küçült, büyüt, eski boyut, kapat ya da sekmeyi kapat diyebilirsin."
    if win is None:
        from jarvis import win32 as win
    if not win.available():
        return "Pencere denetimi yalnızca Windows'ta çalışır."
    hwnd = win.target_window()
    if not hwnd:
        return "Denetlenecek başka bir pencere bulamadım."
    if name == "close":
        ok = win.close_window(hwnd)
    elif name == "close_tab":
        ok = win.close_tab(hwnd)
    else:
        ok = win.show_window(hwnd, WINDOW_SHOW[name])
    return DONE[name] if ok else "Pencereye ulaşamadım."
