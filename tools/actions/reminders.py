from __future__ import annotations

import datetime as dt

from tools.actions import calendar_store as store


def _normalize_query(query: str) -> tuple[str, int]:
    q = (query or "upcoming").strip().lower()
    if any(token in q for token in ("bugun", "bugün", "today")):
        return "today", 8
    if any(token in q for token in ("geciken", "gecikmiş", "overdue")):
        return "overdue", 8
    if any(token in q for token in ("siradaki", "sıradaki", "next")):
        return "next", 1
    if q in {"all", "hepsi", "tumu", "tümü"}:
        return "all", 12
    return "upcoming", 8


def _format_due(item: dict, now: dt.datetime) -> str:
    if not item.get("due_iso"):
        return "zaman atanmamis"
    due = dt.datetime.fromisoformat(item["due_iso"])
    if item.get("all_day"):
        return f"{store.day_label(due, now)} tum gun"
    return f"{store.day_label(due, now)} {due.strftime('%H:%M')}"


def _line(item: dict, now: dt.datetime) -> str:
    parts = [f"{_format_due(item, now)} - {item['title']}"]
    if item.get("list_name"):
        parts.append(f"[{item['list_name']}]")
    if item.get("priority") == 1:
        parts.append("(yuksek oncelik)")
    return " ".join(parts)


def get_reminders(query: str = "upcoming", limit: int = 8, list_name: str = "") -> str:
    mode, default_limit = _normalize_query(query)
    limit = max(1, min(20, int(limit or default_limit)))
    now = dt.datetime.now()
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    with store._store_lock:
        items = list(store.load_store()["reminders"])
    if list_name:
        needle = list_name.casefold()
        items = [item for item in items if needle in str(item.get("list_name", "")).casefold()]
    open_items = [item for item in items if not item.get("completed")]

    def due_of(item: dict) -> dt.datetime | None:
        raw = item.get("due_iso") or ""
        if not raw:
            return None
        try:
            return dt.datetime.fromisoformat(raw)
        except ValueError:
            return None

    if mode == "today":
        selected = [item for item in open_items if (due := due_of(item)) and due <= today_end and due.date() == now.date()]
    elif mode == "overdue":
        selected = [item for item in open_items if (due := due_of(item)) and due < now]
    elif mode == "next":
        selected = [item for item in open_items if (due := due_of(item)) and due >= now]
    elif mode == "all":
        selected = open_items
    else:
        selected = [item for item in open_items if due_of(item) is None or due_of(item) >= now]
    selected.sort(key=lambda item: ((due_of(item) or dt.datetime.max), item.get("title", "").lower()))
    selected = selected[:limit]
    if not selected:
        if mode == "today":
            return "Bugun icin animsatici gorunmuyor."
        if mode == "overdue":
            return "Geciken animsatici gorunmuyor."
        if mode == "next":
            return "Siradaki animsaticiyi bulamadim."
        if mode == "all":
            return "Kayitli acik animsatici gorunmuyor."
        return "Yaklasan animsatici gorunmuyor."
    if mode == "next":
        return f"Siradaki animsatici: {_line(selected[0], now)}."
    headers = {
        "today": f"Bugun icin {len(selected)} animsatici buldum:",
        "overdue": f"Gecikmis {len(selected)} animsatici buldum:",
        "all": f"Acik {len(selected)} animsatici buldum:",
    }
    lines = [headers.get(mode, f"Yaklasan {len(selected)} animsatici buldum:")]
    lines.extend(f"- {_line(item, now)}" for item in selected)
    return "\n".join(lines)


def add_reminder(
    title: str,
    due_iso: str = "",
    notes: str = "",
    list_name: str = "",
    priority: str = "",
    all_day: bool = False,
) -> str:
    if not title or not title.strip():
        return "Animsatici basligi bos olamaz."
    due_text = ""
    inferred_all_day = False
    if due_iso and due_iso.strip():
        parsed, inferred_all_day = store.parse_iso(due_iso)
        if parsed is None:
            return "Animsatici tarihi gecersiz. due_iso icin 'YYYY-MM-DD' veya 'YYYY-MM-DDTHH:MM' kullan."
        due_text = parsed.isoformat()
    priority_raw = str(priority or "").strip().lower()
    record = {
        "id": __import__("uuid").uuid4().hex,
        "title": title.strip(),
        "due_iso": due_text,
        "notes": (notes or "").strip(),
        "list_name": (list_name or "").strip(),
        "priority": 1 if priority_raw in {"high", "yuksek", "yüksek", "1"} else 0,
        "all_day": bool(all_day) or inferred_all_day,
        "completed": False,
    }
    with store._store_lock:
        data = store.load_store()
        data["reminders"].append(record)
        store.save_store(data)
    when = _format_due(record, dt.datetime.now())
    suffix = f" [{record['list_name']}]" if record["list_name"] else ""
    return f"Animsatici eklendi: {when} - {record['title']}{suffix}"


def _pick_reminder(items: list[dict], title: str, reminder_id: str) -> tuple[dict | None, str]:
    needle_id = (reminder_id or "").strip()
    needle = (title or "").strip().casefold()
    if needle_id:
        found = [item for item in items if str(item.get("id") or "") == needle_id]
    elif needle:
        found = [item for item in items if needle in str(item.get("title") or "").casefold() and not item.get("completed")]
        if not found:
            found = [item for item in items if needle in str(item.get("title") or "").casefold()]
    else:
        return None, "Animsatici basligi veya kimligi gerekli."
    if not found:
        return None, "Eslesen animsatici bulunamadi."
    return found[0], ""


def complete_reminder(title: str = "", reminder_id: str = "") -> str:
    with store._store_lock:
        data = store.load_store()
        item, error = _pick_reminder(data["reminders"], title, reminder_id)
        if error or item is None:
            return error
        item["completed"] = True
        store.save_store(data)
    return f"Animsatici tamamlandi: {item['title']}"


def delete_reminder(title: str = "", reminder_id: str = "") -> str:
    with store._store_lock:
        data = store.load_store()
        item, error = _pick_reminder(data["reminders"], title, reminder_id)
        if error or item is None:
            return error
        data["reminders"] = [row for row in data["reminders"] if row.get("id") != item.get("id")]
        store.save_store(data)
    return f"Animsatici silindi: {item['title']}"
