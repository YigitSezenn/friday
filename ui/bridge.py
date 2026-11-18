from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from jarvis import __version__
from jarvis.config import VOICES, has_gemini_api_key, load_app_config
from jarvis.paths import data_root
from ui.dispatch import _settings_phone, dispatch
from ui.panels import PanelsMixin
from ui.sound import SoundMixin
from ui.timer import TimerMixin
from ui.window import WindowMixin

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
            return dispatch(self.ui, kind, data or {})
        except Exception as exc:  # arayüz çökmesin, ama hata görünür olsun
            import traceback

            traceback.print_exc()
            try:
                self.ui.write_log(f"ERR: Arayüz işlemi ({kind}) başarısız: {exc}")
            except Exception:
                pass
            return {"ok": False}


def script_for(name: str, *args) -> str:
    """JS'e gömülecek çağrı. Çıplak sayı startsWith yüzünden betiği düşürür."""
    payload = ", ".join(_js_literal(arg) for arg in args)
    return f"(function(){{ if (window.hud && window.hud.{name}) window.hud.{name}({payload}); return null; }})()"


def _js_literal(value) -> str:
    text = json.dumps(value, ensure_ascii=True)
    return text.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


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


class JarvisUI(SoundMixin, TimerMixin, PanelsMixin, WindowMixin):
    def __init__(self):
        self.on_text_command = None
        self.on_pause_toggle = None
        self.on_webcam_toggle = None
        self.phone_opener = None
        self.on_settings_saved = None
        self.muted = False
        self.paused = False
        self.effects = True
        self.music = False
        self._farewell = False
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
            fullscreen=True,
        )
        self._window.events.loaded += self._on_loaded
        self._window.events.closing += self._on_closing
        self._window.events.minimized += self.minimize_to_taskbar
        webview.start()

    def _on_loaded(self) -> None:
        self._ready = True
        self._ensure_tray()
        threading.Thread(target=self._boot, name="jarvis-boot", daemon=True).start()
        threading.Thread(target=self._check_update, name="friday-update", daemon=True).start()

    def _boot(self) -> None:
        time.sleep(0.05)
        queued = list(self._queue)
        self._queue.clear()
        for script in queued:
            self._js(script)
        self.push_settings()
        self._call("notes", self._notes())
        self.timer_push()
        self.set_state(self._state)
        threading.Thread(target=self._refresh_loop, name="jarvis-hud", daemon=True).start()
        threading.Thread(target=self._load_remote, name="jarvis-remote", daemon=True).start()
        # Açılış sesi (+ ayar açıksa arka plan müziği). push_settings effects/music'i yükledikten sonra.
        self.play_startup_sfx()

    def push_settings(self) -> None:
        from jarvis.config import ADDRESS_PRESETS, LIVE_MODELS, PANEL_KEYS, UI_COLORS, address_phrase, persona_palette
        from jarvis.language import choices, ui_language
        from jarvis.memory_store import load_memory
        from jarvis.gate_client import ensure_gate_key, gate_join_url, pair_code
        from jarvis.phone_server import phone_qr_data_url, phone_status
        from jarvis.story import view

        config = load_app_config()
        self.effects = bool(config.get("effects", True))
        self.music = bool(config.get("music", False))
        keys = ("gemini_api_key", "youtube_api_key", "youtube_channel_handle", "weather_location", "voice", "assistant_name", "address_as", "ui_color", "voice_volume", "effects", "music", "patient_listening", "live_model", "language", "story_enabled", "proactive_enabled", "quiet_minutes", "water_enabled", "break_enabled", "event_alerts", "phone_autostart", "start_with_windows")
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


    # ---- Zamanlayıcı / kronometre (durum Python'da; HUD ve sesli komut aynı sayacı görür) ----


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


    def mark_user_activity(self, _active: bool = True) -> None:
        return


