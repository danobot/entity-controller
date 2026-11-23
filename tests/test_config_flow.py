"""Exercise UI and YAML configuration through Home Assistant's entry managers."""

import asyncio
import json
from types import MappingProxyType

import pytest
import pytest_asyncio
from homeassistant import bootstrap, config_entries, loader
from homeassistant.components.config.config_entries import SubentryManagerFlowResourceView
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers import entity_registry, translation
from homeassistant.setup import async_setup_component

from custom_components.entity_controller.const import DOMAIN, INTEGRATION_UNIQUE_ID, SUBENTRY_CONTROLLER
from custom_components.entity_controller.diagnostics import async_get_config_entry_diagnostics

MOTION = "binary_sensor.motion"
SECOND_MOTION = "binary_sensor.second_motion"
OVERRIDE = "input_boolean.stop_lights"
LIGHT = "light.garden"
SECOND_LIGHT = "light.entry"


@pytest_asyncio.fixture
async def ha(tmp_path, request):
    """Initialize the core and registries without starting unrelated integrations."""
    hass = HomeAssistant(str(tmp_path))
    legacy_settings = getattr(request, "param", ())
    if legacy_settings:
        legacy_entries = [
            config_entries.ConfigEntry(
                domain=DOMAIN, version=1, minor_version=1,
                discovery_keys=MappingProxyType({}), subentries_data=None,
                **settings,
            ).as_dict()
            for settings in legacy_settings
        ]
        storage = tmp_path / ".storage"
        storage.mkdir()
        (storage / config_entries.STORAGE_KEY).write_text(json.dumps({
            "key": config_entries.STORAGE_KEY,
            "version": config_entries.STORAGE_VERSION,
            "minor_version": config_entries.STORAGE_VERSION_MINOR,
            "data": {"entries": legacy_entries},
        }))

    hass.config.skip_pip = True
    hass.config_entries = config_entries.ConfigEntries(hass, {})
    loader.async_setup(hass)
    assert await bootstrap.async_load_base_functionality(hass) is not False
    hass.set_state(CoreState.running)

    calls = []

    async def light_service(call):
        entity_id = call.data["entity_id"]
        calls.append((call.service, entity_id))
        state = "on" if call.service == "turn_on" else "off"
        hass.states.async_set(entity_id, state, context=call.context)

    for service in ("turn_on", "turn_off"):
        hass.services.async_register("light", service, light_service)
    for entity_id in (MOTION, SECOND_MOTION, OVERRIDE, LIGHT, SECOND_LIGHT):
        hass.states.async_set(entity_id, "off")

    yield hass, calls

    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state == config_entries.ConfigEntryState.LOADED:
            await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_stop()


async def _flush(hass):
    await asyncio.sleep(0.01)
    await hass.async_block_till_done()


async def _create_integration(hass):
    manager = hass.config_entries.flow
    user = await manager.async_init(DOMAIN, context={"source": "user"})
    result = await manager.async_configure(user["flow_id"], {})
    assert result["type"] == "create_entry"
    return result["result"]


async def _create(hass, entry, name="Outdoor lights", **data):
    manager = hass.config_entries.subentries
    user = await manager.async_init(
        (entry.entry_id, SUBENTRY_CONTROLLER), context={"source": "user"}
    )
    values = {"name": name, "sensors": [MOTION], "entities": [LIGHT], **data}
    result = await manager.async_configure(user["flow_id"], values)
    assert result["type"] == "create_entry"
    await _flush(hass)
    return next(sub for sub in entry.subentries.values() if sub.title == name)


async def _reconfigure(hass, entry, controller):
    form = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_CONTROLLER),
        context={"source": "reconfigure", "subentry_id": controller.subentry_id},
    )
    assert (form["type"], form["step_id"]) == ("form", "reconfigure")
    return form


def _sections(hass, form):
    """Read the expandable sections as Home Assistant sends them to its frontend."""
    view = SubentryManagerFlowResourceView(hass.config_entries.subentries)
    serialized = view._prepare_result_json(form)["data_schema"]
    assert all(item["type"] == "expandable" and item["required"] for item in serialized)
    return {item["name"]: item for item in serialized}


def _form_values(hass, form):
    return {
        name: {
            field["name"]: field["description"]["suggested_value"]
            for field in group["schema"]
            if "suggested_value" in field.get("description", {})
        }
        for name, group in _sections(hass, form).items()
    }


