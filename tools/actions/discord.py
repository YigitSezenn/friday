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


def _lookup(name: str) -> tuple[str, str]:
    needle = _normalize_lookup(name)
    for key, user_id in _book().items():
        if needle and (_normalize_lookup(key) == needle or needle in _normalize_lookup(key)):
            return key, str(user_id)
    return "", ""


def send_discord_message(message: str, recipient_name: str = "", user_id: str = "", confirm_send: bool = False) -> str:
    """Discord masaüstü uygulamasında kişinin DM'ini açar, mesajı yapıştırır ve Enter ile gönderir."""
    text = (message or "").strip()
    if not text:
        return "Mesaj boş olamaz."
    name = (recipient_name or "").strip()
    uid = re.sub(r"\D", "", user_id or "")
    if uid and not 15 <= len(uid) <= 22:
        return "Discord kullanıcı kimliği 17-19 haneli bir sayıdır (Geliştirici Modu › Kullanıcı Kimliğini Kopyala)."
    if not uid:
        name, uid = _lookup(name)
        if not uid:
            return f"'{recipient_name}' için kayıtlı Discord kimliği yok. Kişinin kimliğini (Geliştirici Modu › Kullanıcı Kimliğini Kopyala) söylersen kaydederim."
    from tools.actions import confirm

    parts = (uid, text)
    if not confirm_send:
        return confirm.ask("discord", parts, f"Discord mesajı — Kime: {name or uid}, Mesaj: {text[:300]}.")
    problem = confirm.check("discord", parts)
    if problem:
        return problem
    return _deliver(name, uid, text)


def _deliver(name: str, uid: str, text: str, save: bool = True) -> str:
    import os

    from jarvis.win32 import available, press_keys, set_clipboard

    start = getattr(os, "startfile", None)
    if not start or not available():
        return "Discord mesajı yalnızca Windows'ta gönderilebilir."
    if save and name and _normalize_lookup(name) not in {_normalize_lookup(k) for k in _book()}:
        book = _book()
        book[name] = uid
        _save(book)
    try:
        start(f"discord://-/users/{uid}")
    except OSError as exc:
        return f"Discord açılamadı: {exc}"
    time.sleep(3.0)
    if not set_clipboard(text):
        return "Discord açıldı ama mesaj panoya konamadı; sohbet hazır, kendin yapıştırabilirsin."
    press_keys(0x11, 0x56)  # Ctrl+V
    time.sleep(0.4)
    press_keys(0x0D)
    return f"Discord'da {name or uid} kişisine mesaj gönderildi (sohbet açıkken gönderildi; doğrulamak için ekrana bakılabilir)."


def self_test(user_id: str) -> str:
    """Ayarlardaki düğme: kullanıcı kendi kimliğine deneme mesajı gönderir (düğmeye basmak onaydır)."""
    uid = re.sub(r"\D", "", user_id or "")
    if not 15 <= len(uid) <= 22:
        return "Önce Discord kimliğini yaz (17-19 haneli sayı)."
    return _deliver("", uid, "FRIDAY test mesajı: Discord bağlantısı çalışıyor.", save=False)
