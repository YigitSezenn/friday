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


_LOOPS: dict[str, object] = {}


def _scaled(file: Path, name: str, volume: int) -> Path:
    """Ses seviyesini dosyaya uygular (MCI waveaudio ses ayarını her sürümde desteklemiyor)."""
    volume = max(0, min(1000, int(volume)))
    if volume >= 1000:
        return file
    import array
    import wave

    from jarvis.paths import data_path

    out = data_path("cache", f"{name}-{volume}.wav")
    if out.is_file() and out.stat().st_mtime >= file.stat().st_mtime:
        return out
    with wave.open(str(file), "rb") as src:
        params = src.getparams()
        frames = src.readframes(src.getnframes())
    samples = array.array("h")
    samples.frombytes(frames)
    gain = volume / 1000.0
    scaled = array.array("h", (int(x * gain) for x in samples))
    with wave.open(str(out), "wb") as dst:
        dst.setparams(params)
        dst.writeframes(scaled.tobytes())
    return out


def _play_once(alias: str, file: Path, wait: bool) -> bool:
    with _lock:
        if alias in _ALIASES:
            _mci(f"close {alias}")
            _ALIASES.discard(alias)
        if _mci(f'open "{file}" type waveaudio alias {alias}') != 0:
            return False
        _ALIASES.add(alias)
    # `wait` kilidin dışında: başka iş parçacığı stop() ile kesebilsin.
    if _mci(f"play {alias}" + (" wait" if wait else "")) != 0:
        _close(alias)
        return False
    return True


def _close(alias: str) -> None:
    with _lock:
        if alias in _ALIASES:
            _mci(f"stop {alias}")
            _mci(f"close {alias}")
            _ALIASES.discard(alias)


def _loop(name: str, file: Path, token: object) -> None:
    """MCI waveaudio 'repeat' bayrağını desteklemez: döngüyü biz kurarız."""
    alias = f"friday_{name}"
    while _LOOPS.get(name) is token:
        if not _play_once(alias, file, wait=True):
            break
        _close(alias)
    if _LOOPS.get(name) is token:
        _LOOPS.pop(name, None)


def play(name: str, wait: bool = False, loop: bool = False, volume: int = 1000) -> bool:
    """Ses dosyasını çalar. Dosya/MCI yoksa False döner; çağıran bip'e düşebilir.

    MCI ayrı takma adlarla çalışır; böylece müzik ile efekt birbirini kesmez.
    """
    file = path(name)
    if file is None or sys.platform != "win32":
        return False
    try:
        file = _scaled(file, name, volume)
        alias = f"friday_{name}"
        if loop:
            token = object()
            _LOOPS[name] = token
            threading.Thread(target=_loop, args=(name, file, token), name=f"friday-sound-{name}", daemon=True).start()
            return True
        if not _play_once(alias, file, wait=wait):
            return False
        if wait:
            _close(alias)
        return True
    except Exception:
        return False


def stop(name: str) -> None:
    alias = f"friday_{name}"
    _LOOPS.pop(name, None)
    if sys.platform != "win32":
        return
    try:
        _close(alias)
    except Exception:
        pass

