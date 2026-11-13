from __future__ import annotations

import json
import os
from pathlib import Path

from jarvis.paths import data_path

VOICES = ("Charon", "Puck", "Aoede", "Kore", "Fenrir", "Leda", "Orus", "Zephyr")

UI_COLORS = {
    "gold": {"label": "Altın", "c": "#e6c98a", "rgb": "230,201,138", "accent": "#e7a0ae", "arg": "231,160,174", "ink": "#f6f1e6", "dim": "#b7a27a", "faint": "#6a5a3c"},
    "cyan": {"label": "Camgöbeği", "c": "#5ed8ff", "rgb": "94,216,255", "accent": "#ff8a3c", "arg": "255,138,60", "ink": "#cfe9f7", "dim": "#5e7c8c", "faint": "#2c4453"},
    "crimson": {"label": "Kırmızı", "c": "#ff5a62", "rgb": "255,90,98", "accent": "#ffd0a8", "arg": "255,208,168", "ink": "#ffe8ea", "dim": "#c98a90", "faint": "#6a3a40"},
    "emerald": {"label": "Zümrüt", "c": "#7dffa8", "rgb": "125,255,168", "accent": "#d7ff6a", "arg": "215,255,106", "ink": "#e7ffef", "dim": "#7eae90", "faint": "#2d4a38"},
    "violet": {"label": "Mor", "c": "#c9a6ff", "rgb": "201,166,255", "accent": "#ff9ad5", "arg": "255,154,213", "ink": "#f4ecff", "dim": "#a894c4", "faint": "#46385c"},
}
ADDRESS_PRESETS = ("adınla", "efendim", "komutanım", "dostum", "patron")
PANEL_KEYS = ("time", "system", "timer", "notes", "weather", "calendar", "reminders", "map")
LIVE_MODELS = (
    "models/gemini-2.5-flash-native-audio-latest",
    "models/gemini-3.8-live",
)
LANGUAGES = ("auto", "tr", "en", "fr", "ar", "az")

DEFAULT_CONFIG = {
    "gemini_api_key": "",
    "voice": "Charon",
    "assistant_name": "FRIDAY",
    "address_as": "adınla",
    "ui_color": "gold",
    "voice_volume": 100,
    "effects": True,
    "panels_off": [],
    "youtube_api_key": "",
    "youtube_channel_handle": "",
    "calendar_backend": "auto",
    # Orijinal sürüm internet tünelini varsayılan açık tutuyordu. Bu yeniden
    # kurulumda telefon sayfası yalnızca bu bilgisayarda açılır; aynı ağ için
    # kullanıcı bunu true yapabilir. Adres yine token ile korunur.
    "web_remote_access": False,
    "phone_autostart": False,
    "start_with_windows": False,
    "weather_location": "",
    "live_model": LIVE_MODELS[0],
    "language": "auto",
    "story_enabled": False,
    "proactive_enabled": False,
    "quiet_minutes": 20,
    "water_enabled": False,
    "break_enabled": False,
    "event_alerts": False,
    # Ayarlar › SES › YANKI ENGELLEME. Açıkken mikrofon Windows Voice Capture DSP'sinden gelir.
    "aec_enabled": True,
}


def config_path() -> Path:
    return data_path("config", "api_keys.json")


def load_app_config() -> dict:
    config = dict(DEFAULT_CONFIG)
    path = config_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return config
    except (OSError, json.JSONDecodeError) as exc:
        backup = path.with_suffix(".json.bak")
        try:
            if path.exists():
                backup.write_bytes(path.read_bytes())
        except OSError:
            pass
        config["_config_error"] = f"Ayar dosyası okunamadı ({exc}). Yedek: {backup.name}"
        return config
    if isinstance(raw, dict):
        config.update(raw)
    config["voice"] = _clean_voice(config.get("voice"))
    config["assistant_name"] = _clean_name(config.get("assistant_name"))
    config["address_as"] = _clean_address(config.get("address_as"))
    config["ui_color"] = _clean_color(config.get("ui_color"))
    config["voice_volume"] = _clean_volume(config.get("voice_volume"))
    config["effects"] = _clean_bool(config.get("effects"), True)
    config["panels_off"] = _clean_panels(config.get("panels_off"))
    backend = str(config.get("calendar_backend", "auto") or "auto").strip().lower()
    if backend not in {"auto", "outlook", "local"}:
        backend = "auto"
    env_backend = os.environ.get("JARVIS_CALENDAR_BACKEND", "").strip().lower()
    if env_backend in {"auto", "outlook", "local"}:
        backend = env_backend
    config["calendar_backend"] = backend
    config["web_remote_access"] = bool(config.get("web_remote_access", False))
    config["phone_autostart"] = _clean_bool(config.get("phone_autostart"), False)
    config["start_with_windows"] = _clean_bool(config.get("start_with_windows"), False)
    config["live_model"] = _clean_model(config.get("live_model"))
    config["language"] = _clean_language(config.get("language"))
    config["story_enabled"] = _clean_bool(config.get("story_enabled"), False)
    config["proactive_enabled"] = _clean_bool(config.get("proactive_enabled"), False)
    config["water_enabled"] = _clean_bool(config.get("water_enabled"), False)
    config["break_enabled"] = _clean_bool(config.get("break_enabled"), False)
    config["event_alerts"] = _clean_bool(config.get("event_alerts"), False)
    config["aec_enabled"] = _clean_bool(config.get("aec_enabled"), True)
    config["quiet_minutes"] = _clean_quiet(config.get("quiet_minutes"))
    return config


