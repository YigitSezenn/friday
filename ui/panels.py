"""HUD panelleri: sistem, takvim/anımsatıcı, hava ve harita, notlar."""

from __future__ import annotations

import math
import time

from jarvis.paths import data_path



class PanelsMixin:
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
            self._load_map(city, card.get("lat"), card.get("lon"))
        except Exception as exc:
            self._call("weather", {"temp": "--°", "city": "KONUM", "desc": "", "detail": f"Hava alınamadı: {exc}", "card": {}})

    def _remote_loop(self) -> None:
        """Hava ve harita 15 dakikada bir tazelenir; konum otomatikse IP'den yeniden bulunur."""
        import time

        while not getattr(self, "_closed", False):
            self._load_remote()
            for _ in range(90):
                if getattr(self, "_closed", False):
                    return
                time.sleep(10)

    def refresh_weather(self) -> None:
        import threading

        from tools.actions.weather import auto_location

        def work() -> None:
            auto_location(force=True)
            self._load_remote()

        threading.Thread(target=work, name="friday-weather", daemon=True).start()

    def _load_map(self, city: str, lat=None, lon=None) -> None:
        try:
            import io

            import requests
            from PIL import Image

            if lat is None or lon is None:
                found = requests.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": city, "format": "json", "limit": 1},
                    headers={"User-Agent": "FRIDAY/4.4 (desktop assistant)"},
                    timeout=12,
                )
                found.raise_for_status()
                rows = found.json()
                if not rows:
                    return
                lat, lon = float(rows[0]["lat"]), float(rows[0]["lon"])
            lat, lon = float(lat), float(lon)
            self._call("place", {"lat": lat, "lon": lon, "label": city})
            zoom = 11
            n = 2 ** zoom
            x = int((lon + 180) / 360 * n)
            y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
            tile = requests.get(
                f"https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{zoom}/{y}/{x}",
                headers={"User-Agent": "FRIDAY/4.4 (desktop assistant)"},
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
        except Exception as exc:
            self.write_debug(f"Harita görüntüsü alınamadı: {exc}")

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
        from jarvis import notes

        return notes.load()
