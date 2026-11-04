import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, PropertyMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from radar import Radar


class RadarHardwareTests(unittest.TestCase):
    def setUp(self):
        self.servo = Mock()
        self.sensor = Mock()
        self.factory = Mock()

        gpiozero = types.ModuleType("gpiozero")
        gpiozero.Servo = Mock(return_value=self.servo)
        gpiozero.DistanceSensor = Mock(return_value=self.sensor)
        pins = types.ModuleType("gpiozero.pins")
        lgpio = types.ModuleType("gpiozero.pins.lgpio")
        lgpio.LGPIOFactory = Mock(return_value=self.factory)
        self.gpio_modules = {
            "gpiozero": gpiozero,
            "gpiozero.pins": pins,
            "gpiozero.pins.lgpio": lgpio,
        }

    def test_sensor_uses_only_the_latest_measurement(self):
        distance_sensor = self.gpio_modules["gpiozero"].DistanceSensor
        with patch.dict(sys.modules, self.gpio_modules):
            radar = Radar()

        distance_sensor.assert_called_once()
        sensor_options = distance_sensor.call_args.kwargs
        self.assertEqual(sensor_options["queue_len"], 1)
        radar.close()

    def test_scan_waits_for_sensor_cycle_after_positioning_servo(self):
        events = []

        with patch.dict(sys.modules, self.gpio_modules):
            radar = Radar()

        with patch.object(
            type(self.servo), "value", new_callable=PropertyMock, create=True
        ) as servo_value:
            with patch.object(
                type(self.sensor), "distance", new_callable=PropertyMock, create=True
            ) as sensor_distance:
                with patch(
                    "radar.time.sleep",
                    side_effect=lambda delay: events.append(("sleep", delay)),
                ):
                    servo_value.side_effect = lambda value: events.append(
                        ("servo", value)
                    )
                    sensor_distance.side_effect = (
                        lambda: events.append(("measure",)) or 0.5
                    )
                    radar.scan_position()

        self.assertEqual(events, [("servo", -1.0), ("sleep", 0.06), ("measure",)])
        radar.close()


if __name__ == "__main__":
    unittest.main()
