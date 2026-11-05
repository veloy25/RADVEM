# Implementation Plan

## Overview

This plan implements fixes for two independent bugs in the RADVEM radar application:

1. **API runtime toggle** — `config.API_ENABLED` defaults to `True` (contradicting the README), and there is no UI control to enable/disable the API at runtime. The fix changes the default to `False` and adds an `ApiToggle` coordinator plus a Tkinter checkbox.
2. **Servo angle formula** — `Radar.set_angle` hardcodes `90` as the half-range, underutilizing the servo's full range. The fix extracts a config-driven `_angle_to_servo_value` static method.

The plan follows the exploratory bugfix workflow: exploration tests are written first (they fail on unfixed code), preservation tests capture existing behavior, then the fixes are implemented and verified.

## Tasks

- [x] 1. Write bug condition exploration test for API runtime toggle
  - **Property 1: Bug Condition** - API Runtime Toggle
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: For deterministic bugs, scope the property to concrete failing cases to ensure reproducibility
  - **Prerequisite**: Install `hypothesis` for property-based tests: `pip install hypothesis` (test-only dependency; project already uses pytest 8.4.2)
  - Create test file `tests/test_api_toggle.py`
  - **Concrete failing cases** (unit-style assertions encoding expected behavior):
    - Assert `config.API_ENABLED` equals `False` (on unfixed code it is `True`, contradicting the README — Requirement 1.3)
    - Assert an `ApiToggle` class exists (importable from a new `src/api_toggle.py` module) exposing `enable()`, `disable()`, `submit()`, `is_enabled()`, `close()` (on unfixed code the class does not exist — Requirements 1.1, 1.2)
    - Assert `ApiToggle(url, timeout_seconds, enabled=True).is_enabled()` returns `True` (initial state reflects startup config — Requirement 2.1)
    - Assert `ApiToggle(url, timeout_seconds, enabled=False).is_enabled()` returns `False` (Requirement 2.1)
    - Assert calling `enable()` on a disabled toggle creates a client (mocked `DetectionApi`) and `is_enabled()` returns `True` (Requirement 2.2)
    - Assert calling `disable()` on an enabled toggle calls `client.close()` and `is_enabled()` returns `False` (Requirement 2.3)
    - Assert calling `enable()` again after `disable()` creates a fresh client (different instance) and `is_enabled()` returns `True` (Requirement 2.4)
    - Assert `submit(detection)` routes to `client.submit()` when enabled and is a no-op when disabled (does not raise)
    - Assert `close()` is idempotent (calling twice does not raise)
  - **Property-based test** (using hypothesis): generate random sequences of `enable()`/`disable()` calls and assert:
    - `is_enabled()` is `True` iff the last action in the sequence was `enable()`
    - `submit(detection)` routes to a client iff enabled (use a mocked `DetectionApi` so no network I/O occurs)
    - After any `disable()`, the previous client's `close()` was called exactly once
  - Use `unittest.mock.patch` to mock `DetectionApi` so no real HTTP client or worker thread is created
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS — `ImportError`/`AttributeError` for missing `ApiToggle` class; `AssertionError` for `config.API_ENABLED` being `True` instead of `False`
  - Document counterexamples found: `config.API_ENABLED` is `True` (should be `False` per README); no `ApiToggle` coordinator exists; `main.py` creates `DetectionApi` only at startup with no close/recreate path; `RadarDisplay` has no widget bound to the API enabled state
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4_

