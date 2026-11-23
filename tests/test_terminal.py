import subprocess
import unittest
from unittest import mock

from tools.actions import apps, shell


class TerminalTests(unittest.TestCase):
    def test_terminal_commands_are_recognized_only_when_bare(self):
        for text, kind in (("cmd", "cmd"), ("CMD.exe", "cmd"), ("start  cmd", "cmd"), ("powershell", "powershell"), ("wt", "terminal")):
            self.assertEqual(shell.terminal_kind(text), kind)
        for text in ("cmd /c dir", "dir", "ipconfig", "echo cmd", ""):
            self.assertEqual(shell.terminal_kind(text), "")

    def test_shell_run_cmd_opens_visible_persistent_console_without_confirmation(self):
        with mock.patch.object(subprocess, "Popen") as popen:
            out = shell.shell_run("cmd")
        self.assertIn("açıldı", out)
        argv = popen.call_args.args[0]
        self.assertEqual(argv, ["cmd.exe", "/k"])
        self.assertEqual(popen.call_args.kwargs["creationflags"], getattr(subprocess, "CREATE_NEW_CONSOLE", 0))

    def test_open_app_cmd_and_powershell(self):
        with mock.patch.object(subprocess, "Popen") as popen:
            self.assertIn("Komut istemi açıldı", apps._open_app("CMD"))
            self.assertIn("PowerShell açıldı", apps._open_app("powershell"))
        self.assertEqual([c.args[0][0] for c in popen.call_args_list], ["cmd.exe", "powershell.exe"])

    def test_windows_terminal_falls_back_to_powershell(self):
        calls = []

        def popen(argv, **kwargs):
            calls.append(argv[0])
            if argv[0] == "wt.exe":
                raise OSError("yok")

        with mock.patch.object(subprocess, "Popen", side_effect=popen):
            self.assertIn("Terminal açıldı", shell.open_terminal("terminal"))
        self.assertEqual(calls, ["wt.exe", "powershell.exe"])


if __name__ == "__main__":
    unittest.main()
