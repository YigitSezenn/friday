from __future__ import annotations

import os
import threading

from jarvis.config import get_app_config_value

_detected_city = ""
_lock = threading.Lock()


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


def get_weather_summary(location: str | None = None) -> str:
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
        known = target or detected_city()
        if known:
            return f"{known} icin hava durumu bilgisi su anda alinamadi."
        return "Hava durumu bilgisi şu anda alınamadı."
    return summarize_weather_payload(payload, target)
