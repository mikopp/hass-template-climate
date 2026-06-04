"""Shared fixtures for the climate_template integration test suite.

The ``ha_integration_test_harness`` plugin provides the session-scoped
``home_assistant`` fixture (a live HA REST/WebSocket client backed by a real
Home Assistant Docker container). These autouse fixtures reset the input helpers
and seed the CI-only stub entities (sensors/binary_sensors/switches that have no
integration inside the container) to known values before every test, so each test
starts from a deterministic baseline.
"""

import pytest

from ha_integration_test_harness import HomeAssistant


# ── Per-test baseline: input helpers ─────────────────────────────────────────
@pytest.fixture(autouse=True)
def baseline_inputs(home_assistant: HomeAssistant) -> None:
    """Reset every input_* helper the climate entities read/write to a known value."""
    ha = home_assistant

    ha.call_action(
        "input_boolean",
        "turn_off",
        {"entity_id": "input_boolean.airflow_cooling_automatic_enabled"},
    )

    for entity_id, value in {
        "input_number.airflow_cooling_target_temperature": 21.5,
        "input_number.airflow_cooling_target_temp_low": 20.0,
        "input_number.airflow_cooling_target_temp_high": 24.0,
        "input_number.airflow_target_humidity": 55,
        "input_number.airflow_temp_step": 0.5,
        "input_number.airflow_min_temp": 16.0,
        "input_number.airflow_max_temp": 28.0,
        # Presets package
        "input_number.hc1_target_temperature": 21.0,
        "input_number.hc1_comfort_setpoint": 22.0,
        "input_number.hc1_reduced_setpoint": 18.0,
        "input_number.hc1_protection_setpoint": 8.0,
        # RoomMind package
        "input_number.roommind_override_target": 21.0,
    }.items():
        ha.call_action(
            "input_number", "set_value", {"entity_id": entity_id, "value": value}
        )

    for entity_id, option in {
        "input_select.comfoconnect_pro_temperature_profile": "comfort",
        "input_select.airflow_fan_mode": "auto",
        "input_select.airflow_swing_mode": "off",
        "input_select.hc1_operating_mode": "comfort",
        "input_select.roommind_override_mode": "auto",
        # Mode-init matrix test helpers — seeded to values matching the
        # DEFAULT_* constants so static-only entities report their defaults.
        "input_select.mode_init_hvac_source": "off",
        "input_select.mode_init_fan_source": "low",
        "input_select.mode_init_swing_source": "off",
        "input_select.mode_init_preset_source": "comfort",
    }.items():
        ha.call_action(
            "input_select", "select_option", {"entity_id": entity_id, "option": option}
        )


# ── Per-test baseline: external stub entities ────────────────────────────────
@pytest.fixture(autouse=True)
def baseline_states(home_assistant: HomeAssistant, baseline_inputs: None) -> None:
    """Seed CI-only stub entities (no backing integration) before each test.

    Runs after ``baseline_inputs`` so template entities that read both helpers and
    stubs settle on consistent values.
    """
    ha = home_assistant
    temp = {"unit_of_measurement": "°C", "device_class": "temperature"}
    hum = {"unit_of_measurement": "%", "device_class": "humidity"}

    # Airflow read-only source sensors.
    ha.set_state("sensor.airflow_avg_indoor_temp_5min", "22.0", temp)
    ha.set_state("sensor.airflow_avg_indoor_humidity_5min", "55.0", hum)
    ha.set_state("sensor.airflow_outdoor_temp_5min", "16.0", temp)
    ha.set_state("sensor.airflow_outdoor_dew_5min", "8.5", temp)
    # Airflow hvac_action inputs.
    ha.set_state("binary_sensor.airflow_free_cooling_available", "off", {})
    ha.set_state("binary_sensor.airflow_humidity_flush_needed", "off", {})
    ha.set_state("switch.comfoconnect_pro_boost", "off", {})

    # Presets package.
    ha.set_state("sensor.hc1_room_temperature", "20.5", temp)

    # RoomMind package.
    ha.set_state(
        "sensor.temperatur_luftfeuchtigkeit_badezimmer_temperature", "23.4", temp
    )
    ha.set_state("sensor.temperatur_luftfeuchtigkeit_badezimmer_humidity", "48", hum)
    ha.set_state("sensor.roommind_badezimmer_target_temp", "22.0", temp)
    ha.set_state("sensor.roommind_badezimmer_mode", "heating", {})
    # Local RoomMind device — carries the min/max temp bounds the template reads,
    # and its mere presence (state != 'unavailable') gates availability_template.
    ha.set_state(
        "climate.fussbodenheizung_badezimmer_local",
        "heat",
        {"min_temp": 5, "max_temp": 30},
    )
    ha.set_state("binary_sensor.fenster_badezimmer_contact", "off", {})
    ha.set_state("switch.roommind_badezimmer_cover_auto", "on", {})
