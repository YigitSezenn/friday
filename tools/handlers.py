"""Arac isleyicileri: her arac adi tek bir kucuk fonksiyona baglanir.

Ortak imza: handler(args, ctx) -> str. `ctx` webcam ve arayuz nesnesini tasir.
Ag, dosya ve Windows bagimliliklari ilk kullanimda iceri alinir.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ToolContext:
    webcam: Any = None
    ui: Any = None


Handler = Callable[[dict, ToolContext], str]
HANDLERS: dict[str, Handler] = {}


def tool(name: str) -> Callable[[Handler], Handler]:
    def register(func: Handler) -> Handler:
        HANDLERS[name] = func
        return func

    return register


def as_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def as_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def text(args: dict, key: str, default: str = "") -> str:
    return str(args.get(key, default))


@tool("save_memory")
def save_memory(args, ctx):
    from jarvis.memory_store import update_memory

    category = str(args.get("category") or "notes").strip() or "notes"
    key = str(args.get("key") or "").strip()
    value = str(args.get("value") or "").strip()
    if not key or not value:
        return "Hafızaya yazılamadı: başlık ve değer dolu olmalı."
    update_memory({category: {key: {"value": value}}})
    return f"Hafızaya kaydedildi: {category}/{key} = {value}"


@tool("delete_memory")
def delete_memory(args, ctx):
    from jarvis.memory_store import delete_memory as remove

    return remove(args.get("category", ""), args.get("key", ""), args.get("match_text", ""))


@tool("open_app")
def open_app(args, ctx):
    from tools.actions.apps import open_app as run

    return run(text(args, "app_name"))


@tool("sys_info")
def sys_info(args, ctx):
    from tools.actions.system import sys_info as run

    if ctx.ui:
        query = text(args, "query").lower()
        ctx.ui.focus_panel("time" if query in {"time", "saat", "date", "tarih"} else "system")
    return run(text(args, "query", "all"))


@tool("get_weather")
def get_weather(args, ctx):
    from tools.actions.weather import get_weather_summary

    if ctx.ui:
        ctx.ui.focus_panel("weather")
    return get_weather_summary(args.get("location") or None)


@tool("get_calendar_events")
def get_calendar_events(args, ctx):
    from tools.actions.calendar import get_calendar_events as run

    return run(text(args, "query", "today"), as_int(args.get("limit", 6), 6))


@tool("add_calendar_event")
def add_calendar_event(args, ctx):
    from tools.actions.calendar import add_calendar_event as run

    return run(
        text(args, "title"),
        text(args, "start_iso"),
        text(args, "end_iso"),
        text(args, "notes"),
        text(args, "location"),
        text(args, "calendar_name"),
        bool(args.get("all_day", False)),
    )


@tool("delete_calendar_event")
def delete_calendar_event(args, ctx):
    from tools.actions.calendar import delete_calendar_event as run

    return run(
        text(args, "title"),
        text(args, "start_iso"),
        text(args, "calendar_name"),
        bool(args.get("delete_all_matches", False)),
    )


@tool("get_reminders")
def get_reminders(args, ctx):
    from tools.actions.reminders import get_reminders as run

    return run(text(args, "query", "upcoming"), as_int(args.get("limit", 8), 8), text(args, "list_name"))


@tool("add_reminder")
def add_reminder(args, ctx):
    from tools.actions.reminders import add_reminder as run

    return run(
        text(args, "title"),
        text(args, "due_iso"),
        text(args, "notes"),
        text(args, "list_name"),
        text(args, "priority"),
        bool(args.get("all_day", False)),
        as_float(args.get("after_minutes")),
    )


@tool("complete_reminder")
def complete_reminder(args, ctx):
    from tools.actions.reminders import complete_reminder as run

    return run(text(args, "title"), text(args, "id"))


@tool("delete_reminder")
def delete_reminder(args, ctx):
    from tools.actions.reminders import delete_reminder as run

    return run(text(args, "title"), text(args, "id"))


@tool("browser_control")
def browser_control(args, ctx):
    from tools.actions.browser import browser_control as run

    return run(args.get("action"), args.get("url"), args.get("query"))


@tool("shell_run")
def shell_run(args, ctx):
    from tools.actions.shell import shell_run as run

    return run(text(args, "command"), confirm_run=bool(args.get("confirm", False)), visible=bool(args.get("visible", False)))


STOP_WORDS = {"stop", "off", "close", "kapat", "kapa", "kapali", "kapalı", "durdur", "disable"}


@tool("toggle_webcam")
def toggle_webcam(args, ctx):
    action = text(args, "action", "start").strip().lower()
    if ctx.webcam is None:
        return "Kamera bu oturumda kullanılamıyor."
    if action not in STOP_WORDS:  # "start", "aç", "open", "on"… hepsi açma sayılır; yalnızca açık kapatma sözcükleri kapatır
        status = ctx.webcam.start()
        if ctx.ui:
            ctx.ui.set_webcam_active(status in {"ok", "already_active"})
        if status == "ok":
            return "Kamera açıldı. Artık görüntünü görebiliyorum."
        if status == "already_active":
            return "Kamera zaten açık, görüntü alıyorum."
        return "Kamera açılamadı."
    ctx.webcam.stop()
    if ctx.ui:
        ctx.ui.set_webcam_active(False)
    return "Kamera kapatıldı."


def _ui_or_none(ctx):
    ui = ctx.ui
    return ui if ui is not None and hasattr(ui, "_call") else None


@tool("notes_list")
def notes_list(args, ctx):
    from jarvis import notes

    lines = notes.load()
    if not lines:
        return "Hiç not yok."
    return "Notlar:\n" + "\n".join(f"{i}. {line}" for i, line in enumerate(lines, 1))


@tool("note_add")
def note_add(args, ctx):
    from jarvis import notes

    note = text(args, "text")
    if not note.strip():
        return "Not metni boş."
    lines = notes.add(note)
    if (ui := _ui_or_none(ctx)) is not None:
        ui._call("notes", lines)
    return f"Not eklendi ({len(lines)}. not): {lines[-1]}"


@tool("note_delete")
def note_delete(args, ctx):
    from jarvis import notes

    lines, removed = notes.remove(text(args, "target"))
    if removed is None:
        return "Silinecek not bulunamadı. Numarasını ya da içinden bir kelimeyi söyle."
    if (ui := _ui_or_none(ctx)) is not None:
        ui._call("notes", lines)
    return f"Not silindi: {removed}"


@tool("note_edit")
def note_edit(args, ctx):
    from jarvis import notes

    lines, old = notes.edit(text(args, "target"), text(args, "text"))
    if old is None:
        return "Düzenlenecek not bulunamadı ya da yeni metin boş."
    if (ui := _ui_or_none(ctx)) is not None:
        ui._call("notes", lines)
    return f"Not güncellendi: '{old}' -> '{text(args, 'text').strip()}'"


@tool("timer_set")
def timer_set(args, ctx):
    from jarvis.timer import clock, parse_seconds

    ui = _ui_or_none(ctx)
    seconds = parse_seconds(args.get("minutes"), args.get("seconds"))
    if ui is None:
        return "Zamanlayıcı şu an kullanılamıyor."
    if seconds <= 0:
        return "Süre belirtilmedi."
    ui.timer_set(seconds, text(args, "label"))
    return f"Zamanlayıcı kuruldu: {clock(seconds)}" + (f" ({text(args, 'label')})" if text(args, "label") else "") + "."


@tool("timer_add")
def timer_add(args, ctx):
    import time as _time

    from jarvis.timer import clock, parse_seconds

    ui = _ui_or_none(ctx)
    seconds = parse_seconds(args.get("minutes"), args.get("seconds"))
    if ui is None:
        return "Zamanlayıcı şu an kullanılamıyor."
    if seconds == 0:
        return "Eklenecek süre belirtilmedi."
    running = ui.timer_add(seconds)
    left = ui.timer.remaining(_time.time())
    return (f"Sureye eklendi; kalan {clock(left)}." if running else f"Çalışan zamanlayıcı yoktu; {clock(left)} yeni zamanlayıcı kuruldu.")


@tool("timer_cancel")
def timer_cancel(args, ctx):
    ui = _ui_or_none(ctx)
    if ui is None:
        return "Zamanlayıcı şu an kullanılamıyor."
    return "Zamanlayıcı iptal edildi." if ui.timer_cancel() else "Çalışan zamanlayıcı yok."


@tool("timer_status")
def timer_status(args, ctx):
    import time as _time

    from jarvis.timer import clock, spoken

    ui = _ui_or_none(ctx)
    if ui is None:
        return "Zamanlayıcı şu an kullanılamıyor."
    now = _time.time()
    left = ui.timer.remaining(now)
    parts = [f"Zamanlayicida {spoken(left)} kaldı ({clock(left)})." if left else "Çalışan zamanlayıcı yok."]
    watched = ui.timer.elapsed(now)
    if watched:
        parts.append(f"Kronometre {clock(int(watched))}" + (" (çalışıyor)." if ui.timer.watch_running else " (durdu)."))
    return " ".join(parts)


@tool("stopwatch")
def stopwatch(args, ctx):
    from jarvis.timer import clock

    ui = _ui_or_none(ctx)
    if ui is None:
        return "Kronometre şu an kullanılamıyor."
    action = text(args, "action", "toggle")
    elapsed = ui.timer_watch(action)
    state = "çalışıyor" if ui.timer.watch_running else "durdu"
    return f"Kronometre {state}: {clock(int(elapsed))}."


@tool("sleep_mode")
def sleep_mode(args, ctx):
    asleep = bool(args.get("asleep", True))
    ui = ctx.ui
    if ui is None or not hasattr(ui, "_js"):
        return "Uyku modu şu an kullanılamıyor."
    if asleep:
        # Model "cevap alamadım" diye kendi kendine uyutmasın: kullanıcı gerçekten istemiş olmalı.
        from jarvis.intents import is_sleep
        from tools.actions.confirm import recent_said

        if not any(is_sleep(t) for t in recent_said()):
            return "Uyku modu yalnızca kullanıcı isterse açılır. Kullanıcı istemedi; uyumadan dinlemeye devam et, cevap gelmediyse sessiz kal."
    # Kısa gecikme: önce vedalaşma cümlesi söylenir, sonra mikrofon uykuya geçer.
    ui._js(f"window.hud && window.hud.sleep({'true' if asleep else 'false'}, {2500 if asleep else 0})")
    if asleep:
        from jarvis.shown import with_note

        return with_note("Uyku moduna geçiyorum. Uyandırmak için çekirdeğe tıkla, F4'e bas ya da bir şey yaz.", "Kullanıcıya kısa bir veda et; uyandırmak için çekirdeğe tıklamasını, F4'e basmasını ya da bir şey yazmasını söyle.")
    return "Uyandım."


@tool("app_window")
def app_window(args, ctx):
    import threading

    ui = _ui_or_none(ctx)
    if ui is None:
        return "Pencere komutu şu an kullanılamıyor."
    action = text(args, "action").lower()
    if action in {"minimize", "kucult", "küçült", "kucul", "küçül"}:
        threading.Timer(1.5, ui.minimize_to_taskbar).start()
        from jarvis.shown import with_note

        return with_note("Pencere küçültülüyor.", "Kısa bir onay söyle.")
    if action in {"close", "quit", "kapat", "kapan"}:
        threading.Timer(3.5, ui.quit_app).start()
        from jarvis.shown import with_note

        return with_note("FRIDAY kapanıyor.", "Kullanıcıya kısa bir veda et.")
    if action in {"restore", "show", "ac", "aç", "geri"}:
        ui.restore_from_taskbar()
        return "Pencere geri getirildi."
    return "Bilinmeyen pencere komutu: minimize, close ya da restore."


@tool("file_access")
def file_access(args, ctx):
    from tools.actions.fileaccess import run

    return run(text(args, "action"), text(args, "path"), text(args, "destination"), text(args, "content"), text(args, "query"), bool(args.get("confirm", False)), int(args.get("older_than_days") or 0))


@tool("home_control")
def home_control(args, ctx):
    from tools.actions.home import run

    return run(text(args, "action"), text(args, "device"), text(args, "command"), text(args, "host"))


@tool("desktop_action")
def desktop_action(args, ctx):
    from tools.actions.desktop import run

    return run(text(args, "action"))


@tool("set_volume")
def set_volume(args, ctx):
    from tools.actions.volume import set_volume as run

    mute = args.get("mute")
    return run(text(args, "target", "spotify"), args.get("level"), args.get("change"), None if mute is None else bool(mute))


@tool("play_media")
def play_media(args, ctx):
    from tools.actions.media import play_media as run

    return run(text(args, "query"), text(args, "provider", "auto"), bool(args.get("autoplay", True)))


@tool("control_media")
def control_media(args, ctx):
    from tools.actions.media import control_media as run

    return run(text(args, "action", "pause"))


@tool("get_youtube_channel_report")
def get_youtube_channel_report(args, ctx):
    from tools.actions.youtube import get_youtube_channel_report as run

    return run(text(args, "query", "overview"), text(args, "handle"), as_int(args.get("video_limit", 6), 6))


@tool("analyze_screen")
def analyze_screen(args, ctx):
    from tools.actions.screen import analyze_screen as run

    return run(text(args, "query", "Ekranda ne var?"), text(args, "target", "active_window"))


@tool("send_whatsapp_message")
def send_whatsapp_message(args, ctx):
    from tools.actions.whatsapp import send_whatsapp_message as run

    return run(
        text(args, "message"),
        text(args, "phone_number"),
        text(args, "recipient_name"),
        bool(args.get("send_now", False)),
        text(args, "app_target", "auto"),
        bool(args.get("confirm", False)),
    )


@tool("send_email")
def send_email(args, ctx):
    from tools.actions.mail import send_email as run

    return run(text(args, "to"), text(args, "subject"), text(args, "body"), text(args, "recipient_name"), bool(args.get("confirm", False)), text(args, "provider", "auto"))


@tool("save_email_contact")
def save_email_contact(args, ctx):
    from tools.actions.mail import save_email_contact as run

    return run(text(args, "display_name"), text(args, "email"), text(args, "aliases"))


@tool("connect_gmail")
def connect_gmail(args, ctx):
    from tools.actions.mail import connect_gmail as run

    return run()


@tool("open_mail")
def open_mail(args, ctx):
    from tools.actions.mail import open_mail as run

    return run(text(args, "provider", "auto"))


@tool("send_discord_message")
def send_discord_message(args, ctx):
    from tools.actions.discord import send_discord_message as run

    return run(text(args, "message"), text(args, "recipient_name"), text(args, "username"), bool(args.get("confirm", False)))


@tool("hand_control")
def hand_control(args, ctx):
    from tools.actions.handmove import hand_control as run

    return run(text(args, "action", "start").strip().lower(), bool(args.get("confirm", False)), ctx.webcam, ctx.ui)


@tool("save_whatsapp_contact")
def save_whatsapp_contact(args, ctx):
    from tools.actions.whatsapp import save_whatsapp_contact as run

    return run(text(args, "display_name"), text(args, "phone_number"), text(args, "aliases"))


@tool("web_search")
def web_search(args, ctx):
    from tools.actions.search import web_search as run

    return run(text(args, "query"))


@tool("list_files")
def list_files(args, ctx):
    from tools.actions.files import list_user_files

    return list_user_files(text(args, "folder", "desktop"))


@tool("set_location")
def set_location(args, ctx):
    from jarvis.config import save_app_config
    from tools.actions.weather import clear_detected_city

    if bool(args.get("auto", False)):
        save_app_config({"weather_location": ""})
        clear_detected_city()
        if ctx.ui and hasattr(ctx.ui, "refresh_weather"):
            ctx.ui.refresh_weather()
        return "Konum otomatik yapıldı; internet bağlantından yeniden bulunacak."
    place = " ".join(text(args, "location").split())
    if not place or len(place) > 80:
        return "Konum geçersiz: şehir ya da semt adı söyle."
    save_app_config({"weather_location": place})
    clear_detected_city()
    if ctx.ui:
        if hasattr(ctx.ui, "refresh_weather"):
            ctx.ui.refresh_weather()
        ctx.ui.focus_panel("weather")
    return f"Konum kalıcı olarak {place} yapıldı. Hava ve harita oraya geçti."
