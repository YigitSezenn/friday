"""Windows oturumunda FRIDAY'i açma. Varsayılan kapalı. Yönetici gerekmez."""

from __future__ import annotations

import sys
from pathlib import Path

RUN_VALUE = "FRIDAY"


def installed_exe() -> str:
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).resolve())
    local = Path.home() / "AppData" / "Local" / "FRIDAY" / "FRIDAY.exe"
    if local.exists():
        return str(local)
    return str(Path(sys.executable).resolve())


class MemoryRegistry:
    """Testler gerçek HKCU Run anahtarına yazmaz."""

    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def read(self, name: str) -> str | None:
        return self.values.get(name)

    def write(self, name: str, value: str) -> None:
        self.values[name] = value

    def delete(self, name: str) -> None:
        self.values.pop(name, None)


def apply_windows_startup(enabled: bool, exe: str | None = None, registry: MemoryRegistry | None = None) -> str:
    target = exe or installed_exe()
    store = registry if registry is not None else _windows_registry()
    if enabled:
        store.write(RUN_VALUE, f'"{target}"')
        return store.read(RUN_VALUE) or ""
    store.delete(RUN_VALUE)
    return ""


def _windows_registry() -> MemoryRegistry:
    import winreg

    class _Hive:
        def read(self, name: str) -> str | None:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ) as key:
                    value, _ = winreg.QueryValueEx(key, name)
                    return str(value)
            except OSError:
                return None

        def write(self, name: str, value: str) -> None:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)

        def delete(self, name: str) -> None:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as key:
                    winreg.DeleteValue(key, name)
            except OSError:
                return

    return _Hive()
