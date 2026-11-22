"""Uygulama kapalıyken çift alkışla FRIDAY'i açar.

Alkışla uyanma açıksa FRIDAY'den çıkınca ve Windows açılışında küçük bir dinleyici (`--clap-listen`) çalışır:
yalnızca ses seviyesine bakar (kayıt yok, ağ yok), çift alkışta FRIDAY'i başlatır ve kendini kapatır.
"""

from __future__ import annotations

import subprocess
import sys
import time

APP_MUTEX = "Local\\JarvisRebuildSingleInstance"
LISTENER_MUTEX = "Local\\FridayClapListener"
RUN_VALUE = "FRIDAY-Alkis"
CHECK_EVERY = 5.0


def listen(read_level, launch, keep_going, clock=time.monotonic) -> bool:
    """Çift alkış duyulursa `launch()` çağırır ve True döner; `keep_going()` False olursa False döner."""
    from jarvis.audio.clap import ClapDetector

    detector = ClapDetector()
    while keep_going():
        if detector.feed(read_level(), clock()):
            launch()
            return True
    return False


def command(exe: str | None = None, frozen: bool | None = None) -> list[str]:
    frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    if frozen:
        return [exe or sys.executable, "--clap-listen"]
    return [exe or sys.executable, "-m", "jarvis", "--clap-listen"]


def _mutex_exists(name: str) -> bool:
    import ctypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenMutexW.restype = ctypes.c_void_p
    handle = kernel.OpenMutexW(0x100000, False, name)  # SYNCHRONIZE
    if handle:
        kernel.CloseHandle(ctypes.c_void_p(handle))
        return True
    return False


def _clap_wake_enabled() -> bool:
    from jarvis.config import load_app_config

    return bool(load_app_config().get("clap_wake", False))


def spawn_listener() -> None:
    """FRIDAY kapanırken: alkışla uyanma açıksa dinleyiciyi arka planda başlatır."""
    if sys.platform != "win32" or not _clap_wake_enabled():
        return
    try:
        flags = 0x00000008 | 0x08000000  # DETACHED_PROCESS | CREATE_NO_WINDOW
        subprocess.Popen(command(), creationflags=flags, close_fds=True)
    except OSError:
        pass


def launch_app() -> None:
    from jarvis.startup import installed_exe

    exe = installed_exe()
    args = [exe] if getattr(sys, "frozen", False) or exe.lower().endswith("friday.exe") else [exe, "-m", "jarvis"]
    subprocess.Popen(args, creationflags=0x00000008 | 0x08000000, close_fds=True)


def run_listener() -> int:
    if sys.platform != "win32" or not _clap_wake_enabled():
        return 0
    import ctypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.restype = ctypes.c_void_p
    handle = kernel.CreateMutexW(None, False, LISTENER_MUTEX)
    if ctypes.get_last_error() == 183:
        return 0  # dinleyici zaten çalışıyor
    # FRIDAY kapanırken bu dinleyiciyi o başlatır: süreç tamamen bitene kadar (en çok 15 sn) bekle.
    for _ in range(30):
        if not _mutex_exists(APP_MUTEX):
            break
        time.sleep(0.5)
    else:
        return 0  # FRIDAY açık kalmış: dinlemeye gerek yok
    import pyaudio

    from jarvis.audio.barge import peak

    audio = pyaudio.PyAudio()
    try:
        stream = audio.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)
    except Exception:
        audio.terminate()
        return 1
    state = {"checked": time.monotonic()}

    def keep_going() -> bool:
        now = time.monotonic()
        if now - state["checked"] >= CHECK_EVERY:
            state["checked"] = now
            if not _clap_wake_enabled() or _mutex_exists(APP_MUTEX):
                return False  # kapatıldı ya da FRIDAY başka yoldan açıldı
        return True

    try:
        listen(lambda: peak(stream.read(1024, exception_on_overflow=False)), launch_app, keep_going)
    finally:
        try:
            stream.stop_stream(); stream.close(); audio.terminate()
        except Exception:
            pass
    return 0
