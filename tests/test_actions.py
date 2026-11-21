import base64
import io
import os
import tempfile
import time
import unittest
from unittest import mock
from pathlib import Path

import requests

from tests._env import decode_qr, live_api, needs_module, needs_network, windows_only


class ActionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["JARVIS_DATA_DIR"] = self._tmp.name
        os.environ["JARVIS_CALENDAR_BACKEND"] = "local"
        self.addCleanup(self._tmp.cleanup)

    @windows_only
    def test_spotify_opens_the_track(self):
        from tools.actions.media import control_media, play_media, spotify_cli_path, spotify_now

        self.assertIsNotNone(spotify_cli_path(), "spotify_cli.exe yok")
        result = play_media("Blinding Lights", provider="spotify")
        self.assertIn("spotify:track:", result)
        self.assertIn("caliyor", result.lower())
        current = spotify_now()
        self.assertEqual(current.get("uri"), result.rsplit("(", 1)[-1].rstrip(")"))
        self.assertIn("Blinding Lights", str(current.get("description") or ""))
        self.assertTrue(current.get("is_playing"))
        paused = control_media("pause")
        self.assertIn("Spotify", paused)
        time.sleep(1)
        self.assertFalse(spotify_now().get("is_playing"))

    def test_profile_album_request_opens_the_users_item(self):
        from tools.actions.media import play_saved_collection

        saved_uri = "spotify:playlist:fixtureefkar"
        calls = []

        def run(args, timeout=25):
            calls.append(list(args))
            if list(args[:2]) == ["library", "list"]:
                kind = args[args.index("--type") + 1]
                if kind == "album":
                    return {"items": [{"name": "Baska Album", "uri": "spotify:album:notefkar", "type": "album"}]}
                return {"items": [
                    {"name": "Gece", "uri": "spotify:playlist:other", "type": "playlist"},
                    {"name": "Efkar", "uri": saved_uri, "type": "playlist"},
                ]}
            if args[:1] == ["play"]:
                return {"text": "ok"}
            return {}

        result = play_saved_collection("profilimde ki efkar albümünü aç", run)
        self.assertIn(saved_uri, result)
        self.assertIn("Efkar", result)
        self.assertIn(["play", saved_uri], calls)
        self.assertFalse(any(call[:1] == ["search"] for call in calls))
        self.assertIsNone(play_saved_collection("Blinding Lights", run))

    @needs_network
    def test_youtube_opens_a_real_video(self):
        from tools.actions.browser import browser_control

        result = browser_control("play_youtube", query="never gonna give you up")
        self.assertIn("https://www.youtube.com/watch?v=", result)
        watch = "https://" + result.split("https://", 1)[1].split()[0]
        video_id = watch.split("watch?v=", 1)[1].split("&", 1)[0]
        self.assertEqual(len(video_id), 11)
        page = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
            timeout=15,
        )
        page.raise_for_status()
        self.assertTrue(page.json().get("title"))

    @needs_network
    def test_browser_search_opens_google(self):
        from tools.actions.browser import browser_control

        result = browser_control("search", query="jarvis rebuild ankara")
        self.assertIn("https://www.google.com/search?q=", result)
        url = "https://" + result.split("https://", 1)[1].split()[0] if "https://" in result else ""
        self.assertIn("jarvis", result)
        if not url:
            self.fail(result)
        page = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        self.assertLess(page.status_code, 500)

    def test_whatsapp_draft_uses_real_chat_link(self):
        from tools.actions.whatsapp import send_whatsapp_message

        result = send_whatsapp_message("merhaba jarvis", "0555 111 22 33", send_now=False)
        self.assertIn("905551112233", result)
        self.assertIn("merhaba", result.lower())
        self.assertTrue(result.startswith("WhatsApp sohbeti"))
        self.assertIn("whatsapp", result.lower())

    @windows_only
    def test_open_notepad_creates_a_process(self):
        import psutil

        from tools.actions.apps import open_app

        before = {proc.pid for proc in psutil.process_iter(["name"]) if (proc.info["name"] or "").lower() == "notepad.exe"}
        result = open_app("not defteri")
        self.assertTrue("acildi" in result.lower() or "açıldı" in result.lower(), result)
        time.sleep(1)
        after = [proc for proc in psutil.process_iter(["name"]) if (proc.info["name"] or "").lower() == "notepad.exe"]
        fresh = [proc for proc in after if proc.pid not in before]
        self.assertTrue(fresh, result)
        for proc in fresh:
            proc.terminate()

    def test_reminder_is_stored_and_listed(self):
        from tools.actions.calendar_store import load_store
        from tools.actions.reminders import add_reminder, complete_reminder, delete_reminder, get_reminders

        saved = add_reminder("Dis fircasi", "2099-01-02T09:30", notes="test")
        self.assertIn("Dis fircasi", saved)
        titles = [item["title"] for item in load_store()["reminders"]]
        self.assertIn("Dis fircasi", titles)
        listed = get_reminders("all")
        self.assertIn("Dis fircasi", listed)
        self.assertIn("09:30", listed)
        done = complete_reminder("Dis fircasi")
        self.assertIn("tamamlandi", done.lower())
        self.assertNotIn("Dis fircasi", get_reminders("all"))
        removed = delete_reminder("Dis fircasi")
        self.assertIn("silindi", removed.lower())
        self.assertNotIn("Dis fircasi", [item["title"] for item in load_store()["reminders"]])

    @needs_network
    def test_web_search_returns_a_summary(self):
        from tools.actions.search import web_search

        result = web_search("Albert Einstein")
        self.assertNotIn("yapılamadı", result.lower())
        self.assertGreater(len(result.strip()), 20)

    @windows_only
    def test_folder_list_shows_created_file(self):
        from tools.actions.files import list_user_files

        root = Path(self._tmp.name)
        desktop = root / "Desktop"
        desktop.mkdir()
        (desktop / "liste.txt").write_text("icerik", encoding="utf-8")
        (desktop / "api_keys.json").write_text("gizli", encoding="utf-8")
        listed = list_user_files("desktop", root)
        self.assertIn("liste.txt", listed)
        self.assertNotIn("api_keys.json", listed)
        self.assertIn("bakamam", list_user_files("..\\Windows", root).lower())

    @needs_module("qrcode", "cv2")
    def test_phone_qr_decodes_to_the_pairing_url(self):
        from PIL import Image

        from jarvis.config import save_app_config
        from jarvis.phone_server import phone_qr_data_url, phone_qr_payload

        save_app_config({"web_remote_access": False})
        payload = phone_qr_payload()
        encoded = phone_qr_data_url(payload).split(",", 1)[1]
        image = Image.open(io.BytesIO(base64.b64decode(encoded))).convert("RGB")
        value = decode_qr(image)
        self.assertEqual(value, payload)
        self.assertTrue(value.startswith("http://127.0.0.1:8766/join?token="))
        self.assertGreater(len(value.split("token=", 1)[1]), 8)

    @live_api
    def test_screen_analysis_describes_the_window(self):
        from tools.actions.screen import analyze_screen
        from jarvis.config import has_gemini_api_key, save_app_config

        # Gerçek anahtar dosyası okunmaz; anahtar yalnızca ortam değişkeninden gelir.
        save_app_config({"gemini_api_key": os.environ["FRIDAY_TEST_GEMINI_KEY"]})
        if not has_gemini_api_key():
            self.skipTest("Gemini anahtari yok")
        result = analyze_screen("Ekranda kisa olarak ne gorunuyor?")
        lowered = result.lower()
        self.assertNotIn("tamamlanamadi", lowered)
        self.assertNotIn("basarisiz", lowered)
        self.assertNotIn("kod 4", lowered)
        self.assertGreater(len(result.strip()), 30)


