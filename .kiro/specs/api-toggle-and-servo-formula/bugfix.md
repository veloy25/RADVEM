# Bugfix Requirements Document

## Introduction

This document captures the requirements for fixing two defects in the RADVEM radar application:

1. **API runtime toggle**: The API integration cannot be enabled or disabled at runtime. The `DetectionApi` is instantiated once at startup (when `config.API_ENABLED` is `True`) and remains active for the entire session, with no UI control to change its state. Additionally, `config.py` defaults `API_ENABLED` to `True`, contradicting the README which documents the integration as disabled by default (`API_ENABLED = False`).

2. **Servo angle formula**: `Radar.set_angle` hardcodes `90` as the half-range when converting sweep angles to the gpiozero Servo value range (-1 to +1). With the configured sweep range of 0° to 150°, the servo only reaches `0.667` at `ANGLE_MAX` instead of `+1`, so the full configured sweep range does not map to the servo's full range.

## Bug Analysis

### Current Behavior (Defect)

**Bug 1 — API toggle:**

1.1 WHEN the application starts with `config.API_ENABLED = True` THEN the system creates a `DetectionApi` once and keeps it active for the entire session with no way for the user to disable it from the interface

1.2 WHEN the application starts with `config.API_ENABLED = False` and the user wants to enable the API THEN the system provides no mechanism to do so at runtime

1.3 WHEN `config.py` is compared to the README THEN the system contradicts itself: `config.API_ENABLED` defaults to `True` while the README documents `API_ENABLED = False` as the default

**Bug 2 — Servo formula:**

1.4 WHEN `Radar.set_angle` is called with `angle = ANGLE_MAX` (150°) THEN the system sets the servo value to `0.667` (`(150 / 90.0) - 1.0`) instead of `+1.0`, underutilizing the servo's full range

1.5 WHEN `Radar.set_angle` is called with any angle within the sweep range THEN the system computes the servo value using a hardcoded half-range of `90` instead of deriving the mapping from `config.ANGLE_MIN` and `config.ANGLE_MAX`, so the result is incorrect whenever the configured sweep range does not span exactly 180° centered on 90°

### Expected Behavior (Correct)

**Bug 1 — API toggle:**

2.1 WHEN the application starts THEN the system SHALL reflect the initial API enabled state from `config.API_ENABLED`, and `config.API_ENABLED` SHALL default to `False` to match the README

2.2 WHEN the user activates the API toggle control in the Tkinter interface THEN the system SHALL enable the API connection so that detections are submitted to the backend

2.3 WHEN the user deactivates the API toggle control in the Tkinter interface THEN the system SHALL disable the API connection, stop submitting detections, and release the API client resources

2.4 WHEN the API was disabled and the user toggles it on again THEN the system SHALL create a fresh API client and resume submitting detections

**Bug 2 — Servo formula:**

2.5 WHEN `Radar.set_angle` is called with `angle = ANGLE_MIN` THEN the system SHALL set the servo value to `-1.0`

2.6 WHEN `Radar.set_angle` is called with `angle = ANGLE_MAX` THEN the system SHALL set the servo value to `+1.0`

2.7 WHEN `Radar.set_angle` is called with any angle within the sweep range THEN the system SHALL map the angle to the servo value using `config.ANGLE_MIN` and `config.ANGLE_MAX` so that the full configured sweep range maps to the full servo range (-1 to +1)

### Unchanged Behavior (Regression Prevention)

**Bug 1 — API toggle:**

3.1 WHEN the API is enabled and a detection occurs THEN the system SHALL CONTINUE TO submit the detection to the API in the background thread using the existing JSON contract (`angle_degrees`, `distance_cm`, `x_cm`, `y_cm`)

3.2 WHEN the API is disabled and a detection occurs THEN the system SHALL CONTINUE TO process the detection locally (print and display it) without submitting it to the API

3.3 WHEN the scan is running THEN the system SHALL CONTINUE TO allow the user to start and stop the scan independently of the API enabled state

**Bug 2 — Servo formula:**

3.4 WHEN `Radar.set_angle` is called with an angle that would map outside the servo range THEN the system SHALL CONTINUE TO clamp the resulting servo value to the interval `[-1.0, 1.0]`

3.5 WHEN `SimulatedRadar.set_angle` is called THEN the system SHALL CONTINUE TO perform no servo operation (no-op), since simulation does not drive GPIO hardware

3.6 WHEN the sweep direction logic updates the scan angle THEN the system SHALL CONTINUE TO use `config.ANGLE_MIN` and `config.ANGLE_MAX` as the sweep boundaries