- [x] 2. Write bug condition exploration test for servo angle formula
  - **Property 2: Bug Condition** - Servo Angle Mapping
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: Scope the property to concrete failing cases to ensure reproducibility
  - **Prerequisite**: `hypothesis` must be installed (see task 1)
  - Create test file `tests/test_servo_formula.py`
  - **Concrete failing cases** (unit-style assertions encoding expected behavior):
    - Assert `Radar._angle_to_servo_value(config.ANGLE_MAX)` equals `1.0` (on unfixed code the method does not exist; the buggy inline formula `(150 / 90.0) - 1.0` yields `0.667` — Requirement 1.4)
    - Assert `Radar._angle_to_servo_value(config.ANGLE_MIN)` equals `-1.0` (both formulas agree at `ANGLE_MIN` since `ANGLE_MIN = 0`, but the method still does not exist on unfixed code — Requirement 2.5)
    - Assert `Radar._angle_to_servo_value((config.ANGLE_MIN + config.ANGLE_MAX) / 2)` equals `0.0` (the sweep midpoint `75°`; buggy formula yields `-0.167` — Requirement 2.7)
    - Assert `Radar._angle_to_servo_value(90)` equals `2 * (90 - config.ANGLE_MIN) / (config.ANGLE_MAX - config.ANGLE_MIN) - 1` which is `0.2` (buggy formula yields `0.0` — Requirement 1.5)
  - **Property-based test** (using hypothesis): generate random `angle` values across `[config.ANGLE_MIN, config.ANGLE_MAX]` and assert `Radar._angle_to_servo_value(angle)` equals the correct linear mapping `2.0 * (angle - config.ANGLE_MIN) / (config.ANGLE_MAX - config.ANGLE_MIN) - 1.0`
  - **Additional PBT**: generate random valid configs (`ANGLE_MIN < ANGLE_MAX`) by monkeypatching `config.ANGLE_MIN`/`config.ANGLE_MAX` and assert the endpoint mapping holds (`ANGLE_MIN -> -1.0`, `ANGLE_MAX -> +1.0`)
  - Note: `Radar._angle_to_servo_value` is a `@staticmethod` so it can be called on the class without instantiation (no GPIO hardware needed)
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS — `AttributeError` for missing `_angle_to_servo_value` static method on `Radar`
  - Document counterexamples found: `set_angle(150)` produces `0.667` instead of `+1.0`; `set_angle(75)` produces `-0.167` instead of `0.0`; `set_angle(90)` produces `0.0` instead of `0.2`; the hardcoded `90.0` half-range assumes a 180° sweep centered on 90°
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.4, 1.5, 2.5, 2.6, 2.7_

