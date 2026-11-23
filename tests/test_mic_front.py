import array
import unittest

from jarvis.heard import GatedMic, Leveler


def pcm(level: float, n: int = 1024) -> bytes:
    return array.array("h", [int(level * 32767)] * n).tobytes()


def peak_of(data: bytes) -> float:
    a = array.array("h"); a.frombytes(data)
    return max(abs(s) for s in a) / 32768.0


class GatedMicTests(unittest.TestCase):
    def test_closed_sends_silence_and_open_sends_audio(self):
        mic = GatedMic()
        self.assertEqual(mic.process(pcm(0.001), 0.001), [bytes(2048)])
        out = mic.process(pcm(0.3), 0.3)
        self.assertEqual(out[-1], pcm(0.3))

    def test_word_start_before_gate_opens_is_not_lost(self):
        mic = GatedMic()
        quiet = [pcm(0.01 + i * 0.001) for i in range(5)]
        for chunk in quiet:
            mic.process(chunk, 0.01)  # kısık ilk heceler: kapı kapalı
        out = mic.process(pcm(0.3), 0.3)
        self.assertEqual(out, [*quiet[-GatedMic.PREROLL:], pcm(0.3)])

    def test_preroll_is_sent_only_when_opening(self):
        mic = GatedMic()
        mic.process(pcm(0.01), 0.01)
        mic.process(pcm(0.3), 0.3)
        self.assertEqual(mic.process(pcm(0.3), 0.3), [pcm(0.3)])


class LevelerTests(unittest.TestCase):
    def test_quiet_speech_is_raised_but_capped(self):
        leveler = Leveler(); chunk = pcm(0.05)
        for _ in range(40):
            out = leveler.apply(chunk)
        self.assertGreater(peak_of(out), 0.15)
        self.assertLessEqual(peak_of(out), 0.05 * Leveler.MAX_GAIN + 0.001)

    def test_background_noise_is_not_amplified(self):
        leveler = Leveler(); chunk = pcm(0.01)
        self.assertEqual(leveler.apply(chunk), chunk)

    def test_loud_speech_untouched_and_gain_drops_immediately(self):
        leveler = Leveler()
        for _ in range(40):
            leveler.apply(pcm(0.05))
        loud = pcm(0.6)
        self.assertEqual(leveler.apply(loud), loud)
        self.assertAlmostEqual(leveler.gain, 1.0, delta=0.01)

    def test_no_clipping_overflow(self):
        leveler = Leveler(); leveler.gain = 4.0
        out = leveler.apply(pcm(0.9))
        self.assertLessEqual(peak_of(out), 1.0)


if __name__ == "__main__":
    unittest.main()


class TakeOverTests(unittest.TestCase):
    def run_case(self, acquires, answered):
        from jarvis.instance import take_over

        calls = []
        result = take_over(lambda: calls.append("acquire") or acquires.pop(0), lambda: calls.append("signal"),
                           lambda: calls.append("answered") or answered, lambda: calls.append("kill"), lambda s: calls.append("pause"))
        return result, calls

    def test_free_lock_just_starts(self):
        self.assertEqual(self.run_case([True], True), (True, ["acquire"]))

    def test_responsive_running_instance_is_shown_and_we_exit(self):
        self.assertEqual(self.run_case([False], True), (False, ["acquire", "signal", "answered"]))

    def test_hung_instance_is_killed_and_we_take_over(self):
        self.assertEqual(self.run_case([False, True], False), (True, ["acquire", "signal", "answered", "kill", "pause", "acquire"]))


class BrowserFrontTests(unittest.TestCase):
    def test_marker_from_url(self):
        from tools.actions.browser import _front_marker

        self.assertEqual(_front_marker("https://www.youtube.com/watch?v=abc"), "YouTube")
        self.assertEqual(_front_marker("https://music.youtube.com"), "YouTube")
        self.assertEqual(_front_marker("https://open.spotify.com/x"), "spotify")

    def test_open_url_brings_browser_to_front(self):
        from unittest import mock

        from tools.actions import browser

        with mock.patch.object(browser.webbrowser, "open") as opened, mock.patch("tools.actions.apps.front_soon") as front, \
                mock.patch.object(browser, "recently_opened", return_value=False):
            browser.open_url("https://www.youtube.com")
        opened.assert_called_once(); front.assert_called_once_with("YouTube")
