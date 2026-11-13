from __future__ import annotations

import json
import math
import threading
import time
from pathlib import Path

from jarvis import __version__
from jarvis.config import VOICES, has_gemini_api_key, load_app_config, save_app_config
from jarvis.paths import data_path, data_root

def hud_file() -> Path:
    import sys

    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS")) / "ui" / "hud" / "index.html"
    return Path(__file__).resolve().parent / "hud" / "index.html"


HUD = hud_file()


class HudBridge:
    def __init__(self, ui: "JarvisUI"):
        self.ui = ui

    def post(self, kind: str, data: dict | None = None) -> dict:
        try:
            return self._dispatch(kind, data or {})
        except Exception:
            return {"ok": False}


def script_for(name: str, *args) -> str:
    """JS'e gömülecek çağrı. Çıplak sayı startsWith yüzünden betiği düşürür."""
    payload = ", ".join(_js_literal(arg) for arg in args)
    return f"(function(){{ if (window.hud && window.hud.{name}) window.hud.{name}({payload}); return null; }})()"


def _js_literal(value) -> str:
    text = json.dumps(value, ensure_ascii=True)
    return text.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def _dispatch(self, kind: str, payload: dict) -> dict:
        ui = self.ui
        if kind == "command":
            from jarvis.textfix import repair_text

            text = payload.get("text")
            text = repair_text(str(text)).strip() if text is not None else ""
            if text and ui.on_text_command:
                ui.on_text_command(text)
        elif kind == "mute":
            ui.muted = bool(payload.get("muted"))
        elif kind == "camera":
            ui._cam = bool(payload.get("on"))
            if ui.on_webcam_toggle:
                ui.on_webcam_toggle(ui._cam)
        elif kind == "settings":
            saved = save_app_config(dict(payload.get("values") or {}))
            if "start_with_windows" in (payload.get("values") or {}):
                from jarvis.startup import apply_windows_startup

                apply_windows_startup(bool(saved.get("start_with_windows")))
            ui.effects = bool(load_app_config().get("effects", True))
            ui.push_settings()
            ui.write_log("SYS: Ayarlar kaydedildi. Ses karakteri yeniden baglaniyor.")
            if ui.on_settings_saved:
                ui.on_settings_saved()
            from jarvis.config import has_gemini_api_key

            if has_gemini_api_key() and ui.phone_opener:
                ui.phone_opener()
        elif kind == "sleep":
            asleep = bool(payload.get("asleep"))
            ui.paused = asleep
            if ui.on_pause_toggle:
                ui.on_pause_toggle(asleep)
        elif kind == "forget":
            from jarvis.memory_store import delete_memory

            delete_memory(category=str(payload.get("category") or ""), key=str(payload.get("key") or ""))
            ui.push_settings()
        elif kind == "phone":
            url = ""
            if ui.phone_opener:
                url = ui.phone_opener() or ""
            ui._call("phone", _phone_payload(url))
        elif kind == "phone_rotate":
            from jarvis.phone_server import phone_status, rotate_phone_token

            rotate_phone_token()
            ui._call("phone", _phone_payload(str(phone_status().get("url") or "")))
        elif kind == "story":
            from jarvis.story import choose, view

            ending = str(payload.get("ending") or "")
            if ending:
                ui.write_log("SYS: " + choose(ending))
            ui._call("story", view())
        elif kind == "note":
            lines = [str(line).strip() for line in payload.get("lines") or [] if str(line).strip()]
            data_path("memory", "notes.txt").write_text("\n".join(lines), encoding="utf-8")
        elif kind == "beep":
            ui.play_success_sfx()
        elif kind == "minimize":
            ui.minimize_to_taskbar()
        elif kind == "quit":
            ui.close()
        elif kind == "uninstall":
            ui.request_uninstall()
        elif kind == "open_data":
            import os

            os.startfile(data_root())  # type: ignore[attr-defined]
        elif kind == "copy":
            _copy_text(str(payload.get("text") or ""))
        elif kind == "open":
            _open_allowed(str(payload.get("url") or ""))
        elif kind == "reminder":
            action = str(payload.get("action") or "")
            title = str(payload.get("title") or "")
            reminder_id = str(payload.get("id") or "")
            from tools.actions.reminders import complete_reminder, delete_reminder

            if action == "complete":
                ui.write_log("SYS: " + complete_reminder(title, reminder_id))
            elif action == "delete":
                ui.write_log("SYS: " + delete_reminder(title, reminder_id))
            ui._push_agenda()
        return {"ok": True}


