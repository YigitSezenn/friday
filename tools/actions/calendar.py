from __future__ import annotations

import datetime as dt
import re

from tools.actions import calendar_store as store


def _month_start(value: dt.datetime) -> dt.datetime:
    return value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _add_months(value: dt.datetime, months: int) -> dt.datetime:
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    return value.replace(year=year, month=month, day=1)


def normalize_query(query: str) -> dict:
    q = (query or "today").strip().lower()
    now = dt.datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if "gelecek ay" in q or "önümüzdeki ay" in q or "onumuzdeki ay" in q or "next month" in q:
        start = _add_months(_month_start(now), 1)
        return _window(start, _add_months(start, 1), 24, "Gelecek ay icin {count} etkinlik buldum:", "Gelecek ay takviminde etkinlik gorunmuyor.")
    if "bu ay" in q or "this month" in q:
        start = _month_start(now)
        return _window(start, _add_months(start, 1), 24, "Bu ay icin {count} etkinlik buldum:", "Bu ay takviminde etkinlik gorunmuyor.")
    month_match = re.search(r"(\d+)\s*(ay|month|months)", q)
    if month_match:
        months = max(1, min(12, int(month_match.group(1))))
        end = _add_months(_month_start(now), months)
        return _window(today_start, end, min(60, max(12, months * 12)), f"Onumuzdeki {months} ay icin {{count}} etkinlik buldum:", f"Onumuzdeki {months} ayda takviminde etkinlik gorunmuyor.")
    week_match = re.search(r"(\d+)\s*(hafta|week|weeks)", q)
    if week_match:
        weeks = max(1, min(12, int(week_match.group(1))))
        return _window(today_start, today_start + dt.timedelta(days=weeks * 7), min(60, max(8, weeks * 8)), f"Onumuzdeki {weeks} hafta icin {{count}} etkinlik buldum:", f"Onumuzdeki {weeks} haftada takviminde etkinlik gorunmuyor.")
    day_match = re.search(r"(\d+)\s*(g[uü]n|gun|day|days)", q)
    if day_match:
        days = max(1, min(365, int(day_match.group(1))))
        return _window(today_start, today_start + dt.timedelta(days=days), min(60, max(8, days * 2)), f"Onumuzdeki {days} gun icin {{count}} etkinlik buldum:", f"Onumuzdeki {days} gunde takviminde etkinlik gorunmuyor.")
    if any(token in q for token in ("yarin", "tomorrow")):
        start = today_start + dt.timedelta(days=1)
        return _window(start, start + dt.timedelta(days=1), 6, "Yarin icin {count} etkinlik buldum:", "Yarin takviminde etkinlik gorunmuyor.", kind="tomorrow")
    if any(token in q for token in ("hafta", "week", "7 gun")):
        return _window(today_start, today_start + dt.timedelta(days=7), 10, "Onumuzdeki 7 gun icin {count} etkinlik buldum:", "Onumuzdeki 7 gunde takviminde etkinlik gorunmuyor.")
    if any(token in q for token in ("siradaki", "sıradaki", "sonraki", "next")):
        return _window(now, today_start + dt.timedelta(days=60), 1, "", "Siradaki takvim etkinligini bulamadim.", kind="next")
    if any(token in q for token in ("ajanda", "agenda", "yaklasan", "yaklaşan", "upcoming")):
        return _window(now, today_start + dt.timedelta(days=14), 8, "Yaklasan ajandanda {count} etkinlik var:", "Yaklasan takvim etkinligi gorunmuyor.")
    end = today_start + dt.timedelta(days=1)
    return _window(today_start, end, 6, "Bugun icin {count} etkinlik buldum:", "Bugun takviminde etkinlik gorunmuyor.", kind="today")


def _window(start, end, limit, header, empty, kind="range") -> dict:
    return {"start": start, "end": end, "limit": limit, "header": header, "empty": empty, "kind": kind}


def _event_from_record(record: dict) -> dict | None:
    try:
        start = dt.datetime.fromisoformat(record["start_iso"])
        end = dt.datetime.fromisoformat(record["end_iso"])
    except (KeyError, TypeError, ValueError):
        return None
    return {
        "start": start,
        "end": end,
        "calendar": str(record.get("calendar_name") or "JARVIS"),
        "title": str(record.get("title", "")).strip() or "Adsiz etkinlik",
        "location": str(record.get("location") or ""),
        "all_day": bool(record.get("all_day", False)),
    }