async def _save(hass, form, values):
    result = await hass.config_entries.subentries.async_configure(form["flow_id"], values)
    await _flush(hass)
    return result


async def _edit(hass, entry, controller, **changes):
    form = await _reconfigure(hass, entry, controller)
    values = _form_values(hass, form)
    for name, fields in changes.items():
        values[name].update(fields)
    return await _save(hass, form, values)


def _assert_saved(result):
    assert (result["type"], result["reason"]) == ("abort", "reconfigure_successful")


@pytest.mark.asyncio
async def test_single_integration_and_controller_reconfiguration(ha):
    hass, calls = ha
    if hasattr(loader, "async_get_integration_descriptions"):
        descriptions = await loader.async_get_integration_descriptions(hass)
        assert descriptions["custom"]["integration"][DOMAIN]["config_flow"]
    else:
        assert DOMAIN in await loader.async_get_config_flows(hass, "integration")
    entry = await _create_integration(hass)
    subentry = await _create(hass, entry)
    assert entry.state == config_entries.ConfigEntryState.LOADED
    assert hass.states.get("entity_controller.outdoor_lights").state == "idle"
    assert calls == []

    duplicate = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert (duplicate["type"], duplicate["reason"]) == ("abort", "already_configured")

    duplicate = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_CONTROLLER), context={"source": "user"},
    )
    result = await hass.config_entries.subentries.async_configure(duplicate["flow_id"], {
        "name": "Outdoor lights", "sensors": [MOTION], "entities": [LIGHT],
    })
    assert result["errors"] == {"name": "duplicate_name"}

    form = await _reconfigure(hass, entry, subentry)
    sections = _sections(hass, form)
    assert list(sections) == ["general", "schedule", "manual", "lights", "night"]
    assert {name for name, group in sections.items() if group["expanded"]} == {
        "general", "schedule",
    }
    assert form["description_placeholders"]["controller_name"] == "Outdoor lights"
    assert form["description_placeholders"]["monitored_count"] == "1"
    assert form["description_placeholders"]["active_hours"] == "24 h"
    values = _form_values(hass, form)
    assert values["general"]["sensors"] == [MOTION]
    assert values["general"]["entities"] == [LIGHT]
    assert values["schedule"]["delay"] == {"hours": 0, "minutes": 3, "seconds": 0}

    values["general"].update(
        name="Garden", sensors=[MOTION, SECOND_MOTION], state_entities=[LIGHT]
    )
    values["schedule"].update(
        start_time="25:00", end_time="sunrise + 00:30:00", on_enter_constrained="off",
        delay={"minutes": 5}, sensor_type="duration", sensor_resets_timer=True,
    )
    values["manual"].update(overrides=[OVERRIDE], on_enter_overridden="off")
    values["lights"].update(
        brightness_pct=60, transition=2, off_transition=1, service_data={"color_name": "red"}
    )
    values["night"].update(start_time="22:00", brightness_pct=10)

    result = await _save(hass, form, values)
    assert result["errors"] == {"schedule": "invalid_time", "night": "time_pair_required"}
    assert _sections(hass, result)["night"]["expanded"]
    assert _form_values(hass, result) == values
    assert subentry.title == "Outdoor lights"
    assert "night_mode" not in subentry.data
    assert "overrides" not in subentry.data
    assert result["description_placeholders"]["controller_name"] == "Outdoor lights"

    values["schedule"]["start_time"] = "sunset - 00:30"
    values["night"]["end_time"] = "05:00"
    _assert_saved(await _save(hass, result, values))
    assert subentry.title == "Garden"
    assert subentry.unique_id == "outdoor_lights"
    assert hass.states.get("entity_controller.outdoor_lights").name == "Garden"
    assert subentry.data["start_time"] == "sunset - 00:30:00"
    assert subentry.data["service_data"] == {
        "brightness_pct": 60, "transition": 2, "color_name": "red",
    }
    assert subentry.data["service_data_off"] == {"transition": 1}
    assert subentry.data["night_mode"]["service_data"] == {"brightness_pct": 10}
    assert subentry.data["behaviours"]["on_enter_constrained"] == "off"
    assert subentry.data["behaviours"]["on_enter_overridden"] == "off"

    reopened = await _reconfigure(hass, entry, subentry)
    values = _form_values(hass, reopened)
    assert values["manual"]["overrides"] == [OVERRIDE]
    assert values["lights"]["brightness_pct"] == 60
    assert values["night"]["start_time"] == "22:00:00"
    summary = reopened["description_placeholders"]
    assert summary["sensor_count"] == "2"
    assert summary["target_count"] == summary["monitored_count"] == "1"
    assert summary["delay"] == "5 min"
    assert summary["duration_mode"] == summary["reset_on_clear"] == "✓"
    assert summary["active_hours"] == "sunset - 00:30:00 → sunrise + 00:30:00"
    assert summary["override_count"] == "1"

    key = f"component.{DOMAIN}.config_subentries.controller.step.reconfigure"
    for language, label in (("en", "Saved configuration"), ("it", "Configurazione salvata")):
        strings = await translation.async_get_translations(
            hass, language, "config_subentries", [DOMAIN]
        )
        overview = strings[f"{key}.description"].format_map(summary)
        assert label in overview
        assert summary["active_hours"] in overview
        assert strings[f"{key}.submit"] == ("Save" if language == "en" else "Salva")

    previous_data = subentry.data
    _assert_saved(await _save(hass, reopened, values))
    assert subentry.data is previous_data
    assert calls == []


