"""Tip bildirimli küçük Windows API sarmalayıcıları.

ctypes'ta restype/argtypes verilmezse dönüş değeri 32 bit int sayılır. 64 bit Windows'ta
GlobalLock/GlobalAlloc gibi işaretçi döndüren çağrılar kesilir ve sonraki bellek erişimi
uygulamayı yerel bir erişim hatasıyla düşürür. Tüm Windows çağrıları buradan geçer.
"""
from __future__ import annotations

import sys

_api = None


def _lib():
    global _api
    if _api is None:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        user32.OpenClipboard.argtypes = [wintypes.HWND]
        user32.OpenClipboard.restype = wintypes.BOOL
        user32.EmptyClipboard.restype = wintypes.BOOL
        user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
        user32.SetClipboardData.restype = wintypes.HANDLE
        user32.CloseClipboard.restype = wintypes.BOOL
        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        user32.GetWindowTextLengthW.restype = ctypes.c_int
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetWindowTextW.restype = ctypes.c_int
        user32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM), wintypes.LPARAM]
        user32.EnumWindows.restype = wintypes.BOOL
        user32.IsWindowVisible.argtypes = [wintypes.HWND]
        user32.IsWindowVisible.restype = wintypes.BOOL
        user32.IsIconic.argtypes = [wintypes.HWND]
        user32.IsIconic.restype = wintypes.BOOL
        user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.ShowWindow.restype = wintypes.BOOL
        user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        user32.SetForegroundWindow.restype = wintypes.BOOL
        user32.BringWindowToTop.argtypes = [wintypes.HWND]
        user32.BringWindowToTop.restype = wintypes.BOOL
        user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        user32.GetWindowRect.restype = wintypes.BOOL
        user32.IsZoomed.argtypes = [wintypes.HWND]
        user32.IsZoomed.restype = wintypes.BOOL
        user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetClassNameW.restype = ctypes.c_int
        user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        user32.SetWindowPos.restype = wintypes.BOOL
        user32.GetSystemMetrics.argtypes = [ctypes.c_int]
        user32.GetSystemMetrics.restype = ctypes.c_int
        user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user32.PostMessageW.restype = wintypes.BOOL
        user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.GetWindowLongW.restype = ctypes.c_long
        user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_size_t]
        user32.keybd_event.restype = None
        kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
        kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalLock.restype = wintypes.LPVOID
        kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalUnlock.restype = wintypes.BOOL
        kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalFree.restype = wintypes.HGLOBAL
        _api = (ctypes, user32, kernel32)
    return _api


def available() -> bool:
    return sys.platform == "win32"


def set_clipboard(text: str) -> bool:
    if not text or not available():
        return False
    ctypes, user32, kernel32 = _lib()
    data = text.encode("utf-16-le") + b"\x00\x00"
    if not user32.OpenClipboard(None):
        return False
    try:
        user32.EmptyClipboard()
        handle = kernel32.GlobalAlloc(0x0002, len(data))  # GMEM_MOVEABLE
        if not handle:
            return False
        locked = kernel32.GlobalLock(handle)
        if not locked:
            kernel32.GlobalFree(handle)
            return False
        ctypes.memmove(locked, data, len(data))
        kernel32.GlobalUnlock(handle)
        if not user32.SetClipboardData(13, handle):  # CF_UNICODETEXT
            kernel32.GlobalFree(handle)
            return False
        return True  # başarıda bellek panoya geçer; serbest bırakılmaz
    finally:
        user32.CloseClipboard()


def foreground_title() -> str:
    if not available():
        return ""
    ctypes, user32, _kernel32 = _lib()
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ""
    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def press_keys(*codes: int) -> None:
    """Tuşlara sırayla basar, ters sırayla bırakır (ör. Ctrl+Enter: 0x11, 0x0D)."""
    if not available():
        return
    _ctypes, user32, _kernel32 = _lib()
    for code in codes:
        user32.keybd_event(code, 0, 0, 0)
    for code in reversed(codes):
        user32.keybd_event(code, 0, 2, 0)


def find_window(marker: str) -> int:
    """Başlığında `marker` geçen görünür üst düzey pencereyi bulur (0: yok)."""
    if not available() or not marker:
        return 0
    ctypes, user32, _kernel32 = _lib()
    from ctypes import wintypes

    needle = marker.casefold()
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def visit(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        if needle in buffer.value.casefold():
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(visit, 0)
    return int(found[0]) if found else 0


def bring_to_front(hwnd: int) -> bool:
    """Pencereyi öne getirir. Windows yalnızca öndeki sürecin bunu yapmasına izin verir; FRIDAY
    o an öndeyse çalışır. Kısa bir Alt basışı, kilit takılırsa izni açar."""
    if not available() or not hwnd:
        return False
    _ctypes, user32, _kernel32 = _lib()
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    else:
        user32.ShowWindow(hwnd, 5)  # SW_SHOW
    if not user32.SetForegroundWindow(hwnd):
        press_keys(0x12)  # Alt: ön plan kilidini açar
        user32.SetForegroundWindow(hwnd)
    user32.BringWindowToTop(hwnd)
    return int(user32.GetForegroundWindow() or 0) == int(hwnd)


def foreground_window() -> int:
    if not available():
        return 0
    _ctypes, user32, _kernel32 = _lib()
    return int(user32.GetForegroundWindow() or 0)


def window_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    """(sol, üst, sağ, alt) ekran koordinatları."""
    if not available() or not hwnd:
        return None
    _ctypes, user32, _kernel32 = _lib()
    from ctypes import wintypes

    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, _ctypes.byref(rect)):
        return None
    return rect.left, rect.top, rect.right, rect.bottom


