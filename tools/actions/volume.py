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


def _percent(value) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    number = float(str(value).replace("%", "").replace(",", ".").strip())
    # Model bazen yüzdeyi 0-1 kesir olarak verir (0.4 = %40).
    if 0 < abs(number) < 1:
        number *= 100
    return number


def resolve_level(current: float, level=None, change=None) -> float:
    """current/level/change yüzde (0-100). level öncelikli; change göreli."""
    absolute = _percent(level)
    delta = _percent(change)
    if absolute is not None:
        value = absolute
    elif delta is not None:
        value = current + delta
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


def _set_master(api, level, change, mute) -> tuple[float, float]:
    vol = api.master()
    now = vol.GetMasterVolumeLevelScalar() * 100
    new = resolve_level(now, level, change)
    vol.SetMasterVolumeLevelScalar(new / 100, None)
    if mute is not None:
        vol.SetMute(1 if mute else 0, None)
    elif new > now:
        vol.SetMute(0, None)
    return now, new


def set_volume(target: str = "spotify", level=None, change=None, mute=None, backend=None) -> str:
    name = normalize_target(target)
    try:
        api = backend or _Backend()
    except Exception as exc:  # pycaw/comtypes yoksa ya da Windows değilse
        return f"Ses kontrolü kullanılamıyor: {exc}"
    try:
        if name == "system":
            _now, new = _set_master(api, level, change, mute)
            label = "Bilgisayarın sesi"
        else:
            exes = TARGETS.get(name, (name if name.endswith(".exe") else name + ".exe",))
            volumes = api.sessions(exes)
            label = {"spotify": "Spotify", "youtube": "Tarayıcı (YouTube)"}.get(name, target)
            if not volumes:
                # Uygulama ses oturumu yoksa (henüz çalmadı) genel sesi ayarla; kullanıcı yine de sonuç alsın.
                _now, new = _set_master(api, level, change, mute)
                return f"{label} şu an ses çalmıyor; bilgisayarın genel sesini %{round(new)} yaptım."
            now = volumes[0].GetMasterVolume() * 100
            new = resolve_level(now, level, change)
            for vol in volumes:
                vol.SetMasterVolume(new / 100, None)
                if mute is not None:
                    vol.SetMute(1 if mute else 0, None)
                elif new > now:
                    vol.SetMute(0, None)
            # İstenen değer (tavana kırpılmadan): "aç" isteğinin kaydırıcı tavandayken kaybolmaması için.
            delta = _percent(change)
            wanted = _percent(level) if _percent(level) is not None else (now + delta if delta is not None else None)
            # Uygulama kaydırıcısı zaten tavandaysa "aç" isteği genel sese gider (yoksa hiçbir şey değişmezdi).
            if mute is None and wanted is not None and wanted > now and now >= 99.5:
                _m_now, m_new = _set_master(api, None, _percent(change) or 15, None)
                return f"{label} zaten en yüksekteydi; bilgisayarın genel sesini %{round(m_new)} yaptım."
    except Exception as exc:
        return f"Ses ayarlanamadi: {exc}"
    if mute:
        return f"{label} sessize alındı."
    return f"{label} sesi %{round(new)} yapıldı."