- [x] 3. Write preservation property tests (BEFORE implementing fix)
  - **Property 3: Preservation** - Unchanged Behaviors
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy inputs (inputs where the bug condition does NOT hold)
  - Write property-based tests capturing observed behavior patterns from Preservation Requirements
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS on unfixed code (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - **Test files**: add to `tests/test_servo_formula.py`, `tests/test_api_toggle.py`, and verify existing `tests/test_api.py`, `tests/test_radar_simulation.py`, `tests/test_display.py` still pass
  - **Preservation test cases**:
    1. **SimulatedRadar no-op** (Requirement 3.5): PBT generating random angles and asserting `SimulatedRadar.set_angle(angle)` does not raise and does not set any `servo` attribute (SimulatedRadar has no `servo` attribute — the override means the hardware formula is never called). Passes on unfixed code.
    2. **SimulatedRadar targets/measurement unchanged** (Requirement 3.5): existing `tests/test_radar_simulation.py` tests continue to pass — verifies `measure_distance`, `scan_position`, and target logic are unchanged. Passes on unfixed code.
    3. **JSON contract preserved** (Requirement 3.1): existing `tests/test_api.py` `test_posts_detection_as_json` continues to pass — verifies `DetectionApi` still posts `angle_degrees`, `distance_cm`, `x_cm`, `y_cm`. Passes on unfixed code (DetectionApi is unchanged).
    4. **Sweep boundaries preserved** (Requirement 3.6): assert that `Radar.update` (and `SimulatedRadar`) continue to use `config.ANGLE_MIN` and `config.ANGLE_MAX` as sweep boundaries — verify by reading the `update` method logic and/or testing that the angle oscillates between `ANGLE_MIN` and `ANGLE_MAX`. Passes on unfixed code.
    5. **Display drawing unchanged** (Requirement 3.3): existing `tests/test_display.py` tests continue to pass — verifies `_draw_angle` logic is unchanged. Passes on unfixed code.
    6. **Clamping preservation** (Requirement 3.4): PBT generating random angles (including out-of-range values like `-5`, `200`) and asserting `Radar._angle_to_servo_value(angle)` is always within `[-1.0, 1.0]`. **Note**: this test requires the new `_angle_to_servo_value` method added in task 5, so it will fail on unfixed code (AttributeError). After the fix, it passes, confirming the clamp behavior is preserved. Document this as expected.
    7. **Disabled-API local processing** (Requirement 3.2): unit test asserting that when `ApiToggle` is disabled (`is_enabled()` returns `False`), calling `submit(detection)` is a no-op (does not raise, does not call any client). **Note**: requires `ApiToggle` class from task 4, so fails on unfixed code. After the fix, it passes.
  - For tests 1–5: verify they PASS on unfixed code (run the full test suite: `python -m pytest tests/ --run` or `python -m unittest discover -s tests -v`)
  - For tests 6–7: these are preservation properties that require the new code; they are written now but verified after the fix in tasks 4.6 and 5.4
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [x] 4. Fix for API runtime toggle

  - [x] 4.1 Change config default to match README
    - In `src/config.py`, change `API_ENABLED = True` to `API_ENABLED = False`
    - This makes the default match the README which documents the integration as disabled by default
    - _Bug_Condition: isApiToggleBugCondition(input) where input.event = "startup" AND config.API_ENABLED = True_
    - _Expected_Behavior: config.API_ENABLED SHALL default to False to match the README (Requirement 2.1)_
    - _Preservation: When API is disabled and a detection occurs, the detection is still processed locally (Requirement 3.2)_
    - _Requirements: 2.1_

  - [x] 4.2 Implement ApiToggle coordinator class
    - Create new module `src/api_toggle.py` containing the `ApiToggle` class (plain Python, no Tkinter dependency, so it is directly unit-testable)
    - `__init__(self, url, timeout_seconds, enabled)`: store `url` and `timeout_seconds`; set `self.client = None`; if `enabled` is `True`, create `DetectionApi(url, timeout_seconds=timeout_seconds)` immediately (reflects the initial state from `config.API_ENABLED`)
    - `enable()`: if `self.client is None`, create a fresh `DetectionApi(self.url, timeout_seconds=self.timeout_seconds)`
    - `disable()`: if `self.client is not None`, call `self.client.close()` and set `self.client = None` (releases the worker thread and queue)
    - `submit(detection)`: if `self.client is not None`, call `self.client.submit(detection)`; otherwise do nothing (the disabled path)
    - `is_enabled()`: return `self.client is not None`
    - `close()`: idempotent shutdown that calls `self.disable()`; safe to call from both display shutdown and `main.py`'s `finally` block
    - Import `DetectionApi` from `api` module inside `__init__`/`enable` (or at module level) to keep the dependency explicit
    - _Bug_Condition: isApiToggleBugCondition(input) where input.event = "toggle" AND toggleControlAbsent()_
    - _Expected_Behavior: enable() creates a client so detections are submitted (2.2); disable() closes the client, stops submitting, and releases resources (2.3); re-enable() creates a fresh client (2.4)_
    - _Preservation: When API is enabled and a detection occurs, the detection is still submitted in the background thread using the existing JSON contract (3.1); when disabled, detections are processed locally without submission (3.2); scan start/stop is independent of API state (3.3)_
    - _Requirements: 2.2, 2.3, 2.4_

  - [x] 4.3 Implement display.py changes (checkbox, handler, shutdown)
    - In `RadarDisplay.__init__`, accept an `api_toggle` parameter (default `None`) after the existing `on_detection` parameter
    - Add a `tk.BooleanVar` for the API checkbox; initialize it to `api_toggle.is_enabled()` if `api_toggle` is not `None`, otherwise `False`
    - Add a `ttk.Checkbutton` bound to the `BooleanVar` with text "API" (or similar), placed in the existing `controls` frame, packed independently of the scan toggle button
    - Add `_on_api_toggle()` handler: read the `BooleanVar`; if checked, call `self.api_toggle.enable()`; if unchecked, call `self.api_toggle.disable()`; guard against `self.api_toggle is None`
    - Wire the checkbutton's `command` to `self._on_api_toggle`
    - Store `self.api_toggle = api_toggle` as an instance attribute
    - In `_begin_shutdown`, call `self.api_toggle.close()` (if present) before destroying the window so the worker thread is joined and resources released
    - Do NOT change the detection flow in `_show_detection` — it continues to call `self.on_detection(detection)` (API submission happens through `ApiToggle.submit` in `main.py`'s callback)
    - _Bug_Condition: isApiToggleBugCondition(input) where input.event = "toggle" AND toggleControlAbsent()_
    - _Expected_Behavior: activating the checkbox enables the API connection (2.2); deactivating disables it, stops submitting, and releases resources (2.3)_
    - _Preservation: Scan start/stop is independent of API state (3.3); the checkbox does not affect the scan toggle button and vice versa_
    - _Requirements: 2.2, 2.3_

  - [x] 4.4 Implement main.py wiring
    - Remove the `from api import DetectionApi` import (no longer used directly)
    - Add `from api_toggle import ApiToggle` import
    - Remove the `api = None` local and the `if config.API_ENABLED: api = DetectionApi(...)` block
    - Construct `api_toggle = ApiToggle(config.API_URL, config.API_TIMEOUT_SECONDS, config.API_ENABLED)` after creating the radar
    - Change `nova_deteccao` to call `api_toggle.submit(detection)` instead of `api.submit(detection)` (keep the print statements unchanged)
    - Pass `api_toggle=api_toggle` to `RadarDisplay(radar, on_detection=nova_deteccao, api_toggle=api_toggle)`
    - In the `finally` block, close `api_toggle` (idempotent) in addition to `radar.close()`; this preserves the safety net that releases the client even if startup fails before the UI runs
    - _Bug_Condition: isApiToggleBugCondition(input) — the system starts with the initial API state from config.API_ENABLED (2.1) and allows runtime toggling (2.2, 2.3, 2.4)_
    - _Expected_Behavior: the system reflects the initial API enabled state from config.API_ENABLED (2.1); enabling creates a client (2.2); disabling closes it (2.3); re-enabling creates a fresh client (2.4)_
    - _Preservation: When API is enabled, detections are submitted in the background thread using the existing JSON contract (3.1); when disabled, detections are processed locally (3.2); scan start/stop is independent (3.3); closing api_toggle in finally releases resources even on startup failure_
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 4.5 Verify API toggle exploration test now passes
    - **Property 1: Expected Behavior** - API Runtime Toggle
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior (config default False, ApiToggle enable/disable/re-enable, PBT sequences)
    - Run bug condition exploration test from task 1 (`tests/test_api_toggle.py`)
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed — config defaults to False, ApiToggle coordinator works correctly)
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 4.6 Verify preservation tests still pass
    - **Property 3: Preservation** - Unchanged Behaviors
    - **IMPORTANT**: Re-run the SAME tests from task 3 - do NOT write new tests
    - Run preservation property tests from task 3 (including existing `tests/test_api.py`, `tests/test_radar_simulation.py`, `tests/test_display.py`)
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions — JSON contract preserved, SimulatedRadar no-op preserved, scan/API independence preserved, disabled-API local processing preserved)
    - Confirm all tests still pass after fix (no regressions)
    - _Requirements: 3.1, 3.2, 3.3_