def movable(hwnd: int) -> bool:
    """Masaüstü, görev çubuğu ve tam ekran pencereler taşınmaz."""
    if not available() or not hwnd:
        return False
    ctypes, user32, _kernel32 = _lib()
    if user32.IsZoomed(hwnd):
        return False
    buffer = ctypes.create_unicode_buffer(64)
    user32.GetClassNameW(hwnd, buffer, 64)
    return buffer.value not in {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"}


def move_window(hwnd: int, x: int, y: int) -> bool:
    if not available() or not hwnd:
        return False
    _ctypes, user32, _kernel32 = _lib()
    return bool(user32.SetWindowPos(hwnd, None, int(x), int(y), 0, 0, 0x0001 | 0x0004 | 0x0010))  # NOSIZE|NOZORDER|NOACTIVATE


def controllable(hwnd: int) -> bool:
    """Masaüstü ve görev çubuğu dışındaki pencereler (tam ekran olanlar dahil) denetlenebilir."""
    if not available() or not hwnd:
        return False
    ctypes, user32, _kernel32 = _lib()
    buffer = ctypes.create_unicode_buffer(64)
    user32.GetClassNameW(hwnd, buffer, 64)
    return buffer.value not in {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"}


def is_maximized(hwnd: int) -> bool:
    if not available() or not hwnd:
        return False
    _ctypes, user32, _kernel32 = _lib()
    return bool(user32.IsZoomed(hwnd))


def resize_window(hwnd: int, width: int, height: int) -> bool:
    if not available() or not hwnd:
        return False
    _ctypes, user32, _kernel32 = _lib()
    return bool(user32.SetWindowPos(hwnd, None, 0, 0, int(width), int(height), 0x0002 | 0x0004 | 0x0010))  # NOMOVE|NOZORDER|NOACTIVATE


def show_window(hwnd: int, command: int) -> bool:
    """3: büyüt, 6: küçült (görev çubuğuna), 9: eski boyuta getir."""
    if not available() or not hwnd:
        return False
    _ctypes, user32, _kernel32 = _lib()
    return bool(user32.ShowWindow(hwnd, command))


def screen_size() -> tuple[int, int]:
    if not available():
        return 1920, 1080
    _ctypes, user32, _kernel32 = _lib()
    return int(user32.GetSystemMetrics(0)), int(user32.GetSystemMetrics(1))


def close_window(hwnd: int) -> bool:
    """Pencereye kapanma isteği gönderir (uygulama kaydedilmemiş işi sorabilir). FRIDAY'in kendi penceresi kapatılmaz."""
    if not available() or not hwnd:
        return False
    ctypes, user32, _kernel32 = _lib()
    import os
    from ctypes import wintypes

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == os.getpid():
        return False
    return bool(user32.PostMessageW(hwnd, 0x0010, 0, 0))  # WM_CLOSE


def _own(hwnd: int) -> bool:
    ctypes, user32, _kernel32 = _lib()
    import os
    from ctypes import wintypes

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value == os.getpid()


def target_window() -> int:
    """Denetlenecek pencere: öndeki pencere FRIDAY değilse o, değilse Z sırasında altındaki ilk görünür pencere."""
    if not available():
        return 0
    ctypes, user32, _kernel32 = _lib()
    front = foreground_window()
    if front and not _own(front) and controllable(front):
        return front
    found = []
    from ctypes import wintypes

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def visit(hwnd, _lparam):
        if user32.IsWindowVisible(hwnd) and not user32.IsIconic(hwnd) and user32.GetWindowTextLengthW(hwnd) and not _own(hwnd) and controllable(hwnd):
            ex_style = user32.GetWindowLongW(hwnd, -20)
            if not ex_style & 0x80:  # WS_EX_TOOLWINDOW
                found.append(int(hwnd))
                return False
        return True

    user32.EnumWindows(visit, 0)
    return found[0] if found else 0


def close_tab(hwnd: int) -> bool:
    """Pencereyi öne getirip Ctrl+W gönderir (tarayıcı/Gezgin/editör sekmesini kapatır). FRIDAY'in kendi penceresine dokunmaz."""
    if not available() or not hwnd or _own(hwnd):
        return False
    if not bring_to_front(hwnd):
        return False
    press_keys(0x11, 0x57)  # Ctrl+W
    return True
