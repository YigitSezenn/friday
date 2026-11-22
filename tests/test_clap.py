import unittest

from jarvis.audio.clap import ClapDetector


def run(levels, step=0.064):
    detector, hits = ClapDetector(), []
    for i, level in enumerate(levels):
        if detector.feed(level, i * step):
            hits.append(i)
    return hits


QUIET = [0.01] * 5


class ClapTests(unittest.TestCase):
    def test_double_clap_wakes(self):
        self.assertEqual(run(QUIET + [0.8, 0.1, 0.1, 0.8, 0.1] + QUIET), [8])

    def test_single_clap_does_nothing(self):
        self.assertEqual(run(QUIET + [0.8, 0.1] + [0.01] * 30), [])

    def test_slow_pair_is_not_a_double_clap(self):
        self.assertEqual(run(QUIET + [0.8] + [0.01] * 20 + [0.8, 0.1]), [])

    def test_one_clap_spanning_two_chunks_is_single(self):
        self.assertEqual(run(QUIET + [0.8, 0.6, 0.1] + QUIET), [])

    def test_steady_loud_noise_never_triggers(self):
        self.assertEqual(run([0.5] * 60), [])

    def test_cooldown_blocks_immediate_second_wake(self):
        self.assertEqual(run(QUIET + [0.8, 0.1, 0.1, 0.8, 0.1, 0.1, 0.8, 0.1, 0.1, 0.8, 0.1]), [8])


class ClapSettingTests(unittest.TestCase):
    def test_off_by_default(self):
        from jarvis import config

        self.assertIs(config.DEFAULT_CONFIG["clap_wake"], False)


if __name__ == "__main__":
    unittest.main()
