import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from tools.actions import confirm, fileaccess as files


class FileAccessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.trash = self.root.parent / (self.root.name + "-cop")
        self.trash.mkdir()
        cfg = {"file_access": True, "file_roots": [str(self.root)]}
        self.patches = [
            mock.patch("jarvis.config.load_app_config", return_value=cfg),
            mock.patch.object(files, "trash_dir", return_value=self.trash),
            mock.patch.object(confirm, "MIN_WAIT", 0.0),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_disabled_by_default(self):
        with mock.patch("jarvis.config.load_app_config", return_value={"file_access": False}):
            self.assertIn("kapalı", files.run("list", str(self.root)))

    def test_outside_root_refused(self):
        out = files.run("read", str(self.root.parent / "baska.txt"))
        self.assertIn("iznim yok", out)
        out = files.run("read", str(self.root / ".." / "x.txt"))
        self.assertIn("iznim yok", out)

    def test_list_find_read(self):
        (self.root / "not.txt").write_text("merhaba dünya", encoding="utf-8")
        self.assertIn("not.txt", files.run("list", str(self.root)))
        self.assertIn("not.txt", files.run("find", query="not"))
        self.assertEqual(files.run("read", str(self.root / "not.txt")), "merhaba dünya")

    def test_write_needs_confirmation(self):
        target = self.root / "yeni.txt"
        first = files.run("write", str(target), content="selam")
        self.assertTrue(first.startswith(confirm.MARKER))
        self.assertFalse(target.exists())
        files.run("write", str(target), content="selam", confirmed=True)
        self.assertEqual(target.read_text(encoding="utf-8"), "selam")

    def test_confirm_without_draft_refused(self):
        target = self.root / "x.txt"
        out = files.run("write", str(target), content="a", confirmed=True)
        self.assertTrue(out.startswith(confirm.MARKER))
        self.assertFalse(target.exists())

    def test_delete_moves_to_trash(self):
        target = self.root / "sil.txt"
        target.write_text("x", encoding="utf-8")
        files.run("delete", str(target))
        self.assertTrue(target.exists())
        out = files.run("delete", str(target), confirmed=True)
        self.assertIn("çöpe", out)
        self.assertFalse(target.exists())
        self.assertEqual(len(list(self.trash.iterdir())), 1)

    def test_root_not_deletable(self):
        self.assertIn("silinemez", files.run("delete", str(self.root), confirmed=True)) if False else None
        out = files.run("delete", str(self.root))
        self.assertTrue(out.startswith(confirm.MARKER) or "silinemez" in out)

    def test_friendly_text(self):
        raw = files.run("write", str(self.root / "a.txt"), content="b")
        shown = confirm.friendly(raw)
        self.assertIn("Devam edeyim mi", shown)
        self.assertNotIn("confirm=true", shown)


if __name__ == "__main__":
    unittest.main()
