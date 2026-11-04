import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hypothesis import given, settings, strategies as st

import config
from radar import Radar, SimulatedRadar


def correct_linear_mapping(angle, angle_min, angle_max):
    """The config-driven linear mapping the fixed code should implement."""
    span = angle_max - angle_min
    if span <= 0:
        return 0.0
    return 2.0 * (angle - angle_min) / span - 1.0


class ServoFormulaStaticMethodTests(unittest.TestCase):
    """Concrete failing cases encoding expected behavior.

    Validates: Requirements 1.4, 1.5, 2.5, 2.6, 2.7

    On unfixed code Radar has no _angle_to_servo_value static method, so every
    test below fails with AttributeError — confirming the bug exists.
    """

    def test_angle_max_maps_to_positive_one(self):
        # Requirement 1.4 / 2.6
        self.assertEqual(Radar._angle_to_servo_value(config.ANGLE_MAX), 1.0)

    def test_angle_min_maps_to_negative_one(self):
        # Requirement 2.5
        self.assertEqual(Radar._angle_to_servo_value(config.ANGLE_MIN), -1.0)

    def test_sweep_midpoint_maps_to_zero(self):
        # Requirement 2.7
        midpoint = (config.ANGLE_MIN + config.ANGLE_MAX) / 2
        self.assertEqual(Radar._angle_to_servo_value(midpoint), 0.0)

    def test_angle_ninety_maps_to_zero_point_two(self):
        # Requirement 1.5
        expected = 2 * (90 - config.ANGLE_MIN) / (config.ANGLE_MAX - config.ANGLE_MIN) - 1
        self.assertEqual(Radar._angle_to_servo_value(90), expected)
        self.assertAlmostEqual(Radar._angle_to_servo_value(90), 0.2)


class ServoFormulaPropertyTests(unittest.TestCase):
    """Property-based tests for the config-driven servo mapping.

    Validates: Requirements 2.5, 2.6, 2.7
    """

    @given(
        angle=st.floats(
            min_value=config.ANGLE_MIN,
            max_value=config.ANGLE_MAX,
            allow_nan=False,
            allow_infinity=False,
        )
    )
    @settings(max_examples=100)
    def test_linear_mapping_holds_across_sweep_range(self, angle):
        expected = correct_linear_mapping(
            angle, config.ANGLE_MIN, config.ANGLE_MAX
        )
        self.assertAlmostEqual(
            Radar._angle_to_servo_value(angle), expected, places=7
        )

    @given(
        angle_min=st.floats(
            min_value=-180.0, max_value=180.0, allow_nan=False, allow_infinity=False
        ),
        angle_max=st.floats(
            min_value=-180.0, max_value=180.0, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100)
    def test_endpoints_hold_for_random_valid_configs(self, angle_min, angle_max):
        # Skip degenerate configs where ANGLE_MIN is not strictly below ANGLE_MAX.
        if angle_min >= angle_max:
            return

        original_min = config.ANGLE_MIN
        original_max = config.ANGLE_MAX
        config.ANGLE_MIN = angle_min
        config.ANGLE_MAX = angle_max
        try:
            self.assertAlmostEqual(
                Radar._angle_to_servo_value(angle_min), -1.0, places=7
            )
            self.assertAlmostEqual(
                Radar._angle_to_servo_value(angle_max), 1.0, places=7
            )
            midpoint = (angle_min + angle_max) / 2
            self.assertAlmostEqual(
                Radar._angle_to_servo_value(midpoint), 0.0, places=7
            )
        finally:
            config.ANGLE_MIN = original_min
            config.ANGLE_MAX = original_max


class SimulatedRadarSetAngleNoopPreservationTests(unittest.TestCase):
    """Preservation: SimulatedRadar.set_angle is a no-op (Requirement 3.5).

    SimulatedRadar overrides set_angle with ``pass``, so the hardware servo
    formula is never called and no ``servo`` attribute is ever set.  This
    behaviour must be preserved after the formula fix.
    """

    @given(
        angle=st.floats(allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_set_angle_is_noop_without_servo(self, angle):
        # **Validates: Requirements 3.5**
        radar = SimulatedRadar()
        try:
            radar.set_angle(angle)
            self.assertFalse(hasattr(radar, "servo"))
        finally:
            radar.close()


class SweepBoundariesPreservationTests(unittest.TestCase):
    """Preservation: sweep oscillates between ANGLE_MIN and ANGLE_MAX (Requirement 3.6).

    ``Radar.update`` (inherited by ``SimulatedRadar``) must keep the sweep
    angle within ``[config.ANGLE_MIN, config.ANGLE_MAX]`` and bounce at both
    boundaries.  This behaviour is unchanged by the servo formula fix.
    """

    @given(
        start_angle=st.floats(
            min_value=config.ANGLE_MIN,
            max_value=config.ANGLE_MAX,
            allow_nan=False,
            allow_infinity=False,
        ),
        steps=st.integers(min_value=1, max_value=60),
    )
    @settings(max_examples=50, deadline=None)
    def test_angle_remains_within_bounds(self, start_angle, steps):
        # **Validates: Requirements 3.6**
        with patch("radar.time.sleep"):
            radar = SimulatedRadar()
            try:
                radar.ativo = True
                radar.angulo = start_angle
                for _ in range(steps):
                    radar.update()
                self.assertGreaterEqual(radar.angulo, config.ANGLE_MIN)
                self.assertLessEqual(radar.angulo, config.ANGLE_MAX)
            finally:
                radar.close()

    def test_angle_bounces_at_both_boundaries(self):
        # **Validates: Requirements 3.6**
        with patch("radar.time.sleep"):
            radar = SimulatedRadar()
            try:
                radar.ativo = True
                radar.angulo = config.ANGLE_MIN

                reached_max = False
                reached_min = False
                for _ in range(80):
                    radar.update()
                    if radar.angulo >= config.ANGLE_MAX:
                        reached_max = True
                    if radar.angulo <= config.ANGLE_MIN and reached_max:
                        reached_min = True

                self.assertTrue(reached_max, "Angle should reach ANGLE_MAX")
                self.assertTrue(reached_min, "Angle should return to ANGLE_MIN")
            finally:
                radar.close()


class ClampingPreservationTests(unittest.TestCase):
    """Preservation: servo value clamped to [-1.0, 1.0] (Requirement 3.4).

    NOTE: This test requires the ``_angle_to_servo_value`` static method added
    in task 5.  On unfixed code it fails with ``AttributeError`` (expected).
    After the fix it passes, confirming the clamp is preserved.
    """

    @given(
        angle=st.floats(
            min_value=-360.0,
            max_value=360.0,
            allow_nan=False,
            allow_infinity=False,
        )
    )
    @settings(max_examples=100)
    def test_servo_value_within_range(self, angle):
        # **Validates: Requirements 3.4**
        value = Radar._angle_to_servo_value(angle)
        self.assertGreaterEqual(value, -1.0)
        self.assertLessEqual(value, 1.0)


if __name__ == "__main__":
    unittest.main()
