import random
import unittest

from jarvis.oneeuro import OneEuro


class OneEuroTests(unittest.TestCase):
    def test_first_value_passes_through_and_constant_stays(self):
        f = OneEuro(1.0, 5.0)
        self.assertEqual(f(0.4, 0.0), 0.4)
        for i in range(1, 30):
            self.assertAlmostEqual(f(0.4, i / 30), 0.4)

    def test_jitter_at_rest_is_attenuated(self):
        rng = random.Random(1); f = OneEuro(1.0, 0.0)
        raw = [0.5 + rng.uniform(-0.01, 0.01) for _ in range(120)]
        out = [f(v, i / 30) for i, v in enumerate(raw)]
        spread = lambda xs: max(xs[30:]) - min(xs[30:])
        self.assertLess(spread(out), spread(raw) / 2)

    def test_fast_motion_lags_less_with_beta(self):
        def lag(beta):
            f = OneEuro(1.0, beta)
            last = 0.0
            for i in range(30):
                target = i * 0.03  # 0,9 birim/sn
                last = f(target, i / 30)
            return target - last
        self.assertLess(lag(10.0), lag(0.0) / 3)

    def test_frame_rate_independent_step_response(self):
        def settle(fps):
            f = OneEuro(2.0, 0.0); f(0.0, 0.0)
            for i in range(1, fps + 1):
                value = f(1.0, i / fps)
            return value
        self.assertAlmostEqual(settle(15), settle(60), delta=0.1)

    def test_reset_forgets_history(self):
        f = OneEuro(); f(1.0, 0.0); f.reset()
        self.assertEqual(f(0.2, 5.0), 0.2)


if __name__ == "__main__":
    unittest.main()
