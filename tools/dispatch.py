"""Arac bildirimleri ve cagri girisi. Isleyiciler tools/handlers.py icindedir."""

from __future__ import annotations

from tools.handlers import HANDLERS, ToolContext

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
    {"name": "send_whatsapp_message", "description": "WhatsApp mesaji hazirlar veya gondermeye calisir.", "parameters": {"type": "OBJECT", "properties": {"message": {"type": "STRING"}, "phone_number": {"type": "STRING"}, "recipient_name": {"type": "STRING"}, "send_now": {"type": "BOOLEAN"}, "app_target": {"type": "STRING"}, "confirm": {"type": "BOOLEAN", "description": "Kullanici 'gonder' onayini verdikten sonra true"}}, "required": ["message"]}},
    {"name": "send_email", "description": "Gmail ile e-posta gonderir. Ilk cagri taslak doner; kullanici onaylayinca confirm=true ile tekrar cagir.", "parameters": {"type": "OBJECT", "properties": {"to": {"type": "STRING"}, "recipient_name": {"type": "STRING"}, "subject": {"type": "STRING"}, "body": {"type": "STRING"}, "confirm": {"type": "BOOLEAN"}}, "required": ["body"]}},
    {"name": "save_email_contact", "description": "E-posta kisisi kaydeder.", "parameters": {"type": "OBJECT", "properties": {"display_name": {"type": "STRING"}, "email": {"type": "STRING"}, "aliases": {"type": "STRING"}}, "required": ["display_name", "email"]}},
    {"name": "connect_gmail", "description": "Gmail hesabini baglar (OAuth, yalnizca gonderme izni).", "parameters": {"type": "OBJECT", "properties": {}}},
    {"name": "open_mail", "description": "Gmail gelen kutusunu tarayicida acar.", "parameters": {"type": "OBJECT", "properties": {}}},
    {"name": "save_whatsapp_contact", "description": "WhatsApp kisisi kaydeder.", "parameters": {"type": "OBJECT", "properties": {"display_name": {"type": "STRING"}, "phone_number": {"type": "STRING"}, "aliases": {"type": "STRING"}}, "required": ["display_name", "phone_number"]}},
    {"name": "web_search", "description": "Internette kisa bir ozet arar.", "parameters": {"type": "OBJECT", "properties": {"query": {"type": "STRING"}}, "required": ["query"]}},
    {"name": "list_files", "description": "Masaustu, Belgeler veya Indirilenler klasorunu listeler.", "parameters": {"type": "OBJECT", "properties": {"folder": {"type": "STRING"}}, "required": ["folder"]}},
    {"name": "set_location", "description": "Kalici konumu degistirir (hava ve harita da gecer). Kullanici \"Konumum artik Izmir\" veya \"Kadikoy'deyim\" derse cagir. auto=true ise konum yeniden internetten bulunur.", "parameters": {"type": "OBJECT", "properties": {"location": {"type": "STRING"}, "auto": {"type": "BOOLEAN"}}}},
]

ERROR_MARKERS = (
    "hata", "error", "alinamadi", "alınamadı", "bulunamadi", "bulunamadı",
    "acilamadi", "açılamadı", "tamamlanamadi", "tamamlanamadı", "gecersiz",
    "geçersiz", "izin gerekiyor", "izin gerekli", "baglanti", "bağlantı", "gerekli.",
)


def looks_like_error(result) -> bool:
    text = str(result or "").strip().lower()
    return bool(text) and any(marker in text for marker in ERROR_MARKERS)


def execute_tool(name: str, args: dict, webcam=None, ui=None) -> str:
    result = _run_tool(name, args, webcam, ui)
    try:
        from jarvis.story import note_tool

        note_tool(name, result)
    except Exception:
        pass
    return result


def _run_tool(name: str, args: dict, webcam=None, ui=None) -> str:
    handler = HANDLERS.get(name)
    if handler is None:
        return f"Bilinmeyen arac: {name}"
    return handler(args or {}, ToolContext(webcam=webcam, ui=ui))
