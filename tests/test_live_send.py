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

    def test_text_falls_back_on_old_sdk(self):
        s = FakeSession(old_sdk=True)
        asyncio.run(make_live(s)._send_user_text("selam"))
        self.assertEqual(s.calls[0][0], "cc")

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


if __name__ == "__main__":
    unittest.main()
