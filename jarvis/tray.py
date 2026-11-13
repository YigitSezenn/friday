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
        self._done = threading.Event()
        self._shown = False
        self._proc = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="friday-tray", daemon=True)
        self._thread.start()

    def wait_ready(self, timeout: float = 3) -> bool:
        self.start()
        self._done.wait(timeout)
        return self._shown

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

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        import win32con
        import win32gui

        if msg in {win32con.WM_CLOSE, win32con.WM_DESTROY}:
            self._remove(hwnd)
            win32gui.PostQuitMessage(0)
            return 0
        if msg == win32con.WM_USER + 20:
            if lparam in {win32con.WM_LBUTTONUP, win32con.WM_LBUTTONDBLCLK}:
                self._on_show()
            elif lparam == win32con.WM_RBUTTONUP:
                self._menu(hwnd)
            return 0
        command = wparam & 0xFFFF
        if msg == win32con.WM_COMMAND and command == 1:
            self._on_show()
            return 0
        if msg == win32con.WM_COMMAND and command == 2:
            self._on_quit()
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _run(self) -> None:
        try:
            import win32api
            import win32con
            import win32gui

            self._proc = self._wnd_proc
            instance = win32api.GetModuleHandle(None)
            klass = win32gui.WNDCLASS()
            klass.hInstance = instance
            klass.lpszClassName = "FRIDAY.Tray"
            klass.lpfnWndProc = self._proc
            klass.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
            try:
                win32gui.RegisterClass(klass)
            except win32gui.error:
                pass
            hwnd = win32gui.CreateWindow(
                klass.lpszClassName,
                "FRIDAY",
                win32con.WS_OVERLAPPED,
                0,
                0,
                0,
                0,
                0,
                0,
                instance,
                None,
            )
            self._hwnd = hwnd or 0
            if self._hwnd:
                self._add(self._hwnd)
                win32gui.PumpMessages()
        finally:
            self._done.set()

    def _icon_handle(self):
        import win32con
        import win32gui

        path = _icon_file()
        if path is not None:
            try:
                return win32gui.LoadImage(
                    0,
                    str(path),
                    win32con.IMAGE_ICON,
                    16,
                    16,
                    win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE,
                )
            except Exception:
                pass
        if getattr(sys, "frozen", False):
            try:
                handle = win32gui.ExtractIcon(0, sys.executable, 0)
                if handle:
                    return handle
            except Exception:
                pass
        return win32gui.LoadIcon(0, win32con.IDI_APPLICATION)

    def _add(self, hwnd) -> None:
        import win32con
        import win32gui

        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        nid = (hwnd, 1, flags, win32con.WM_USER + 20, self._icon_handle(), "FRIDAY")
        try:
            win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (hwnd, 1))
        except Exception:
            pass
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
        self._shown = True
        self._done.set()

    def _remove(self, hwnd) -> None:
        import win32gui

        try:
            win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (hwnd, 1))
        except Exception:
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


def _icon_file() -> Path | None:
    candidates = []
    if getattr(sys, "frozen", False):
        root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidates.append(root / "assets" / "friday.ico")
    candidates.append(Path(__file__).resolve().parents[1] / "assets" / "friday.ico")
    for path in candidates:
        if path.is_file():
            return path
    return None