HudBridge._dispatch = _dispatch


def _open_allowed(url: str) -> None:
    import webbrowser

    allowed = {
        "https://aistudio.google.com/apikey",
        "https://youtu.be/VZl5uBT4a60",
        "https://ai.studio/projects",
    }
    if url in allowed or url.startswith("https://aistudio.google.com/apikey"):
        webbrowser.open(url)


def _copy_text(text: str) -> None:
    if not text:
        return
    import ctypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    if not user32.OpenClipboard(None):
        return
    try:
        user32.EmptyClipboard()
        encoded = text.encode("utf-16-le") + b"\x00\x00"
        handle = kernel32.GlobalAlloc(0x0002, len(encoded))
        locked = kernel32.GlobalLock(handle)
        ctypes.memmove(locked, encoded, len(encoded))
        kernel32.GlobalUnlock(handle)
        if not user32.SetClipboardData(13, handle):
            kernel32.GlobalFree(handle)
    finally:
        user32.CloseClipboard()


def _settings_phone(status: dict, qr_fn) -> dict:
    url = str(status.get("url") or "")
    qr = ""
    if url:
        try:
            qr = qr_fn(url)
        except Exception:
            qr = ""
    return {"running": bool(status.get("running")), "url": url, "qr": qr}


def _phone_payload(url: str) -> dict:
    from jarvis.phone_server import phone_qr_data_url

    if not url:
        return {"running": False, "url": "", "qr": ""}
    try:
        qr = phone_qr_data_url(url)
    except Exception:
        qr = ""
    return {"running": True, "url": url, "qr": qr}


class _Root:
    def __init__(self, ui: "JarvisUI"):
        self.ui = ui
        self._alive = True

    def withdraw(self) -> None:
        self.ui._smoke = True

    def update(self) -> None:
        return

    def update_idletasks(self) -> None:
        return

    def winfo_exists(self) -> bool:
        return self._alive

    def destroy(self) -> None:
        self._alive = False
        self.ui.close()

    def mainloop(self) -> None:
        if not self.ui._smoke:
            self.ui._open()


