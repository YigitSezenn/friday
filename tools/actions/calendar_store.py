from __future__ import annotations

import datetime as dt
import json
import subprocess
import threading
import uuid

from jarvis.config import get_app_config_value
from jarvis.paths import data_path

_store_lock = threading.Lock()

TR_MONTHS = (
    "",
    "Ocak",
    "Subat",
    "Mart",
    "Nisan",
    "Mayis",
    "Haziran",
    "Temmuz",
    "Agustos",
    "Eylul",
    "Ekim",
    "Kasim",
    "Aralik",
)
TR_WEEKDAYS = ("Pazartesi", "Sali", "Carsamba", "Persembe", "Cuma", "Cumartesi", "Pazar")


def store_path():
    return data_path("memory", "calendar_store.json")


def ics_path():
    return data_path("memory", "jarvis.ics")


def _empty_store() -> dict:
    return {"events": [], "reminders": []}


def load_store() -> dict:
    path = store_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_store()
    if not isinstance(raw, dict):
        return _empty_store()
    raw.setdefault("events", [])
    raw.setdefault("reminders", [])
    if not isinstance(raw["events"], list):
        raw["events"] = []
    if not isinstance(raw["reminders"], list):
        raw["reminders"] = []
    return raw


def save_store(store: dict) -> None:
    path = store_path()
    path.write_text(json.dumps(store, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        write_ics(store)
    except OSError:
        pass


def write_ics(store: dict) -> None:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//JARVIS//Windows//TR",
        "CALSCALE:GREGORIAN",
    ]
    for event in store.get("events", []):
        try:
            start = dt.datetime.fromisoformat(event["start_iso"])
            end = dt.datetime.fromisoformat(event["end_iso"])
        except (KeyError, TypeError, ValueError):
            continue
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{event.get('id', uuid.uuid4().hex)}@jarvis")
        lines.append("DTSTAMP:" + dt.datetime.now().strftime("%Y%m%dT%H%M%S"))
        if event.get("all_day"):
            lines.append("DTSTART;VALUE=DATE:" + start.strftime("%Y%m%d"))
            lines.append("DTEND;VALUE=DATE:" + end.strftime("%Y%m%d"))
        else:
            lines.append("DTSTART:" + start.strftime("%Y%m%dT%H%M%S"))
            lines.append("DTEND:" + end.strftime("%Y%m%dT%H%M%S"))
        lines.append("SUMMARY:" + _ics_escape(str(event.get("title", ""))))
        if event.get("location"):
            lines.append("LOCATION:" + _ics_escape(str(event["location"])))
        if event.get("notes"):
            lines.append("DESCRIPTION:" + _ics_escape(str(event["notes"])))
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    ics_path().write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")


def _ics_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def parse_iso(value: str) -> tuple[dt.datetime | None, bool]:
    raw = (value or "").strip()
    if not raw:
        return None, False
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(raw)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone().replace(tzinfo=None)
        return parsed, len((value or "").strip()) == 10
    except ValueError:
        pass
    formats = (
        ("%Y-%m-%d %H:%M:%S", False),
        ("%Y-%m-%d %H:%M", False),
        ("%d.%m.%Y %H:%M", False),
        ("%d/%m/%Y %H:%M", False),
        ("%Y-%m-%d", True),
        ("%d.%m.%Y", True),
        ("%d/%m/%Y", True),
    )
    for fmt, all_day in formats:
        try:
            return dt.datetime.strptime(raw, fmt), all_day
        except ValueError:
            continue
    return None, False


def outlook_running() -> bool:
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq OUTLOOK.EXE", "/NH"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return "OUTLOOK.EXE" in (result.stdout or "").upper()


def use_outlook() -> bool:
    mode = str(get_app_config_value("calendar_backend", "auto") or "auto").strip().lower()
    if mode == "local":
        return False
    if mode == "auto" and not outlook_running():
        return False
    if mode == "outlook" and not outlook_running():
        return False
    return outlook_running()


def day_label(when: dt.datetime, now: dt.datetime) -> str:
    if when.date() == now.date():
        return "bugun"
    if when.date() == now.date() + dt.timedelta(days=1):
        return "yarin"
    return f"{when.day} {TR_MONTHS[when.month]} {TR_WEEKDAYS[when.weekday()]}"
