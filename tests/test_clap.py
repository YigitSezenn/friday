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
    SOFT = QUIET + [0.14, 0.01, 0.01, 0.14] + SETTLE

    def test_default_needs_a_real_clap_not_a_whisper(self):
        self.assertEqual(run(self.SOFT), [])

    def test_higher_sensitivity_catches_softer_claps(self):
        self.assertEqual([c for _, c in run(self.SOFT, sensitivity=2.0)], [2])

    def test_lower_sensitivity_ignores_medium_claps(self):
        medium = QUIET + [0.3, 0.01, 0.01, 0.3] + SETTLE
        self.assertEqual([c for _, c in run(medium)], [2])
        self.assertEqual(run(medium, sensitivity=0.5), [])

    def test_set_sensitivity_is_clamped(self):
        d = ClapDetector(); d.set_sensitivity(99); self.assertAlmostEqual(d.loud, 0.1)
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
