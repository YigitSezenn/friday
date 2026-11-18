from __future__ import annotations

import os
import threading

from jarvis.config import get_app_config_value

_detected_city = ""
_lock = threading.Lock()


def clear_detected_city() -> None:
    global _detected_city
    with _lock:
        _detected_city = ""


def configured_location() -> str:
    value = str(get_app_config_value("weather_location", "") or "").strip()
    if value:
        return value
    env = (os.environ.get("JARVIS_WEATHER_LOCATION") or "").strip()
    if env:
        return env
    # Kullanıcının çalışan V4 penceresinde seçtiği şehir. Anahtar okunmaz.
    try:
        import json
        from pathlib import Path

        path = Path(os.environ.get("APPDATA", "")) / "JARVIS V4" / "settings.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        city = str(data.get("location") or "").strip()
        if city and len(city) < 80:
            return city
    except (OSError, ValueError, TypeError):
        pass
    return ""


def detected_city() -> str:
    with _lock:
        return _detected_city


def current_location_label() -> str:
    return configured_location() or detected_city() or "Konum araniyor"


def _extract_city(payload: dict) -> str:
    try:
        area = (payload.get("nearest_area") or [{}])[0]
        name = ((area.get("areaName") or [{}])[0]).get("value", "").strip()
        region = ((area.get("region") or [{}])[0]).get("value", "").strip()
        return region or name
    except (AttributeError, IndexError, TypeError):
        return ""


_CONDITIONS = (
    ("light drizzle", "hafif çisenti"),
    ("light rain", "hafif yağmur"),
    ("partly cloudy", "parçalı bulutlu"),
    ("overcast", "kapalı"),
    ("drizzle", "çisenti"),
    ("cloudy", "bulutlu"),
    ("sunny", "güneşli"),
    ("clear", "açık"),
    ("rain", "yağmur"),
    ("mist", "pus"),
    ("fog", "sis"),
    ("snow", "kar"),
)


def _turkish_condition(text: str) -> str:
    lowered = text.strip().lower()
    for english, turkish in _CONDITIONS:
        if english in lowered:
            return turkish
    return lowered


_WIND = {
    "N": "kuzey", "NNE": "KKD", "NE": "KD", "ENE": "DKD",
    "E": "doğu", "ESE": "DGD", "SE": "GD", "SSE": "GGD",
    "S": "güney", "SSW": "GGB", "SW": "GB", "WSW": "BGB",
    "W": "batı", "WNW": "BKB", "NW": "KB", "NNW": "KKB",
}
_MOON = {
    "new moon": "Yeni ay",
    "waxing crescent": "Büyüyen hilal",
    "first quarter": "İlk dördün",
    "waxing gibbous": "Büyüyen şişkin ay",
    "full moon": "Dolunay",
    "waning gibbous": "Küçülen şişkin ay",
    "last quarter": "Son dördün",
    "waning crescent": "Küçülen hilal",
}


def _wind_from(point: str) -> str:
    label = _WIND.get(str(point or "").strip().upper(), "")
    return f"{label} yönünden" if label else ""


def _uv_label(value: str) -> str:
    try:
        number = float(str(value).strip())
    except ValueError:
        return ""
    if number <= 2:
        return "düşük"
    if number <= 5:
        return "orta"
    if number <= 7:
        return "yüksek"
    return "çok yüksek"


def _hhmm(raw: object) -> str:
    digits = "".join(ch for ch in str(raw or "0") if ch.isdigit()) or "0"
    value = int(digits)
    return f"{value // 100:02d}:{value % 100:02d}"


def _observed_clock(text: str) -> str:
    import re

    match = re.search(r"(\d{1,2}):(\d{2})\s*([AP]M)?", str(text or ""), re.I)
    if not match:
        return ""
    hour = int(match.group(1))
    minute = int(match.group(2))
    mark = (match.group(3) or "").upper()
    if mark == "PM" and hour < 12:
        hour += 12
    if mark == "AM" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute:02d}"


def _country(payload: dict) -> str:
    try:
        area = (payload.get("nearest_area") or [{}])[0]
        return str(((area.get("country") or [{}])[0]).get("value", "")).strip()
    except (AttributeError, IndexError, TypeError):
        return ""


def _hours(payload: dict) -> list[dict]:
    rows = []
    for day in (payload.get("weather") or [])[:2]:
        if not isinstance(day, dict):
            continue
        for hour in day.get("hourly") or []:
            if not isinstance(hour, dict):
                continue
            desc = ((hour.get("weatherDesc") or [{}])[0]).get("value", "")
            rows.append({
                "time": _hhmm(hour.get("time")),
                "temp": str(hour.get("tempC") or ""),
                "rain": str(hour.get("chanceofrain") or "0"),
                "desc": _turkish_condition(str(desc)),
            })
    return rows[:8]


