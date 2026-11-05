"""Bug condition exploration test for the API runtime toggle.

This file encodes the EXPECTED (fixed) behaviour for the API toggle feature.
On the UNFIXED code every test here is expected to FAIL:

  * ``config.API_ENABLED`` is ``True`` on the unfixed code (the README documents
    it as ``False``), so ``ConfigDefaultTests`` fails with ``AssertionError``.
  * The ``ApiToggle`` coordinator does not exist on the unfixed code, so
    ``ApiToggleBugConditionTests`` fails with ``ImportError`` (the class and its
    module ``src/api_toggle.py`` are missing).

The ``DetectionApi`` HTTP client is mocked with ``unittest.mock.patch`` so no
real HTTP client or worker thread is ever created.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import config

from hypothesis import given, strategies as st


URL = "http://localhost/detections"
TIMEOUT = 5


def _detection():
    return {
        "radar_id": "RADVEM-001",
        "detection_id": 1,
        "timestamp": "2026-10-28T19:00:00-03:00",
        "angle_deg": 45,
        "distance_cm": 12.5,
        "x": 420,
        "y": 260,
    }


def _client_factory(created):
    """Return a side_effect that records every constructed client mock."""

    def factory(*args, **kwargs):
        client = MagicMock()
        created.append(client)
        return client

    return factory


class ConfigDefaultTests(unittest.TestCase):
    def test_api_enabled_defaults_to_false(self):
        # **Validates: Requirements 1.3**
        # The README documents the integration as disabled by default.
        self.assertEqual(config.API_ENABLED, False)


class ApiToggleBugConditionTests(unittest.TestCase):
    def setUp(self):
        # Lazy import so the config test (above) can surface its own
        # AssertionError independently of the missing ApiToggle module.
        from api_toggle import ApiToggle

        self.ApiToggle = ApiToggle

    def test_class_exposes_required_methods(self):
        # **Validates: Requirements 1.1, 1.2**
        for method in ("enable", "disable", "submit", "is_enabled", "close"):
            self.assertTrue(
                callable(getattr(self.ApiToggle, method, None)),
                f"ApiToggle deve expor {method}()",
            )

    def test_enabled_by_default_when_enabled_true(self):
        # **Validates: Requirements 2.1**
        with patch("api_toggle.DetectionApi") as mock_api:
            created = []
            mock_api.side_effect = _client_factory(created)

            toggle = self.ApiToggle(URL, timeout_seconds=TIMEOUT, enabled=True)
            self.assertTrue(toggle.is_enabled())
            self.assertEqual(len(created), 1)

    def test_disabled_by_default_when_enabled_false(self):
        # **Validates: Requirements 2.1**
        with patch("api_toggle.DetectionApi") as mock_api:
            created = []
            mock_api.side_effect = _client_factory(created)

            toggle = self.ApiToggle(URL, timeout_seconds=TIMEOUT, enabled=False)
            self.assertFalse(toggle.is_enabled())
            self.assertEqual(len(created), 0)

    def test_enable_creates_client_when_disabled(self):
        # **Validates: Requirements 2.2**
        with patch("api_toggle.DetectionApi") as mock_api:
            created = []
            mock_api.side_effect = _client_factory(created)

            toggle = self.ApiToggle(URL, timeout_seconds=TIMEOUT, enabled=False)
            self.assertFalse(toggle.is_enabled())

            toggle.enable()
            self.assertTrue(toggle.is_enabled())
            self.assertEqual(len(created), 1)

    def test_disable_closes_client_when_enabled(self):
        # **Validates: Requirements 2.3**
        with patch("api_toggle.DetectionApi") as mock_api:
            created = []
            mock_api.side_effect = _client_factory(created)

            toggle = self.ApiToggle(URL, timeout_seconds=TIMEOUT, enabled=True)
            self.assertTrue(toggle.is_enabled())

            toggle.disable()
            self.assertFalse(toggle.is_enabled())
            self.assertEqual(len(created), 1)
            created[0].close.assert_called_once()

    def test_re_enable_creates_fresh_client(self):
        # **Validates: Requirements 2.4**
        with patch("api_toggle.DetectionApi") as mock_api:
            created = []
            mock_api.side_effect = _client_factory(created)

            toggle = self.ApiToggle(URL, timeout_seconds=TIMEOUT, enabled=True)
            first = created[0]

            toggle.disable()
            toggle.enable()

            self.assertTrue(toggle.is_enabled())
            self.assertEqual(len(created), 2)
            self.assertIsNot(created[1], first)
            first.close.assert_called_once()
            created[1].close.assert_not_called()

    def test_submit_routes_to_client_when_enabled(self):
        with patch("api_toggle.DetectionApi") as mock_api:
            created = []
            mock_api.side_effect = _client_factory(created)

            toggle = self.ApiToggle(URL, timeout_seconds=TIMEOUT, enabled=True)
            detection = _detection()
            toggle.submit(detection)

            created[0].submit.assert_called_once_with(detection)

    def test_submit_is_noop_when_disabled(self):
        with patch("api_toggle.DetectionApi") as mock_api:
            created = []
            mock_api.side_effect = _client_factory(created)

            toggle = self.ApiToggle(URL, timeout_seconds=TIMEOUT, enabled=False)
            # Must not raise and must not touch any client.
            toggle.submit(_detection())

            mock_api.assert_not_called()
            self.assertEqual(created, [])

    def test_close_is_idempotent(self):
        with patch("api_toggle.DetectionApi") as mock_api:
            created = []
            mock_api.side_effect = _client_factory(created)

            toggle = self.ApiToggle(URL, timeout_seconds=TIMEOUT, enabled=True)

            toggle.close()
            # Calling close() a second time must not raise.
            toggle.close()

            self.assertFalse(toggle.is_enabled())
            created[0].close.assert_called_once()

    @given(actions=st.lists(st.sampled_from(["enable", "disable"]), max_size=15))
    def test_toggle_state_machine_properties(self, actions):
        # **Validates: Requirements 2.2, 2.3, 2.4**
        with patch("api_toggle.DetectionApi") as mock_api:
            created = []
            mock_api.side_effect = _client_factory(created)

            toggle = self.ApiToggle(URL, timeout_seconds=TIMEOUT, enabled=False)

            # Model the state machine: ``enable`` only creates a client when
            # currently disabled; ``disable`` only closes the active client.
            active = None  # index into ``created`` of the current client
            disabled_indices = []

            for action in actions:
                if action == "enable":
                    toggle.enable()
                    if active is None:
                        active = len(created) - 1
                else:  # "disable"
                    if active is not None:
                        disabled_indices.append(active)
                    toggle.disable()
                    active = None

            # Property: is_enabled() is True iff the last action was enable().
            expected_enabled = bool(actions) and actions[-1] == "enable"
            self.assertEqual(toggle.is_enabled(), expected_enabled)

            # Property: submit() routes to a client iff enabled.
            detection = _detection()
            toggle.submit(detection)
            if expected_enabled:
                created[active].submit.assert_called_once_with(detection)
            else:
                for client in created:
                    client.submit.assert_not_called()

            # Property: after any disable(), the previous client's close()
            # was called exactly once.
            for idx in disabled_indices:
                self.assertEqual(created[idx].close.call_count, 1)

            # The currently active client (if any) must not have been closed.
            if active is not None:
                self.assertEqual(created[active].close.call_count, 0)

            # Cleanup (after assertions) so no resources linger.
            toggle.close()


class DisabledApiLocalProcessingPreservationTests(unittest.TestCase):
    """Preservation: disabled API processes detections locally (Requirement 3.2).

    NOTE: This test requires the ``ApiToggle`` class from task 4.  On unfixed
    code it fails with ``ImportError`` (expected).  After the fix it passes,
    confirming that a disabled toggle is a no-op for ``submit()``.
    """

    def test_submit_is_noop_when_disabled(self):
        # **Validates: Requirements 3.2**
        from api_toggle import ApiToggle

        with patch("api_toggle.DetectionApi") as mock_api:
            created = []
            mock_api.side_effect = _client_factory(created)

            toggle = ApiToggle(URL, timeout_seconds=TIMEOUT, enabled=False)
            self.assertFalse(toggle.is_enabled())

            # submit must not raise and must not create or call any client.
            toggle.submit(_detection())

            mock_api.assert_not_called()
            self.assertEqual(created, [])

            toggle.close()


if __name__ == "__main__":
    unittest.main()
