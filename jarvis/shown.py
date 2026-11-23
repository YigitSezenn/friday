"""Araç sonuçlarının ekranda nasıl görüneceği.

Araçlar modele hem sonucu hem de bir talimat (ör. "kısa bir veda et") döndürebilir.
Talimat `MODEL_NOTE` ile ayrılır; ekrana yalnızca önceki kısım ve okunur onay soruları yazılır.
"""

from __future__ import annotations

MODEL_NOTE = "\n[model notu] "


def with_note(visible: str, note: str) -> str:
    return f"{visible}{MODEL_NOTE}{note}"


def for_screen(result: object) -> str:
    from jarvis.textfix import repair_text
    from tools.actions.confirm import friendly

    text = repair_text(str(result or "")).split(MODEL_NOTE)[0].strip()
    return friendly(text)


TOOL_LABELS = {
    "get_weather": "Hava durumu", "get_calendar_events": "Takvim", "add_calendar_event": "Takvime ekleme",
    "delete_calendar_event": "Takvimden silme", "get_reminders": "Anımsatıcılar", "add_reminder": "Anımsatıcı ekleme",
    "browser_control": "Tarayıcı", "shell_run": "PowerShell", "toggle_webcam": "Kamera", "play_media": "Müzik/video",
    "set_volume": "Ses ayarı", "control_media": "Medya kontrolü", "analyze_screen": "Ekran okuma", "web_search": "İnternet araması",
    "send_whatsapp_message": "WhatsApp", "send_discord_message": "Discord", "send_email": "E-posta", "open_mail": "Gelen kutusu", "open_app": "Uygulama açma",
    "list_files": "Dosya listesi", "set_location": "Konum", "timer_set": "Zamanlayıcı", "stopwatch": "Kronometre",
    "note_add": "Not ekleme", "note_delete": "Not silme", "notes_list": "Notlar", "save_memory": "Hafıza", "desktop_action": "Masaüstü komutu",
    "app_window": "Pencere komutu", "window_control": "Pencere denetimi", "connect_gmail": "Gmail bağlantısı", "sys_info": "Sistem bilgisi",
}


def tool_label(name: str) -> str:
    return TOOL_LABELS.get(name, "Bir işlem")
