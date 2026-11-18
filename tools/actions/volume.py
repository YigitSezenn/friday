"""Uygulama başına ses: Spotify, tarayıcı (YouTube) ya da sistemin genel sesi.

Windows Core Audio (pycaw) ile çalışır; FRIDAY'in kendi konuşma sesine dokunmaz.
"""
from __future__ import annotations

import re

TARGETS = {
    "spotify": ("spotify.exe",),
    "youtube": ("chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "brave.exe"),
    "tarayici": ("chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "brave.exe"),
    "browser": ("chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "brave.exe"),
    "chrome": ("chrome.exe",),
    "edge": ("msedge.exe",),
    "discord": ("discord.exe",),
    "vlc": ("vlc.exe",),
}
SYSTEM_WORDS = {"system", "sistem", "genel", "bilgisayar", "pc", "hepsi", "tum", "tüm", "master", ""}


def normalize_target(target: str) -> str:
    key = (target or "").strip().casefold().replace("ı", "i")
    key = re.sub(r"[^a-z0-9.]+", "", key.replace("ç", "c").replace("ş", "s").replace("ğ", "g").replace("ö", "o").replace("ü", "u"))
    if key in SYSTEM_WORDS:
        return "system"
    for name in TARGETS:
        if name in key:
            return name
    return key


def resolve_level(current: float, level=None, change=None) -> float:
    """current/level/change yüzde (0-100). level öncelikli; change göreli."""
    if level is not None and str(level).strip() != "":
        value = float(str(level).replace("%", "").strip())
    elif change is not None and str(change).strip() != "":
        value = current + float(str(change).replace("%", "").strip())
    else:
        value = current
    return max(0.0, min(100.0, value))


class _Backend:
    """Gerçek Windows arka ucu (yalnızca Windows'ta içe aktarılır)."""

    def __init__(self):
        import comtypes
        from pycaw.pycaw import AudioUtilities

        try:
            comtypes.CoInitialize()
        except OSError:
            pass
        self._utils = AudioUtilities

    def sessions(self, exe_names):
        out = []
        for session in self._utils.GetAllSessions():
            proc = session.Process
            if proc is not None and proc.name().lower() in exe_names:
                out.append(session.SimpleAudioVolume)
        return out

    def master(self):
        return self._utils.GetSpeakers().EndpointVolume


def set_volume(target: str = "spotify", level=None, change=None, mute=None, backend=None) -> str:
    name = normalize_target(target)
    try:
        api = backend or _Backend()
    except Exception as exc:  # pycaw/comtypes yoksa ya da Windows değilse
        return f"Ses kontrolu kullanilamiyor: {exc}"
    try:
        if name == "system":
            vol = api.master()
            now = vol.GetMasterVolumeLevelScalar() * 100
            new = resolve_level(now, level, change)
            vol.SetMasterVolumeLevelScalar(new / 100, None)
            if mute is not None:
                vol.SetMute(1 if mute else 0, None)
            label = "Bilgisayarin sesi"
        else:
            exes = TARGETS.get(name, (name if name.endswith(".exe") else name + ".exe",))
            volumes = api.sessions(exes)
            if not volumes:
                return f"{target} su an ses calmiyor ya da acik degil; once calmaya baslat."
            now = volumes[0].GetMasterVolume() * 100
            new = resolve_level(now, level, change)
            for vol in volumes:
                vol.SetMasterVolume(new / 100, None)
                if mute is not None:
                    vol.SetMute(1 if mute else 0, None)
            label = {"spotify": "Spotify", "youtube": "Tarayici (YouTube)"}.get(name, target)
    except Exception as exc:
        return f"Ses ayarlanamadi: {exc}"
    if mute:
        return f"{label} sessize alindi."
    return f"{label} sesi %{round(new)} yapildi."
