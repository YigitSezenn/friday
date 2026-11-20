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
_lock = threading.Lock()


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
            return "ONAY GEREKLİ: kullanıcının cevabini bekle; onayi kendin varsayma."
        _pending.pop(k, None)
    return ""
