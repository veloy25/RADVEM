import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import config
from radar import SimulatedRadar


class SimulatedRadarTests(unittest.TestCase):
    def setUp(self):
        self.radar = SimulatedRadar()

    def tearDown(self):
        self.radar.close()

    def test_reports_synthetic_target_distance(self):
        self.radar.angulo = 30

        self.assertEqual(self.radar.measure_distance(), 8.0)

    def test_reports_no_target_outside_detection_distance(self):
        self.radar.angulo = 35

        self.assertGreater(
            self.radar.measure_distance(),
            config.DETECTION_DISTANCE_CM,
        )

    def test_scan_creates_detection_for_target(self):
        self.radar.angulo = 75

        detection = self.radar.scan_position()

        self.assertIsNotNone(detection)
        self.assertEqual(detection["angle_deg"], 75)
        self.assertEqual(detection["distance_cm"], 14.0)


if __name__ == "__main__":
    unittest.main()
