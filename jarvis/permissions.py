"""Windows gizlilik izinleri: mikrofon ve kamera acik mi? Yalnizca okur, hicbirini degistirmez."""

from __future__ import annotations

import sys

KINDS = {"microphone": "ms-settings:privacy-microphone", "webcam": "ms-settings:privacy-webcam"}
_STORE = r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore"


def state_from_value(value) -> str:
    text = str(value or "").strip().lower()
    if text == "allow":
        return "granted"
    if text == "deny":
        return "denied"
    return "unknown"


def permission_state(kind: str) -> str:
    """granted | denied | unknown. Anahtar yoksa Windows varsayilani izin verir; bilinmiyor deriz."""
    if kind not in KINDS or sys.platform != "win32":
        return "unknown"
    try:
        import winreg
    except ImportError:
        return "unknown"
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(hive, f"{_STORE}\\{kind}") as handle:
                state = state_from_value(winreg.QueryValueEx(handle, "Value")[0])
        except OSError:
            continue
        if state == "denied":
            return state
        if state == "granted" and hive == winreg.HKEY_CURRENT_USER:
            return state
    return "unknown"


def snapshot() -> dict:
    return {kind: permission_state(kind) for kind in KINDS}


def settings_uri(kind: str) -> str:
    return KINDS.get(kind, "")
