"""Integration tests for the Airflow climate_template entity.

Exercises every getter template, mode list and setter/action of the platform
against a real Home Assistant instance. Actions are asserted by checking the
backing input_* helper actually changed — proving the action script ran — rather
than only the entity's own (optimistically updated) attribute.

The entity has an ``hvac_mode_template``, so its reported hvac_mode is always
derived from the helpers (the optimistic value set by a service call is
immediately overwritten by the template re-render). Tests therefore assert the
helper writes for set_hvac_mode and the template-derived state that follows.
"""

import pytest

from ha_integration_test_harness import HomeAssistant

CLIMATE = "climate.airflow_climate"

TEMP_ATTRS = {"unit_of_measurement": "°C", "device_class": "temperature"}
HUM_ATTRS = {"unit_of_measurement": "%", "device_class": "humidity"}


def _profile(ha: HomeAssistant, option: str) -> None:
    ha.call_action("input_select", "select_option", {
        "entity_id": "input_select.comfoconnect_pro_temperature_profile",
        "option": option,
    })


def _enable_auto(ha: HomeAssistant) -> None:
    ha.call_action("input_boolean", "turn_on",
                   {"entity_id": "input_boolean.airflow_cooling_automatic_enabled"})


def _approx(value: float):
    return lambda s: s not in ("unknown", "unavailable") and abs(float(s) - value) < 1e-6


# ── Getters ──────────────────────────────────────────────────────────────────
def test_current_temperature_and_humidity(home_assistant: HomeAssistant) -> None:
    home_assistant.set_state("sensor.airflow_avg_indoor_temp_5min", "23.5", TEMP_ATTRS)
    home_assistant.set_state("sensor.airflow_avg_indoor_humidity_5min", "60.0", HUM_ATTRS)
    home_assistant.assert_entity_state(
        CLIMATE,
        expected_attributes={"current_temperature": 23.5, "current_humidity": 60.0},
    )


def test_target_temperature_getter(home_assistant: HomeAssistant) -> None:
    # 'auto' is a single-setpoint mode, so target_temperature is exposed.
    _enable_auto(home_assistant)
    home_assistant.call_action("input_number", "set_value", {
        "entity_id": "input_number.airflow_cooling_target_temperature", "value": 23.0})
    home_assistant.assert_entity_state(
        CLIMATE, "auto", expected_attributes={"temperature": 23.0})


def test_target_temperature_range_getter(home_assistant: HomeAssistant) -> None:
    # Baseline (auto off, profile comfort) → heat_cool, which exposes the range.
    home_assistant.call_action("input_number", "set_value", {
        "entity_id": "input_number.airflow_cooling_target_temp_low", "value": 19.5})
    home_assistant.call_action("input_number", "set_value", {
        "entity_id": "input_number.airflow_cooling_target_temp_high", "value": 25.5})
    home_assistant.assert_entity_state(
        CLIMATE, "heat_cool",
        expected_attributes={"target_temp_low": 19.5, "target_temp_high": 25.5})


def test_target_humidity_getter(home_assistant: HomeAssistant) -> None:
    home_assistant.call_action("input_number", "set_value", {
        "entity_id": "input_number.airflow_target_humidity", "value": 62})
    home_assistant.assert_entity_state(
        CLIMATE, expected_attributes={"humidity": 62.0})


def test_min_max_temp_and_step_getters(home_assistant: HomeAssistant) -> None:
    home_assistant.call_action("input_number", "set_value", {
        "entity_id": "input_number.airflow_min_temp", "value": 15.0})
    home_assistant.call_action("input_number", "set_value", {
        "entity_id": "input_number.airflow_max_temp", "value": 27.0})
    home_assistant.call_action("input_number", "set_value", {
        "entity_id": "input_number.airflow_temp_step", "value": 0.5})
    home_assistant.assert_entity_state(
        CLIMATE,
        expected_attributes={"min_temp": 15.0, "max_temp": 27.0, "target_temp_step": 0.5},
    )


def test_fan_and_swing_getters(home_assistant: HomeAssistant) -> None:
    home_assistant.call_action("input_select", "select_option", {
        "entity_id": "input_select.airflow_fan_mode", "option": "high"})
    home_assistant.call_action("input_select", "select_option", {
        "entity_id": "input_select.airflow_swing_mode", "option": "vertical"})
    home_assistant.assert_entity_state(
        CLIMATE, expected_attributes={"fan_mode": "high", "swing_mode": "vertical"})


def test_custom_attributes(home_assistant: HomeAssistant) -> None:
    home_assistant.set_state("sensor.airflow_outdoor_dew_5min", "9.1", TEMP_ATTRS)
    home_assistant.set_state("sensor.airflow_outdoor_temp_5min", "15.2", TEMP_ATTRS)
    home_assistant.set_state("binary_sensor.airflow_free_cooling_available", "on", {})
    home_assistant.assert_entity_state(
        CLIMATE,
        expected_attributes={
            "outdoor_dew": 9.1,
            "outdoor_temp": 15.2,
            "free_cooling_available": True,
        },
    )


