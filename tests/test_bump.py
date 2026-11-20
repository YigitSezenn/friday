import shutil
import tempfile
import unittest
from pathlib import Path

from tools import bump_version

ROOT = Path(__file__).resolve().parents[1]


class BumpTest(unittest.TestCase):
    def test_bump_updates_every_file_and_keeps_encoding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in ("jarvis/__init__.py", "packaging/friday.iss", "phone-android/app/build.gradle.kts", "site/index.html"):
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(ROOT / rel, root / rel)
            bump_version.bump("9.8.7", root)
            self.assertIn('__version__ = "9.8.7"', (root / "jarvis/__init__.py").read_text(encoding="utf-8"))
            iss = (root / "packaging/friday.iss").read_bytes()
            self.assertTrue(iss.startswith(b"\xef\xbb\xbf"))
            self.assertIn("AppVersion=9.8.7", iss.decode("utf-8-sig"))
            self.assertIn("kaldır", iss.decode("utf-8-sig"))
            kts = (root / "phone-android/app/build.gradle.kts").read_text(encoding="utf-8")
            self.assertIn('versionName = "9.8.7"', kts)
            self.assertIn("versionCode = 90807", kts)
            html = (root / "site/index.html").read_text(encoding="utf-8")
            self.assertIn("Sürüm 9.8.7", html)
            self.assertNotIn("?v=4.", html)

    def test_version_code(self):
        self.assertEqual(bump_version.version_code("4.10.3"), 41003)
        self.assertEqual(bump_version.version_code("5.0"), 50000)

    def test_installer_root_overridable_for_ci(self):
        iss = (ROOT / "packaging/friday.iss").read_bytes().decode("utf-8-sig")
        self.assertIn("#ifndef AppRoot", iss)


if __name__ == "__main__":
    unittest.main()