@pytest.mark.asyncio
async def test_reconfigure_clears_fields_and_merges_another_forms_edits(ha):
    hass, _ = ha
    entry = await _create_integration(hass)
    subentry = await _create(hass, entry)
    _assert_saved(await _edit(
        hass, entry, subentry,
        schedule={"start_time": "17:00", "end_time": "06:00"},
        night={"start_time": "22:00", "end_time": "05:00", "brightness_pct": 10},
    ))
    first = await _reconfigure(hass, entry, subentry)
    second = await _reconfigure(hass, entry, subentry)
    first_values = _form_values(hass, first)
    second_values = _form_values(hass, second)

    second_values["schedule"]["delay"] = {"minutes": 8}
    _assert_saved(await _save(hass, second, second_values))

    first_values["schedule"].pop("start_time")
    first_values["schedule"].pop("end_time")
    first_values["night"].pop("brightness_pct")
    _assert_saved(await _save(hass, first, first_values))
    assert subentry.data["delay"] == 480
    assert subentry.data["start_time"] is None
    assert subentry.data["end_time"] is None
    assert subentry.data["night_mode"] == {"start_time": "22:00:00", "end_time": "05:00:00"}


@pytest.mark.asyncio
async def test_yaml_import_keeps_registry_identity_and_saved_options(ha, tmp_path):
    hass, _ = ha
    registry = entity_registry.async_get(hass)
    old_entity = registry.async_get_or_create(DOMAIN, DOMAIN, "perimeter", suggested_object_id="outside")
    yaml_config = {
        DOMAIN: {
            "perimeter": {
                "friendly_name": "Luci Perimetro",
                "unique_id": "old_yaml_value",
                "sensor": MOTION,
                "entities": [LIGHT, SECOND_LIGHT],
                "state_entities": [LIGHT],
                "override": OVERRIDE,
                "sensor_type": "duration",
                "sensor_resets_timer": True,
                "delay": 300,
                "start_time": "sunset - 00:30:00",
                "end_time": "sunrise + 00:30:00",
                "behaviours": {"on_enter_constrained": "off"},
            }
        }
    }
    assert await async_setup_component(hass, DOMAIN, yaml_config)
    await _flush(hass)
    (entry,) = hass.config_entries.async_entries(DOMAIN)
    assert entry.source == "import"
    assert entry.unique_id == INTEGRATION_UNIQUE_ID
    (subentry,) = entry.subentries.values()
    assert subentry.unique_id == "perimeter"
    assert subentry.data["overrides"] == [OVERRIDE]
    assert hass.states.get(old_entity.entity_id) is not None
    assert registry.async_get(old_entity.entity_id).config_entry_id == entry.entry_id

    assert registry.async_get(old_entity.entity_id).config_subentry_id == subentry.subentry_id

    result = await _edit(
        hass, entry, subentry,
        general={"sensors": [MOTION, SECOND_MOTION]},
        schedule={"delay": {"minutes": 6}},
    )
    _assert_saved(result)
    (tmp_path / "configuration.yaml").write_text(
        "entity_controller:\n"
        "  perimeter:\n"
        "    sensor: binary_sensor.motion\n"
        "    entity: light.garden\n"
        "    delay: 999\n"
        "  porch:\n"
        "    sensor: binary_sensor.second_motion\n"
        "    entity: light.entry\n"
    )
    await hass.services.async_call(DOMAIN, "reload", blocking=True)
    await _flush(hass)
    assert hass.config_entries.async_entries(DOMAIN) == [entry]
    assert {sub.unique_id for sub in entry.subentries.values()} == {"perimeter", "porch"}
    assert subentry.data["delay"] == 360
    controller = entry.runtime_data.controllers[subentry.subentry_id]
    assert controller.model.config["delay"] == 360
    assert controller.model.stateEntities == [LIGHT]


