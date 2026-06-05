"""Integration test: set_temperature action reads entity's own attribute.

The E2M Fußbodenheizung pattern: the set_temperature action script references
state_attr('climate.e2m_test_template', 'temperature') — the entity's OWN
freshly-committed temperature attribute — instead of the {{ temperature }} script
variable. It also derives a second value from it (raw setpoint = temp * 6.375).

This test verifies the integration's ordering contract: the attribute is written
to HA state BEFORE the action script runs, so state_attr(self, 'temperature')
inside the script always sees the new value, not the previous one.
"""

from ha_integration_test_harness import HomeAssistant

CLIMATE = "climate.e2m_test_template"


def test_set_temperature_derives_from_self_attribute(
    home_assistant: HomeAssistant,
) -> None:
    """set_temperature writes the attribute to state before the action runs.

    Calling set_temperature(21.5) must:
      - update climate.e2m_test_template temperature to 21.5
      - write input_number.e2m_setpoint_temp = 21.5  (from state_attr(self,'temperature'))
      - write input_number.e2m_setpoint_raw = 137    (round(21.5 * 6.375))

    If the action ran BEFORE the state write, state_attr(self,'temperature') would
    return the stale default and both helpers would get wrong values.
    """
    home_assistant.call_action(
        "climate",
        "set_temperature",
        {"entity_id": CLIMATE, "temperature": 21.5},
    )
    home_assistant.assert_entity_state(
        CLIMATE,
        expected_attributes={"temperature": 21.5},
    )
    home_assistant.assert_entity_state("input_number.e2m_setpoint_temp", "21.5")
    home_assistant.assert_entity_state("input_number.e2m_setpoint_raw", "137")
