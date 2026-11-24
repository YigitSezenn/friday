import unittest

from jarvis.audio.clap import ClapDetector


def run(levels, step=0.064, sensitivity=1.0):
    detector, hits = ClapDetector(sensitivity), []
    for i, level in enumerate(levels):
        count = detector.feed(level, i * step)
        if count:
            hits.append((i, count))
    return hits


QUIET = [0.01] * 5
SETTLE = [0.01] * 14  # ~0,9 sn sessizlik: sayı kesinleşir


class ClapCountTests(unittest.TestCase):
    def test_two_claps_return_two(self):
        self.assertEqual([c for _, c in run(QUIET + [0.8, 0.1, 0.1, 0.8] + SETTLE)], [2])

    def test_three_claps_return_three(self):
        self.assertEqual([c for _, c in run(QUIET + [0.8, 0.1, 0.1, 0.8, 0.1, 0.1, 0.8] + SETTLE)], [3])

    def test_decision_waits_for_the_third_clap(self):
        hits = run(QUIET + [0.8, 0.1, 0.1, 0.8, 0.1, 0.1, 0.8] + SETTLE)
        self.assertEqual(hits[0][0], 5 + 7 + 10)  # son alkıştan ~0,7 sn sonra, ikinci alkışta değil

    def test_single_clap_does_nothing(self):
        self.assertEqual(run(QUIET + [0.8, 0.1] + SETTLE * 3), [])

    def test_slow_pair_is_two_single_claps(self):
        self.assertEqual(run(QUIET + [0.8] + SETTLE + [0.8, 0.1] + SETTLE), [])

    def test_one_clap_spanning_two_chunks_is_single(self):
        self.assertEqual(run(QUIET + [0.8, 0.6, 0.1] + SETTLE), [])

    def test_steady_loud_noise_never_triggers(self):
        self.assertEqual(run([0.5] * 80), [])

    def test_four_or_more_claps_are_noise(self):
        levels = QUIET + [0.8, 0.1, 0.1] * 4 + SETTLE
        self.assertEqual(run(levels), [])

    def test_cooldown_blocks_immediate_repeat(self):
        levels = QUIET + [0.8, 0.1, 0.1, 0.8] + SETTLE[:11] + [0.8, 0.1, 0.1, 0.8] + SETTLE
        self.assertEqual(len(run(levels)), 1)


class SensitivityTests(unittest.TestCase):
    SOFT = QUIET + [0.25, 0.01, 0.01, 0.25] + SETTLE

    def test_default_needs_a_real_clap_not_a_whisper(self):
        self.assertEqual(run(self.SOFT), [])

    def test_speech_level_peaks_never_wake_it(self):
        speech = QUIET + [0.2, 0.01, 0.2, 0.01, 0.2, 0.01, 0.18, 0.01] + SETTLE  # bu mikrofonda normal konuşma tepe ~0,2
        self.assertEqual(run(speech), [])

    def test_higher_sensitivity_catches_softer_claps(self):
        self.assertEqual([c for _, c in run(self.SOFT, sensitivity=2.0)], [2])

    def test_lower_sensitivity_ignores_medium_claps(self):
        medium = QUIET + [0.5, 0.01, 0.01, 0.5] + SETTLE
        self.assertEqual([c for _, c in run(medium)], [2])
        self.assertEqual(run(medium, sensitivity=0.5), [])

    def test_set_sensitivity_is_clamped(self):
        d = ClapDetector(); d.set_sensitivity(99); self.assertAlmostEqual(d.loud, 0.14)
        d.set_sensitivity(0); self.assertGreater(d.loud, 0.0)


class ClapSettingTests(unittest.TestCase):
    def test_defaults(self):
        from jarvis import config

        self.assertIs(config.DEFAULT_CONFIG["clap_wake"], False)
        self.assertEqual(config.DEFAULT_CONFIG["clap_sensitivity"], 100)
        self.assertEqual(config._clean_clap_sensitivity("999"), 200)
        self.assertEqual(config._clean_clap_sensitivity("x"), 100)


if __name__ == "__main__":
    unittest.main()


class ClapShapeTests(unittest.TestCase):
    """Sentetik sesler (16 kHz, 1024 örnek): alkış kısa/keskin/geniş bantlı; öteki sesler yüksek olsa da sayılmaz."""

    RATE = 16000

    def pcm(self, fn, amp=0.6, n=1024, seed=3):
        import array
        import math
        import random

        rng = random.Random(seed)
        return array.array("h", [int(max(-1, min(1, amp * fn(i / self.RATE, rng))) * 32767) for i in range(n)]).tobytes(), math

    def clap(self, offset=0.012, tau=0.006, amp=0.7):
        import math

        data, _ = self.pcm(lambda t, rng: (rng.uniform(-1, 1) * math.exp(-(t - offset) / tau)) if t >= offset else rng.uniform(-1, 1) * 0.004, amp)
        return data

    def test_clap_counts_as_level_others_do_not(self):
        import math

        from jarvis.audio.clap import clap_level

        self.assertGreater(clap_level(self.clap()), 0.3)
        speech, _ = self.pcm(lambda t, rng: sum(math.sin(2 * math.pi * 130 * k * t) / k for k in range(1, 8)) * 0.2)
        thump, _ = self.pcm(lambda t, rng: math.sin(2 * math.pi * 70 * t) * math.exp(-t / 0.03))
        hum, _ = self.pcm(lambda t, rng: rng.uniform(-1, 1) * 0.6)  # sürekli geniş bantlı gürültü
        tone, _ = self.pcm(lambda t, rng: math.sin(2 * math.pi * 1000 * t))
        for name, data in (("konuşma", speech), ("gümleme", thump), ("uğultu", hum), ("ton", tone), ("sessizlik", bytes(2048))):
            self.assertEqual(clap_level(data), 0.0, name)

    def test_clap_at_chunk_edges_still_counts(self):
        from jarvis.audio.clap import clap_level

        self.assertGreater(clap_level(self.clap(offset=0.002)), 0.3)  # başta
        self.assertGreater(clap_level(self.clap(offset=0.055)), 0.3)  # sonda: sönüş görülmez ama keskinlik yeter

    def test_two_claps_through_the_detector_count_as_two(self):
        from jarvis.audio.clap import clap_level

        quiet = bytes(2048)
        chunks = [quiet] * 5 + [self.clap(), quiet, quiet, self.clap(offset=0.014)] + [quiet] * 14
        detector, hits = ClapDetector(), []
        for i, chunk in enumerate(chunks):
            count = detector.feed(clap_level(chunk), i * 0.064)
            if count:
                hits.append(count)
        self.assertEqual(hits, [2])


class ClapRobustnessTests(ClapShapeTests):
    def test_reverberant_clap_with_a_long_tail_counts(self):
        from jarvis.audio.clap import clap_level

        self.assertGreater(clap_level(self.clap(tau=0.025)), 0.3)

    def test_rejected_loud_sound_is_written_to_the_debug_log_once_per_second(self):
        import math

        from jarvis.audio.clap import debug_rejected

        hum, _ = self.pcm(lambda t, rng: rng.uniform(-1, 1) * 0.6)
        lines = []
        debug_rejected(hum, 100.0, lines.append); debug_rejected(hum, 100.3, lines.append); debug_rejected(hum, 101.5, lines.append)
        self.assertEqual(len(lines), 2)
        self.assertIn("sharp=", lines[0])
        debug_rejected(self.clap(), 200.0, lines.append)  # kabul edilen alkış günlüğe yazılmaz
        self.assertEqual(len(lines), 2)