@pytest.mark.asyncio
async def test_options_preserve_active_timer_and_manual_block(ha):
    hass, calls = ha
    entry = await _create_integration(hass)
    subentry = await _create(hass, entry, delay={"seconds": 30})
    controller = entry.runtime_data.controllers[subentry.subentry_id]
    await hass.services.async_call(
        DOMAIN, "activate", {"entity_id": controller.entity_id}, blocking=True
    )
    await _flush(hass)
    assert controller.state == "active_timer"
    deadline = controller.model.timer_deadline
    assert calls == [("turn_on", LIGHT)]

    result = await _edit(hass, entry, subentry, schedule={"delay": {"minutes": 2}})
    _assert_saved(result)
    assert controller.state == "active_timer"
    assert controller.model.timer_deadline == pytest.approx(deadline, abs=0.01, rel=0)
    assert calls == [("turn_on", LIGHT)]

    hass.states.async_set(LIGHT, "on", {"brightness": 70})
    await _flush(hass)
    assert controller.state == "blocked"
    assert controller.model.timer_deadline is None
    _assert_saved(await _edit(
        hass, entry, subentry, manual={"block_timeout": {"seconds": 30}}
    ))
    assert controller.state == "blocked"
    assert controller.model.block_deadline is not None
    assert calls == [("turn_on", LIGHT)]

    report = await async_get_config_entry_diagnostics(hass, entry)
    diagnostics = report["controllers"][subentry.subentry_id]
    assert diagnostics["state"] == "blocked"
    assert [t["to"] for t in diagnostics["transitions"]] == ["idle", "active_timer", "blocked"]


@pytest.mark.asyncio
async def test_duration_override_expiry_and_independent_unload(ha):
    hass, calls = ha
    entry = await _create_integration(hass)
    first = await _create(hass, entry, delay={"seconds": 1}, sensor_type="duration")
    second = await _create(hass, entry, name="Entry", entities=[SECOND_LIGHT], sensors=[SECOND_MOTION])
    first_controller = entry.runtime_data.controllers[first.subentry_id]
    second_controller = entry.runtime_data.controllers[second.subentry_id]
    _assert_saved(await _edit(
        hass, entry, first,
        schedule={"sensor_resets_timer": True},
        manual={"overrides": [OVERRIDE]},
    ))

    hass.states.async_set(MOTION, "on")
    await _flush(hass)
    assert first_controller.state == "active_timer"
    await asyncio.sleep(1.05)
    assert first_controller.state == "active_timer"
    assert first_controller.attributes["expires_at"] == "pending sensor"

    hass.states.async_set(OVERRIDE, "on")
    await _flush(hass)
    assert first_controller.state == "overridden"
    hass.states.async_set(OVERRIDE, "off")
    await _flush(hass)
    assert first_controller.state == "active_timer"

    hass.states.async_set(MOTION, "off")
    await _flush(hass)
    assert first_controller.model.timer_deadline is not None
    await asyncio.sleep(1.05)
    await _flush(hass)
    assert first_controller.state == "idle"
    assert calls[-1] == ("turn_off", LIGHT)

    hass.states.async_set(MOTION, "on")
    await _flush(hass)
    hass.states.async_set(SECOND_MOTION, "on")
    await _flush(hass)
    second_model = second_controller.model
    second_deadline = second_model.timer_deadline

    _assert_saved(await _edit(hass, entry, first, lights={"brightness_pct": 60}))
    assert first_controller.model.config["service_data"] == {"brightness_pct": 60}
    assert second_controller.model is second_model
    assert second_controller.model.timer_deadline == second_deadline

    _assert_saved(await _edit(hass, entry, first, general={"enabled": False}))
    assert first.subentry_id not in entry.runtime_data.controllers
    assert first_controller.model.timer_deadline is None
    assert second_controller.model is second_model
    assert second_controller.model.timer_deadline == second_deadline

    _assert_saved(await _edit(hass, entry, first, general={"enabled": True}))
    first_controller = entry.runtime_data.controllers[first.subentry_id]
    hass.states.async_set(LIGHT, "off")
    hass.states.async_set(MOTION, "off")
    hass.states.async_set(MOTION, "on")
    await _flush(hass)
    assert first_controller.model.timer_deadline is not None

    form = await _reconfigure(hass, entry, first)
    values = _form_values(hass, form)
    values["lights"]["brightness_pct"] = 50
    assert hass.config_entries.async_remove_subentry(entry, first.subentry_id)
    await _flush(hass)
    result = await _save(hass, form, values)
    assert (result["type"], result["reason"]) == ("abort", "controller_removed")
    assert first_controller.model.timer_deadline is None
    assert entity_registry.async_get(hass).async_get(first_controller.entity_id) is None
    state = hass.states.get(first_controller.entity_id)
    assert state is None or state.state == "unavailable"
    calls.clear()
    hass.states.async_set(MOTION, "off")
    assert second_controller.state == "active_timer"
    await asyncio.sleep(1.05)
    assert calls == []
    assert entry.state == config_entries.ConfigEntryState.LOADED


