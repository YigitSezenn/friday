import unittest

from jarvis import clap_launcher
from jarvis.startup import MemoryRegistry, apply_clap_startup, apply_windows_startup


class ListenTests(unittest.TestCase):
    def run_levels(self, levels, step=0.064):
        launched, clock = [], iter(i * step for i in range(10000))
        queue = iter(levels)
        calls = {"n": 0}

        def keep_going():
            calls["n"] += 1
            return calls["n"] <= len(levels)

        result = clap_launcher.listen(lambda: next(queue), lambda: launched.append(1), keep_going, lambda: next(clock))
        return result, launched

    def test_double_clap_launches_app_once_and_stops(self):
        result, launched = self.run_levels([0.01] * 5 + [0.8, 0.1, 0.1, 0.8] + [0.01] * 14)
        self.assertTrue(result); self.assertEqual(launched, [1])

    def test_three_claps_never_launch(self):
        result, launched = self.run_levels([0.01] * 5 + [0.8, 0.1, 0.1, 0.8, 0.1, 0.1, 0.8] + [0.01] * 20)
        self.assertFalse(result); self.assertEqual(launched, [])

    def test_noise_and_single_clap_never_launch(self):
        result, launched = self.run_levels([0.01] * 5 + [0.8, 0.1] + [0.01] * 30)
        self.assertFalse(result); self.assertEqual(launched, [])

    def test_stops_when_told_to(self):
        self.assertEqual(self.run_levels([])[0], False)


class CommandTests(unittest.TestCase):
    def test_frozen_and_dev_commands(self):
        self.assertEqual(clap_launcher.command("C:/F/FRIDAY.exe", True), ["C:/F/FRIDAY.exe", "--clap-listen"])
        self.assertEqual(clap_launcher.command("py", False), ["py", "-m", "jarvis", "--clap-listen"])


class StartupEntryTests(unittest.TestCase):
    def test_clap_startup_is_separate_from_app_startup(self):
        store = MemoryRegistry()
        apply_clap_startup(True, "C:/F/FRIDAY.exe", store)
        self.assertEqual(store.read("FRIDAY-Alkis"), '"C:/F/FRIDAY.exe" --clap-listen')
        self.assertIsNone(store.read("FRIDAY"))
        apply_windows_startup(True, "C:/F/FRIDAY.exe", store)
        self.assertEqual(store.read("FRIDAY"), '"C:/F/FRIDAY.exe"')
        apply_clap_startup(False, None, store)
        self.assertIsNone(store.read("FRIDAY-Alkis")); self.assertIsNotNone(store.read("FRIDAY"))


if __name__ == "__main__":
    unittest.main()