def _clean_voice(value) -> str:
    voice = str(value or "Charon").strip()
    return voice if voice in VOICES else "Charon"


def _clean_name(value) -> str:
    name = "".join(ch for ch in str(value or "").strip() if ch.isprintable() and ch not in "\r\n\t")
    name = " ".join(name.split())
    return name[:24] or "FRIDAY"


def _clean_address(value) -> str:
    text = "".join(ch for ch in str(value or "").strip() if ch.isprintable() and ch not in "\r\n\t")
    text = " ".join(text.split())
    return text[:32] or "adınla"


def _clean_bool(value, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "hayir", "off", "kapali", ""}
    if value is None:
        return default
    return bool(value)


def _clean_volume(value) -> int:
    try:
        level = int(float(value))
    except (TypeError, ValueError):
        level = 100
    return max(0, min(150, level))


def _clean_panels(value) -> list[str]:
    if not isinstance(value, list):
        return []
    seen = []
    for item in value:
        key = str(item or "").strip()
        if key in PANEL_KEYS and key not in seen:
            seen.append(key)
    return seen


def _clean_model(value) -> str:
    model = str(value or LIVE_MODELS[0]).strip()
    return model if model in LIVE_MODELS else LIVE_MODELS[0]


def _clean_language(value) -> str:
    key = str(value or "auto").strip().lower()
    return key if key in LANGUAGES else "auto"


def _clean_quiet(value) -> int:
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        minutes = 20
    return minutes if minutes in {10, 20, 40} else 20


def _clean_color(value) -> str:
    key = str(value or "gold").strip().lower()
    return key if key in UI_COLORS else "gold"


def address_phrase(config: dict | None = None) -> str:
    current = config or load_app_config()
    raw = str(current.get("address_as") or "").strip().lower()
    if raw in {"", "adinla", "adınla", "adin"}:
        return _clean_name(current.get("assistant_name"))
    return _clean_address(current.get("address_as"))


def persona_palette(config: dict | None = None) -> dict:
    current = config or load_app_config()
    palette = dict(UI_COLORS[_clean_color(current.get("ui_color"))])
    palette["id"] = _clean_color(current.get("ui_color"))
    return palette


def persona_note(config: dict | None = None) -> str:
    current = config or load_app_config()
    name = _clean_name(current.get("assistant_name"))
    address = address_phrase(current)
    return (
        "\nKİMLİK:\n"
        f"- Görünen adın {name}. Kendini bu adla tanıt.\n"
        f"- Kullanıcı sana «{address}» diye hitap eder. Bu hitabı kabul et ve aynı sıcaklıkta yanıt ver.\n"
    )


def save_app_config(updates: dict) -> dict:
    config = load_app_config()
    config.pop("_config_error", None)
    for key, value in (updates or {}).items():
        if value is None or key.startswith("_"):
            continue
        config[key] = value
    config["voice"] = _clean_voice(config.get("voice"))
    config["assistant_name"] = _clean_name(config.get("assistant_name"))
    config["address_as"] = _clean_address(config.get("address_as"))
    config["ui_color"] = _clean_color(config.get("ui_color"))
    config["voice_volume"] = _clean_volume(config.get("voice_volume"))
    config["effects"] = _clean_bool(config.get("effects"), True)
    config["panels_off"] = _clean_panels(config.get("panels_off"))
    config["live_model"] = _clean_model(config.get("live_model"))
    config["language"] = _clean_language(config.get("language"))
    config["story_enabled"] = _clean_bool(config.get("story_enabled"), False)
    config["proactive_enabled"] = _clean_bool(config.get("proactive_enabled"), False)
    config["water_enabled"] = _clean_bool(config.get("water_enabled"), False)
    config["break_enabled"] = _clean_bool(config.get("break_enabled"), False)
    config["event_alerts"] = _clean_bool(config.get("event_alerts"), False)
    config["aec_enabled"] = _clean_bool(config.get("aec_enabled"), True)
    config["phone_autostart"] = _clean_bool(config.get("phone_autostart"), False)
    config["start_with_windows"] = _clean_bool(config.get("start_with_windows"), False)
    config["quiet_minutes"] = _clean_quiet(config.get("quiet_minutes"))
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=4, ensure_ascii=False), encoding="utf-8")
    return config


def get_app_config_value(key: str, default=None):
    return load_app_config().get(key, default)


def has_gemini_api_key() -> bool:
    return bool(str(get_app_config_value("gemini_api_key", "") or "").strip())
