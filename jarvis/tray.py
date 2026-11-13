"""Küçülünce FRIDAY sistem tepsisinde çalışmaya devam eder."""

from __future__ import annotations

import sys
import threading
from pathlib import Path


class FridayTray:
    def __init__(self, on_show, on_quit) -> None:
        self._on_show = on_show
        self._on_quit = on_quit
        self._hwnd = 0
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="friday-tray", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        hwnd = self._hwnd
        if not hwnd:
            return
        try:
            import win32con
            import win32gui

            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        except Exception:
            return

    def _run(self) -> None:
        try:
            import win32con
            import win32gui
        except Exception:
            return
        message = win32con.WM_USER + 20
        window = self

        def wnd_proc(hwnd, msg, wparam, lparam):
            if msg == win32con.WM_CLOSE or msg == win32con.WM_DESTROY:
                window._remove(hwnd)
                win32gui.PostQuitMessage(0)
                return 0
            if msg == message:
                if lparam in {win32con.WM_LBUTTONUP, win32con.WM_LBUTTONDBLCLK}:
                    window._on_show()
                elif lparam == win32con.WM_RBUTTONUP:
                    window._menu(hwnd)
                return 0
            if msg == win32con.WM_COMMAND and (wparam & 0xFFFF) == 2:
                window._on_quit()
                return 0
            if msg == win32con.WM_COMMAND and (wparam & 0xFFFF) == 1:
                window._on_show()
                return 0
            return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

        import win32api

        instance = win32api.GetModuleHandle(None)
        klass = win32gui.WNDCLASS()
        klass.hInstance = instance
        klass.lpszClassName = "FRIDAYTray"
        klass.lpfnWndProc = wnd_proc
        try:
            win32gui.RegisterClass(klass)
        except win32gui.error:
            pass
        hwnd = win32gui.CreateWindow(klass.lpszClassName, "FRIDAY", 0, 0, 0, 0, 0, 0, 0, instance, None)
        self._hwnd = hwnd
        self._add(hwnd)
        win32gui.PumpMessages()

    def _icon(self):
        import win32con
        import win32gui

        if getattr(sys, "frozen", False):
            try:
                return win32gui.ExtractIcon(0, sys.executable, 0)
            except Exception:
                pass
        path = Path(__file__).resolve().parents[1] / "assets" / "friday.ico"
        if path.is_file():
            return win32gui.LoadImage(
                0,
                str(path),
                win32con.IMAGE_ICON,
                0,
                0,
                win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE,
            )
        return win32gui.LoadIcon(0, win32con.IDI_APPLICATION)

    def _add(self, hwnd) -> None:
        import win32con
        import win32gui

        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        nid = (hwnd, 0, flags, win32con.WM_USER + 20, self._icon(), "FRIDAY")
        try:
            win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
        except win32gui.error:
            return

    def _remove(self, hwnd) -> None:
        import win32gui

        try:
            win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (hwnd, 0))
        except win32gui.error:
            return

    def _menu(self, hwnd) -> None:
        import win32con
        import win32gui

        menu = win32gui.CreatePopupMenu()
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1, "Göster")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 2, "Çıkış")
        pos = win32gui.GetCursorPos()
        win32gui.SetForegroundWindow(hwnd)
        win32gui.TrackPopupMenu(menu, win32con.TPM_LEFTALIGN, pos[0], pos[1], 0, hwnd, None)
        win32gui.PostMessage(hwnd, win32con.WM_NULL, 0, 0)
