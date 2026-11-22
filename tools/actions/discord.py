from __future__ import annotations

import json
import re
import time

from jarvis.paths import data_path
from tools.actions.whatsapp import _normalize_lookup


def _book() -> dict:
    path = data_path("memory", "discord_contacts.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(book: dict) -> None:
    path = data_path("memory", "discord_contacts.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(book, ensure_ascii=False, indent=1), encoding="utf-8")


def _entry(value) -> dict:
    """Kayıt biçimi: {'username': ..., 'id': ...}; eski kayıtlar yalnızca kimlik metniydi."""
    if isinstance(value, dict):
        return {"username": str(value.get("username") or ""), "id": str(value.get("id") or "")}
    return {"username": "", "id": str(value or "")}


def _lookup(name: str) -> tuple[str, dict]:
    needle = _normalize_lookup(name)
    for key, value in _book().items():
        if needle and (_normalize_lookup(key) == needle or needle in _normalize_lookup(key)):
            return key, _entry(value)
    return "", _entry("")


def _clean_username(value: str) -> str:
    """Discord kullanıcı adı: baştaki @ atılır, boşluksuz, küçük harf/rakam/nokta/alt çizgi."""
    return re.sub(r"[^a-z0-9._]", "", str(value or "").strip().lstrip("@").lower())[:32]


def send_discord_message(message: str, recipient_name: str = "", username: str = "", confirm_send: bool = False, user_id: str = "") -> str:
    """Discord masaüstü uygulamasında hızlı geçişle (Ctrl+K) kişinin DM'ini açar, mesajı yapıştırır ve Enter ile gönderir."""
    text = (message or "").strip()
    if not text:
        return "Mesaj boş olamaz."
    name = (recipient_name or "").strip()
    handle = _clean_username(username)
    if not handle:
        name, entry = _lookup(name)
        handle = _clean_username(entry["username"])
        if not handle:
            return (
                f"'{recipient_name}' için kayıtlı Discord kullanıcı adı yok. Kişinin kullanıcı adını (profilinde isminin altında yazan, "
                "örneğin yakupp) söylersen kaydederim."
            )
    from tools.actions import confirm

    parts = (handle, text)
    if not confirm_send:
        return confirm.ask("discord", parts, f"Discord mesajı — Kime: {name or handle} (@{handle}), Mesaj: {text[:300]}.")
    problem = confirm.check("discord", parts)
    if problem:
        return problem
    return _deliver(name, handle, text)


def _deliver(name: str, handle: str, text: str, save: bool = True) -> str:
    import os

    from jarvis import win32
    from tools.actions.apps import front_wait

    start = getattr(os, "startfile", None)
    if not start or not win32.available():
        return "Discord mesajı yalnızca Windows'ta gönderilebilir."
    try:
        start("discord://-/channels/@me")  # Discord'u açar ya da öne getirir; kimseye bir şey göndermez
    except OSError as exc:
        return f"Discord açılamadı: {exc}"
    if not front_wait("Discord", timeout=10.0):
        return "Discord penceresi açılmadı; mesaj göndermedim."
    time.sleep(1.5)
    if "discord" not in win32.foreground_title().lower():
        return "Discord öne gelmedi; başka bir uygulamaya yazmamak için mesaj göndermedim."
    win32.press_keys(0x1B)  # açık bir pencere (profil kartı gibi) varsa kapat
    time.sleep(0.4)
    win32.press_keys(0x11, 0x4B)  # Ctrl+K: hızlı geçiş
    time.sleep(0.8)
    if not (win32.set_clipboard("@" + handle) and _paste_and_wait(win32, 1.4)):
        return "Discord'da kişi aranamadı (pano kullanılamadı); mesaj göndermedim."
    win32.press_keys(0x0D)  # aranan kişinin sohbetini aç
    time.sleep(1.6)
    if "discord" not in win32.foreground_title().lower() or not win32.set_clipboard(text):
        return "Sohbet açıldı ama mesaj gönderilemedi."
    _paste_and_wait(win32, 0.4)
    win32.press_keys(0x0D)
    if save and name:
        book = _book()
        if _normalize_lookup(name) not in {_normalize_lookup(k) for k in book}:
            book[name] = {"username": handle, "id": ""}
            _save(book)
    return f"Discord'da {name or handle} kişisine mesaj gönderildi (@{handle} aranıp ilk sonuç açıldı; doğru kişi olduğunu sohbette kontrol et)."


def _paste_and_wait(win32, delay: float) -> bool:
    win32.press_keys(0x11, 0x56)  # Ctrl+V
    time.sleep(delay)
    return True


def self_test(username: str) -> str:
    """Ayarlardaki düğme: kullanıcı kendi kullanıcı adına deneme mesajı gönderir (düğmeye basmak onaydır)."""
    handle = _clean_username(username)
    if not handle:
        return "Önce Discord kullanıcı adını yaz (örn. dev.yigit)."
    return _deliver("", handle, "FRIDAY test mesajı: Discord bağlantısı çalışıyor.", save=False)
