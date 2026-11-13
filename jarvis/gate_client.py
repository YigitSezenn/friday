"""Bilgisayar, sunucudaki kapıya dışarıdan bağlanır. Anahtar yazılmaz."""

from __future__ import annotations

import os
import time

import requests

from jarvis.paths import data_path


def gate_url() -> str:
    env = str(os.environ.get("FRIDAY_GATE_URL") or "").strip()
    if env:
        return env.rstrip("/")
    path = data_path("config", "gate_url.txt")
    if path.exists():
        saved = path.read_text(encoding="utf-8").strip()
        if saved:
            return saved.rstrip("/")
    return "http://94.154.34.222:8787"


def gate_key() -> str:
    path = data_path("config", "gate_key.txt")
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def ensure_gate_key() -> str:
    current = gate_key()
    if current:
        return current
    import secrets

    created = secrets.token_urlsafe(24)
    data_path("config", "gate_key.txt").write_text(created, encoding="utf-8")
    return created


SITE = "https://site-seven-bay-75.vercel.app"


def pair_code(key: str) -> str:
    total = 0
    for index, char in enumerate(key):
        total = (total * 131 + ord(char) + index) % 1000000
    return f"{total:06d}"


def gate_join_url(key: str | None = None) -> str:
    from urllib.parse import quote

    current = key or ensure_gate_key()
    return f"{SITE}/#k={quote(current, safe='')}"


def run_gate(on_text) -> None:
    while True:
        key = gate_key()
        if not key:
            time.sleep(5)
            continue
        try:
            response = requests.get(
                f"{gate_url()}/pc/poll",
                headers={"X-Friday-Key": key},
                timeout=20,
            )
            if response.status_code != 200:
                time.sleep(5)
                continue
            payload = response.json()
        except Exception:
            time.sleep(5)
            continue
        for item in payload.get("commands") or []:
            text = str(item.get("text") or "").strip()
            if text and on_text:
                try:
                    on_text(text)
                except Exception:
                    continue
        time.sleep(1)
