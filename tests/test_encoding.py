import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOJIBAKE = ("Ã", "Ä±", "Å", "Ã¢â", "â€")


class EncodingTest(unittest.TestCase):
    """Yayın betiği UTF-8 dosyaları bozmasın (bozuk kısayol adı kurulumu düşürüyordu)."""

    def test_installer_script_is_utf8_with_bom_and_clean(self):
        raw = (ROOT / "packaging" / "friday.iss").read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"), "Inno Setup UTF-8'i yalnızca BOM ile okur")
        text = raw.decode("utf-8-sig")
        self.assertIn("kaldır", text)
        for bad in MOJIBAKE:
            self.assertNotIn(bad, text)

    def test_version_files_are_clean(self):
        for rel in ("jarvis/__init__.py", "phone-android/app/build.gradle.kts", "packaging/friday.iss"):
            text = (ROOT / rel).read_bytes().decode("utf-8-sig")
            for bad in MOJIBAKE:
                self.assertNotIn(bad, text, rel)

    def test_release_script_reads_utf8(self):
        script = (ROOT / "tools" / "release.ps1").read_bytes().decode("utf-8-sig")
        self.assertNotIn("Get-Content $iss", script)
        self.assertIn("Write-Utf8Bom $iss", script)
        # PowerShell 5.1 BOM'suz .ps1'i ANSI okur; "Sürüm" gibi dizgeler bozulur.
        self.assertTrue((ROOT / "tools" / "release.ps1").read_bytes().startswith(b"\xef\xbb\xbf"))


if __name__ == "__main__":
    unittest.main()
