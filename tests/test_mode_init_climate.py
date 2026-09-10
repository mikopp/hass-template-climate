"""Tests for the static / template / static+template configuration matrix.

Each climate mode property (hvac_mode, fan_mode, swing_mode, preset_mode)
has a hardcoded DEFAULT_* and an optional *_template. The bug class: when
only the static configuration is used (no template), the default was never
reconciled with the configured modes list, so an entity could initialise
with — and try to restore — a mode value that is not in its own list.

Three scenarios are exercised for each property:

  1. Static only (1a + 1b)
     1a. Default IS in the configured modes list → entity reports the default.
     1b. Default NOT in the configured modes list → fan/swing/preset reconcile
         to None (null attribute). (hvac_mode has no such case — see the note
         above test_hvacmode_template_follows_source.)

  2. Template only
     Entity's current mode tracks the backing input_select in real time.

  3. Static + template
     Entity initialises from the valid static default; once the template
     evaluates it takes over as the active driver.

Entities and helpers are defined in ha_config/packages/mode_init_climate.yaml.
The conftest baseline_inputs fixture resets every helper to its default-aligned
value before each test.
"""

from ha_integration_test_harness import HomeAssistant


def _set_source(ha: HomeAssistant, entity_id: str, option: str) -> None:
    ha.call_action(
        "input_select",
        "select_option",
        {"entity_id": entity_id, "option": option},
    )


# ── hvac_mode ──────────────────────────────────────────────────────────────────


def test_hvacmode_static_default_valid(home_assistant: HomeAssistant) -> None:
    """Static-only: DEFAULT_HVAC_MODE ('off') in hvac_modes → state 'off'."""
    home_assistant.assert_entity_state("climate.mode_init_hvacmode_static_valid", "off")


# Note: there is no hvac_mode "static invalid" case. DEFAULT_HVAC_MODE is
# HVACMode.OFF, so the default is only "invalid" when hvac_modes omits OFF —
# and Home Assistant rejects such an entity outright (TURN_ON/TURN_OFF features
# are only enabled when OFF is configured). hvac_mode is the entity state and
# cannot be reconciled to None like the fan/swing/preset attributes below.


def test_hvacmode_template_follows_source(home_assistant: HomeAssistant) -> None:
    """Template-only: hvac_mode tracks the backing input_select in real time."""
    _set_source(home_assistant, "input_select.mode_init_hvac_source", "heat")
    home_assistant.assert_entity_state("climate.mode_init_hvacmode_template", "heat")
    _set_source(home_assistant, "input_select.mode_init_hvac_source", "auto")
    home_assistant.assert_entity_state("climate.mode_init_hvacmode_template", "auto")


def test_hvacmode_static_and_template_init_with_static(
    home_assistant: HomeAssistant,
) -> None:
    """Static + template: at baseline (source = 'off' = default) entity is in
    the valid static-default state."""
    home_assistant.assert_entity_state(
        "climate.mode_init_hvacmode_static_and_template", "off"
    )


def test_hvacmode_static_and_template_overrides(
    home_assistant: HomeAssistant,
) -> None:
    """Static + template: template value ('auto') overrides static default ('off')."""
    _set_source(home_assistant, "input_select.mode_init_hvac_source", "auto")
    home_assistant.assert_entity_state(
        "climate.mode_init_hvacmode_static_and_template", "auto"
    )


# ── fan_mode ───────────────────────────────────────────────────────────────────


def test_fanmode_static_default_valid(home_assistant: HomeAssistant) -> None:
    """Static-only: DEFAULT_FAN_MODE ('low') in fan_modes → entity reports 'low'."""
    home_assistant.assert_entity_state(
        "climate.mode_init_fanmode_static_valid",
        expected_attributes={"fan_mode": "low"},
    )


def test_fanmode_static_default_invalid(home_assistant: HomeAssistant) -> None:
    """Static-only: DEFAULT_FAN_MODE ('low') not in [high, medium]
    → reconciled to None."""
    state = home_assistant.get_state("climate.mode_init_fanmode_static_invalid")
    assert state is not None, "climate.mode_init_fanmode_static_invalid not found"
    fan_mode = state["attributes"].get("fan_mode")
    assert (
        fan_mode is None
    ), f"Expected fan_mode=None after reconciliation, got {fan_mode!r}"


def test_fanmode_template_follows_source(home_assistant: HomeAssistant) -> None:
    """Template-only: fan_mode tracks the backing input_select in real time."""
    _set_source(home_assistant, "input_select.mode_init_fan_source", "high")
    home_assistant.assert_entity_state(
        "climate.mode_init_fanmode_template",
        expected_attributes={"fan_mode": "high"},
    )
    _set_source(home_assistant, "input_select.mode_init_fan_source", "medium")
    home_assistant.assert_entity_state(
        "climate.mode_init_fanmode_template",
        expected_attributes={"fan_mode": "medium"},
    )


def test_fanmode_static_and_template_init_with_static(
    home_assistant: HomeAssistant,
) -> None:
    """Static + template: at baseline (source = 'low' = default) entity is in
    the valid static-default state."""
    home_assistant.assert_entity_state(
        "climate.mode_init_fanmode_static_and_template",
        expected_attributes={"fan_mode": "low"},
    )


