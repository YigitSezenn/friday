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
