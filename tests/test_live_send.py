import asyncio
import sys
import types
import unittest
from unittest import mock


class FakeSession:
    def __init__(self, old_sdk=False):
        self.calls = []
        self.old_sdk = old_sdk

    async def send_realtime_input(self, **kw):
        if self.old_sdk and ("text" in kw or "audio" in kw):
            raise TypeError("unexpected keyword")
        self.calls.append(("rt", kw))

    async def send_client_content(self, **kw):
        self.calls.append(("cc", kw))


def make_live(session):
    from jarvis.live import JarvisLive

    live = JarvisLive.__new__(JarvisLive)
    live.session = session
    return live


class LiveSendTest(unittest.TestCase):
    def test_text_uses_realtime_input(self):
        s = FakeSession()
        asyncio.run(make_live(s)._send_user_text("selam"))
        self.assertEqual(s.calls, [("rt", {"text": "selam"})])

    def test_text_never_uses_client_content(self):
        # 3.x canlı oturumda send_client_content 1007 ile bağlantıyı kapatır (S-022).
        s = FakeSession(old_sdk=True)
        live = make_live(s)
        logged = []
        live.ui = types.SimpleNamespace(write_log=logged.append)
        asyncio.run(live._send_user_text("selam"))
        self.assertEqual(s.calls, [])
        self.assertTrue(logged and logged[0].startswith("ERR"))

    def test_error_log_masks_key(self):
        import os
        import tempfile

        from jarvis import live

        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"JARVIS_DATA_DIR": tmp}):
            try:
                raise RuntimeError("1007 bad request key=GIZLI123")
            except RuntimeError as exc:
                with mock.patch.object(live, "current_live_model", return_value="models/x"):
                    live._log_error(exc, "GIZLI123")
            text = open(os.path.join(tmp, "logs", "live-errors.log"), encoding="utf-8").read()
        self.assertIn("1007", text)
        self.assertNotIn("GIZLI123", text)

    def test_audio_uses_audio_blob_with_rate(self):
        fake_types = types.SimpleNamespace(Blob=lambda data, mime_type: {"data": data, "mime_type": mime_type})
        genai = types.ModuleType("google.genai")
        genai.types = fake_types
        google = types.ModuleType("google")
        google.genai = genai
        s = FakeSession()
        with mock.patch.dict(sys.modules, {"google": google, "google.genai": genai}):
            asyncio.run(make_live(s)._send_audio(b"\x00\x01"))
        kind, kw = s.calls[0]
        self.assertEqual(kind, "rt")
        self.assertEqual(kw["audio"]["mime_type"], "audio/pcm;rate=16000")
        self.assertNotIn("media", kw)


class SafeStreamTest(unittest.TestCase):
    def test_close_waits_for_inflight_write(self):
        import threading
        import time as _t

        from jarvis.live import SafeStream

        events = []

        class Stream:
            def write(self, data):
                events.append("write-start")
                _t.sleep(0.2)
                events.append("write-end")

            def stop_stream(self):
                events.append("stop")

            def close(self):
                events.append("close")

        class Audio:
            def terminate(self):
                events.append("terminate")

        safe = SafeStream(Audio(), Stream())
        worker = threading.Thread(target=safe.write, args=(b"x",))
        worker.start()
        _t.sleep(0.05)
        safe.close()  # yazma bitmeden kapanmamalı
        worker.join()
        self.assertEqual(events, ["write-start", "write-end", "stop", "close", "terminate"])
        safe.write(b"y")
        self.assertEqual(safe.read(4), b"")
        safe.close()
        self.assertEqual(events.count("close"), 1)


class ListeningConfigTest(unittest.TestCase):
    def test_patient_mode_waits_for_pause(self):
        from jarvis.live import listening_config

        cfg = listening_config(True)
        self.assertEqual(cfg["end_of_speech_sensitivity"], "END_SENSITIVITY_LOW")
        self.assertEqual(cfg["start_of_speech_sensitivity"], "START_SENSITIVITY_HIGH")
        self.assertTrue(500 <= cfg["silence_duration_ms"] <= 1200)
        self.assertIsNone(listening_config(False))

    def test_default_on(self):
        from jarvis.config import DEFAULT_CONFIG

        self.assertTrue(DEFAULT_CONFIG["patient_listening"])


if __name__ == "__main__":
    unittest.main()
