# API Toggle and Servo Formula Bugfix Design

## Overview

This design addresses two defects in the RADVEM radar application:

1. **API runtime toggle** — The `DetectionApi` is instantiated once at startup in
   `main.py` (only when `config.API_ENABLED` is `True`) and stays active for the
   whole session with no UI control to change its state. In addition,
   `config.py` defaults `API_ENABLED` to `True`, contradicting the README, which
   documents the integration as disabled by default (`API_ENABLED = False`). The
   fix changes the default to `False` and adds a Tkinter checkbox that lets the
   user enable/disable the API connection at runtime. Enabling creates a
   `DetectionApi` client; disabling closes it and releases its worker-thread
   resources; enabling again creates a fresh client.

2. **Servo angle formula** — `Radar.set_angle` converts sweep angles to the
   gpiozero `Servo` value range (-1 to +1) using a hardcoded half-range of `90`
   (`(angle / 90.0) - 1.0`). With the configured sweep range of 0° to 150°, the
   servo only reaches `0.667` at `ANGLE_MAX` instead of `+1.0`, so the full
   configured sweep does not map to the servo's full range. The fix replaces the
   hardcoded formula with a linear interpolation derived from
   `config.ANGLE_MIN` and `config.ANGLE_MAX` so the entire sweep range maps to the
   full servo range, while keeping the existing clamp to `[-1.0, 1.0]`. The fix
   only touches the hardware `Radar` class; `SimulatedRadar.set_angle` remains a
   no-op.

The general strategy is a minimal, targeted change: correct the config default,
introduce a small coordinator (`ApiToggle`) that owns the `DetectionApi`
lifecycle and routes submissions, wire a Tkinter checkbox in `RadarDisplay`
that delegates to that coordinator, and replace the servo formula with a
config-driven mapping extracted as a pure, testable helper.

## Glossary

- **Bug_Condition (C)**: The set of inputs that trigger the bugs — API state
  requests that the system cannot honor at runtime (or a startup default that
  contradicts the README), and hardware `set_angle` calls whose computed servo
  value differs from the correct config-driven mapping.
- **Property (P)**: The desired behavior for buggy inputs — the API toggle
  creates/closes/fresh-creates the client on demand, and `set_angle` maps the
  full configured sweep to the full servo range (`-1` to `+1`).
- **Preservation**: Existing behavior that must remain unchanged: the background
  JSON submission contract when the API is enabled, local detection processing
  (print/display) when disabled, scan start/stop independence from the API
  state, servo clamping, `SimulatedRadar.set_angle` no-op, and sweep boundaries.
- **ApiToggle**: A small coordinator (constructed in `main.py`) that owns the
  current `DetectionApi` client and exposes `enable()`, `disable()`, `submit()`,
  and `close()`. It is plain Python with no Tkinter dependency, so it is directly
  unit-testable.
- **RadarDisplay**: The Tkinter view class in `src/display.py` that owns the
  canvas, the scan toggle button, the status label, and (after the fix) the API
  checkbox. It delegates API state changes to `ApiToggle`.
- **DetectionApi**: The HTTP client in `src/api.py` that runs a background worker
  thread, accepts detections via `submit()`, posts them as JSON, and releases
  resources via `close()`. It is unchanged by this fix.
- **Servo value**: The dimensionless value gpiozero assigns to a `Servo`:
  `-1` = minimum, `0` = center, `+1` = maximum.
- **Sweep range**: The interval `[config.ANGLE_MIN, config.ANGLE_MAX]` over which
  the radar scans. With the current config this is `[0, 150]`.

## Bug Details

### Bug Condition

The overall bug condition is the union of two independent conditions: one for
the missing API runtime toggle (and wrong default), and one for the servo
formula. Each has its own input type.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type ApiStateRequest OR SetAngleRequest
  OUTPUT: boolean

  RETURN isApiToggleBugCondition(input) OR isServoFormulaBugCondition(input)
END FUNCTION


FUNCTION isApiToggleBugCondition(input)
  INPUT: input of type ApiStateRequest with fields
         { event: "startup" | "toggle", desiredEnabled: boolean }
  OUTPUT: boolean

  RETURN
    (input.event = "startup" AND config.API_ENABLED = True)
    OR
    (input.event = "toggle" AND toggleControlAbsent())
