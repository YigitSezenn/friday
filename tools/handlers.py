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


def text(args: dict, key: str, default: str = "") -> str:
    return str(args.get(key, default))


@tool("save_memory")
def save_memory(args, ctx):
    from jarvis.memory_store import update_memory

    category = str(args.get("category") or "notes").strip() or "notes"
    key = str(args.get("key") or "").strip()
    value = str(args.get("value") or "").strip()
    if not key or not value:
        return "Hafizaya yazilamadi: key ve value dolu olmali."
    update_memory({category: {key: {"value": value}}})
    return f"Hafizaya kaydedildi: {category}/{key} = {value}"


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

    return run(text(args, "command"))


@tool("toggle_webcam")
def toggle_webcam(args, ctx):
    action = text(args, "action", "start").strip().lower()
    if ctx.webcam is None:
        return "Webcam bu oturumda kullanilamiyor."
    if action == "start":
        status = ctx.webcam.start()
        if ctx.ui:
            ctx.ui.set_webcam_active(status in {"ok", "already_active"})
        if status == "ok":
            return "Webcam akisi baslatildi. Artik kamerani goruyorum."
        if status == "already_active":
            return "Webcam zaten acik, goruntu aliyorum."
        return "Webcam baslatilamadi."
    ctx.webcam.stop()
    if ctx.ui:
        ctx.ui.set_webcam_active(False)
    return "Webcam akisi durduruldu."


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
        return "Konum otomatik yapildi; internet baglantindan yeniden bulunacak."
    place = " ".join(text(args, "location").split())
    if not place or len(place) > 80:
        return "Konum gecersiz: sehir ya da semt adi soyle."
    save_app_config({"weather_location": place})
    clear_detected_city()
    if ctx.ui:
        ctx.ui.focus_panel("weather")
    return f"Konum kalici olarak {place} yapildi. Hava ve harita oraya gecti."
