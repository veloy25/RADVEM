import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from api import DetectionApi


class DetectionApiTests(unittest.TestCase):
    def test_rejects_placeholder_url(self):
        with self.assertRaises(ValueError):
            DetectionApi("http://SEU_SERVIDOR/detections")

    def test_rejects_non_positive_timeout(self):
        with self.assertRaises(ValueError):
            DetectionApi("http://localhost/detections", timeout_seconds=0)

    @patch("api.urllib.request.urlopen")
    def test_posts_detection_as_json(self, urlopen):
        response = urlopen.return_value.__enter__.return_value
        response.status = 201
        detection = {
            "radar_id": "RADVEM-001",
            "detection_id": 3,
            "angle_deg": 135.5,
            "distance_cm": 82.3,
            "x": 115,
            "y": 115,
            "timestamp": "2026-10-28T19:00:00-03:00",
        }
        client = DetectionApi("http://localhost/detections")

        try:
            client.submit(detection)
        finally:
            client.close()

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://localhost/detections")
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.get_header("Content-type"), "application/json")
        self.assertEqual(
            request.data.decode("utf-8"),
            '{"angle_degrees": 135.5, "distance_cm": 82.3, "x_cm": -58.7, "y_cm": 57.7}',
        )
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 5)


if __name__ == "__main__":
    unittest.main()