@pytest.mark.asyncio
@pytest.mark.parametrize("ha", [[
    {
        "title": "Existing controller",
        "unique_id": "existing",
        "data": {"sensors": [MOTION], "entities": [LIGHT], "delay": 10},
        "options": {"delay": 300, "sensor_type": "duration"},
        "source": "user",
    },
    {
        "title": "Paused controller",
        "unique_id": "paused",
        "data": {"sensors": [SECOND_MOTION], "entities": [SECOND_LIGHT]},
        "options": {},
        "source": "import",
        "disabled_by": config_entries.ConfigEntryDisabler.USER,
    },
]], indirect=True)
async def test_migrates_legacy_entries_and_preserves_registry(ha):
    hass, calls = ha
    registry = entity_registry.async_get(hass)
    old, paused = hass.config_entries.async_entries(DOMAIN)
    entity = registry.async_get_or_create(
        DOMAIN, DOMAIN, old.unique_id, config_entry=old, suggested_object_id="custom_old_id"
    )
    registry.async_update_entity(entity.entity_id, name="Custom name")
    paused_entity = registry.async_get_or_create(
        DOMAIN, DOMAIN, paused.unique_id, config_entry=paused
    )

    assert await async_setup_component(hass, DOMAIN, {
        DOMAIN: {"existing": {"sensor": MOTION, "entity": LIGHT, "delay": 999}},
    })
    await _flush(hass)
    (entry,) = hass.config_entries.async_entries(DOMAIN)
    assert entry.unique_id == INTEGRATION_UNIQUE_ID
    subentries = {subentry.unique_id: subentry for subentry in entry.subentries.values()}
    assert set(subentries) == {"existing", "paused"}
    assert subentries["existing"].data["delay"] == 300
    assert subentries["existing"].data["sensor_type"] == "duration"
    assert subentries["paused"].data["enabled"] is False
    assert hass.states.get(entity.entity_id).name == "Custom name"
    assert calls == []

    for previous, slug in ((entity, "existing"), (paused_entity, "paused")):
        record = registry.async_get(previous.entity_id)
        assert record.config_entry_id == entry.entry_id
        assert record.config_subentry_id == subentries[slug].subentry_id

    paused_subentry = subentries["paused"]
    assert paused_subentry.subentry_id not in entry.runtime_data.controllers
    _assert_saved(await _edit(hass, entry, paused_subentry, general={"enabled": True}))
    assert hass.states.get(paused_entity.entity_id).state == "idle"

    assert await hass.config_entries.async_reload(entry.entry_id)
    await _flush(hass)
    assert hass.states.get(entity.entity_id).name == "Custom name"
    assert hass.states.get(paused_entity.entity_id).state == "idle"
    assert calls == []
