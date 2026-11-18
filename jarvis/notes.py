"""Notlar: HUD paneli, sesli komutlar ve telefon aynı dosyayı paylaşır (data/memory/notes.txt)."""
from __future__ import annotations

from jarvis.atomic import LOCK, write_text
from jarvis.paths import data_path

MAX_NOTES = 200


def _path():
    return data_path("memory", "notes.txt")


def load() -> list[str]:
    try:
        return [line.strip() for line in _path().read_text(encoding="utf-8").splitlines() if line.strip()]
    except OSError:
        return []


def save(lines) -> list[str]:
    clean = [" ".join(str(line).split()) for line in (lines or []) if str(line).strip()][-MAX_NOTES:]
    with LOCK:
        write_text(_path(), "\n".join(clean))
    return clean


def add(text: str) -> list[str]:
    note = " ".join(str(text or "").split())
    if not note:
        return load()
    with LOCK:
        return save(load() + [note])


def find(lines: list[str], target) -> int:
    """1'den başlayan sıra numarası ya da metin parçasıyla notu bulur; yoksa -1."""
    raw = str(target or "").strip()
    if raw.isdigit():
        index = int(raw) - 1
        return index if 0 <= index < len(lines) else -1
    needle = raw.casefold()
    if not needle:
        return -1
    for index in range(len(lines) - 1, -1, -1):
        if lines[index].casefold() == needle:
            return index
    for index in range(len(lines) - 1, -1, -1):
        if needle in lines[index].casefold():
            return index
    return -1


def remove(target) -> tuple[list[str], str | None]:
    with LOCK:
        lines = load()
        index = find(lines, target)
        if index < 0:
            return lines, None
        removed = lines.pop(index)
        return save(lines), removed


def edit(target, text: str) -> tuple[list[str], str | None]:
    note = " ".join(str(text or "").split())
    with LOCK:
        lines = load()
        index = find(lines, target)
        if index < 0 or not note:
            return lines, None
        old = lines[index]
        lines[index] = note
        return save(lines), old
