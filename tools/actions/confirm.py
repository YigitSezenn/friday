"""Gönderim onayı: mesaj/e-posta önce taslak olarak bekletilir, kullanıcı onaylayınca gider.

Kodda zorlanır (yalnızca isteme güvenilmez): onay çağrısı, aynı içeriğin daha önce
bekletilmiş olmasını ve kısa bir bekleme geçmesini ister; kayıt süresi dolar.
"""
from __future__ import annotations

import hashlib
import threading
import time

TTL = 180.0
MIN_WAIT = 2.0
_pending: dict[str, float] = {}
_lock = threading.RLock()


# Gerçek kullanıcı onayı: model aracı iki kez çağırarak kendi kendine onay veremez.
# Canlı oturum kullanıcının söylediği/yazdığı metni buraya yazar; onay için ask()'tan SONRA
# olumlu bir cevap (evet/tamam/olur…) ve olumsuz kelime (hayır/dur/vazgeç…) olmaması gerekir.
require_user_yes = False
_said: list[tuple[float, str]] = []
YES = ("evet", "tamam", "olur", "onayla", "onaylıyorum", "onaylıyorum", "yap", "gönder", "sil", "devam", "kabul", "yes", "ok", "çalıştır", "calistir", "tabii", "tabi", "başlat", "baslat")
NO = ("hayır", "hayir", "yapma", "dur", "vazgeç", "vazgec", "iptal", "olmaz", "gönderme", "silme", "no", "stop")


def note_user_said(text: str) -> None:
    text = str(text or "").strip()
    if not text:
        return
    now = time.time()
    with _lock:
        _said.append((now, text.lower()))
        del _said[:-20]


def recent_said(seconds: float = 40.0) -> list[str]:
    """Kullanıcının son söylediği/yazdığı cümleler (model kendi başına karar vermesin diye)."""
    cutoff = time.time() - seconds
    with _lock:
        return [t for ts, t in _said if ts >= cutoff]


def _user_approved(since: float) -> bool:
    import re

    with _lock:
        recent = " ".join(t for ts, t in _said if ts >= since)
    words = set(re.findall(r"[a-zçğıöşü]+", recent))
    if any(w in words for w in NO):
        return False
    return any(w in words for w in YES)


def required() -> bool:
    try:
        from jarvis.config import load_app_config

        return bool(load_app_config().get("confirm_send", True))
    except Exception:
        return True


def _key(kind: str, parts: tuple) -> str:
    raw = "\x1f".join([kind, *[str(p).strip() for p in parts]])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def ask(kind: str, parts: tuple, summary: str) -> str:
    now = time.time()
    with _lock:
        for k in [k for k, t in _pending.items() if now - t > TTL]:
            _pending.pop(k, None)
        _pending[_key(kind, parts)] = now
    return f"ONAY GEREKLİ: {summary} Göndermeden önce kullanıcıya sesli sor: 'Göndereyim mi?' Evet derse aynı bilgilerle confirm=true ile tekrar çağır."


def check(kind: str, parts: tuple) -> str:
    """Onaylanabilirse '' döner; değilse nedenini."""
    now = time.time()
    k = _key(kind, parts)
    with _lock:
        t = _pending.get(k)
        if t is None or now - t > TTL:
            return "ONAY GEREKLİ: önce taslağı kullanıcıya söyle ve 'Göndereyim mi?' diye sor; onay gelince tekrar çağır."
        if now - t < MIN_WAIT:
            return "ONAY GEREKLİ: kullanıcının cevabını bekle; onayı kendin varsayma."
        if require_user_yes and not _user_approved(t):
            return "ONAY GEREKLİ: kullanıcıdan açık bir 'evet' duymadım; cevabını bekle, onayı kendin varsayma."
        _pending.pop(k, None)
    return ""


MARKER = "ONAY GEREKLİ:"


def friendly(result: str) -> str:
    """Modele giden onay talimatını ekranda okunur bir soruya çevirir. Diğer metinlere dokunmaz."""
    import re

    text = str(result or "")
    if not text.startswith(MARKER):
        return text
    body = text[len(MARKER):].strip()
    for cut in (" Göndermeden önce", " Evet derse"):
        body = body.split(cut)[0]
    body = body.strip().rstrip(".")
    chat = re.search(r"WhatsApp taslağı — Kime: (.+?), Mesaj: (.+)$", body, re.S)
    if chat:
        return f"WhatsApp mesajı hazır. Kime: {chat.group(1)} · Mesaj: “{chat.group(2).strip()}”. Göndereyim mi? (evet / hayır)"
    mail = re.search(r"E-posta taslağı \((.+?)\) — Kime: (.+?), Konu: (.+?), Metin: (.+)$", body, re.S)
    if mail:
        return f"E-posta hazır. Kime: {mail.group(2)} · Konu: {mail.group(3)} · Metin: “{mail.group(4).strip()}”. Göndereyim mi? (evet / hayır)"
    shell = re.search(r"Bu komut bilgisayarda değişiklik yapabilir: `(.+)`", body, re.S)
    if shell:
        return f"Bu işlem bilgisayarda değişiklik yapabilir: {shell.group(1).strip()}. Çalıştırayım mı? (evet / hayır)"
    fil = re.search(r"Dosya işlemi: (.+)$", body, re.S)
    if fil:
        return f"{fil.group(1).strip().capitalize()}. Devam edeyim mi? (evet / hayır)"
    if "cevabini bekle" in body or "cevabını bekle" in body:
        return "Cevabını bekliyorum."
    if "taslağı" in body and "sor" in body:
        return "Önce taslağı sana göstermem gerekiyor; sonra göndereyim mi diye soracağım."
    return "Devam etmeden önce onayını bekliyorum. (evet / hayır)"
