import os
import tempfile
import unittest
from unittest import mock


class SpotifyVerificationTests(unittest.TestCase):
    def test_same_uri_playing_is_confirmed(self):
        from tools.actions.media import track_is_playing

        current = {"uri": "spotify:track:1", "is_playing": True, "description": "Blinding Lights - The Weeknd"}
        self.assertTrue(track_is_playing(current, "spotify:track:1", "Blinding Lights"))

    def test_relinked_uri_with_same_title_counts_as_playing(self):
        from tools.actions.media import track_is_playing

        current = {"uri": "spotify:track:OTHER", "is_playing": True, "description": "Blinding Lights - The Weeknd"}
        self.assertTrue(track_is_playing(current, "spotify:track:1", "Blinding Lights"))

    def test_paused_or_different_track_is_not_confirmed(self):
        from tools.actions.media import track_is_playing

        paused = {"uri": "spotify:track:1", "is_playing": False, "description": "Blinding Lights"}
        other = {"uri": "spotify:track:9", "is_playing": True, "description": "Another Song"}
        self.assertFalse(track_is_playing(paused, "spotify:track:1", "Blinding Lights"))
        self.assertFalse(track_is_playing(other, "spotify:track:1", "Blinding Lights"))
        self.assertFalse(track_is_playing({}, "spotify:track:1", "Blinding Lights"))

    def test_wait_gives_late_start_time_to_catch_up(self):
        from tools.actions.media import wait_until_playing

        states = iter([{}, {"is_playing": False}, {"uri": "spotify:track:1", "is_playing": True, "description": "X"}])
        slept = []
        confirmed, current = wait_until_playing("spotify:track:1", "X", poll=lambda: next(states), sleep=slept.append)
        self.assertTrue(confirmed)
        self.assertEqual(len(slept), 3)

    def test_wait_gives_up_after_all_delays(self):
        from tools.actions.media import wait_until_playing

        confirmed, current = wait_until_playing("u", "n", poll=lambda: {}, sleep=lambda _: None, delays=(0.1, 0.1))
        self.assertFalse(confirmed)

    def test_unconfirmed_play_never_says_it_failed_to_open(self):
        from tools.actions import media

        def run(args, timeout=25):
            if args[0] == "status":
                return {"running": True, "logged_in": True}
            if args[0] == "search":
                return {"tracks": [{"uri": "spotify:track:1", "name": "Blinding Lights"}]}
            return {"text": "ok"}

        with mock.patch.object(media, "spotify_cli_path", return_value="cli"), \
                mock.patch.object(media, "_spotify_run", side_effect=run), \
                mock.patch.object(media, "play_saved_collection", return_value=None), \
                mock.patch.object(media, "wait_until_playing", return_value=(False, {})):
            result = media._play_spotify("Blinding Lights", "spotify.exe")
        self.assertIn("doğrulayamadım", result)
        self.assertNotIn("acilmadi", result)
        self.assertNotIn("acilamadi", result)