if __name__ == "__main__":
    unittest.main()


class ReminderRelativeTests(unittest.TestCase):
    def test_after_minutes_and_duplicate_guard(self):
        import datetime as dt
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            os.environ["JARVIS_DATA_DIR"] = tmp
            try:
                from tools.actions import reminders

                out = reminders.add_reminder("Su iç", after_minutes=1)
                self.assertIn("eklendi", out)
                again = reminders.add_reminder("Su iç", after_minutes=1)
                self.assertIn("zaten var", again)
            finally:
                os.environ.pop("JARVIS_DATA_DIR", None)


class ReminderDueTests(unittest.TestCase):
    def test_due_reminder_fires_once(self):
        import datetime as dt
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            os.environ["JARVIS_DATA_DIR"] = tmp
            try:
                from tools.actions import reminders

                reminders.add_reminder("Su iç", after_minutes=1)
                later = dt.datetime.now() + dt.timedelta(minutes=2)
                early = dt.datetime.now()
                self.assertEqual(reminders.due_now(early), [])
                self.assertEqual([i["title"] for i in reminders.due_now(later)], ["Su iç"])
                self.assertEqual(reminders.due_now(later), [])
            finally:
                os.environ.pop("JARVIS_DATA_DIR", None)


class DiscordMessageTests(unittest.TestCase):
    def test_needs_id_then_confirmation(self):
        from tools.actions import discord

        with mock.patch.object(discord, "_book", return_value={}):
            self.assertIn("kayıtlı Discord kimliği yok", discord.send_discord_message("selam", "Ali"))
            self.assertIn("17-19 haneli", discord.send_discord_message("selam", "Ali", "123"))
            self.assertIn("ONAY GEREKLİ", discord.send_discord_message("selam", "Ali", "123456789012345678"))
        with mock.patch.object(discord, "_book", return_value={"Ali": "123456789012345678"}):
            self.assertIn("ONAY GEREKLİ", discord.send_discord_message("selam", "ali"))

    def test_confirmed_send_pastes_enter_and_saves_contact(self):
        from tools.actions import confirm, discord

        uid = "123456789012345678"
        calls = []
        saved = {}
        win = mock.Mock(available=lambda: True, set_clipboard=lambda t: calls.append(("clip", t)) or True, press_keys=lambda *k: calls.append(("keys", k)))
        with mock.patch.object(discord, "_book", side_effect=lambda: dict(saved)), \
             mock.patch.object(discord, "_save", side_effect=saved.update), \
             mock.patch.object(discord.time, "sleep"), \
             mock.patch.object(confirm, "MIN_WAIT", 0), \
             mock.patch.object(os, "startfile", lambda url: calls.append(("open", url)), create=True), \
             mock.patch.dict("sys.modules", {"jarvis.win32": win}):
            self.assertIn("ONAY GEREKLİ", discord.send_discord_message("selam", "Ali", uid))
            self.assertEqual(calls, [])
            confirm.note_user_said("evet gönder")
            out = discord.send_discord_message("selam", "Ali", uid, confirm_send=True)
        self.assertIn("gönderildi", out)
        self.assertEqual(calls, [("open", f"discord://-/users/{uid}"), ("clip", "selam"), ("keys", (0x11, 0x56)), ("keys", (0x0D,))])
        self.assertEqual(saved, {"Ali": uid})

    def test_confirm_without_user_yes_does_not_send(self):
        from tools.actions import confirm, discord

        with mock.patch.object(os, "startfile", mock.Mock(), create=True) as opener:
            discord.send_discord_message("selam", "Ali", "123456789012345678")
            out = discord.send_discord_message("selam", "Ali", "123456789012345678", confirm_send=True)
        self.assertNotIn("gönderildi", out)
        opener.assert_not_called()

    def test_self_test_validates_id_and_skips_saving(self):
        from tools.actions import discord

        self.assertIn("Önce Discord kimliğini", discord.self_test("12"))
        with mock.patch.object(discord, "_deliver", return_value="ok gönderildi") as deliver:
            discord.self_test("123456789012345678")
        deliver.assert_called_once()
        self.assertFalse(deliver.call_args.kwargs.get("save", True))


