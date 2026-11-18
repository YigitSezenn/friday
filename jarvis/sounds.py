"""FRIDAY ses efektleri ve arka plan müziği (Windows MCI; başka sistemde sessiz)."""
from __future__ import annotations

import sys
import threading
from pathlib import Path

_lock = threading.Lock()
_ALIASES: set[str] = set()


def _dir() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / "assets" / "sounds"


def path(name: str) -> Path | None:
    file = _dir() / f"{name}.wav"
    return file if file.is_file() else None


def _mci(command: str) -> int:
    import ctypes

    return int(ctypes.windll.winmm.mciSendStringW(command, None, 0, None))


def play(name: str, wait: bool = False, loop: bool = False, volume: int = 1000) -> bool:
    """Ses dosyasını çalar. Dosya/MCI yoksa False döner; çağıran bip'e düşebilir.

    MCI ayrı takma adlarla çalışır; böylece müzik ile efekt birbirini kesmez.
    """
    file = path(name)
    if file is None or sys.platform != "win32":
        return False
    alias = f"friday_{name}"
    try:
        with _lock:
            if alias in _ALIASES:
                _mci(f"close {alias}")
                _ALIASES.discard(alias)
            if _mci(f'open "{file}" type waveaudio alias {alias}') != 0:
                return False
            _ALIASES.add(alias)
            _mci(f"setaudio {alias} volume to {max(0, min(1000, int(volume)))}")
            command = f"play {alias}" + (" repeat" if loop else "") + (" wait" if wait and not loop else "")
        if _mci(command) != 0:
            stop(name)
            return False
        if wait and not loop:
            stop(name)
        return True
    except Exception:
        return False


def stop(name: str) -> None:
    alias = f"friday_{name}"
    if sys.platform != "win32":
        return
    try:
        with _lock:
            if alias in _ALIASES:
                _mci(f"stop {alias}")
                _mci(f"close {alias}")
                _ALIASES.discard(alias)
    except Exception:
        pass


def stop_all() -> None:
    for alias in list(_ALIASES):
        stop(alias.removeprefix("friday_"))
