"""Sık söylenen komutların yerel tanınması.

Model "uyu" gibi kısa bir sözü araca çevirmeyebilir; bu yüzden döküm burada da denetlenir.
Saf mantık: arayüz ve ağ bilgisi tutmaz.
"""

from __future__ import annotations

import re

_TR = str.maketrans("çğıöşüâîû", "cgiosuaiu")

_SLEEP = (
    r"uyu",
    r"uyu(n|yalim)?",
    r"uyku(ya|ma|moduna|moduna gec|mod)?",
    r"uyku moduna (gec|al)",
    r"uykuya (gec|yat|dal)",
    r"git uyu",
    r"biraz dinlen",
    r"dinlen",
    r"yat(ip)? uyu",
    r"iyi geceler",
    r"sessize gec",
    r"sus(ar misin|abilir misin)?",
    r"dinlemeyi birak",
    r"beni dinleme",
)
_WAKE = (r"uyan", r"uyan(sana|abilir misin)", r"gunaydin", r"hadi uyan", r"geri gel")

_NAME = r"(?:friday|fraydey|freydi|jarvis|cuma)?"


def normalize(text: str) -> str:
    value = str(text or "").lower().replace("İ", "i").replace("I", "ı")
    value = value.translate(_TR)
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return " ".join(value.split())


def _matches(text: str, patterns: tuple[str, ...]) -> bool:
    value = normalize(text)
    value = re.sub(rf"^{_NAME}\s*", "", value)
    value = re.sub(r"\b(lutfen|artik|simdi|hadi|tamam)\b", " ", value)
    value = " ".join(value.split())
    if not value or len(value.split()) > 5:
        return False
    return any(re.fullmatch(pattern, value) for pattern in patterns)


def is_sleep(text: str) -> bool:
    return _matches(text, _SLEEP)


def is_wake(text: str) -> bool:
    return _matches(text, _WAKE)
