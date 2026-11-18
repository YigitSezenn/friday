import sys
import unittest

from jarvis import win32


class Win32Test(unittest.TestCase):
    def test_safe_off_windows(self):
        if sys.platform == "win32":
            self.skipTest("Windows'ta gerçek pano kullanılır")
        self.assertFalse(win32.set_clipboard("merhaba"))
        self.assertEqual(win32.foreground_title(), "")
        win32.press_keys(0x0D)  # sessizce hiçbir şey yapmaz

    def test_pointer_returning_calls_are_typed(self):
        if sys.platform != "win32":
            self.skipTest("yalnızca Windows")
        import ctypes

        _c, _user32, kernel32 = win32._lib()
        self.assertIs(kernel32.GlobalLock.restype, ctypes.c_void_p)


if __name__ == "__main__":
    unittest.main()
