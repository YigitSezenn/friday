import datetime as dt
import os
import tempfile
import unittest
from pathlib import Path


class JarvisTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["JARVIS_DATA_DIR"] = self._tmp.name
        os.environ["JARVIS_CALENDAR_BACKEND"] = "local"
        from jarvis import config as config_module

        self.addCleanup(self._tmp.cleanup)

    def test_config_roundtrip_and_bad_voice(self):
        from jarvis.config import load_app_config, save_app_config

        saved = save_app_config({"voice": "Nope", "weather_location": "Ankara", "gemini_api_key": "test-key"})
        self.assertEqual(saved["voice"], "Charon")
        self.assertEqual(load_app_config()["weather_location"], "Ankara")

    def test_corrupt_config_does_not_crash(self):
        from jarvis.config import config_path, load_app_config

        path = config_path()
        path.write_text("{bozuk", encoding="utf-8")
        config = load_app_config()
        self.assertIn("_config_error", config)
        self.assertEqual(config["voice"], "Charon")

    def test_memory_save_and_delete(self):
        from jarvis.memory_store import delete_memory, format_memory_for_prompt, load_memory, update_memory

        update_memory({"identity": {"name": {"value": "Alp"}}})
        self.assertIn("Alp", format_memory_for_prompt(load_memory()))
        message = delete_memory(match_text="alp")
        self.assertIn("kaldirildi", message)
        self.assertEqual(format_memory_for_prompt(load_memory()), "")
        self.assertIn("yok", delete_memory(category="identity", key="name").lower() + delete_memory())

    def test_shell_blocks_destructive_commands(self):
        from jarvis.actions.shell import shell_run

        blocked = shell_run("Remove-Item -Recurse C:\\")
        self.assertIn("Guvenlik", blocked)
        self.assertIn("Guvenlik", shell_run("del C:\\Windows\\notepad.exe"))
        self.assertIn("belirtilmedi", shell_run("   ").lower())

    def test_shell_runs_safe_command(self):
        from jarvis.actions.shell import shell_run

        self.assertEqual(shell_run("Write-Output tamam"), "tamam")

    def test_calendar_and_reminder_roundtrip(self):
        from jarvis.actions.calendar import add_calendar_event, delete_calendar_event, get_calendar_events
        from jarvis.actions.reminders import add_reminder, get_reminders

        self.assertIn("gorunmuyor", get_calendar_events("today"))
        when = (dt.datetime.now() + dt.timedelta(days=2)).replace(hour=15, minute=0, second=0, microsecond=0)
        added = add_calendar_event("Disci", when.strftime("%Y-%m-%dT%H:%M"))
        self.assertIn("Takvime eklendi", added)
        self.assertIn("Disci", get_calendar_events("30 gun"))
        ambiguous = add_calendar_event("Toplanti", "2099-03-01T10:00")
        add_calendar_event("Toplanti", "2099-03-02T10:00")
        self.assertIn("eslesen", delete_calendar_event("Toplanti").lower())
        self.assertIn("silindi", delete_calendar_event("Toplanti", delete_all_matches=True).lower())
        self.assertIn("eklendi", add_reminder("Sut al", "2099-04-01T09:00").lower())
        self.assertIn("Sut al", get_reminders("all"))
        self.assertTrue(ambiguous)

    def test_prompt_is_windows(self):
        from jarvis.prompt import load_system_prompt

        prompt = load_system_prompt()
        self.assertIn("Windows'ta çalışan", prompt)
        self.assertIn("PowerShell", prompt)
        self.assertNotIn("ls ~/Desktop", prompt)

    def test_persona_name_address_and_color(self):
        from jarvis.config import address_phrase, load_app_config, persona_palette, save_app_config
        from jarvis.prompt import load_system_prompt

        saved = save_app_config({"assistant_name": "  Cuma\n", "address_as": "komutanım", "ui_color": "nope"})
        self.assertEqual(saved["assistant_name"], "Cuma")
        self.assertEqual(saved["address_as"], "komutanım")
        self.assertEqual(saved["ui_color"], "gold")
        self.assertEqual(address_phrase(saved), "komutanım")
        saved = save_app_config({"ui_color": "cyan", "assistant_name": "X" * 40, "address_as": ""})
        self.assertEqual(saved["ui_color"], "cyan")
        self.assertEqual(saved["assistant_name"], "X" * 24)
        self.assertEqual(saved["address_as"], "adınla")
        self.assertEqual(address_phrase(load_app_config()), "X" * 24)
        self.assertEqual(persona_palette()["c"], "#5ed8ff")
        prompt = load_system_prompt()
        self.assertIn("X" * 24, prompt)
        self.assertIn("hitap", prompt)

    def test_voice_volume_panels_and_phone_address(self):
        from jarvis.config import save_app_config
        from jarvis.phone_server import phone_url

        saved = save_app_config({"voice": "Puck", "voice_volume": 999, "panels_off": ["map", "yok"], "effects": False})
        self.assertEqual(saved["voice"], "Puck")
        self.assertEqual(saved["voice_volume"], 150)
        self.assertEqual(saved["panels_off"], ["map"])
        self.assertFalse(saved["effects"])
        save_app_config({"web_remote_access": False})
        self.assertIn("127.0.0.1:8766", phone_url())
        self.assertIn("token=", phone_url())

    def test_whatsapp_contact_lookup(self):
        from jarvis.actions.whatsapp import find_contact, normalize_phone, save_whatsapp_contact

        self.assertEqual(normalize_phone("0555 111 22 33"), "905551112233")
        self.assertIn("kaydedildi", save_whatsapp_contact("Annem", "05551112233", "anne").lower())
        found = find_contact("anne")
        self.assertIsNotNone(found)
        self.assertIn("905551112233", found["value"])
        with self.assertRaises(ValueError):
            normalize_phone("12")

    def test_tool_dispatch_and_unknown(self):
        from jarvis.tools import execute_tool

        saved = execute_tool("save_memory", {"category": "notes", "key": "renk", "value": "mavi"})
        self.assertIn("mavi", saved)
        self.assertIn("dolu olmali", execute_tool("save_memory", {"category": "notes"}))
        self.assertIn("Bilinmeyen", execute_tool("yok", {}))
        self.assertIn("yalnizca aktif pencere", execute_tool("analyze_screen", {"target": "desktop"}))
        self.assertIn("YouTube API", execute_tool("get_youtube_channel_report", {}))

    def test_weather_summary_parser(self):
        from jarvis.actions.weather import summarize_weather_payload

        text = summarize_weather_payload(
            {
                "nearest_area": [{"areaName": [{"value": "Kucukpazar"}], "region": [{"value": "Istanbul"}]}],
                "current_condition": [{
                    "temp_C": "18",
                    "FeelsLikeC": "17",
                    "humidity": "60",
                    "weatherDesc": [{"value": "Cloudy"}],
                }],
            },
            target="",
        )
        self.assertIn("Istanbul", text)
        self.assertIn("18 derece", text)
        self.assertIn("nem", text)
        from jarvis.actions.weather import weather_card

        card = weather_card(
            {
                "nearest_area": [{"areaName": [{"value": "Kepez"}], "region": [{"value": "Antalya"}]}],
                "current_condition": [{
                    "temp_C": "22",
                    "FeelsLikeC": "21",
                    "humidity": "55",
                    "windspeedKmph": "14",
                    "winddir16Point": "N",
                    "winddirDegree": "10",
                    "pressure": "1016",
                    "visibility": "10",
                    "uvIndex": "5",
                    "cloudcover": "20",
                    "precipMM": "0.0",
                    "weatherDesc": [{"value": "Sunny"}],
                }],
                "weather": [{"date": "2026-11-13", "maxtempC": "24", "mintempC": "16", "hourly": [{"weatherDesc": [{"value": "Sunny"}], "chanceofrain": "0"}], "astronomy": [{"sunrise": "07:12 AM", "sunset": "05:48 PM"}]}],
            },
            target="Antalya",
        )
        self.assertEqual(card["place"], "Antalya")
        self.assertEqual(card["wind"], "14")
        self.assertEqual(card["high"], "24")
        self.assertEqual(card["sunrise"], "07:12 AM")
        self.assertEqual(card["windFrom"], "kuzey yönünden")
        self.assertEqual(card["uvLabel"], "orta")
        self.assertEqual(len(card["hours"]), 1)

    def test_gate_rejects_a_wrong_key_and_queues_a_command(self):
        from gate.logic import CommandQueue, key_matches

        self.assertFalse(key_matches("", "abc"))
        self.assertFalse(key_matches("dogru-anahtar", "yanlis"))
        self.assertTrue(key_matches("dogru-anahtar", "dogru-anahtar"))
        queue = CommandQueue()
        item = queue.push("bilgisayarda ac not defteri", "site")
        self.assertEqual(item["text"], "bilgisayarda ac not defteri")
        self.assertEqual(queue.take()[0]["source"], "site")
        self.assertEqual(queue.take(), [])

    def test_app_alias_without_launching(self):
        from jarvis.actions.apps import resolve_alias

        self.assertEqual(resolve_alias("hesap makinesi"), "Calculator")
        self.assertEqual(resolve_alias("not defteri"), "Notepad")
        self.assertEqual(resolve_alias("haritalar"), "Maps")
        self.assertEqual(resolve_alias("takvim"), "Calendar")

    def test_transcript_cleaner(self):
        from jarvis.live import clean_transcript

        text, noisy = clean_transcript("Merhaba <ctrl46>   dünya\x01")
        self.assertEqual(text, "Merhaba dünya")
        self.assertTrue(noisy)

    def test_turn_closes_after_silence(self):
        from jarvis.audio.turn import TurnGate

        gate = TurnGate(speech=0.02, silence_s=0.7)
        loud = b"\xff\x0f" * 160
        quiet = b"\x00\x00" * 160
        before, after = gate.feed(loud, 0.0)
        self.assertEqual(before, ["start"])
        self.assertEqual(after, [])
        before, after = gate.feed(quiet, 0.3)
        self.assertEqual((before, after), ([], []))
        before, after = gate.feed(quiet, 1.1)
        self.assertEqual(after, ["end"])
        self.assertFalse(gate.open)

    def test_command_body_is_urlencoded_and_refresh_stays_quiet(self):
        from urllib.parse import parse_qs, urlencode
        from pathlib import Path

        from jarvis.gate_client import ensure_gate_key, pair_code, rotate_gate_key

        body = urlencode({"key": "ornek", "text": "spotify aç"}).encode()
        parsed = {key: values[0] for key, values in parse_qs(body.decode("utf-8")).items()}
        self.assertEqual(parsed["text"], "spotify aç")
        self.assertNotIn("text", parse_qs(b'--bound\r\nContent-Disposition: form-data; name="text"\r\n\r\nspotify ac'.decode("utf-8")))
        root = Path(__file__).resolve().parents[1]
        script = (root / "site" / "src" / "main.js").read_text(encoding="utf-8")
        phone = (root / "phone-android" / "app" / "src" / "main" / "java" / "com" / "friday" / "phone" / "MainActivity.kt").read_text(encoding="utf-8")
        hud = (root / "ui" / "hud" / "index.html").read_text(encoding="utf-8")
        self.assertIn("URLSearchParams", script)
        self.assertNotIn("new FormData()", script)
        self.assertIn("ACTION_RECOGNIZE_SPEECH", phone)
        self.assertIn('id="pair-refresh"', hud)
        first = ensure_gate_key()
        second = rotate_gate_key()
        self.assertFalse(first == second)
        self.assertEqual(len(pair_code(second)), 6)
        self.assertTrue(pair_code(second).isdigit())

    def test_phone_number_chat_does_not_crash_or_duplicate(self):
        from jarvis.live import JarvisLive, repeated_typed_line
        from ui.bridge import HudBridge, script_for

        number = "0555 111 22 33"
        logs = []

        class UI:
            muted = False
            paused = False

            def write_log(self, text):
                logs.append(str(text))

        live = JarvisLive.__new__(JarvisLive)
        live.ui = UI()
        live._paused = False
        live._loop = None
        live.session = None
        live._typed = None
        live._on_text_command(number)
        live._on_text_command(905551112233)
        self.assertFalse(any(number in line or "905551112233" in line for line in logs))
        self.assertTrue(repeated_typed_line(number, number))
        self.assertFalse(repeated_typed_line(number, "yarin hava nasil"))

        bridge = HudBridge(UI())
        bridge.ui.on_text_command = live._on_text_command
        self.assertEqual(bridge.post("command", {"text": number}).get("ok"), True)
        self.assertEqual(bridge.post("command", {"text": 905551112233}).get("ok"), True)
        script = script_for("log", str(905551112233))
        self.assertIn('"905551112233"', script)
        self.assertNotIn("log(905551112233)", script)
        self.assertIn("return null", script)

    def test_ics_written(self):
        from jarvis.actions.calendar import add_calendar_event
        from jarvis.actions.calendar_store import ics_path

        add_calendar_event("Deneme", "2099-05-05")
        ics = Path(ics_path()).read_text(encoding="utf-8")
        self.assertIn("BEGIN:VEVENT", ics)
        self.assertIn("Deneme", ics)


    def test_qr_payload_rotates_token(self):
        from jarvis.config import save_app_config
        from jarvis.phone_server import phone_qr_payload, rotate_phone_token

        save_app_config({"web_remote_access": False})
        first = phone_qr_payload()
        self.assertTrue(first.startswith("http://127.0.0.1:8766/join?token="))
        rotate_phone_token()
        second = phone_qr_payload()
        self.assertTrue(second.startswith("http://127.0.0.1:8766/join?token="))
        self.assertNotEqual(first, second)

    def test_map_tint_follows_ui_color(self):
        from PIL import Image

        from jarvis.mapcolor import tint_gray

        gray = Image.new("L", (4, 4), 180)
        gold = tint_gray(gray, "#e6c98a").getpixel((1, 1))
        cyan = tint_gray(gray, "#5ed8ff").getpixel((1, 1))
        self.assertNotEqual(gold, cyan)
        self.assertGreater(cyan[2], gold[2])

    def test_live_model_and_language(self):
        from jarvis.config import LIVE_MODELS, save_app_config
        from jarvis.prompt import load_system_prompt

        self.assertIn("models/gemini-2.5-flash-native-audio-latest", LIVE_MODELS)
        self.assertIn("models/gemini-3.8-live", LIVE_MODELS)
        saved = save_app_config({"live_model": "models/gemini-3.8-live", "language": "tr"})
        self.assertEqual(saved["live_model"], "models/gemini-3.8-live")
        self.assertEqual(saved["language"], "tr")
        self.assertIn("TÜRKÇE", load_system_prompt())
        saved = save_app_config({"live_model": "models/nope", "language": "klingon"})
        self.assertEqual(saved["live_model"], LIVE_MODELS[0])
        self.assertEqual(saved["language"], "auto")
        self.assertNotIn("KONUŞMA DİLİ", load_system_prompt())
        from jarvis.language import speech_codes, ui_language
        from jarvis.textfix import repair_text

        self.assertEqual(speech_codes({"language": "tr"}), ["tr-TR"])
        self.assertEqual(speech_codes({"language": "en"}), ["en-US"])
        self.assertEqual(ui_language({"language": "fr"}), "fr")
        self.assertEqual(ui_language({"language": "auto"}), "tr")
        garbled = "spotify a" + "ç".encode("utf-8").decode("latin-1")
        self.assertEqual(repair_text(garbled), "spotify aç")
        self.assertEqual(repair_text("spotify aç"), "spotify aç")
        from jarvis.language import live_speech_code
        from jarvis.updater import is_newer

        self.assertIsNone(live_speech_code("models/gemini-2.5-flash-native-audio-latest"))
        self.assertEqual(live_speech_code("models/gemini-3.8-live", {"language": "en"}), "en")
        self.assertTrue(is_newer("3.6", "3.5"))
        self.assertFalse(is_newer("3.5", "3.6"))
        hud = (Path(__file__).resolve().parents[1] / "ui" / "hud" / "hud.js").read_text(encoding="utf-8")
        self.assertIn("applyLanguage", hud)
        self.assertIn("send(\"settings\", {values: {language: value}})", hud)

    def test_story_search_files_and_vision_code(self):
        from pathlib import Path

        from jarvis.actions.files import list_user_files
        from jarvis.actions.screen import VISION_MODELS, explain_vision_error
        from jarvis.actions.search import web_search
        from jarvis.config import save_app_config
        from jarvis.proactive import due_nudges
        from jarvis.story import note_tool, view
        from jarvis.tools import execute_tool

        self.assertIn("models/gemini-3.1-flash-lite", VISION_MODELS)
        self.assertIn("models/gemini-3.8-flash", VISION_MODELS)
        self.assertIn("models/gemini-flash-latest", VISION_MODELS)
        self.assertNotIn("models/gemini-2.0-flash", VISION_MODELS)
        self.assertIn("kod 4", explain_vision_error(RuntimeError("4")))
        self.assertIn("bos", web_search("  ").lower())
        folder = Path(self._tmp.name) / "Desktop"
        folder.mkdir()
        (folder / "not.txt").write_text("x", encoding="utf-8")
        listed = list_user_files("desktop", folder.parent)
        self.assertIn("not.txt", listed)
        self.assertIn("bakamam", list_user_files("..", folder.parent).lower())
        save_app_config({"story_enabled": True})
        note_tool("get_weather", "Antalya icin acik.")
        seen = view()
        self.assertTrue(any(row["got"] and row["key"] == "weather" for row in seen["achievements"]))
        self.assertTrue(seen["hints"])
        save_app_config({"story_enabled": False})
        self.assertEqual(view()["hints"], [])
        self.assertIn("mavi", execute_tool("save_memory", {"category": "notes", "key": "renk", "value": "mavi"}))
        state = {"heard": 0, "water": 0, "break": 10**12, "silence": 10**12, "event": 10**12}
        notes = due_nudges(4000, state, {"proactive_enabled": True, "water_enabled": True, "quiet_minutes": 20}, paused=False)
        self.assertTrue(any("Su" in note for note in notes))


    def test_capture_path_applies_echo_and_noise_filter(self):
        import array

        from jarvis.audio.capture import CaptureFilter, aec_wanted, chunks_for_model
        from jarvis.config import save_app_config

        self.assertTrue(aec_wanted())
        save_app_config({"aec_enabled": False})
        self.assertFalse(aec_wanted())
        save_app_config({"aec_enabled": True})
        quiet = array.array("h", [80] * 1024).tobytes()
        loud = array.array("h", [16000] * 1024).tobytes()
        filt = CaptureFilter()
        filt.note_playback(b"\x00\x00" * 24000, now=0.0)
        dropped = []
        now = 10.0
        for step in range(4):
            dropped.extend(chunks_for_model(quiet, speaking=True, echo_cancelled=True, filt=filt, now=now + step * 0.05))
        self.assertEqual(dropped, [])
        sent = []
        for step in range(6):
            sent.extend(chunks_for_model(loud, speaking=True, echo_cancelled=True, filt=filt, now=now + 1 + step * 0.05))
        self.assertIn(loud, sent)
        self.assertLess(len(dropped), 4)
        plain = chunks_for_model(loud, speaking=True, echo_cancelled=False, filt=CaptureFilter(), now=now)
        self.assertEqual(plain, [])
        heard = chunks_for_model(loud, speaking=False, echo_cancelled=False, filt=CaptureFilter(), now=now)
        self.assertEqual(heard, [loud])
        self.assertEqual(chunks_for_model(quiet, speaking=False, echo_cancelled=True, filt=filt, now=now + 8), [quiet])

    def test_first_run_screen_closes_and_uses_hud_type(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "ui" / "hud" / "index.html").read_text(encoding="utf-8")
        css = (root / "ui" / "hud" / "hud.css").read_text(encoding="utf-8")
        script = (root / "ui" / "hud" / "hud.js").read_text(encoding="utf-8")
        self.assertIn('id="onboard"', html)
        self.assertNotIn("ov-welcome", html)
        self.assertNotIn("greet-ring", html)
        self.assertIn("font-family:var(--sans)", css)
        self.assertIn("background:transparent", css)
        self.assertIn("@keyframes obLift", css)
        self.assertIn("closeOnboard", script)
        self.assertIn("FRIDAY ayakta", script)
        self.assertNotIn("#ff4fd8", script)
        self.assertNotIn("sepia", css)
        self.assertNotIn("rgba(230,201,138", css)
        self.assertIn("mix-blend-mode:color", css)

    def test_welcome_waits_for_key_then_shows_ready(self):
        from jarvis.onboarding import READY_TEXT, onboarding_view

        first = onboarding_view(has_key=False, connected=False, mic_ok=False)
        self.assertTrue(first["show_welcome"])
        self.assertFalse(first["start_services"])
        self.assertEqual(first["message"], "")
        saved = onboarding_view(has_key=True, connected=True, mic_ok=True)
        self.assertFalse(saved["show_welcome"])
        self.assertTrue(saved["start_services"])
        self.assertEqual(saved["message"], READY_TEXT)
        self.assertEqual(READY_TEXT, "Her şey çalıştı. FRIDAY ayakta.")
        again = onboarding_view(has_key=True, connected=False, mic_ok=False)
        self.assertFalse(again["show_welcome"])
        self.assertEqual(again["message"], "")

    def test_installer_does_not_ship_local_secrets(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / "packaging" / "friday.iss").read_text(encoding="utf-8")
        self.assertNotIn("api_keys.json", text)
        self.assertNotIn("phone_token.txt", text)
        self.assertNotIn("dist\\FRIDAY\\data\\*", text)

    def test_windows_startup_uses_the_given_registry(self):
        from jarvis.startup import MemoryRegistry, apply_windows_startup

        registry = MemoryRegistry()
        self.assertEqual(apply_windows_startup(False, r"C:\FRIDAY\FRIDAY.exe", registry), "")
        self.assertEqual(registry.values, {})
        written = apply_windows_startup(True, r"C:\FRIDAY\FRIDAY.exe", registry)
        self.assertIn(r"C:\FRIDAY\FRIDAY.exe", written)
        self.assertEqual(apply_windows_startup(False, r"C:\FRIDAY\FRIDAY.exe", registry), "")
        self.assertNotIn("FRIDAY", registry.values)

    def test_phone_mic_and_desktop_command_reach_the_pc(self):
        from jarvis.phone_server import handle_phone_request, phone_command_for_pc, phone_token, relay_phone_audio, take_phone_audio

        pcm = b"\x01\x00" * 32
        relay_phone_audio(pcm)
        self.assertEqual(take_phone_audio(), pcm)
        seen = []
        token = phone_token()
        status, _, _ = handle_phone_request("POST", f"/command?token={token}", b"text=bilgisayarda+ac+not+defteri", seen.append)
        self.assertEqual(status, 200 if False else 204)
        self.assertEqual(seen, ["not defteri"])
        self.assertEqual(phone_command_for_pc("Bilgisayara ilet tarayıcıyı aç"), "tarayıcıyı aç")
        denied, _, _ = handle_phone_request("POST", "/mic?token=yanlis", pcm, seen.append)
        self.assertEqual(denied, 403)
        self.assertEqual(seen, ["not defteri"])
        page_status, page, _ = handle_phone_request("GET", f"/?token={token}", b"", None)
        self.assertEqual(page_status, 200)
        self.assertIn(b'id="copy-key"', page)
        self.assertNotIn(b"<!--gate-->", page)
        join_status, join_page, _ = handle_phone_request("GET", f"/join?token={token}", b"", None)
        self.assertEqual(join_status, 200)
        self.assertIn(b'id="copy-key"', join_page)

    def test_close_and_minimize_stay_on_the_taskbar(self):
        from jarvis.taskbar import installer_is_running, keep_on_taskbar

        self.assertTrue(keep_on_taskbar(False))
        self.assertTrue(keep_on_taskbar(False, installer_running=False))
        self.assertFalse(keep_on_taskbar(True))
        self.assertFalse(keep_on_taskbar(False, installer_running=True))
        self.assertFalse(installer_is_running(["chrome.exe", "python.exe"]))
        self.assertTrue(installer_is_running(["FRIDAY-Kurulum.exe"]))
        self.assertTrue(installer_is_running(["unins000.exe"]))
        root = Path(__file__).resolve().parents[1]
        bridge = (root / "ui" / "bridge.py").read_text(encoding="utf-8")
        html = (root / "ui" / "hud" / "index.html").read_text(encoding="utf-8")
        script = (root / "ui" / "hud" / "hud.js").read_text(encoding="utf-8")
        self.assertIn("events.closing", bridge)
        self.assertIn("minimize_to_taskbar", bridge)
        self.assertIn("play_close_sfx", bridge)
        self.assertIn('id="quit"', html)
        self.assertIn('send("quit")', script)

    def test_uninstall_deletes_only_friday_folders(self):
        import contextlib
        import io

        from jarvis.uninstall import delete_friday_dir, delete_friday_dirs, friday_data_dirs, launch_uninstaller

        root = Path(self._tmp.name)
        local = root / "Local"
        roaming = root / "Roaming"
        secret = "secret-value-should-not-print"
        keep = [
            local / "Jarvis",
            local / "JARVIS V4",
            roaming / "JARVIS V4",
            roaming / "JARVIS V4 yedek",
            root / "JarvisV4",
            root / "dist" / "FRIDAY",
        ]
        for folder in keep:
            folder.mkdir(parents=True)
            (folder / "note.txt").write_text("kalir", encoding="utf-8")
        targets = list(friday_data_dirs(local, roaming))
        self.assertEqual(targets, [local / "FRIDAY", roaming / "FRIDAY"])
        for folder in targets:
            data = folder / "data" / "config"
            data.mkdir(parents=True)
            (data / "api_keys.json").write_text('{"gemini_api_key":"%s"}' % secret, encoding="utf-8")
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            removed = delete_friday_dirs(targets)
        self.assertEqual(len(removed), 2)
        self.assertNotIn(secret, captured.getvalue())
        self.assertNotIn(secret, " ".join(removed))
        for folder in targets:
            self.assertFalse(folder.exists())
        for folder in keep:
            self.assertTrue((folder / "note.txt").read_text(encoding="utf-8") == "kalir")
        self.assertFalse(delete_friday_dir(root / "dist" / "FRIDAY"))
        self.assertFalse(delete_friday_dir(local / "Jarvis"))
        self.assertFalse(delete_friday_dir(roaming / "JARVIS V4"))
        self.assertFalse(delete_friday_dir(root / "JarvisV4"))
        seen = []

        def popen(args, **kwargs):
            seen.append((args, kwargs))
            return object()

        setup = local / "FRIDAY" / "unins000.exe"
        setup.parent.mkdir()
        setup.write_bytes(b"")
        self.assertTrue(launch_uninstaller(setup, popen))
        self.assertEqual(seen[0][0][1], "/SILENT")
        self.assertFalse(launch_uninstaller(root / "JarvisV4" / "unins000.exe", popen))
        self.assertFalse(launch_uninstaller(root / "dist" / "FRIDAY" / "missing.exe", popen))
        iss = (Path(__file__).resolve().parents[1] / "packaging" / "friday.iss").read_text(encoding="utf-8")
        self.assertIn("{localappdata}\\FRIDAY", iss)
        self.assertIn("{userappdata}\\FRIDAY", iss)
        self.assertIn("DeleteFridayDir", iss)
        self.assertIn("CompareText(Parent, 'Local')", iss)
        self.assertIn("CompareText(Parent, 'Roaming')", iss)
        self.assertIn("taskkill.exe", iss)
        self.assertNotIn("JarvisV4", iss)
        self.assertNotIn("JARVIS V4", iss)
        self.assertNotIn("pywebview", iss)
        self.assertNotIn(secret, iss)
        hud = (Path(__file__).resolve().parents[1] / "ui" / "hud" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="uninstall"', hud)


    def test_missing_gate_key_is_created_once_and_qr_matches(self):
        import base64
        import io

        import cv2
        import numpy as np
        from PIL import Image

        from jarvis.gate_client import ensure_gate_key, gate_key
        from jarvis.paths import data_path
        from jarvis.phone_server import phone_qr_data_url

        path = data_path("config", "gate_key.txt")
        if path.exists():
            path.unlink()
        first = ensure_gate_key()
        self.assertTrue(bool(first))
        self.assertTrue(gate_key() == first and ensure_gate_key() == first)
        from jarvis.gate_client import gate_join_url, pair_code

        encoded = phone_qr_data_url(gate_join_url(first)).split(",", 1)[1]
        image = Image.open(io.BytesIO(base64.b64decode(encoded))).convert("RGB")
        value, _points, _straight = cv2.QRCodeDetector().detectAndDecode(np.array(image))
        code = pair_code(first)
        self.assertTrue(value.startswith("https://site-seven-bay-75.vercel.app/#k="))
        self.assertTrue(first in value)
        self.assertTrue(len(code) == 6 and code.isdigit() and pair_code(first) == code)

if __name__ == "__main__":
    unittest.main()
