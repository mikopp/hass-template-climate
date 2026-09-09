"""Integration tests for the climate_template preset feature set.

Covers preset_modes, preset_mode_template, set_preset_mode, and the
presets_features / presets_template / set_presets trio on the Heating Circuit 1
entity (presets_features=35 → editable + preserved + target_temperature).
"""

from ha_integration_test_harness import HomeAssistant

CLIMATE = "climate.heating_circuit_1"


def _approx(value: float):
    return (
        lambda s: s not in ("unknown", "unavailable") and abs(float(s) - value) < 1e-6
    )


def test_preset_mode_getter(home_assistant: HomeAssistant) -> None:
    home_assistant.call_action(
        "input_select",
        "select_option",
        {"entity_id": "input_select.hc1_operating_mode", "option": "reduced"},
    )
    home_assistant.assert_entity_state(
        CLIMATE, expected_attributes={"preset_mode": "reduced"}
    )


def test_presets_attribute_exposed(home_assistant: HomeAssistant) -> None:
    # presets_template feeds the `presets` state attribute with each mode's values.
    home_assistant.assert_entity_state(
        CLIMATE,
        expected_attributes={
            "preset_modes": ["automatic", "comfort", "reduced", "protection"],
            "presets": lambda p: isinstance(p, dict)
            and p.get("reduced", {}).get("target_temperature") == 18.0
            and p.get("comfort", {}).get("target_temperature") == 22.0,
        },
    )


def test_set_preset_mode_applies_target_temperature(
    home_assistant: HomeAssistant,
) -> None:
    # Selecting 'reduced' (18°C) must both flip the operating-mode helper and apply
    # the preset's target_temperature through the set_temperature chain.
    home_assistant.call_action(
        "climate", "set_preset_mode", {"entity_id": CLIMATE, "preset_mode": "reduced"}
    )
    home_assistant.assert_entity_state("input_select.hc1_operating_mode", "reduced")
    home_assistant.assert_entity_state(
        "input_number.hc1_target_temperature", _approx(18.0)
    )
    home_assistant.assert_entity_state(
        CLIMATE, expected_attributes={"preset_mode": "reduced", "temperature": 18.0}
    )


def test_set_presets_writes_back_edited_setpoint(home_assistant: HomeAssistant) -> None:
    # With an editable preset active, changing the target temperature fires
    # set_presets, which writes the new value back to the comfort setpoint helper.
    home_assistant.call_action(
        "input_select",
        "select_option",
        {"entity_id": "input_select.hc1_operating_mode", "option": "comfort"},
    )
    home_assistant.assert_entity_state(
        CLIMATE, expected_attributes={"preset_mode": "comfort"}
    )
    home_assistant.call_action(
        "climate", "set_temperature", {"entity_id": CLIMATE, "temperature": 23.5}
    )
    home_assistant.assert_entity_state(
        "input_number.hc1_comfort_setpoint", _approx(23.5)
    )
