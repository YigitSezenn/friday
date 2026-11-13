"""Sohbet metnindeki bozulmuş Türkçe harfleri geri çevirir. Anahtar yazılmaz."""

from __future__ import annotations


def repair_text(text: str) -> str:
    raw = str(text or "")
    if not raw or not any(mark in raw for mark in ("Ã", "Ä", "Å", "Â")):
        return raw
    for encoding in ("latin-1", "cp1252"):
        try:
            fixed = raw.encode(encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if fixed:
            return fixed
    return raw
