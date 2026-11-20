"""HUD'dan (JavaScript) gelen istekler: her tür için küçük bir işleyici."""

from __future__ import annotations

from jarvis.config import load_app_config, save_app_config
from jarvis.paths import data_root


def _on_command(ui, payload: dict) -> None:
    from jarvis.textfix import repair_text

    text = payload.get("text")
    text = repair_text(str(text)).strip() if text is not None else ""
    if text and ui.on_text_command:
        ui.on_text_command(text)


def _on_mute(ui, payload: dict) -> None:
    ui.muted = bool(payload.get("muted"))


def _on_camera(ui, payload: dict) -> None:
    ui._cam = bool(payload.get("on"))
    if ui.on_webcam_toggle:
        ui.on_webcam_toggle(ui._cam)


def _on_settings(ui, payload: dict) -> None:
    saved = save_app_config(dict(payload.get("values") or {}))
    if "start_with_windows" in (payload.get("values") or {}):
        from jarvis.startup import apply_windows_startup

        apply_windows_startup(bool(saved.get("start_with_windows")))
    ui.effects = bool(load_app_config().get("effects", True))
    ui.music = bool(load_app_config().get("music", False))
    ui.sync_music()
    ui.push_settings()
    ui.write_log("SYS: Ayarlar kaydedildi. Ses karakteri yeniden bağlanıyor.")
    if ui.on_settings_saved:
        ui.on_settings_saved()
    from jarvis.config import has_gemini_api_key

    if has_gemini_api_key() and ui.phone_opener:
        ui.phone_opener()


def _on_sleep(ui, payload: dict) -> None:
    asleep = bool(payload.get("asleep"))
    ui.paused = asleep
    if ui.on_pause_toggle:
        ui.on_pause_toggle(asleep)


def _on_forget(ui, payload: dict) -> None:
    from jarvis.memory_store import delete_memory

    delete_memory(category=str(payload.get("category") or ""), key=str(payload.get("key") or ""))
    ui.push_settings()


def _on_phone(ui, payload: dict) -> None:
    url = ""
    if ui.phone_opener:
        url = ui.phone_opener() or ""
    ui._call("phone", _phone_payload(url))


def _on_phone_rotate(ui, payload: dict) -> None:
    from jarvis.phone_server import phone_status, rotate_phone_token

    rotate_phone_token()
    ui._call("phone", _phone_payload(str(phone_status().get("url") or "")))


def _on_story(ui, payload: dict) -> None:
    from jarvis.story import choose, view

    ending = str(payload.get("ending") or "")
    if ending:
        ui.write_log("SYS: " + choose(ending))
    ui._call("story", view())


def _on_note(ui, payload: dict) -> None:
    from jarvis import notes

    notes.save(payload.get("lines") or [])


def _on_note_delete(ui, payload: dict) -> None:
    from jarvis import notes

    lines, _removed = notes.remove(str(int(payload.get("index", -1)) + 1))
    ui._call("notes", lines)


def _on_note_edit(ui, payload: dict) -> None:
    from jarvis import notes

    lines, _old = notes.edit(str(int(payload.get("index", -1)) + 1), str(payload.get("text") or ""))
    ui._call("notes", lines)


def _on_timer(ui, payload: dict) -> None:
    action = str(payload.get("action") or "")
    seconds = int(payload.get("seconds") or 0)
    if action == "set":
        ui.timer_set(seconds, str(payload.get("label") or ""))
    elif action == "add":
        ui.timer_add(seconds)
    elif action == "cancel":
        ui.timer_cancel()
    elif action == "watch":
        ui.timer_watch(str(payload.get("watch") or "toggle"))
    elif action == "dismiss":
        from jarvis import sounds

        sounds.stop("alarm")


def _on_beep(ui, payload: dict) -> None:
    ui.play_success_sfx()


def _on_minimize(ui, payload: dict) -> None:
    ui.minimize_to_taskbar()