class JarvisUI:
    def __init__(self):
        self.on_text_command = None
        self.on_pause_toggle = None
        self.on_webcam_toggle = None
        self.phone_opener = None
        self.on_settings_saved = None
        self.muted = False
        self.paused = False
        self.effects = True
        self.last_heard = time.time()
        self._map_city = ""
        self._state = "INITIALISING"
        self._cam = False
        self._smoke = False
        self._ready = False
        self._closed = False
        self._quitting = False
        self._queue: list[str] = []
        self._window = None
        self._bridge = HudBridge(self)
        self.root = _Root(self)

    def _call(self, name: str, *args) -> None:
        safe = tuple(str(arg) if name == "log" and not isinstance(arg, str) else arg for arg in args)
        self._js(script_for(name, *safe))

    def _js(self, script: str) -> None:
        if self._smoke or self._closed:
            return
        if not self._ready or self._window is None:
            self._queue.append(script)
            return
        try:
            self._window.evaluate_js(script)
        except Exception:
            self._queue.append(script)

    def _open(self) -> None:
        import webview

        self._window = webview.create_window(
            "FRIDAY",
            HUD.as_uri(),
            js_api=self._bridge,
            width=1360,
            height=860,
            min_size=(1100, 720),
            background_color="#000000",
        )
        self._window.events.loaded += self._on_loaded
        self._window.events.closing += self._stay_on_taskbar
        webview.start()

    def _on_loaded(self) -> None:
        self._ready = True
        threading.Thread(target=self._boot, name="jarvis-boot", daemon=True).start()

    def _boot(self) -> None:
        time.sleep(0.05)
        queued = list(self._queue)
        self._queue.clear()
        for script in queued:
            self._js(script)
        self.push_settings()
        self._call("notes", self._notes())
        self.set_state(self._state)
        threading.Thread(target=self._refresh_loop, name="jarvis-hud", daemon=True).start()
        threading.Thread(target=self._load_remote, name="jarvis-remote", daemon=True).start()

    def push_settings(self) -> None:
        from jarvis.config import ADDRESS_PRESETS, LIVE_MODELS, PANEL_KEYS, UI_COLORS, address_phrase, persona_palette
        from jarvis.language import choices, ui_language
        from jarvis.memory_store import load_memory
        from jarvis.gate_client import ensure_gate_key, gate_join_url, pair_code
        from jarvis.phone_server import phone_qr_data_url, phone_status
        from jarvis.story import view

        config = load_app_config()
        self.effects = bool(config.get("effects", True))
        keys = ("gemini_api_key", "youtube_api_key", "youtube_channel_handle", "weather_location", "voice", "assistant_name", "address_as", "ui_color", "voice_volume", "effects", "aec_enabled", "live_model", "language", "story_enabled", "proactive_enabled", "quiet_minutes", "water_enabled", "break_enabled", "event_alerts", "phone_autostart", "start_with_windows")
        safe = {key: config.get(key, "") for key in keys}
        memories = []
        for category, items in load_memory().items():
            if not isinstance(items, dict):
                continue
            for key, value in items.items():
                text = value.get("value") if isinstance(value, dict) else value
                memories.append({"category": str(category), "key": str(key), "text": str(text)[:180]})
        self._call(
            "settings",
            {
                "voices": list(VOICES),
                "config": safe,
                "needKey": not has_gemini_api_key(),
                "dataDir": str(data_root()),
                "version": __version__,
                "colors": [{"id": key, "label": value["label"]} for key, value in UI_COLORS.items()],
                "addresses": list(ADDRESS_PRESETS),
                "panels": [{"id": key, "off": key in config.get("panels_off", [])} for key in PANEL_KEYS],
                "palette": persona_palette(config),
                "name": config["assistant_name"],
                "address": address_phrase(config),
                "memories": memories[:40],
                "phone": _settings_phone(phone_status(), phone_qr_data_url),
                "gateKeyQr": phone_qr_data_url(gate_join_url(ensure_gate_key())),
                "pairCode": pair_code(ensure_gate_key()),
                "languages": choices(),
                "uiLanguage": ui_language(config),
                "models": list(LIVE_MODELS),
                "story": view(),
            },
        )
        self._recolor_map()
        window = self._window
        if window is not None:
            try:
                window.set_title(str(config["assistant_name"]))
            except Exception:
                pass

    def _refresh_loop(self) -> None:
        while not self._closed:
            self._push_stats()
            self._push_agenda()
            time.sleep(2)

    def _push_stats(self) -> None:
        cpu = ram = disk = 0
        try:
            import psutil

            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage("C:\\").percent
        except Exception:
            pass
        self._call("stats", {"cpu": cpu, "ram": ram, "disk": disk})

    def _push_agenda(self) -> None:
        calendar = "Bugün takviminde etkinlik yok."
        reminders = "Bekleyen anımsatıcı yok."
        cal_count = rem_count = 0
        try:
            from tools.actions.calendar import get_calendar_events
            from tools.actions.reminders import get_reminders

            raw_calendar = get_calendar_events("today")
            raw_reminders = get_reminders("upcoming")
            cal_items = [line for line in raw_calendar.splitlines() if line.startswith("- ")]
            rem_items = [line for line in raw_reminders.splitlines() if line.startswith("- ")]
            cal_count = len(cal_items)
            rem_count = len(rem_items)
            if cal_items:
                calendar = "\n".join(cal_items[:3])
            if rem_items:
                reminders = "\n".join(rem_items[:3])
        except Exception as exc:
            calendar = f"Takvim okunamadı: {exc}"
        self._call("agenda", {"calendar": calendar, "reminders": reminders, "calendarCount": cal_count, "reminderCount": rem_count})

    def _load_remote(self) -> None:
        try:
            from tools.actions.weather import get_weather_report

            card = get_weather_report(None)
            city = str(card.get("place") or "Konum")
            wind = str(card.get("wind") or "")
            detail = f"Hissedilen {card.get('feels') or '—'}° · Nem %{card.get('humidity') or '—'} · Rüzgar {wind or '—'} km/s"
            self._call("weather", {
                "temp": f"{card.get('temp') or '--'}°",
                "city": city.upper(),
                "desc": str(card.get("desc") or "")[:40],
                "detail": detail,
                "card": card,
            })
            self._map_city = city
            self._load_map(city)
        except Exception as exc:
            self._call("weather", {"temp": "--°", "city": "KONUM", "desc": "", "detail": f"Hava alınamadı: {exc}", "card": {}})

    def _load_map(self, city: str) -> None:
        try:
            import io

            import requests
            from PIL import Image, ImageOps

            found = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": city, "format": "json", "limit": 1},
                headers={"User-Agent": "FRIDAY/3.5 (desktop assistant)"},
                timeout=12,
            )
            found.raise_for_status()
            rows = found.json()
            if not rows:
                return
            lat, lon = float(rows[0]["lat"]), float(rows[0]["lon"])
            self._call("place", {"lat": lat, "lon": lon, "label": city})
            zoom = 11
            n = 2 ** zoom
            x = int((lon + 180) / 360 * n)
            y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
            tile = requests.get(
                f"https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{zoom}/{y}/{x}",
                headers={"User-Agent": "FRIDAY/3.5 (desktop assistant)"},
                timeout=12,
            )
            tile.raise_for_status()
            gray = Image.open(io.BytesIO(tile.content)).convert("L").resize((496, 264))
            gray.save(data_path("cache", "map-gray.png"))
            from jarvis.config import persona_palette
            from jarvis.mapcolor import tint_gray

            image = tint_gray(gray, persona_palette()["c"])
            path = data_path("cache", "map.png")
            image.save(path)
            import base64

            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            self._call("map", f"data:image/png;base64,{encoded}")
        except Exception:
            return

    def _recolor_map(self) -> None:
        path = data_path("cache", "map-gray.png")
        if not path.exists():
            return
        try:
            import base64

            from PIL import Image

            from jarvis.config import persona_palette
            from jarvis.mapcolor import tint_gray

            image = tint_gray(Image.open(path), persona_palette()["c"])
            out = data_path("cache", "map.png")
            image.save(out)
            encoded = base64.b64encode(out.read_bytes()).decode("ascii")
            self._call("map", f"data:image/png;base64,{encoded}")
        except Exception:
            return

    def _notes(self) -> list[str]:
        try:
            return [line.strip() for line in data_path("memory", "notes.txt").read_text(encoding="utf-8").splitlines() if line.strip()]
        except OSError:
            return []

    def write_log(self, text: str) -> None:
        from jarvis.textfix import repair_text

        self._call("log", repair_text(str(text)))

    def write_debug(self, text: str, level: str = "INFO") -> None:
        self.write_log(f"{level}: {text}")

    def set_state(self, state: str) -> None:
        self._state = state
        mapped = {
            "INITIALISING": "connecting",
            "LISTENING": "paused" if self.muted else "listening",
            "SPEAKING": "speaking",
            "THINKING": "thinking",
            "ERROR": "error",
        }.get(state, "idle")
        self._call("state", mapped)

    def focus_panel(self, name: str, duration_ms: int = 5000) -> None:
        labels = {"time": "time", "system": "system", "weather": "weather"}
        self._call("focus", labels.get(name, name))

    def set_webcam_active(self, active: bool) -> None:
        self._cam = active
        self._call("camera", active)

    def update_webcam_preview(self, jpeg: bytes) -> None:
        import base64

        self._call("preview", "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii"))

    def play_success_sfx(self) -> None:
        if not self.effects:
            return
        try:
            import winsound

            winsound.Beep(740, 80)
        except RuntimeError:
            pass

    def mark_user_activity(self, _active: bool = True) -> None:
        return

    def open_settings(self) -> None:
        self._js("document.getElementById('ov-settings').hidden = false")

    def open_phone(self) -> None:
        if self.phone_opener:
            self.phone_opener()

    def wait_for_api_key(self) -> None:
        return

    def _stay_on_taskbar(self) -> bool:
        from jarvis.taskbar import installer_is_running, keep_on_taskbar

        if keep_on_taskbar(self._quitting, installer_is_running()):
            threading.Thread(target=self._minimize_after_close, name="friday-taskbar", daemon=True).start()
            return False
        return True

    def _minimize_after_close(self) -> None:
        time.sleep(0.12)
        self.minimize_to_taskbar()

    def minimize_to_taskbar(self) -> None:
        window = self._window
        if window is None or self._quitting or self._closed:
            return
        try:
            window.minimize()
        except Exception:
            pass

    def restore_from_taskbar(self) -> bool:
        window = self._window
        if window is None or self._quitting or self._closed or self._smoke:
            return False
        try:
            window.restore()
            window.show()
            return True
        except Exception:
            return False

    def request_uninstall(self) -> None:
        from jarvis.uninstall import installed_uninstaller, launch_uninstaller

        if not launch_uninstaller(installed_uninstaller()):
            self.write_log("ERR: Kaldırma yalnız kurulmuş FRIDAY için. Kaynak klasörü ve başka klasörler silinmedi.")
            return
        self._quitting = True
        self.close()

    def close(self) -> None:
        self._quitting = True
        self._closed = True
        window = self._window
        if window is not None:
            try:
                window.destroy()
            except Exception:
                pass
