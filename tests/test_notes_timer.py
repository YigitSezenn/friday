import os
import tempfile
import unittest
from unittest import mock

from jarvis.timer import TimerState, clock, parse_seconds, spoken


class NotesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        p = mock.patch.dict(os.environ, {"JARVIS_DATA_DIR": self.tmp.name})
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_add_remove_edit(self):
        from jarvis import notes

        notes.add("süt al")
        notes.add("  faturayı   öde ")
        notes.add("ödev")
        self.assertEqual(notes.load(), ["süt al", "faturayı öde", "ödev"])
        lines, removed = notes.remove("2")
        self.assertEqual(removed, "faturayı öde")
        lines, removed = notes.remove("SÜT")
        self.assertEqual(removed, "süt al")
        self.assertEqual(lines, ["ödev"])
        self.assertEqual(notes.remove("yok")[1], None)
        lines, old = notes.edit("1", "ödevi bitir")
        self.assertEqual((lines, old), (["ödevi bitir"], "ödev"))
        self.assertEqual(notes.save([" a ", "", "b"]), ["a", "b"])


class TimerTest(unittest.TestCase):
    def test_parse_and_format(self):
        self.assertEqual(parse_seconds(minutes=10), 600)
        self.assertEqual(parse_seconds(minutes="1,5", seconds=10), 100)
        self.assertEqual(clock(65), "01:05")
        self.assertEqual(clock(3725), "1:02:05")
        self.assertEqual(spoken(90), "1 dakika 30 saniye")

    def test_countdown_add_and_fire_once(self):
        t = TimerState()
        t.set(60, "makarna", now=100)
        self.assertEqual(t.remaining(130), 30)
        self.assertTrue(t.add(120, now=130))  # süre ekle
        self.assertEqual(t.remaining(130), 150)
        self.assertIsNone(t.due(279))
        self.assertEqual(t.due(280), "makarna")
        self.assertIsNone(t.due(281))  # bir kez
        self.assertFalse(t.add(300, now=400))  # çalışmıyorsa yeni kurar
        self.assertEqual(t.remaining(400), 300)
        self.assertTrue(t.cancel())
        self.assertEqual(t.remaining(400), 0)

    def test_stopwatch(self):
        t = TimerState()
        t.watch("start", 10)
        self.assertEqual(t.elapsed(15), 5)
        t.watch("stop", 20)
        self.assertEqual(t.elapsed(99), 10)
        t.watch("toggle", 100)
        self.assertEqual(t.elapsed(103), 13)
        t.watch("reset", 104)
        self.assertEqual(t.elapsed(200), 0)


if __name__ == "__main__":
    unittest.main()
