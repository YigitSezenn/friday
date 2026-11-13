from __future__ import annotations

TOOL_DECLARATIONS = [
    {"name": "open_app", "description": "Windows'ta bir uygulamayi acar.", "parameters": {"type": "OBJECT", "properties": {"app_name": {"type": "STRING"}}, "required": ["app_name"]}},
    {"name": "sys_info", "description": "Pil, CPU, RAM, disk, saat, tarih veya ag bilgisi.", "parameters": {"type": "OBJECT", "properties": {"query": {"type": "STRING", "description": "battery|cpu|ram|disk|time|date|network|all"}}, "required": ["query"]}},
    {"name": "get_weather", "description": "Anlik hava durumu. Konum bos ise bulunan sehir kullanilir.", "parameters": {"type": "OBJECT", "properties": {"location": {"type": "STRING"}}}},
    {"name": "get_calendar_events", "description": "Takvimi okur. Outlook aciksa Outlook, degilse JARVIS yerel takvimi.", "parameters": {"type": "OBJECT", "properties": {"query": {"type": "STRING"}, "limit": {"type": "NUMBER"}}, "required": ["query"]}},
    {"name": "add_calendar_event", "description": "Takvime etkinlik ekler.", "parameters": {"type": "OBJECT", "properties": {"title": {"type": "STRING"}, "start_iso": {"type": "STRING"}, "end_iso": {"type": "STRING"}, "location": {"type": "STRING"}, "notes": {"type": "STRING"}, "calendar_name": {"type": "STRING"}, "all_day": {"type": "BOOLEAN"}}, "required": ["title", "start_iso"]}},
    {"name": "delete_calendar_event", "description": "Takvimden etkinlik siler.", "parameters": {"type": "OBJECT", "properties": {"title": {"type": "STRING"}, "start_iso": {"type": "STRING"}, "calendar_name": {"type": "STRING"}, "delete_all_matches": {"type": "BOOLEAN"}}, "required": ["title"]}},
    {"name": "get_reminders", "description": "Animsaticilari okur.", "parameters": {"type": "OBJECT", "properties": {"query": {"type": "STRING"}, "limit": {"type": "NUMBER"}, "list_name": {"type": "STRING"}}, "required": ["query"]}},
    {"name": "add_reminder", "description": "Animsatici ekler.", "parameters": {"type": "OBJECT", "properties": {"title": {"type": "STRING"}, "due_iso": {"type": "STRING"}, "notes": {"type": "STRING"}, "list_name": {"type": "STRING"}, "priority": {"type": "STRING"}, "all_day": {"type": "BOOLEAN"}}, "required": ["title"]}},
    {"name": "complete_reminder", "description": "Animsaticiyi tamamlandi olarak isaretler.", "parameters": {"type": "OBJECT", "properties": {"title": {"type": "STRING"}, "id": {"type": "STRING"}}}},
    {"name": "delete_reminder", "description": "Animsaticiyi siler.", "parameters": {"type": "OBJECT", "properties": {"title": {"type": "STRING"}, "id": {"type": "STRING"}}}},
    {"name": "browser_control", "description": "URL acar, Google'da arar veya YouTube videosu acar.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING"}, "url": {"type": "STRING"}, "query": {"type": "STRING"}}, "required": ["action"]}},
    {"name": "shell_run", "description": "Guvenlik filtreli PowerShell komutu calistirir.", "parameters": {"type": "OBJECT", "properties": {"command": {"type": "STRING"}}, "required": ["command"]}},
    {"name": "toggle_webcam", "description": "Kamerayi acar veya kapatir.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING"}}, "required": ["action"]}},
    {"name": "play_media", "description": "Spotify veya YouTube'da icerik acar.", "parameters": {"type": "OBJECT", "properties": {"query": {"type": "STRING"}, "provider": {"type": "STRING"}, "autoplay": {"type": "BOOLEAN"}}, "required": ["query"]}},
    {"name": "control_media", "description": "Calan medyayi durdurur, devam ettirir veya parca degistirir.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING"}}, "required": ["action"]}},
    {"name": "get_youtube_channel_report", "description": "YouTube kanal istatistiklerini raporlar.", "parameters": {"type": "OBJECT", "properties": {"query": {"type": "STRING"}, "handle": {"type": "STRING"}, "video_limit": {"type": "NUMBER"}}}},
    {"name": "analyze_screen", "description": "Aktif pencerenin goruntusunu okur.", "parameters": {"type": "OBJECT", "properties": {"query": {"type": "STRING"}, "target": {"type": "STRING"}}}},
    {"name": "save_memory", "description": "Kalici hafizaya kaydeder.", "parameters": {"type": "OBJECT", "properties": {"category": {"type": "STRING"}, "key": {"type": "STRING"}, "value": {"type": "STRING"}}, "required": ["category", "key", "value"]}},
    {"name": "delete_memory", "description": "Kalici hafizadan kayit siler.", "parameters": {"type": "OBJECT", "properties": {"category": {"type": "STRING"}, "key": {"type": "STRING"}, "match_text": {"type": "STRING"}}}},
    {"name": "send_whatsapp_message", "description": "WhatsApp mesaji hazirlar veya gondermeye calisir.", "parameters": {"type": "OBJECT", "properties": {"message": {"type": "STRING"}, "phone_number": {"type": "STRING"}, "recipient_name": {"type": "STRING"}, "send_now": {"type": "BOOLEAN"}, "app_target": {"type": "STRING"}}, "required": ["message"]}},
    {"name": "save_whatsapp_contact", "description": "WhatsApp kisisi kaydeder.", "parameters": {"type": "OBJECT", "properties": {"display_name": {"type": "STRING"}, "phone_number": {"type": "STRING"}, "aliases": {"type": "STRING"}}, "required": ["display_name", "phone_number"]}},
    {"name": "web_search", "description": "Internette kisa bir ozet arar.", "parameters": {"type": "OBJECT", "properties": {"query": {"type": "STRING"}}, "required": ["query"]}},
    {"name": "list_files", "description": "Masaustu, Belgeler veya Indirilenler klasorunu listeler.", "parameters": {"type": "OBJECT", "properties": {"folder": {"type": "STRING"}}, "required": ["folder"]}},
]

