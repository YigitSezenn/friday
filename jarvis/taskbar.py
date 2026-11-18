"""Pencere kapanınca veya küçülünce FRIDAY görev çubuğunda çalışmaya devam eder."""

from __future__ import annotations

SHOW_EVENT = "Local\\FRIDAY.Rebuild.Show"


def keep_on_taskbar(quitting: bool, installer_running: bool = False) -> bool:
    """Kapatma ve küçültme süreci bitirmez. Kurulum veya kaldırma varsa pencere kapanabilir."""
    return not quitting and not installer_running


def installer_is_running(names: list[str] | None = None) -> bool:
    """Kurulum veya kaldırma çalışıyorsa pencere gerçekten kapanır. Yalnız süreç adı bakılır."""
    if names is None:
        try:
            import psutil
        except Exception:
            return False
        found: list[str] = []
        try:
            for proc in psutil.process_iter(["name"]):
                found.append(str(proc.info.get("name") or ""))
        except Exception:
            return False
        names = found
    wanted = {"unins000.exe", "friday-kurulum.exe"}
    return any(name.casefold() in wanted for name in names)