def _day_rows(payload: dict) -> list[dict]:
    rows = []
    for day in (payload.get("weather") or [])[:3]:
        if not isinstance(day, dict):
            continue
        hours = day.get("hourly") or []
        desc = ""
        rain = ""
        if hours and isinstance(hours[0], dict):
            desc = _turkish_condition(str(((hours[0].get("weatherDesc") or [{}])[0]).get("value", "")))
            rain = str(hours[len(hours) // 2].get("chanceofrain") or "")
        rows.append({
            "date": str(day.get("date") or ""),
            "hi": str(day.get("maxtempC") or ""),
            "lo": str(day.get("mintempC") or ""),
            "desc": desc,
            "rain": rain,
        })
    return rows


def weather_card(payload: dict, target: str = "") -> dict:
    detected = _extract_city(payload)
    if not target and detected:
        with _lock:
            global _detected_city
            _detected_city = detected
    city = target or detected or "Konum"
    current = (payload.get("current_condition") or [{}])[0]
    if not isinstance(current, dict):
        current = {}
    desc = ((current.get("weatherDesc") or [{}])[0]).get("value", "")
    days = _day_rows(payload)
    today = days[0] if days else {}
    astro = ((payload.get("weather") or [{}])[0] or {}).get("astronomy") or [{}]
    sun = astro[0] if isinstance(astro, list) and astro else {}
    moon_name = str((sun or {}).get("moon_phase") or "").strip().lower()
    return {
        "place": city,
        "country": _country(payload),
        "observed": _observed_clock(str(current.get("localObsDateTime") or "")),
        "windFrom": _wind_from(str(current.get("winddir16Point") or "")),
        "uvLabel": _uv_label(str(current.get("uvIndex") or "")),
        "moon": _MOON.get(moon_name, str((sun or {}).get("moon_phase") or "")),
        "moonLight": str((sun or {}).get("moon_illumination") or ""),
        "hours": _hours(payload),
        "temp": str(current.get("temp_C") or ""),
        "feels": str(current.get("FeelsLikeC") or ""),
        "desc": _turkish_condition(str(desc)),
        "humidity": str(current.get("humidity") or ""),
        "wind": str(current.get("windspeedKmph") or ""),
        "windDir": str(current.get("winddir16Point") or ""),
        "windDeg": str(current.get("winddirDegree") or ""),
        "pressure": str(current.get("pressure") or ""),
        "visibility": str(current.get("visibility") or ""),
        "uv": str(current.get("uvIndex") or ""),
        "cloud": str(current.get("cloudcover") or ""),
        "precip": str(current.get("precipMM") or ""),
        "high": str(today.get("hi") or ""),
        "low": str(today.get("lo") or ""),
        "sunrise": str((sun or {}).get("sunrise") or ""),
        "sunset": str((sun or {}).get("sunset") or ""),
        "days": days,
    }


def summarize_weather_payload(payload: dict, target: str = "") -> str:
    detected = _extract_city(payload)
    if not target and detected:
        with _lock:
            global _detected_city
            _detected_city = detected
    city = target or detected
    current = (payload.get("current_condition") or [{}])[0]
    temp_c = current.get("temp_C")
    feels_like = current.get("FeelsLikeC")
    weather_desc = ((current.get("weatherDesc") or [{}])[0]).get("value", "")
    humidity = current.get("humidity")
    parts = []
    if temp_c:
        parts.append(f"{temp_c} derece")
    if weather_desc:
        parts.append(_turkish_condition(str(weather_desc)))
    if feels_like and feels_like != temp_c:
        parts.append(f"hissedilen {feels_like} derece")
    if humidity:
        parts.append(f"nem yüzde {humidity}")
    if not parts:
        return "Hava durumu bilgisi şu anda alınamadı."
    label = city or "Bulunduğun konum"
    return f"{label} için hava durumu: " + ", ".join(parts) + "."


def _fetch_payload(location: str | None = None) -> tuple[str, dict | None]:
    import requests

    explicit = (location or "").strip()
    target = explicit or configured_location()
    url = f"https://wttr.in/{target}" if target else "https://wttr.in"
    try:
        response = requests.get(
            url,
            params={"format": "j1"},
            timeout=12,
            headers={"User-Agent": "JARVIS Windows"},
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return target, None
    if not isinstance(payload, dict):
        return target, None
    return target, payload


def get_weather_summary(location: str | None = None) -> str:
    target, payload = _fetch_payload(location)
    if payload is None:
        known = target or detected_city()
        if known:
            return f"{known} icin hava durumu bilgisi su anda alinamadi."
        return "Hava durumu bilgisi şu anda alınamadı."
    return summarize_weather_payload(payload, target)


def get_weather_report(location: str | None = None) -> dict:
    target, payload = _fetch_payload(location)
    if payload is None:
        known = target or detected_city() or "Konum"
        return {"place": known, "temp": "", "feels": "", "desc": "", "humidity": "", "wind": "", "days": []}
    return weather_card(payload, target)
