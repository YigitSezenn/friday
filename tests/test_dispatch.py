import os
import tempfile
import time
import unittest
from unittest import mock


class DispatchSmokeTest(unittest.TestCase):
    """HUD'un gönderdiği her istek türü işleyiciye ulaşır; bilinmeyen tür reddedilir."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        p = mock.patch.dict(os.environ, {"JARVIS_DATA_DIR": self.tmp.name})
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_all_kinds(self):
        from jarvis import notes
        from ui.bridge import JarvisUI
        from ui.dispatch import HANDLERS

        ui = JarvisUI()
        ui._smoke = True
        post = ui._bridge.post
        for kind, data in [
            ("command", {"text": "selam"}), ("mute", {"muted": True}), ("camera", {"on": False}),
            ("sleep", {"asleep": True}), ("sleep", {"asleep": False}),
            ("note", {"lines": ["a", "b"]}), ("note_edit", {"index": 0, "text": "A"}), ("note_delete", {"index": 1}),
            ("timer", {"action": "set", "seconds": 60, "label": "x"}), ("timer", {"action": "add", "seconds": 30}),
            ("timer", {"action": "watch", "watch": "toggle"}), ("timer", {"action": "cancel"}),
        ]:
            self.assertEqual(post(kind, data), {"ok": True}, kind)
        self.assertEqual(notes.load(), ["A"])
        self.assertEqual(ui.timer.remaining(time.time()), 0)
        self.assertFalse(post("bilinmeyen", {})["ok"])
        for kind in ("quit", "minimize", "update", "uninstall", "settings", "copy", "open", "reminder", "permissions"):
            self.assertIn(kind, HANDLERS)


if __name__ == "__main__":
    unittest.main()
