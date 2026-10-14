import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from display import RadarDisplay


class RadarDisplayTests(unittest.TestCase):
    def setUp(self):
        self.display = RadarDisplay.__new__(RadarDisplay)
        self.display.canvas = Mock()
        self.display.sweep_line = 1

    def test_draws_zero_degree_sweep_to_right(self):
        self.display._draw_angle(0)

        self.display.canvas.coords.assert_called_once_with(
            1,
            400,
            390,
            730.0,
            390.0,
        )

    def test_draws_ninety_degree_sweep_upward(self):
        self.display._draw_angle(90)

        coordinates = self.display.canvas.coords.call_args.args
        self.assertAlmostEqual(coordinates[3], 400)
        self.assertAlmostEqual(coordinates[4], 60)


if __name__ == "__main__":
    unittest.main()
