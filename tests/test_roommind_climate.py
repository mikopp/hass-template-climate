"""Integration tests for the RoomMind "Fußbodenheizung Badezimmer" entity.

Real-world second scenario from jcwillox/hass-template-climate PR #134. Covers the
deprecated config aliases (availability_template, min_temp_template /
max_temp_template), branching hvac_mode_template / hvac_action_template, custom
attributes, and chained climate→climate set_temperature / set_hvac_mode actions
landing on the observable override echo entity.
"""

from ha_integration_test_harness import HomeAssistant

CLIMATE = "climate.fussbodenheizung_badezimmer_template"
OVERRIDE = "climate.roommind_badezimmer_override"

TEMP_ATTRS = {"unit_of_measurement": "°C", "device_class": "temperature"}


def _approx(value: float):
    return lambda s: s not in ("unknown", "unavailable") and abs(float(s) - value) < 1e-6


def _override_mode(ha: HomeAssistant, option: str) -> None:
    ha.call_action("input_select", "select_option", {
        "entity_id": "input_select.roommind_override_mode", "option": option})


def test_getters_and_min_max_templates(home_assistant: HomeAssistant) -> None:
    home_assistant.set_state(
        "sensor.temperatur_luftfeuchtigkeit_badezimmer_temperature", "24.1", TEMP_ATTRS)
    home_assistant.set_state("sensor.roommind_badezimmer_target_temp", "21.5", TEMP_ATTRS)
    # min/max come from the seeded local device attributes via the deprecated templates.
    home_assistant.assert_entity_state(
        CLIMATE,
        expected_attributes={
            "current_temperature": 24.1,
            "temperature": 21.5,
            "min_temp": 5.0,
            "max_temp": 30.0,
        },
    )


def test_custom_attributes(home_assistant: HomeAssistant) -> None:
    home_assistant.set_state("binary_sensor.fenster_badezimmer_contact", "on", {})
    home_assistant.set_state("switch.roommind_badezimmer_cover_auto", "off", {})
    home_assistant.assert_entity_state(
        CLIMATE,
        expected_attributes={"window_open": "open", "cover_automatic": "off"},
    )


def test_availability_template(home_assistant: HomeAssistant) -> None:
    # When the backing local device is unavailable, the template entity is too.
    home_assistant.set_state("climate.fussbodenheizung_badezimmer_local", "unavailable", {})
    home_assistant.assert_entity_state(CLIMATE, "unavailable")


def test_hvac_mode_template_auto(home_assistant: HomeAssistant) -> None:
    _override_mode(home_assistant, "auto")
    home_assistant.assert_entity_state(CLIMATE, "auto")


def test_hvac_mode_template_heat(home_assistant: HomeAssistant) -> None:
    _override_mode(home_assistant, "off")
    home_assistant.set_state("sensor.roommind_badezimmer_mode", "heating", {})
    home_assistant.assert_entity_state(
        CLIMATE, "heat", expected_attributes={"hvac_action": "heating"})


def test_hvac_mode_template_off(home_assistant: HomeAssistant) -> None:
    _override_mode(home_assistant, "off")
    home_assistant.set_state("sensor.roommind_badezimmer_mode", "idle", {})
    home_assistant.assert_entity_state(
        CLIMATE, "off", expected_attributes={"hvac_action": "idle"})


def test_set_temperature_chains_to_override(home_assistant: HomeAssistant) -> None:
    # set_temperature on the template calls climate.set_temperature on the override
    # (with hvac_mode=auto), which writes the override's backing helper.
    home_assistant.call_action("climate", "set_temperature",
                               {"entity_id": CLIMATE, "temperature": 22.5})
    home_assistant.assert_entity_state(
        "input_number.roommind_override_target", _approx(22.5))
    home_assistant.assert_entity_state(
        OVERRIDE, expected_attributes={"temperature": 22.5})


def test_set_hvac_mode_chains_to_override(home_assistant: HomeAssistant) -> None:
    home_assistant.call_action("climate", "set_hvac_mode",
                               {"entity_id": CLIMATE, "hvac_mode": "heat"})
    home_assistant.assert_entity_state("input_select.roommind_override_mode", "heat")
    home_assistant.assert_entity_state(OVERRIDE, "heat")


def test_set_preset_mode_writes_helper(home_assistant: HomeAssistant) -> None:
    home_assistant.call_action("climate", "set_preset_mode",
                               {"entity_id": CLIMATE, "preset_mode": "Boost 10 min"})
    home_assistant.assert_entity_state("input_select.roommind_preset", "Boost 10 min")