class PlaybackTests(unittest.TestCase):
    def test_exclude_pattern_is_sanitised(self):
        from tools.actions.playback import _safe_pattern

        self.assertEqual(_safe_pattern("Spotify'; Remove-Item *"), "Spotify Remove-Item ")
        self.assertEqual(_safe_pattern("SpotifyAB.SpotifyMusic"), "SpotifyAB.SpotifyMusic")

    def test_command_is_encoded_and_only_pauses_playing_sessions(self):
        import base64

        from tools.actions.playback import build_command

        command = build_command("Spotify")
        self.assertEqual(command[0], "powershell.exe")
        script = base64.b64decode(command[-1]).decode("utf-16-le")
        self.assertIn("-ne 'Playing'", script)
        self.assertIn("'Spotify'", script)
        self.assertNotIn("__EXCLUDE__", script)

    def test_non_windows_does_nothing(self):
        from tools.actions import playback

        with mock.patch.object(playback.sys, "platform", "linux"), mock.patch.object(playback.subprocess, "run") as run:
            self.assertEqual(playback.pause_playing_sessions(), 0)
        run.assert_not_called()

    def test_windows_failure_is_swallowed(self):
        from tools.actions import playback

        with mock.patch.object(playback.sys, "platform", "win32"), \
                mock.patch.object(playback.subprocess, "run", side_effect=OSError("yok")):
            self.assertEqual(playback.pause_playing_sessions(), 0)

    def test_windows_reads_the_count(self):
        from tools.actions import playback

        done = mock.Mock(stdout="2\r\n")
        with mock.patch.object(playback.sys, "platform", "win32"), mock.patch.object(playback.subprocess, "run", return_value=done):
            self.assertEqual(playback.pause_playing_sessions(), 2)

    def test_new_youtube_video_pauses_the_old_sound_first(self):
        from tools.actions import browser

        order = []
        with mock.patch.object(browser, "_stop_current_playback", side_effect=lambda: order.append("pause")), \
                mock.patch.object(browser, "_find_first_youtube_video", return_value="dQw4w9WgXcQ"), \
                mock.patch.object(browser, "open_url", side_effect=lambda url: order.append("open")):
            result = browser.browser_control("play_youtube", query="x")
        self.assertEqual(order, ["pause", "open"])
        self.assertIn("watch?v=dQw4w9WgXcQ", result)


class WebSearchTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["JARVIS_DATA_DIR"] = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def _key(self):
        from jarvis.config import save_app_config

        save_app_config({"gemini_api_key": "AIzaTEST"})

    def test_first_model_answer_wins(self):
        from tools.actions.search import SEARCH_MODELS, web_search

        self._key()
        calls = []

        def ask(key, model, query):
            calls.append(model)
            return "Cevap."

        self.assertEqual(web_search("hava", ask=ask, fallback=lambda q: "ddg"), "Cevap.")
        self.assertEqual(calls, [SEARCH_MODELS[0]])

    def test_falls_through_the_three_models_then_duckduckgo(self):
        from tools.actions.search import SEARCH_MODELS, web_search

        self._key()
        calls = []

        def ask(key, model, query):
            calls.append(model)
            raise RuntimeError("getaddrinfo failed")

        self.assertEqual(web_search("x", ask=ask, fallback=lambda q: "ddg ozeti"), "ddg ozeti")
        # Geçici ağ hatasında her model bir kez daha denenir.
        self.assertEqual(calls, [m for m in SEARCH_MODELS for _ in range(2)])

    def test_account_level_rejection_stops_model_loop(self):
        from tools.actions.search import web_search

        self._key()
        calls = []

        def ask(key, model, query):
            calls.append(model)
            raise RuntimeError("1008 Your project has been denied access")

        result = web_search("x", ask=ask, fallback=lambda q: "")
        self.assertEqual(len(calls), 1)
        self.assertIn("ERİŞİM KAPALI", result)
        self.assertIn("yapılamadı", result)

    def test_everything_failing_names_each_reason_and_hides_the_key(self):
        from tools.actions.search import web_search

        self._key()

        def ask(key, model, query):
            raise RuntimeError("SSL failed AIzaTEST")

        def broken(query):
            raise TimeoutError("zaman asimi")

        result = web_search("x", ask=ask, fallback=broken)
        self.assertIn("SSL SORUNU", result)
        self.assertIn("DuckDuckGo", result)
        self.assertNotIn("AIzaTEST", result)

    def test_without_a_key_only_duckduckgo_runs(self):
        from tools.actions.search import web_search

        def ask(*args):
            raise AssertionError("anahtar yokken Gemini cagrilmamali")

        self.assertEqual(web_search("x", ask=ask, fallback=lambda q: "ozet"), "ozet")

    def test_empty_query_and_long_answers(self):
        from tools.actions.search import ANSWER_LIMIT, web_search

        self.assertIn("boş", web_search("   "))
        self._key()
        self.assertEqual(len(web_search("x", ask=lambda *a: "a" * 5000)), ANSWER_LIMIT)


if __name__ == "__main__":
    unittest.main()