def test_fanmode_static_and_template_overrides(
    home_assistant: HomeAssistant,
) -> None:
    """Static + template: template value ('high') overrides static default ('low')."""
    _set_source(home_assistant, "input_select.mode_init_fan_source", "high")
    home_assistant.assert_entity_state(
        "climate.mode_init_fanmode_static_and_template",
        expected_attributes={"fan_mode": "high"},
    )


# ── swing_mode ─────────────────────────────────────────────────────────────────


def test_swingmode_static_default_valid(home_assistant: HomeAssistant) -> None:
    """Static-only: DEFAULT_SWING_MODE ('off') in swing_modes → reports 'off'."""
    home_assistant.assert_entity_state(
        "climate.mode_init_swingmode_static_valid",
        expected_attributes={"swing_mode": "off"},
    )


def test_swingmode_static_default_invalid(home_assistant: HomeAssistant) -> None:
    """Static-only: DEFAULT_SWING_MODE ('off') not in [horizontal, vertical]
    → reconciled to None."""
    state = home_assistant.get_state("climate.mode_init_swingmode_static_invalid")
    assert state is not None, "climate.mode_init_swingmode_static_invalid not found"
    swing_mode = state["attributes"].get("swing_mode")
    assert (
        swing_mode is None
    ), f"Expected swing_mode=None after reconciliation, got {swing_mode!r}"


def test_swingmode_template_follows_source(home_assistant: HomeAssistant) -> None:
    """Template-only: swing_mode tracks the backing input_select in real time."""
    _set_source(home_assistant, "input_select.mode_init_swing_source", "horizontal")
    home_assistant.assert_entity_state(
        "climate.mode_init_swingmode_template",
        expected_attributes={"swing_mode": "horizontal"},
    )
    _set_source(home_assistant, "input_select.mode_init_swing_source", "vertical")
    home_assistant.assert_entity_state(
        "climate.mode_init_swingmode_template",
        expected_attributes={"swing_mode": "vertical"},
    )


def test_swingmode_static_and_template_init_with_static(
    home_assistant: HomeAssistant,
) -> None:
    """Static + template: at baseline (source = 'off' = default) entity is in
    the valid static-default state."""
    home_assistant.assert_entity_state(
        "climate.mode_init_swingmode_static_and_template",
        expected_attributes={"swing_mode": "off"},
    )


def test_swingmode_static_and_template_overrides(
    home_assistant: HomeAssistant,
) -> None:
    """Static + template: template value overrides static default ('off')."""
    _set_source(home_assistant, "input_select.mode_init_swing_source", "horizontal")
    home_assistant.assert_entity_state(
        "climate.mode_init_swingmode_static_and_template",
        expected_attributes={"swing_mode": "horizontal"},
    )


# ── preset_mode ────────────────────────────────────────────────────────────────


def test_presetmode_static_default_valid(home_assistant: HomeAssistant) -> None:
    """Static-only: DEFAULT_PRESET_MODE ('comfort') in preset_modes → reports 'comfort'."""
    home_assistant.assert_entity_state(
        "climate.mode_init_presetmode_static_valid",
        expected_attributes={"preset_mode": "comfort"},
    )


def test_presetmode_static_default_invalid(home_assistant: HomeAssistant) -> None:
    """Static-only: DEFAULT_PRESET_MODE ('comfort') not in [eco, away, boost]
    → reconciled to None."""
    state = home_assistant.get_state("climate.mode_init_presetmode_static_invalid")
    assert state is not None, "climate.mode_init_presetmode_static_invalid not found"
    preset_mode = state["attributes"].get("preset_mode")
    assert (
        preset_mode is None
    ), f"Expected preset_mode=None after reconciliation, got {preset_mode!r}"


def test_presetmode_template_follows_source(home_assistant: HomeAssistant) -> None:
    """Template-only: preset_mode tracks the backing input_select in real time."""
    _set_source(home_assistant, "input_select.mode_init_preset_source", "eco")
    home_assistant.assert_entity_state(
        "climate.mode_init_presetmode_template",
        expected_attributes={"preset_mode": "eco"},
    )
    _set_source(home_assistant, "input_select.mode_init_preset_source", "boost")
    home_assistant.assert_entity_state(
        "climate.mode_init_presetmode_template",
        expected_attributes={"preset_mode": "boost"},
    )


def test_presetmode_static_and_template_init_with_static(
    home_assistant: HomeAssistant,
) -> None:
    """Static + template: at baseline (source = 'comfort' = default) entity is
    in the valid static-default state."""
    home_assistant.assert_entity_state(
        "climate.mode_init_presetmode_static_and_template",
        expected_attributes={"preset_mode": "comfort"},
    )


def test_presetmode_static_and_template_overrides(
    home_assistant: HomeAssistant,
) -> None:
    """Static + template: template value overrides static default ('comfort')."""
    _set_source(home_assistant, "input_select.mode_init_preset_source", "eco")
    home_assistant.assert_entity_state(
        "climate.mode_init_presetmode_static_and_template",
        expected_attributes={"preset_mode": "eco"},
    )
