from __future__ import annotations

import difflib
import json
import os
import re
import subprocess

APP_ALIASES = {
    "safari": "Microsoft Edge",
    "edge": "Microsoft Edge",
    "chrome": "Google Chrome",
    "krom": "Google Chrome",
    "google": "Google Chrome",
    "fotoşop": "Photoshop",
    "fotosop": "Photoshop",
    "photoshop": "Photoshop",
    "firefox": "Firefox",
    "opera": "Opera",
    "brave": "Brave",
    "terminal": "Windows Terminal",
    "komut istemi": "Command Prompt",
    "powershell": "Windows PowerShell",
    "finder": "File Explorer",
    "explorer": "File Explorer",
    "dosya gezgini": "File Explorer",
    "spotify": "Spotify",
    "vscode": "Visual Studio Code",
    "vs code": "Visual Studio Code",
    "code": "Visual Studio Code",
    "visual studio": "Visual Studio",
    "notion": "Notion",
    "slack": "Slack",
    "discord": "Discord",
    "whatsapp": "WhatsApp",
    "telegram": "Telegram",
    "zoom": "Zoom",
    "teams": "Microsoft Teams",
    "mail": "Mail",
    "posta": "Mail",
    "outlook": "Outlook",
    "calendar": "Calendar",
    "takvim": "Calendar",
    "notepad": "Notepad",
    "not defteri": "Notepad",
    "notlar": "Notepad",
    "notes": "Notepad",
    "textedit": "Notepad",
    "sticky notes": "Sticky Notes",
    "music": "Media Player",
    "müzik": "Media Player",
    "photos": "Photos",
    "fotoğraflar": "Photos",
    "preview": "Photos",
    "önizleme": "Photos",
    "maps": "Maps",
    "haritalar": "Maps",
    "calculator": "Calculator",
    "hesap makinesi": "Calculator",
    "settings": "Settings",
    "ayarlar": "Settings",
    "system settings": "Settings",
    "system preferences": "Settings",
    "denetim masası": "Control Panel",
    "control panel": "Control Panel",
    "görev yöneticisi": "Task Manager",
    "gorev yoneticisi": "Task Manager",
    "task manager": "Task Manager",
    "activity monitor": "Task Manager",
    "aktivite monitörü": "Task Manager",
    "paint": "Paint",
    "word": "Word",
    "excel": "Excel",
    "powerpoint": "PowerPoint",
    "figma": "Figma",
    "postman": "Postman",
    "docker": "Docker Desktop",
    "steam": "Steam",
}

DIRECT_TARGETS = {
    "File Explorer": "explorer.exe",
    "Notepad": "notepad.exe",
    "Calculator": "calc.exe",
    "Paint": "mspaint.exe",
    "Task Manager": "taskmgr.exe",
    "Settings": "ms-settings:",
    "Control Panel": "control.exe",
    "Command Prompt": "cmd.exe",
    "Windows PowerShell": "powershell.exe",
    "Maps": "bingmaps:",
    "Calendar": "outlookcal:",
    "Mail": "outlookmail:",
}

_TR_FOLD = str.maketrans({
    "ı": "i", "İ": "i", "I": "i",
    "ş": "s", "Ş": "s",
    "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u",
    "ö": "o", "Ö": "o",
    "ç": "c", "Ç": "c",
})
_ALIAS_LOOKUP = {re.sub(r"\s+", " ", key.casefold().translate(_TR_FOLD)).strip(): value for key, value in APP_ALIASES.items()}


def normalize_name(text: str) -> str:
    lowered = (text or "").strip().casefold().translate(_TR_FOLD)
    return re.sub(r"\s+", " ", lowered).strip()


def resolve_alias(app_name: str) -> str:
    needle = normalize_name(app_name)
    if not needle:
        return (app_name or "").strip()
    exact = _ALIAS_LOOKUP.get(needle)
    if exact:
        return exact
    best, best_score = None, 0.0
    for alias, target in _ALIAS_LOOKUP.items():
        score = difflib.SequenceMatcher(None, needle, alias).ratio()
        if alias.startswith(needle) and len(needle) >= 4:
            score = max(score, 0.9)
        if score > best_score:
            best, best_score = target, score
    if best and best_score >= 0.78:
        return best
    return app_name.strip()


def _start(target: str, via_explorer: bool = False) -> bool:
    try:
        if via_explorer:
            result = subprocess.run(
                ["explorer.exe", target],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return result.returncode in (0, 1)
        os.startfile(target)  # type: ignore[attr-defined]
        return True
    except OSError:
        return False


def _start_apps() -> list[dict]:
    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Get-StartApps | Select-Object Name, AppID | ConvertTo-Json -Compress",
            ],
            capture_output=True,
            text=True,
            timeout=25,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0 or not (result.stdout or "").strip():
        return []
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        data = [data]
    apps = []
    for item in data:
        if isinstance(item, dict) and item.get("Name") and item.get("AppID"):
            apps.append({"name": str(item["Name"]).strip(), "app_id": str(item["AppID"]).strip()})
    return apps


def _find_start_app(target_name: str, allow_fuzzy: bool = True) -> tuple[str, str]:
    needle = normalize_name(target_name)
    if not needle:
        return "", ""
    best_score = 0.0
    best = None
    for app in _start_apps():
        candidate = normalize_name(app["name"])
        if candidate == needle:
            score = 300.0
        elif candidate.startswith(needle) or needle.startswith(candidate):
            score = 220.0
        elif needle in candidate:
            score = 160.0
        elif allow_fuzzy:
            score = difflib.SequenceMatcher(None, needle, candidate).ratio() * 100
        else:
            score = 0.0
        if score > best_score:
            best_score, best = score, app
    threshold = 150 if not allow_fuzzy else 78
    if best and best_score >= threshold:
        return best["app_id"], best["name"]
    return "", ""


def open_app(app_name: str) -> str:
    raw = (app_name or "").strip()
    if not raw:
        return "Uygulama adi belirtilmedi."
    needle = normalize_name(raw)
    resolved = _ALIAS_LOOKUP.get(needle)
    if resolved is None:
        app_id, matched = _find_start_app(raw, allow_fuzzy=False)
        if app_id and _start(f"shell:AppsFolder\\{app_id}", via_explorer=True):
            return f"{matched} acildi."
        resolved = resolve_alias(raw)
    direct = DIRECT_TARGETS.get(resolved)
    if direct and _start(direct):
        return f"{resolved} acildi."
    for candidate_name in (resolved, raw):
        app_id, matched = _find_start_app(candidate_name)
        if app_id and _start(f"shell:AppsFolder\\{app_id}", via_explorer=True):
            return f"{matched} acildi."
    candidate = resolved if resolved.lower().endswith(".exe") else f"{resolved}.exe"
    if _start(candidate.replace(" ", "")):
        return f"{resolved} acildi."
    return f"'{app_name}' bulunamadi veya acilamadi."