- [x] 5. Fix for servo angle formula

  - [x] 5.1 Implement _angle_to_servo_value static method in Radar
    - Add a `@staticmethod` method `_angle_to_servo_value(angle)` to the `Radar` class in `src/radar.py`
    - Compute: `span = config.ANGLE_MAX - config.ANGLE_MIN`
    - If `span <= 0`: return `0.0` (degenerate range; avoids division by zero)
    - Otherwise: `valor = 2.0 * (angle - config.ANGLE_MIN) / span - 1.0`
    - Return `max(-1.0, min(1.0, valor))` (preserved clamp to `[-1.0, 1.0]`)
    - This is a pure function (no hardware access) so it is directly testable via `Radar._angle_to_servo_value(angle)` without instantiation
    - _Bug_Condition: isServoFormulaBugCondition(input) where input.target = "hardware" AND config.ANGLE_MIN <= input.angle <= config.ANGLE_MAX AND buggyServoValue(input.angle) != correctServoValue(input.angle)_
    - _Expected_Behavior: ANGLE_MIN maps to -1.0 (2.5), ANGLE_MAX maps to +1.0 (2.6), intermediate angles map proportionally via linear interpolation (2.7)_
    - _Preservation: Radar.set_angle continues to clamp the servo value to [-1.0, 1.0] (3.4); SimulatedRadar.set_angle remains a no-op (3.5); sweep boundaries use ANGLE_MIN/ANGLE_MAX (3.6)_
    - _Requirements: 2.5, 2.6, 2.7_

  - [x] 5.2 Replace hardcoded formula in Radar.set_angle
    - In `Radar.set_angle` in `src/radar.py`, replace `valor = (angle / 90.0) - 1.0` and the inline `valor = max(-1.0, min(1.0, valor))` clamp with `self.servo.value = self._angle_to_servo_value(angle)`
    - Remove the now-unused `valor` variable and inline clamp (clamping now lives inside `_angle_to_servo_value`)
    - Keep the docstring updated to reflect the config-driven mapping
    - Do NOT change `SimulatedRadar.set_angle` — it overrides `set_angle` with `pass` (no-op) and never calls the hardware formula, so simulation is unaffected
    - _Bug_Condition: isServoFormulaBugCondition(input) — the hardcoded 90.0 half-range is replaced with config-driven linear interpolation_
    - _Expected_Behavior: the full configured sweep range maps to the full servo range -1 to +1 (2.7)_
    - _Preservation: clamp to [-1.0, 1.0] is preserved inside _angle_to_servo_value (3.4); SimulatedRadar.set_angle remains a no-op (3.5); ANGLE_MIN/ANGLE_MAX sweep boundaries unchanged (3.6)_
    - _Requirements: 2.7_

  - [x] 5.3 Verify servo exploration test now passes
    - **Property 2: Expected Behavior** - Servo Angle Mapping
    - **IMPORTANT**: Re-run the SAME test from task 2 - do NOT write a new test
    - The test from task 2 encodes the expected behavior (ANGLE_MAX -> 1.0, ANGLE_MIN -> -1.0, midpoint -> 0.0, PBT linear mapping)
    - Run bug condition exploration test from task 2 (`tests/test_servo_formula.py`)
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed — full sweep range maps to full servo range)
    - _Requirements: 2.5, 2.6, 2.7_

  - [x] 5.4 Verify preservation tests still pass
    - **Property 3: Preservation** - Unchanged Behaviors
    - **IMPORTANT**: Re-run the SAME tests from task 3 - do NOT write new tests
    - Run preservation property tests from task 3 (including the clamping PBT from test case 6, which now passes with the new `_angle_to_servo_value` method)
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions — clamping preserved, SimulatedRadar no-op preserved, sweep boundaries preserved)
    - Confirm all tests still pass after fix (no regressions)
    - _Requirements: 3.4, 3.5, 3.6_

