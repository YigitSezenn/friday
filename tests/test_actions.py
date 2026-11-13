import base64
import io
import os
import tempfile
import time
import unittest
from pathlib import Path

import requests


class ActionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["JARVIS_DATA_DIR"] = self._tmp.name
        os.environ["JARVIS_CALENDAR_BACKEND"] = "local"
        self.addCleanup(self._tmp.cleanup)

    def test_spotify_opens_the_track(self):
        from jarvis.actions.media import control_media, play_media, spotify_cli_path, spotify_now

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
        from jarvis.actions.media import play_saved_collection

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

    def test_youtube_opens_a_real_video(self):
        from jarvis.actions.browser import browser_control

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

    def test_browser_search_opens_google(self):
        from jarvis.actions.browser import browser_control

        result = browser_control("search", query="jarvis rebuild ankara")
        self.assertIn("https://www.google.com/search?q=", result)
        url = "https://" + result.split("https://", 1)[1].split()[0] if "https://" in result else ""
        self.assertIn("jarvis", result)
        if not url:
            self.fail(result)
        page = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        self.assertLess(page.status_code, 500)

    def test_whatsapp_draft_uses_real_chat_link(self):
        from jarvis.actions.whatsapp import send_whatsapp_message

        result = send_whatsapp_message("merhaba jarvis", "0555 111 22 33", send_now=False)
        self.assertIn("905551112233", result)
        self.assertIn("merhaba", result.lower())
        self.assertTrue(result.startswith("WhatsApp sohbeti"))
        self.assertIn("whatsapp", result.lower())

    def test_open_notepad_creates_a_process(self):
        import psutil

        from jarvis.actions.apps import open_app

        before = {proc.pid for proc in psutil.process_iter(["name"]) if (proc.info["name"] or "").lower() == "notepad.exe"}
        result = open_app("not defteri")
        self.assertIn("acildi", result.lower())
        time.sleep(1)
        after = [proc for proc in psutil.process_iter(["name"]) if (proc.info["name"] or "").lower() == "notepad.exe"]
        fresh = [proc for proc in after if proc.pid not in before]
        self.assertTrue(fresh, result)
        for proc in fresh:
            proc.terminate()

    def test_reminder_is_stored_and_listed(self):
        from jarvis.actions.calendar_store import load_store
        from jarvis.actions.reminders import add_reminder, complete_reminder, delete_reminder, get_reminders

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

    def test_web_search_returns_a_summary(self):
        from jarvis.actions.search import web_search

        result = web_search("Albert Einstein")
        self.assertNotIn("yapilamadi", result.lower())
        self.assertGreater(len(result.strip()), 20)

    def test_folder_list_shows_created_file(self):
        from jarvis.actions.files import list_user_files

        root = Path(self._tmp.name)
        desktop = root / "Desktop"
        desktop.mkdir()
        (desktop / "liste.txt").write_text("icerik", encoding="utf-8")
        (desktop / "api_keys.json").write_text("gizli", encoding="utf-8")
        listed = list_user_files("desktop", root)
        self.assertIn("liste.txt", listed)
        self.assertNotIn("api_keys.json", listed)
        self.assertIn("bakamam", list_user_files("..\\Windows", root).lower())

    def test_phone_qr_decodes_to_the_pairing_url(self):
        import cv2
        import numpy as np
        from PIL import Image

        from jarvis.config import save_app_config
        from jarvis.phone_server import phone_qr_data_url, phone_qr_payload

        save_app_config({"web_remote_access": False})
        payload = phone_qr_payload()
        encoded = phone_qr_data_url(payload).split(",", 1)[1]
        image = Image.open(io.BytesIO(base64.b64decode(encoded))).convert("RGB")
        value, _points, _straight = cv2.QRCodeDetector().detectAndDecode(np.array(image))
        self.assertEqual(value, payload)
        self.assertTrue(value.startswith("http://127.0.0.1:8766/join?token="))
        self.assertGreater(len(value.split("token=", 1)[1]), 8)

    def test_screen_analysis_describes_the_window(self):
        import json

        from jarvis.actions.screen import analyze_screen
        from jarvis.config import has_gemini_api_key, save_app_config

        real = Path(r"C:\Users\yigit\Desktop\jarvis-rebuild\data\config\api_keys.json")
        if real.exists():
            try:
                key = str(json.loads(real.read_text(encoding="utf-8")).get("gemini_api_key") or "")
            except (OSError, json.JSONDecodeError):
                key = ""
            if key:
                save_app_config({"gemini_api_key": key})
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