END FUNCTION


FUNCTION isServoFormulaBugCondition(input)
  INPUT: input of type SetAngleRequest with fields
         { target: "hardware" | "simulated", angle: number }
  OUTPUT: boolean

  RETURN
    input.target = "hardware"
    AND config.ANGLE_MIN <= input.angle <= config.ANGLE_MAX
    AND buggyServoValue(input.angle) != correctServoValue(input.angle)
END FUNCTION

WHERE
  buggyServoValue(a)  = clamp((a / 90.0) - 1.0)
  correctServoValue(a) = clamp(2 * (a - config.ANGLE_MIN)
                               / (config.ANGLE_MAX - config.ANGLE_MIN) - 1)
  clamp(v)             = max(-1.0, min(1.0, v))
  toggleControlAbsent() = true when no Tkinter control exists to change the
                          API enabled state at runtime (the buggy system)
```

Notes:
- `isApiToggleBugCondition` covers both the wrong startup default (`True`
  instead of the README's `False`) and any runtime toggle request, which the
  buggy system cannot honor because no control exists.
- `isServoFormulaBugCondition` is restricted to the hardware `Radar` target;
  `SimulatedRadar.set_angle` is a no-op and is therefore never a buggy input.
  The condition holds whenever the hardcoded `90` half-range disagrees with the
  config-driven mapping, which for the current config (`0` to `150`) is true for
  almost every angle except `ANGLE_MIN` (both formulas yield `-1.0` there).

### Examples

API toggle — current (defective) vs. expected:

- Startup: `config.API_ENABLED = True`, README says `False`. Actual: the API
  auto-connects at startup with no way to disable it and the default contradicts
  the README. Expected: default `False`, and a checkbox reflects/changes the
  state.
- User starts with the API disabled and wants to enable it: no control exists.
  Expected: checking the API checkbox creates a `DetectionApi` and resumes
  submission.
- User wants to disable the API at runtime: no control exists. Expected:
  unchecking the checkbox closes the client and stops submission.
- User enables, disables, then enables again: only the first client ever
  exists. Expected: re-enabling creates a fresh client.

Servo formula — current (defective) vs. expected, with `ANGLE_MIN = 0`,
`ANGLE_MAX = 150`:

- `set_angle(150)` — actual: `(150 / 90.0) - 1.0 = 0.667`; expected: `+1.0`.
- `set_angle(75)` — actual: `(75 / 90.0) - 1.0 = -0.167`; expected: `0.0`
  (the midpoint of the sweep).
- `set_angle(90)` — actual: `0.0`; expected: `2 * (90 / 150) - 1 = 0.2`.
- `set_angle(0)` — actual: `-1.0`; expected: `-1.0` (edge case: both formulas
  agree at `ANGLE_MIN` because `ANGLE_MIN = 0`).
- `set_angle(-5)` (out of range, e.g. transient overshoot) — actual: clamped to
  `-1.0`; expected: still clamped to `-1.0` (preserved clamp behavior).

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- When the API is enabled and a detection occurs, the detection is still
  submitted to the API in the background worker thread using the existing JSON
  contract (`angle_degrees`, `distance_cm`, `x_cm`, `y_cm`). The contract logic
  lives in `DetectionApi._post_detection`, which is unchanged.
- When the API is disabled and a detection occurs, the detection is still
  processed locally (printed to the console and drawn on the canvas) without
  being submitted to the API.
- The scan can still be started and stopped independently of the API enabled
  state; the API checkbox and the scan toggle button do not affect each other.
- `Radar.set_angle` continues to clamp the resulting servo value to
  `[-1.0, 1.0]`.
- `SimulatedRadar.set_angle` continues to perform no servo operation (no-op);
  the simulation does not drive GPIO hardware.
- The sweep direction logic continues to use `config.ANGLE_MIN` and
  `config.ANGLE_MAX` as the sweep boundaries.

**Scope:**
All inputs that do NOT satisfy either bug condition should be completely
unaffected by this fix. This includes:
- Mouse clicks and other interactions on the scan toggle button and canvas
  (unrelated to the API checkbox).
- Other keyboard inputs, window-close handling, and the scan loop timing.
- `SimulatedRadar` servo behavior (no-op) and `SimulatedRadar.measure_distance`
  / `scan_position` logic.
- Detection creation (`create_detection`), polar-to-cartesian conversion
  (`polar_to_xy`), and the radar sweep state machine (`update`).

**Note:** The actual expected correct behavior for buggy inputs is defined in
the Correctness Properties section (Properties 1 and 2). This section focuses on
what must NOT change.

## Hypothesized Root Cause

Based on the bug description and code analysis, the most likely causes are:

1. **Missing runtime control (API)**: `RadarDisplay` builds only a scan toggle
   button and a status label. There is no widget bound to the API enabled
   state, so the user has no way to change it at runtime.
2. **Static client lifecycle (API)**: `main.py` constructs `DetectionApi` once
   (when `config.API_ENABLED` is `True`) and stores it in a local variable
   captured by the `nova_deteccao` closure. There is no path to create, close,
   or recreate the client after startup.
3. **Config/README mismatch (API)**: `config.py` sets `API_ENABLED = True` while
   the README states the integration is disabled by default
   (`API_ENABLED = False`), so the documented and actual defaults disagree.
4. **Hardcoded half-range (servo)**: `Radar.set_angle` uses the literal `90.0`
   as the half-range (`(angle / 90.0) - 1.0`). This assumes a 180° sweep centered
   on 90° (`[0, 180] -> [-1, +1]`). With `ANGLE_MAX = 150` the mapping is wrong
   for almost every angle, and `ANGLE_MAX` maps to `0.667` instead of `+1.0`.

## Correctness Properties

Property 1: Bug Condition - API Runtime Toggle

_For any_ `ApiStateRequest` where the bug condition holds (the system starts
with `config.API_ENABLED = True`, or the user issues a runtime toggle request),
the fixed system SHALL default `config.API_ENABLED` to `False`, expose a Tkinter
checkbox that reflects the current API state, and when the checkbox is activated
create a `DetectionApi` client so that subsequent detections are submitted to the
backend; when deactivated close the client, stop submitting, and release the
worker-thread resources; and when activated again create a fresh client and
resume submission.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

Property 2: Bug Condition - Servo Angle Mapping

_For any_ `SetAngleRequest` targeting the hardware `Radar` with an angle in the
sweep range where the bug condition holds (the hardcoded formula disagrees with
the config-driven mapping), the fixed `Radar.set_angle` SHALL compute the servo
value by linear interpolation from `config.ANGLE_MIN` and `config.ANGLE_MAX` so
that `ANGLE_MIN` maps to `-1.0`, `ANGLE_MAX` maps to `+1.0`, and intermediate
angles map proportionally.

**Validates: Requirements 2.5, 2.6, 2.7**

Property 3: Preservation - Unchanged Behaviors

_For any_ input where the bug condition does NOT hold (non-toggle UI
interactions, `SimulatedRadar` servo calls, out-of-range servo angles, API
submission when enabled, and detection processing when disabled), the fixed
system SHALL produce the same result as the original system, preserving the
background JSON submission contract, local detection processing, scan/API
independence, servo clamping, the `SimulatedRadar.set_angle` no-op, and the
`ANGLE_MIN`/`ANGLE_MAX` sweep boundaries.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

## Fix Implementation

Assuming the root cause analysis is correct, the changes below are required.

### Bug 1 — API runtime toggle

**File**: `src/config.py`
1. **Default change**: Set `API_ENABLED = False` so the default matches the
   README.

**New coordinator** (constructed in `src/main.py`, kept as plain Python with no
Tkinter dependency so it is directly testable):
2. **`ApiToggle` class**: Owns the current `DetectionApi` client (or `None`).
   - `__init__(self, url, timeout_seconds, enabled)`: stores config; if
     `enabled` is `True`, create the client immediately (reflects the initial
     state from `config.API_ENABLED`).
   - `enable()`: if `self.client is None`, create a fresh
     `DetectionApi(url, timeout_seconds=timeout_seconds)`.
   - `disable()`: if `self.client is not None`, call `self.client.close()` and
     set `self.client = None` (releases the worker thread and queue).
   - `submit(detection)`: if `self.client is not None`, call
     `self.client.submit(detection)`; otherwise do nothing (the disabled path).
   - `is_enabled()`: returns `self.client is not None`.
   - `close()`: idempotent shutdown that calls `disable()`; safe to call from
     both the display shutdown and `main.py`'s `finally` block.

**File**: `src/display.py`
3. **Checkbox control**: In `RadarDisplay.__init__`, accept an `api_toggle`
   parameter (the `ApiToggle` coordinator). Add a `ttk.Checkbutton` bound to a
   `tk.BooleanVar` whose initial value is `api_toggle.is_enabled()` (or `False`
   when `api_toggle` is `None`). The checkbox is placed in the existing controls
   frame, independent of the scan toggle button.
4. **Toggle handler**: Add `_on_api_toggle()` that reads the `BooleanVar`; if
   checked it calls `api_toggle.enable()`, otherwise `api_toggle.disable()`.
   Guard against `api_toggle is None` so the display still works without an API
   coordinator.
5. **Submission routing is unchanged in the display**: the display continues to
   call `self.on_detection(detection)` in `_show_detection`; the API submission
   itself happens through `ApiToggle.submit` (see `main.py` below), so no
   detection-flow change is needed in `RadarDisplay`.
6. **Shutdown**: In `_begin_shutdown`, call `api_toggle.close()` (if present)
   before destroying the window so the worker thread is joined and resources are
   released.

**File**: `src/main.py`
7. **Wiring**: Remove the direct `DetectionApi` creation and the `api` local.
   Construct `api_toggle = ApiToggle(config.API_URL, config.API_TIMEOUT_SECONDS,
   config.API_ENABLED)`. Change `nova_deteccao` to print the detection (unchanged)
   and then call `api_toggle.submit(detection)` instead of `api.submit`. Pass
   `api_toggle=api_toggle` to `RadarDisplay`. In the `finally` block, close
   `api_toggle` (idempotent) in addition to `radar.close()`; this preserves the
   existing safety net that releases the client even if startup fails before the
   UI runs.

### Bug 2 — Servo angle formula

**File**: `src/radar.py`
1. **Pure helper**: Add a `@staticmethod _angle_to_servo_value(angle)` that
   computes the config-driven mapping without touching hardware:
   - `span = config.ANGLE_MAX - config.ANGLE_MIN`
   - if `span <= 0`: return `0.0` (degenerate range; avoids division by zero)
   - else: `valor = 2.0 * (angle - config.ANGLE_MIN) / span - 1.0`
   - return `max(-1.0, min(1.0, valor))` (preserved clamp).
2. **`Radar.set_angle`**: Replace `valor = (angle / 90.0) - 1.0` and the inline
   clamp with `self.servo.value = self._angle_to_servo_value(angle)`.
3. **`SimulatedRadar.set_angle`**: Leave as `pass` (no-op). Because
   `SimulatedRadar` overrides `set_angle`, it never calls the hardware formula,
   so simulation is unaffected.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface
counterexamples that demonstrate the bugs on unfixed code, then verify the fixes
work correctly and preserve existing behavior. The servo formula is the primary
target for property-based testing because it is a pure function of the angle; the
API toggle is validated with unit and integration tests plus a mocked
`DetectionApi`.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bugs BEFORE implementing
the fix. Confirm or refute the root cause analysis. If we refute, we will need to
re-hypothesize.

**Test Plan**: Write tests that exercise the buggy formulas and observe the
missing control. Run these on the UNFIXED code to observe failures.

**Test Cases**:
1. **Servo at ANGLE_MAX**: Compute the buggy servo value for `angle = 150`
   (`(150 / 90.0) - 1.0`) and assert it equals `0.667`, not `+1.0`. This
   demonstrates the under-range mapping (will fail to meet the expected `+1.0`
   on unfixed code).
2. **Servo at midpoint**: Compute the buggy value for `angle = 75`
   (`-0.167`) and show it is not `0.0`, the correct midpoint.
3. **API control absence**: Inspect `RadarDisplay` and confirm no widget is bound
   to the API enabled state; confirm `main.py` creates `DetectionApi` only at
   startup with no close/recreate path.
4. **Config default**: Assert `config.API_ENABLED` is currently `True`,
   contradicting the README's documented `False`.

**Expected Counterexamples**:
- The servo reaches only `0.667` at `ANGLE_MAX` instead of `+1.0`.
- The servo midpoint (`75°`) maps to `-0.167` instead of `0.0`.
- No API toggle control exists; the client lifecycle is static.
- Possible causes: hardcoded `90` half-range; missing UI control; wrong default.

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed
function produces the expected behavior.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := fixedFunction(input)
  ASSERT expectedBehavior(result)
END FOR
```