def _on_update(ui, payload: dict) -> None:
    ui.install_update()


def _on_gate_refresh(ui, payload: dict) -> None:
    if payload.get("rotate"):
        from jarvis.gate_client import rotate_gate_key

        rotate_gate_key()
        ui.write_log("SYS: Yeni telefon anahtarı oluşturuldu. Telefonda QR'ı yeniden okut.")
    ui.push_settings()


def _on_quit(ui, payload: dict) -> None:
    ui.quit_app()


def _on_uninstall(ui, payload: dict) -> None:
    ui.request_uninstall()


def _on_open_data(ui, payload: dict) -> None:
    import os

    os.startfile(data_root())  # type: ignore[attr-defined]


def _on_permissions(ui, payload: dict) -> None:
    from jarvis.permissions import snapshot

    ui._call("permissions", snapshot())


def _on_open_privacy(ui, payload: dict) -> None:
    import os

    from jarvis.permissions import settings_uri

    uri = settings_uri(str(payload.get("kind") or ""))
    if uri:
        os.startfile(uri)  # type: ignore[attr-defined]


def _on_copy(ui, payload: dict) -> None:
    _copy_text(str(payload.get("text") or ""))


def _on_mail_test(ui, payload: dict) -> None:
    import threading

    def run() -> None:
        from tools.actions.mail import smtp_test

        result = smtp_test(str(payload.get("address") or ""), str(payload.get("password") or ""))
        ui.write_log(("SYS: " if "gönderildi" in result else "ERR: ") + result)
        ui._call("mailTest", result)

    threading.Thread(target=run, name="friday-mail-test", daemon=True).start()


def _on_open(ui, payload: dict) -> None:
    _open_allowed(str(payload.get("url") or ""))


def _on_reminder(ui, payload: dict) -> None:
    action = str(payload.get("action") or "")
    title = str(payload.get("title") or "")
    reminder_id = str(payload.get("id") or "")
    from tools.actions.reminders import complete_reminder, delete_reminder

    if action == "complete":
        ui.write_log("SYS: " + complete_reminder(title, reminder_id))
    elif action == "delete":
        ui.write_log("SYS: " + delete_reminder(title, reminder_id))
    ui._push_agenda()


HANDLERS = {
    "command": _on_command,
    "mute": _on_mute,
    "camera": _on_camera,
    "settings": _on_settings,
    "sleep": _on_sleep,
    "forget": _on_forget,
    "phone": _on_phone,
    "phone_rotate": _on_phone_rotate,
    "story": _on_story,
    "note": _on_note,
    "note_delete": _on_note_delete,
    "note_edit": _on_note_edit,
    "timer": _on_timer,
    "beep": _on_beep,
    "minimize": _on_minimize,
    "update": _on_update,
    "gate_refresh": _on_gate_refresh,
    "quit": _on_quit,
    "uninstall": _on_uninstall,
    "open_data": _on_open_data,
    "permissions": _on_permissions,
    "open_privacy": _on_open_privacy,
    "copy": _on_copy,
    "open": _on_open,
    "mail_test": _on_mail_test,
    "reminder": _on_reminder,
}


def dispatch(ui, kind: str, payload: dict) -> dict:
    handler = HANDLERS.get(kind)
    if handler is None:
        return {"ok": False, "error": f"bilinmeyen istek: {kind}"}
    handler(ui, payload)
    return {"ok": True}


def _open_allowed(url: str) -> None:
    import webbrowser

    allowed = {
        "https://aistudio.google.com/apikey",
        "https://youtu.be/VZl5uBT4a60",
        "https://ai.studio/projects",
        "https://myaccount.google.com/apppasswords",
    }
    if url in allowed or url.startswith("https://aistudio.google.com/apikey"):
        webbrowser.open(url)


def _copy_text(text: str) -> None:
    from jarvis.win32 import set_clipboard

    set_clipboard(text)


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