# ── hvac_mode getter matrix ──────────────────────────────────────────────────
@pytest.mark.parametrize("auto, profile, expected", [
    (True, "comfort", "auto"),
    (False, "warm", "heat"),
    (False, "comfort", "heat_cool"),
    (False, "cool", "cool"),
])
def test_hvac_mode_template(home_assistant: HomeAssistant, auto, profile, expected) -> None:
    if auto:
        _enable_auto(home_assistant)
    else:
        home_assistant.call_action("input_boolean", "turn_off",
                                   {"entity_id": "input_boolean.airflow_cooling_automatic_enabled"})
    _profile(home_assistant, profile)
    home_assistant.assert_entity_state(CLIMATE, expected)


# ── hvac_action getter matrix ────────────────────────────────────────────────
@pytest.mark.parametrize("profile, free_cool, boost, flush, expected", [
    ("cool", "off", "off", "off", "cooling"),
    ("warm", "off", "off", "off", "heating"),
    ("comfort", "off", "off", "off", "fan"),
    ("cool", "off", "off", "on", "drying"),
    ("comfort", "on", "on", "off", "drying"),
])
def test_hvac_action_template(home_assistant, profile, free_cool, boost, flush, expected) -> None:
    _profile(home_assistant, profile)
    home_assistant.set_state("binary_sensor.airflow_free_cooling_available", free_cool, {})
    home_assistant.set_state("switch.comfoconnect_pro_boost", boost, {})
    home_assistant.set_state("binary_sensor.airflow_humidity_flush_needed", flush, {})
    home_assistant.assert_entity_state(CLIMATE, expected_attributes={"hvac_action": expected})


# ── Setters / actions (assert the helper actually changed) ───────────────────
def test_set_temperature_action(home_assistant: HomeAssistant) -> None:
    _enable_auto(home_assistant)  # single-setpoint mode
    home_assistant.call_action("climate", "set_temperature",
                               {"entity_id": CLIMATE, "temperature": 23.0})
    home_assistant.assert_entity_state(
        "input_number.airflow_cooling_target_temperature", _approx(23.0))


def test_set_temperature_range_action(home_assistant: HomeAssistant) -> None:
    # Baseline state is heat_cool, which accepts a low/high range.
    home_assistant.call_action("climate", "set_temperature", {
        "entity_id": CLIMATE, "target_temp_low": 19.0, "target_temp_high": 25.0})
    home_assistant.assert_entity_state(
        "input_number.airflow_cooling_target_temp_low", _approx(19.0))
    home_assistant.assert_entity_state(
        "input_number.airflow_cooling_target_temp_high", _approx(25.0))


def test_set_humidity_action(home_assistant: HomeAssistant) -> None:
    home_assistant.call_action("climate", "set_humidity",
                               {"entity_id": CLIMATE, "humidity": 48})
    home_assistant.assert_entity_state(
        "input_number.airflow_target_humidity", _approx(48.0))


def test_set_fan_mode_action(home_assistant: HomeAssistant) -> None:
    home_assistant.call_action("climate", "set_fan_mode",
                               {"entity_id": CLIMATE, "fan_mode": "low"})
    home_assistant.assert_entity_state("input_select.airflow_fan_mode", "low")


def test_set_swing_mode_action(home_assistant: HomeAssistant) -> None:
    home_assistant.call_action("climate", "set_swing_mode",
                               {"entity_id": CLIMATE, "swing_mode": "both"})
    home_assistant.assert_entity_state("input_select.airflow_swing_mode", "both")


@pytest.mark.parametrize("hvac_mode, expect_auto, expect_profile, expect_state", [
    ("auto", "on", None, "auto"),
    ("heat", "off", "warm", "heat"),
    ("cool", "off", "cool", "cool"),
    ("heat_cool", "off", "comfort", "heat_cool"),
    ("off", "off", "comfort", "heat_cool"),  # 'off' maps to the comfort profile
])
def test_set_hvac_mode_action(home_assistant, hvac_mode, expect_auto, expect_profile, expect_state) -> None:
    # Start from a different state so each write is an observable change.
    _enable_auto(home_assistant)
    _profile(home_assistant, "warm")
    home_assistant.call_action("climate", "set_hvac_mode",
                               {"entity_id": CLIMATE, "hvac_mode": hvac_mode})
    home_assistant.assert_entity_state(
        "input_boolean.airflow_cooling_automatic_enabled", expect_auto)
    if expect_profile is not None:
        home_assistant.assert_entity_state(
            "input_select.comfoconnect_pro_temperature_profile", expect_profile)
    home_assistant.assert_entity_state(CLIMATE, expect_state)


def test_turn_off_action(home_assistant: HomeAssistant) -> None:
    # turn_off → set_hvac_mode(off): disables automatic and selects the comfort profile.
    _enable_auto(home_assistant)
    home_assistant.assert_entity_state(CLIMATE, "auto")
    home_assistant.call_action("climate", "turn_off", {"entity_id": CLIMATE})
    home_assistant.assert_entity_state(
        "input_boolean.airflow_cooling_automatic_enabled", "off")
    home_assistant.assert_entity_state(
        "input_select.comfoconnect_pro_temperature_profile", "comfort")