ERROR_MARKERS = (
    "hata", "error", "alinamadi", "alınamadı", "bulunamadi", "bulunamadı",
    "acilamadi", "açılamadı", "tamamlanamadi", "tamamlanamadı", "gecersiz",
    "geçersiz", "izin gerekiyor", "izin gerekli", "baglanti", "bağlantı", "gerekli.",
)


def looks_like_error(result) -> bool:
    text = str(result or "").strip().lower()
    return bool(text) and any(marker in text for marker in ERROR_MARKERS)


def _as_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def execute_tool(name: str, args: dict, webcam=None, ui=None) -> str:
    result = _run_tool(name, args, webcam, ui)
    try:
        from jarvis.story import note_tool

        note_tool(name, result)
    except Exception:
        pass
    return result


def _run_tool(name: str, args: dict, webcam=None, ui=None) -> str:
    args = args or {}
    if name == "save_memory":
        from jarvis.memory_store import update_memory

        category = str(args.get("category") or "notes").strip() or "notes"
        key = str(args.get("key") or "").strip()
        value = str(args.get("value") or "").strip()
        if not key or not value:
            return "Hafizaya yazilamadi: key ve value dolu olmali."
        update_memory({category: {key: {"value": value}}})
        return f"Hafizaya kaydedildi: {category}/{key} = {value}"
    if name == "delete_memory":
        from jarvis.memory_store import delete_memory

        return delete_memory(args.get("category", ""), args.get("key", ""), args.get("match_text", ""))
    if name == "open_app":
        from tools.actions.apps import open_app

        return open_app(str(args.get("app_name", "")))
    if name == "sys_info":
        from tools.actions.system import sys_info

        if ui:
            query = str(args.get("query", "")).lower()
            ui.focus_panel("time" if query in {"time", "saat", "date", "tarih"} else "system")
        return sys_info(str(args.get("query", "all")))
    if name == "get_weather":
        from tools.actions.weather import get_weather_summary

        if ui:
            ui.focus_panel("weather")
        return get_weather_summary(args.get("location") or None)
    if name == "get_calendar_events":
        from tools.actions.calendar import get_calendar_events

        return get_calendar_events(str(args.get("query", "today")), _as_int(args.get("limit", 6), 6))
    if name == "add_calendar_event":
        from tools.actions.calendar import add_calendar_event

        return add_calendar_event(
            str(args.get("title", "")),
            str(args.get("start_iso", "")),
            str(args.get("end_iso", "")),
            str(args.get("notes", "")),
            str(args.get("location", "")),
            str(args.get("calendar_name", "")),
            bool(args.get("all_day", False)),
        )
    if name == "delete_calendar_event":
        from tools.actions.calendar import delete_calendar_event

        return delete_calendar_event(
            str(args.get("title", "")),
            str(args.get("start_iso", "")),
            str(args.get("calendar_name", "")),
            bool(args.get("delete_all_matches", False)),
        )
    if name == "get_reminders":
        from tools.actions.reminders import get_reminders

        return get_reminders(str(args.get("query", "upcoming")), _as_int(args.get("limit", 8), 8), str(args.get("list_name", "")))
    if name == "add_reminder":
        from tools.actions.reminders import add_reminder

        return add_reminder(
            str(args.get("title", "")),
            str(args.get("due_iso", "")),
            str(args.get("notes", "")),
            str(args.get("list_name", "")),
            str(args.get("priority", "")),
            bool(args.get("all_day", False)),
        )
    if name == "complete_reminder":
        from tools.actions.reminders import complete_reminder

        return complete_reminder(str(args.get("title", "")), str(args.get("id", "")))
    if name == "delete_reminder":
        from tools.actions.reminders import delete_reminder

        return delete_reminder(str(args.get("title", "")), str(args.get("id", "")))
    if name == "browser_control":
        from tools.actions.browser import browser_control

        return browser_control(args.get("action"), args.get("url"), args.get("query"))
    if name == "shell_run":
        from tools.actions.shell import shell_run

        return shell_run(str(args.get("command", "")))
    if name == "toggle_webcam":
        action = str(args.get("action", "start")).strip().lower()
        if webcam is None:
            return "Webcam bu oturumda kullanilamiyor."
        if action == "start":
            status = webcam.start()
            if ui:
                ui.set_webcam_active(status in {"ok", "already_active"})
            if status == "ok":
                return "Webcam akisi baslatildi. Artik kamerani goruyorum."
            if status == "already_active":
                return "Webcam zaten acik, goruntu aliyorum."
            return "Webcam baslatilamadi."
        webcam.stop()
        if ui:
            ui.set_webcam_active(False)
        return "Webcam akisi durduruldu."
    if name == "play_media":
        from tools.actions.media import play_media

        return play_media(str(args.get("query", "")), str(args.get("provider", "auto")), bool(args.get("autoplay", True)))
    if name == "control_media":
        from tools.actions.media import control_media

        return control_media(str(args.get("action", "pause")))
    if name == "get_youtube_channel_report":
        from tools.actions.youtube import get_youtube_channel_report

        return get_youtube_channel_report(str(args.get("query", "overview")), str(args.get("handle", "")), _as_int(args.get("video_limit", 6), 6))
    if name == "analyze_screen":
        from tools.actions.screen import analyze_screen

        return analyze_screen(str(args.get("query", "Ekranda ne var?")), str(args.get("target", "active_window")))
    if name == "send_whatsapp_message":
        from tools.actions.whatsapp import send_whatsapp_message

        return send_whatsapp_message(
            str(args.get("message", "")),
            str(args.get("phone_number", "")),
            str(args.get("recipient_name", "")),
            bool(args.get("send_now", False)),
            str(args.get("app_target", "auto")),
        )
    if name == "save_whatsapp_contact":
        from tools.actions.whatsapp import save_whatsapp_contact

        return save_whatsapp_contact(str(args.get("display_name", "")), str(args.get("phone_number", "")), str(args.get("aliases", "")))
    if name == "web_search":
        from tools.actions.search import web_search

        return web_search(str(args.get("query", "")))
    if name == "list_files":
        from tools.actions.files import list_user_files

        return list_user_files(str(args.get("folder", "desktop")))
    return f"Bilinmeyen arac: {name}"