def _overlaps(event: dict, start: dt.datetime, end: dt.datetime) -> bool:
    return event["end"] > start and event["start"] < end


def _format_event_line(event: dict, now: dt.datetime) -> str:
    prefix = store.day_label(event["start"], now)
    if event["all_day"]:
        when = f"{prefix} tum gun"
    else:
        when = f"{prefix} {event['start'].strftime('%H:%M')}-{event['end'].strftime('%H:%M')}"
    pieces = [f"{when} - {event['title']}", f"[{event['calendar']}]"]
    if event["location"]:
        pieces.append(f"@ {event['location']}")
    return " ".join(pieces)


def get_calendar_events(query: str = "today", limit: int = 6) -> str:
    window = normalize_query(query)
    limit = max(1, min(60, int(limit or window["limit"])))
    with store._store_lock:
        records = store.load_store()["events"]
    events = []
    for record in records:
        event = _event_from_record(record)
        if event and _overlaps(event, window["start"], window["end"]):
            events.append(event)
    events.sort(key=lambda item: item["start"])
    if window["kind"] == "next":
        now = dt.datetime.now()
        events = [item for item in events if item["end"] >= now]
    events = events[:limit]
    if not events:
        return window["empty"]
    now = dt.datetime.now()
    if window["kind"] == "next":
        return f"Siradaki etkinlik: {_format_event_line(events[0], now)}."
    lines = [window["header"].format(count=len(events))]
    lines.extend(f"- {_format_event_line(event, now)}" for event in events)
    return "\n".join(lines)


def add_calendar_event(
    title: str,
    start_iso: str,
    end_iso: str = "",
    notes: str = "",
    location: str = "",
    calendar_name: str = "",
    all_day: bool = False,
) -> str:
    title = (title or "").strip()
    if not title:
        return "Takvime eklemek icin etkinlik basligi gerekli."
    if not (start_iso or "").strip():
        return "Takvime eklemek icin baslangic tarihi gerekli."
    start, start_all_day = store.parse_iso(start_iso)
    if start is None:
        return "Takvim etkinligi eklenemedi: Baslangic tarihi anlasilamadi."
    all_day = bool(all_day) or start_all_day
    end, _ = store.parse_iso(end_iso or "")
    if end is None:
        if all_day:
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + dt.timedelta(days=1)
        else:
            end = start + dt.timedelta(hours=1)
    if end <= start:
        end = start + (dt.timedelta(days=1) if all_day else dt.timedelta(hours=1))
    record = {
        "id": __import__("uuid").uuid4().hex,
        "title": title,
        "start_iso": start.isoformat(),
        "end_iso": end.isoformat(),
        "notes": (notes or "").strip(),
        "location": (location or "").strip(),
        "calendar_name": (calendar_name or "").strip() or "JARVIS",
        "all_day": all_day,
    }
    with store._store_lock:
        data = store.load_store()
        data["events"].append(record)
        store.save_store(data)
    event = _event_from_record(record)
    return f"Takvime eklendi: {_format_event_line(event, dt.datetime.now())}."


def delete_calendar_event(
    title: str,
    start_iso: str = "",
    calendar_name: str = "",
    delete_all_matches: bool = False,
) -> str:
    title = (title or "").strip()
    if not title:
        return "Takvimden silmek icin etkinlik basligi gerekli."
    needle = title.casefold()
    start_filter, _ = store.parse_iso(start_iso or "")
    with store._store_lock:
        data = store.load_store()
        matched = []
        for index, record in enumerate(data["events"]):
            if needle not in str(record.get("title", "")).casefold():
                continue
            if calendar_name and calendar_name.casefold() not in str(record.get("calendar_name", "")).casefold():
                continue
            if start_filter is not None:
                try:
                    record_start = dt.datetime.fromisoformat(record["start_iso"])
                except (KeyError, TypeError, ValueError):
                    continue
                if abs((record_start - start_filter).total_seconds()) > 3600:
                    continue
            matched.append(index)
        if not matched:
            return f"'{title}' baslikli bir etkinlik bulunamadi."
        if len(matched) > 1 and not delete_all_matches:
            return (
                f"'{title}' ile eslesen {len(matched)} etkinlik var. "
                "Hangisini silecegimi belirt (baslangic saatiyle) ya da tumunu sil."
            )
        for index in sorted(matched, reverse=True):
            data["events"].pop(index)
        store.save_store(data)
    count = len(matched)
    if count == 1:
        return f"Takvimden silindi: {title}."
    return f"Takvimden {count} etkinlik silindi: {title}."
