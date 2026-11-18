import unittest
from unittest import mock

from tools.actions import confirm
from tools.actions.shell import is_read_only, shell_run


class ShellConfirmTest(unittest.TestCase):
    def setUp(self):
        confirm._pending.clear()

    def test_read_only_detection(self):
        for cmd in ("Get-Process | Sort-Object CPU", "ls ~/Desktop", "ipconfig /all", "Write-Output tamam", "dir C:\\ && whoami"):
            self.assertTrue(is_read_only(cmd), cmd)
        for cmd in ("Stop-Process -Name chrome", "Get-Process; Stop-Process x", "echo hi > a.txt", "iex (iwr x)",
                    "Start-Process notepad", "Get-ChildItem | ForEach-Object { rm $_ }", "& notepad", "cmd /c del x"):
            self.assertFalse(is_read_only(cmd), cmd)

    def test_changing_command_needs_confirm(self):
        with mock.patch("subprocess.run") as run:
            out = shell_run("Stop-Process -Name notepad")
            self.assertIn("ONAY GEREKLİ", out)
            self.assertIn("Çalıştırayım mı?", out)
            run.assert_not_called()
            self.assertIn("ONAY", shell_run("Stop-Process -Name notepad", confirm_run=True))  # çok erken
            run.assert_not_called()
            with mock.patch.object(confirm, "MIN_WAIT", 0):
                run.return_value = mock.Mock(stdout="", stderr="", returncode=0)
                shell_run("Stop-Process -Name notepad", confirm_run=True)
            run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
