import json
import unittest

from jarvis import __version__
from jarvis.patchnotes import load_local, merge, parse


class PatchNotesTests(unittest.TestCase):
    def test_bundled_notes_cover_current_version(self):
        entries = load_local()
        self.assertTrue(entries)
        self.assertEqual(entries[0]["surum"], __version__, "sürüm çıkarken yenilikler.json'a satır eklenmeli")

    def test_parse_ignores_junk(self):
        raw = json.dumps({"surumler": [{"surum": "x"}, {"surum": "4.1.0", "maddeler": ["a", "", "b"]}, 7]})
        entries = parse(raw)
        self.assertEqual([e["surum"] for e in entries], ["4.1.0"])
        self.assertEqual(entries[0]["maddeler"], ["a", "b"])
        self.assertEqual(parse("{bozuk"), [])

    def test_merge_sorts_newest_first_and_prefers_first_list(self):
        remote = [{"surum": "4.12.0", "tarih": "", "baslik": "r", "maddeler": []}, {"surum": "4.11.0", "tarih": "", "baslik": "uzak", "maddeler": []}]
        local = [{"surum": "4.11.0", "tarih": "", "baslik": "yerel", "maddeler": []}, {"surum": "4.9.0", "tarih": "", "baslik": "", "maddeler": []}]
        merged = merge(remote, local)
        self.assertEqual([e["surum"] for e in merged], ["4.12.0", "4.11.0", "4.9.0"])
        self.assertEqual(merged[1]["baslik"], "uzak")


if __name__ == "__main__":
    unittest.main()
