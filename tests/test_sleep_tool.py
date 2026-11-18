import unittest

from tools.dispatch import TOOL_DECLARATIONS, execute_tool


class FakeUI:
    def __init__(self):
        self.scripts = []

    def _js(self, script):
        self.scripts.append(script)


class SleepToolTest(unittest.TestCase):
    def test_declared(self):
        self.assertIn("sleep_mode", {d["name"] for d in TOOL_DECLARATIONS})

    def test_sleep_and_wake_call_hud(self):
        ui = FakeUI()
        out = execute_tool("sleep_mode", {"asleep": True}, ui=ui)
        self.assertIn("Uyku", out)
        self.assertIn("window.hud.sleep(true, 2500)", ui.scripts[-1])
        execute_tool("sleep_mode", {"asleep": False}, ui=ui)
        self.assertIn("window.hud.sleep(false, 0)", ui.scripts[-1])

    def test_without_ui(self):
        self.assertIn("kullanilamiyor", execute_tool("sleep_mode", {"asleep": True}))


if __name__ == "__main__":
    unittest.main()
