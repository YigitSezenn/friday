from __future__ import annotations

import asyncio
import ctypes
import sys
import threading
import traceback

from jarvis import __version__
from jarvis.config import has_gemini_api_key
from jarvis.paths import data_path


def run_selftest() -> int:
    lines = [f"J.A.R.V.I.S yeniden kurulum tanisi {__version__}", ""]
    ok = bad = 0

    def check(label: str, fn) -> None:
        nonlocal ok, bad
        try:
            detail = fn()
            lines.append(f"  [OK]   {label}" + (f" — {detail}" if detail else ""))
            ok += 1
        except Exception as exc:
            lines.append(f"  [HATA] {label} — {type(exc).__name__}: {exc}")
            bad += 1

    lines.append("Moduller:")
    for module_name in ("psutil", "PIL.Image", "requests", "google.genai", "cv2", "pyaudio", "mss"):
        check(module_name, lambda name=module_name: __import__(name) and "")

    lines.append("\nCekirdek:")
    check("prompt", lambda: "Windows" if "Windows" in __import__("jarvis.prompt", fromlist=["load_system_prompt"]).load_system_prompt() else (_ for _ in ()).throw(RuntimeError("Windows notu yok")))
    check("ayar yazma", _write_probe)
    check("API anahtari", lambda: "var" if has_gemini_api_key() else "yok (uygulamadan gir)")
    check("sistem", lambda: __import__("jarvis.actions.system", fromlist=["sys_info"]).sys_info("time"))
    check("takvim", lambda: __import__("jarvis.actions.calendar", fromlist=["get_calendar_events"]).get_calendar_events("today"))
    check("powershell", lambda: __import__("jarvis.actions.shell", fromlist=["shell_run"]).shell_run("Write-Output tamam"))

    lines.append(f"\nSONUC: {ok} basarili, {bad} hatali")
    report = "\n".join(lines)
    print(report)
    try:
        data_path("jarvis_tani.log").write_text(report, encoding="utf-8")
    except OSError:
        pass
    return 1 if bad else 0


def _write_probe() -> str:
    path = data_path("config", ".probe")
    path.write_text("ok", encoding="utf-8")
    path.unlink()
    return str(path.parent)


def smoke_ui() -> int:
    from ui.bridge import JarvisUI

    ui = JarvisUI()
    ui.root.withdraw()
    ui.set_state("LISTENING")
    ui.write_log("SYS: Arayuz duman testi.")
    ui.root.update_idletasks()
    ui.root.update()
    ui.root.destroy()
    print("Arayuz olusturuldu ve kapatildi.")
    return 0


def _acquire_single_instance() -> bool:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = kernel.CreateMutexW(None, False, "Local\\JarvisRebuildSingleInstance")
    if ctypes.get_last_error() == 183:
        return False
    globals()["_mutex"] = handle
    return True


def _proactive_loop(ui, live_box: dict) -> None:
    import time

    from jarvis.config import load_app_config
    from jarvis.proactive import due_nudges

    state = {"heard": time.time(), "water": time.time(), "break": time.time(), "silence": 0, "event": 0}
    while not ui._closed:
        time.sleep(30)
        state["heard"] = getattr(ui, "last_heard", state["heard"])
        try:
            notes = due_nudges(time.time(), state, load_app_config(), paused=bool(ui.paused or ui.muted))
        except Exception:
            continue
        live = live_box.get("live")
        for note in notes:
            if live:
                live.nudge(note)


def _note_launch() -> None:
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FRIDAY.Rebuild")
    except Exception:
        pass
    try:
        path = data_path("launch.log")

        def hook(exc_type, exc, tb) -> None:
            path.write_text("".join(traceback.format_exception(exc_type, exc, tb)), encoding="utf-8")

        sys.excepthook = hook
        path.write_text("acildi\n", encoding="utf-8")
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return run_selftest()
    if "--smoke-ui" in argv:
        return smoke_ui()
    _note_launch()
    if not _acquire_single_instance():
        print("JARVIS zaten calisiyor.")
        return 0

    from jarvis.live import JarvisLive
    from jarvis.phone_server import start_phone_server
    from ui.bridge import JarvisUI

    ui = JarvisUI()
    live_box: dict = {}

    def open_phone() -> None:
        def send(text: str) -> None:
            command = live_box.get("command")
            if command:
                command(text)
            else:
                ui.write_log("ERR: Telefon komutu icin baglanti henuz hazir degil.")

        try:
            url = start_phone_server(send, lan=True)
        except OSError as exc:
            ui.write_log(f"ERR: Telefon sunucusu acilamadi. ({exc})")
            return ""
        ui.write_log("SYS: Telefon ayni Wi-Fi icin hazir. QR Ayarlar icinde, paylasma.")
        try:
            from jarvis.story import note_phone

            note_phone()
        except Exception:
            pass
        return url

    ui.phone_opener = open_phone
    from jarvis.config import load_app_config

    if has_gemini_api_key() or load_app_config().get("phone_autostart"):
        threading.Thread(target=open_phone, name="jarvis-phone", daemon=True).start()

    def runner() -> None:
        live = JarvisLive(ui)
        live_box["live"] = live
        live_box["command"] = live._on_text_command
        try:
            asyncio.run(live.run())
        except Exception:
            traceback.print_exc()

    threading.Thread(target=runner, name="jarvis-live", daemon=True).start()
    threading.Thread(target=lambda: _proactive_loop(ui, live_box), name="jarvis-proactive", daemon=True).start()
    ui.root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