- [x] 6. Checkpoint - Ensure all tests pass
  - Run the full test suite: `python -m pytest tests/ --run` (or `python -m unittest discover -s tests -v`)
  - Ensure all tests pass — exploration tests (now passing after fixes), preservation tests (still passing), existing tests (unchanged)
  - Ask the user if questions arise

## Task Dependency Graph

```json
{
  "waves": [
    {
      "tasks": [
        {"id": 1, "title": "Write bug condition exploration test for API runtime toggle", "depends_on": []},
        {"id": 2, "title": "Write bug condition exploration test for servo angle formula", "depends_on": []},
        {"id": 3, "title": "Write preservation property tests", "depends_on": []}
      ]
    },
    {
      "tasks": [
        {"id": 4, "title": "Fix for API runtime toggle", "depends_on": [1, 3]},
        {"id": 5, "title": "Fix for servo angle formula", "depends_on": [2, 3]}
      ]
    },
    {
      "tasks": [
        {"id": 6, "title": "Checkpoint - Ensure all tests pass", "depends_on": [4, 5]}
      ]
    }
  ]
}
```

- **Wave 1** (Tasks 1, 2, 3): Exploration and preservation tests — standalone, no dependencies, must be completed before fixes.
- **Wave 2** (Tasks 4, 5): Implementation fixes — Task 4 depends on Tasks 1 and 3; Task 5 depends on Tasks 2 and 3. Task 5 should follow Task 4 to avoid merge conflicts in shared files.
- **Wave 3** (Task 6): Checkpoint — depends on both fixes; all tests must pass.

## Notes

- **hypothesis dependency**: The property-based tests in Tasks 1, 2, and 3 use the `hypothesis` library, which is not currently installed. Install it as a test-only dependency before writing tests: `pip install hypothesis`. The project already uses pytest 8.4.2, which integrates with hypothesis natively.
- **Test file organization**:
  - `tests/test_servo_formula.py` — new file for servo exploration tests (Task 2), clamping PBT (Task 3 case 6), and endpoint PBT
  - `tests/test_api_toggle.py` — new file for ApiToggle exploration tests (Task 1) and preservation tests (Task 3 cases 6–7)
  - `tests/test_api.py`, `tests/test_radar_simulation.py`, `tests/test_display.py` — existing files; verify they still pass after fixes (preservation)
- **New source module**: `src/api_toggle.py` will be created for the `ApiToggle` coordinator class. This keeps it plain Python with no Tkinter dependency, making it directly unit-testable.
- **Hardware dependency note**: `Radar.__init__` creates gpiozero objects requiring Raspberry Pi hardware. The servo formula fix uses a `@staticmethod` (`_angle_to_servo_value`) so it can be tested without instantiation. `SimulatedRadar` overrides `set_angle` with a no-op, so it never calls the hardware formula and is unaffected by the fix.
- **Mocking strategy**: ApiToggle tests mock `DetectionApi` using `unittest.mock.patch` to avoid creating real HTTP clients and worker threads.