class WebSearchRetryTests(unittest.TestCase):
    def test_transient_failure_is_retried_once_and_reason_names_the_error(self):
        from unittest import mock
        from tools.actions import search

        calls = []

        def flaky(key, model, query):
            calls.append(model)
            if len(calls) == 1:
                raise ConnectionError("boom")
            return "Cevap"

        with mock.patch("jarvis.config.get_app_config_value", return_value="K" * 39):
            self.assertEqual(search.web_search("x", ask=flaky, fallback=lambda q: ""), "Cevap")
            self.assertEqual(calls[0], calls[1])

            def always(key, model, query):
                raise ConnectionError("boom")

            out = search.web_search("x", ask=always, fallback=lambda q: "")
        self.assertIn("ConnectionError", out)

    def test_http_error_code_and_message_are_reported_without_the_key(self):
        from unittest import mock
        from tools.actions import search

        class ClientError(Exception):
            code = 429
            message = "Quota exceeded for KKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKK"

        def deny(key, model, query):
            raise ClientError()

        with mock.patch("jarvis.config.get_app_config_value", return_value="K" * 39):
            out = search.web_search("x", ask=deny, fallback=lambda q: "")
        self.assertIn("ClientError 429", out)
        self.assertIn("Quota exceeded", out)
        self.assertNotIn("K" * 20, out)


class SearchResultParsingTests(unittest.TestCase):
    def test_parses_titles_and_snippets(self):
        from tools.actions.search import _parse_results

        page = (
            '<a rel="nofollow" class="result__a" href="//x">PS5 <b>825GB</b> vs 1TB</a>'
            '<a class="result__snippet" href="//x">1 TB model daha fazla alan sunar &amp; pahalıdır.</a>'
            '<a class="result__a" href="//y">İkinci sonuç</a>'
        )
        lines = _parse_results(page)
        self.assertEqual(lines[0], "PS5 825GB vs 1TB — 1 TB model daha fazla alan sunar & pahalıdır.")
        self.assertEqual(lines[1], "İkinci sonuç")
        self.assertEqual(_parse_results("<html></html>"), [])


class TavilySearchTests(unittest.TestCase):
    def test_tavily_is_used_first_when_key_is_saved_and_failure_falls_through(self):
        from unittest import mock
        from tools.actions import search

        values = {"tavily_api_key": "tvly-abc", "gemini_api_key": ""}
        with mock.patch("jarvis.config.get_app_config_value", side_effect=lambda k, d="": values.get(k, d)):
            self.assertEqual(search.web_search("x", tavily=lambda key, q: "Tavily cevabı", fallback=lambda q: "ddg"), "Tavily cevabı")

            def broken(key, q):
                raise ConnectionError("x")

            self.assertEqual(search.web_search("x", ask=lambda k, m, q: "", tavily=broken, fallback=lambda q: "ddg"), "ddg")

    def test_no_key_skips_tavily(self):
        from unittest import mock
        from tools.actions import search

        with mock.patch("jarvis.config.get_app_config_value", return_value=""):
            out = search.web_search("x", tavily=lambda k, q: "olmamalı", fallback=lambda q: "ddg")
        self.assertEqual(out, "ddg")