For the servo, this means: for every `angle` in
`[ANGLE_MIN, ANGLE_MAX]`, `_angle_to_servo_value(angle)` equals the correct
linear mapping and the endpoints are exactly `-1.0` and `+1.0`. For the API
toggle, this means: enabling creates a client, disabling closes it, and
re-enabling creates a fresh one.

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the
fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT originalFunction(input) = fixedFunction(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation
checking of the servo formula because:
- It generates many angles (and many valid `ANGLE_MIN`/`ANGLE_MAX` configs)
  automatically across the input domain.
- It catches edge cases that manual unit tests might miss (midpoints, rounding,
  out-of-range clamping, degenerate ranges).
- It provides strong guarantees that behavior is unchanged for non-buggy
  inputs (e.g. `SimulatedRadar` no-op, clamping).

**Test Plan**: Observe behavior on UNFIXED code first for non-buggy inputs
(`SimulatedRadar.set_angle` no-op, clamping, JSON contract, local processing
when disabled), then write property-based and unit tests capturing that
behavior.

**Test Cases**:
1. **Clamp preservation**: Verify that out-of-range angles still clamp to
  `[-1.0, 1.0]` after the fix.
2. **SimulatedRadar no-op**: Verify `SimulatedRadar.set_angle` still performs no
  servo operation and that targets/measurement logic is unchanged.
3. **JSON contract preservation**: Verify `DetectionApi` still posts
  `angle_degrees`, `distance_cm`, `x_cm`, `y_cm` (existing `test_api.py` continues
  to pass).
4. **Disabled-API local processing**: Verify that when the API is disabled,
  detections are still printed and drawn and not submitted.
5. **Scan/API independence**: Verify starting/stopping the scan does not affect
  the API checkbox state and vice versa.

### Unit Tests

- `_angle_to_servo_value`: `ANGLE_MIN -> -1.0`, `ANGLE_MAX -> +1.0`, the
  configured midpoint `-> 0.0`, and clamping for out-of-range inputs.
- `ApiToggle`: `enable()` creates a client (mocked `DetectionApi`), `disable()`
  closes it and clears the reference, `is_enabled()` tracks state, `submit()`
  routes only when enabled and is a no-op when disabled, and re-`enable()`
  creates a fresh client. `close()` is idempotent.
- `SimulatedRadar.set_angle`: still a no-op (no servo attribute touched).
- `config.API_ENABLED`: defaults to `False`.

### Property-Based Tests

- Generate random `angle` values across `[ANGLE_MIN, ANGLE_MAX]` and assert
  `_angle_to_servo_value` is linear and monotonic, with endpoints exactly
  `-1.0` and `+1.0`.
- Generate random valid configs (`ANGLE_MIN < ANGLE_MAX`) and assert the
  endpoint mapping (`ANGLE_MIN -> -1.0`, `ANGLE_MAX -> +1.0`) and that all
  in-range values stay within `[-1.0, 1.0]`.
- Generate random angles (including out-of-range) and assert the result is
  always clamped to `[-1.0, 1.0]` (preservation of clamp behavior).
- (API toggle) Generate random sequences of enable/disable calls and assert the
  client is non-`None` iff the last action was enable, and `submit` routes iff
  enabled — using a mocked `DetectionApi` so no network is used.

### Integration Tests

- Full scan flow with the API enabled: verify detections are submitted via the
  worker thread using the existing JSON contract (mocked transport).
- Full scan flow with the API disabled: verify detections are printed/drawn and
  not submitted.
- Toggle the API checkbox during an active scan: verify the scan continues
  unaffected and submission starts/stops with the checkbox state.
- Toggle off then on: verify a fresh client is created and submission resumes.
