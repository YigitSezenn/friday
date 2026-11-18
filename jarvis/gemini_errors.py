"""Gemini baglanti hatalarini kullaniciya anlasilir bir duruma cevirir.

Saf fonksiyonlar: ag veya arayuz bilgisi tasimaz, kolayca test edilir.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

GOOGLE_HOSTS = "generativelanguage.googleapis.com,.googleapis.com"
MAX_REJECTIONS = 20


@dataclass(frozen=True)
class ConnectIssue:
    code: str  # arayuzde kisa durum etiketi
    message: str  # gunluge yazilan acik cumle
    retry: bool = True  # False ise ayni anahtarla bos yere denenmez
    rejection: bool = False  # Google'in bagi reddetmesi sayilir


def clean_api_key(value) -> str:
    """Yapistirmadan gelen bosluk, satir sonu ve tirnaklari atar."""
    return re.sub(r"\s+", "", str(value or "")).strip("\"'`")


def without_proxy_for_google() -> None:
    """Bozuk proxy ayari Gemini'ye baglanmayi kirmasin: Google adresleri proxy'siz gider."""
    for name in ("NO_PROXY", "no_proxy"):
        current = os.environ.get(name, "")
        if "googleapis.com" not in current:
            os.environ[name] = f"{current},{GOOGLE_HOSTS}".strip(",")


def _text(exc: BaseException) -> str:
    parts = [str(exc)]
    for item in getattr(exc, "exceptions", None) or ():
        parts.append(_text(item))
    cause = exc.__cause__ or exc.__context__
    if cause is not None and cause is not exc:
        parts.append(str(cause))
    return " ".join(parts)


def classify(exc: BaseException, key: str = "") -> ConnectIssue:
    detail = _text(exc)
    secret = clean_api_key(key)
    if secret:
        detail = detail.replace(secret, "")
    low = detail.lower()

    if "free tier is not available" in low:
        return ConnectIssue("ERİŞİM KAPALI", "ERR: ERİŞİM KAPALI. Google bu proje için ücretsiz Gemini'yi açmıyor. "
                            "Başka bir Google hesabından anahtar al. " + _reason(detail), retry=False, rejection=True)
    if "denied access" in low or ("1008" in low and "project" in low):
        return ConnectIssue("ERİŞİM KAPALI", "ERR: ERİŞİM KAPALI. Google bu anahtarın hesabında ücretsiz Gemini'yi kapatmış "
                            "(çoğunlukla 18 yaş altı ya da kısıtlı hesap). Başka bir Google hesabından anahtar al.",
                            retry=False, rejection=True)
    if "prepayment credits" in low or "credits are depleted" in low:
        return ConnectIssue("KREDİ BİTTİ", "ERR: KREDİ BİTTİ. Anahtarın ön ödemeli kredisi tükenmiş. "
                            "Kredi yükleyince bir şey yaz ya da mikrofona bas; yeni anahtar kaydedersen yeniden denerim.",
                            retry=False, rejection=True)
    if "ssl" in low or "certificate" in low:
        return ConnectIssue("SSL SORUNU", "ERR: SSL SORUNU. Güvenli bağlantı kurulamadı. Tarih-saati, antivirüsü ve ağ filtresini kontrol et.")
    if "invalid port" in low or "proxy" in low:
        return ConnectIssue("PROXY SORUNU", "ERR: PROXY SORUNU. Windows'taki proxy ayarı bağlantıyı bozuyor. Ayarlar › Ağ › Proxy'yi kontrol et.")
    if any(token in low for token in ("name or service not known", "getaddrinfo", "nodename", "timed out", "timeout", "unreachable", "connection refused")):
        return ConnectIssue("GOOGLE'A ULAŞILAMIYOR", "ERR: GOOGLE'A ULAŞILAMIYOR. İnternet açık görünüyor ama Google'a erişilemiyor; DNS ya da güvenlik duvarı olabilir.")
    if "api key" in low or "invalid" in low and "key" in low or "401" in low or "403" in low:
        return ConnectIssue("ANAHTAR GEÇERSİZ", "ERR: ANAHTAR GEÇERSİZ. Ayarlar'dan anahtarı yeniden yapıştır.", retry=False)
    return ConnectIssue("BAĞLANTI KOPTU", f"ERR: Bağlantı koptu. API anahtarını ve interneti kontrol et. ({_reason(detail)})")


def _reason(detail: str) -> str:
    text = " ".join(detail.split())
    return text[:160] + "…" if len(text) > 160 else text


class RejectionBudget:
    """Google ust uste reddederse denemeyi birakir; kullanici hareketi yeniden acar."""

    def __init__(self, limit: int = MAX_REJECTIONS):
        self.limit = limit
        self.count = 0
        self.blocked_key = ""

    def note(self, issue: ConnectIssue, key: str) -> None:
        if issue.rejection:
            self.count += 1
            if not issue.retry or self.count >= self.limit:
                self.blocked_key = clean_api_key(key)
        else:
            self.count = 0

    def success(self) -> None:
        self.count = 0
        self.blocked_key = ""

    def should_wait(self, key: str) -> bool:
        """True ise ayni anahtarla bekle; anahtar degistiyse engel kalkar."""
        if not self.blocked_key:
            return False
        if clean_api_key(key) != self.blocked_key:
            self.reset()
            return False
        return True

    def reset(self) -> None:
        self.count = 0
        self.blocked_key = ""
