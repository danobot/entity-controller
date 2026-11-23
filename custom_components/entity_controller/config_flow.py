"""Set up Entity Controller and edit its behaviour from Home Assistant."""

from copy import copy
import json

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigSubentryFlow
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import AbortFlow, section
from homeassistant.helpers import selector
from homeassistant.util import slugify

from .config import controller_config, normalize_time
from .const import (
    CONF_BEHAVIOURS,
    CONF_BLOCK_TIMEOUT,
    CONF_CONTROL_ENTITIES,
    CONF_DELAY,
    CONF_DISABLE_BLOCK,
    CONF_ENABLED,
    CONF_END_TIME,
    CONF_NIGHT_MODE,
    CONF_ON_ENTER_CONSTRAINED,
    CONF_ON_ENTER_OVERRIDDEN,
    CONF_ON_EXIT_OVERRIDDEN,
    CONF_OVERRIDES,
    CONF_SENSORS,
    CONF_SENSOR_RESETS_TIMER,
    CONF_SENSOR_STATES_OFF,
    CONF_SENSOR_STATES_ON,
    CONF_SENSOR_TYPE,
    CONF_SERVICE_DATA,
    CONF_SERVICE_DATA_OFF,
    CONF_START_TIME,
    CONF_STATE_ENTITIES,
    CONF_TRANSITION_BEHAVIOUR_IGNORE,
    CONF_TRANSITION_BEHAVIOUR_OFF,
    CONF_TRANSITION_BEHAVIOUR_ON,
    CONF_TRIGGER_ON_ACTIVATE,
    DEFAULT_DELAY,
    DOMAIN,
    INTEGRATION_NAME,
    INTEGRATION_UNIQUE_ID,
    SENSOR_TYPE_DURATION,
    SENSOR_TYPE_EVENT,
    SUBENTRY_CONTROLLER,
)

SERVICE_DATA_FIELDS = (CONF_SERVICE_DATA, CONF_SERVICE_DATA_OFF)
OVERRIDE_ACTIONS = (CONF_ON_ENTER_OVERRIDDEN, CONF_ON_EXIT_OVERRIDDEN)
BEHAVIOUR_FIELDS = (CONF_ON_ENTER_CONSTRAINED, *OVERRIDE_ACTIONS)
OPEN_SECTIONS = {"general", "schedule"}
LIGHT_FIELDS = {
    "brightness_pct": (CONF_SERVICE_DATA, "brightness_pct"),
    "transition": (CONF_SERVICE_DATA, "transition"),
    "off_transition": (CONF_SERVICE_DATA_OFF, "transition"),
}


def _duration(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return {"hours": hours, "minutes": minutes, "seconds": seconds}


def _duration_seconds(data, errors, key):
    value = data.get(key)
    if not value:
        return None
    try:
        seconds = cv.time_period_dict(value).total_seconds()
        if seconds >= 0 and seconds.is_integer():
            return int(seconds)
    except (vol.Invalid, ValueError, TypeError, OverflowError):
        pass
    errors[key] = "invalid_duration"
    return None


def _entities():
    return selector.EntitySelector({"multiple": True})


def _select(key, values):
    return selector.SelectSelector({"options": list(values), "translation_key": key})


def _suggest(fields, values):
    schema = {}
    for field, validator in fields.items():
        if field.schema in values and values[field.schema] is not None:
            field = copy(field)
            field.description = {"suggested_value": values[field.schema]}
        schema[field] = validator
    return vol.Schema(schema)


def _sensor_type():
    return _select(CONF_SENSOR_TYPE, (SENSOR_TYPE_EVENT, SENSOR_TYPE_DURATION))


def _behaviour():
    return _select("behaviour", (
        CONF_TRANSITION_BEHAVIOUR_IGNORE,
        CONF_TRANSITION_BEHAVIOUR_ON,
        CONF_TRANSITION_BEHAVIOUR_OFF,
    ))


def _time_fields():
    return {
        vol.Optional(CONF_START_TIME): selector.TextSelector(),
        vol.Optional(CONF_END_TIME): selector.TextSelector(),
    }


def _light_fields():
    transition = selector.NumberSelector({"min": 0, "step": 0.1, "mode": "box"})
    return {
        vol.Optional("brightness_pct"): selector.NumberSelector(
            {"min": 0, "max": 100, "step": 1, "mode": "box"}
        ),
        vol.Optional("transition"): transition,
        vol.Optional("off_transition"): transition,
        **{vol.Optional(key): selector.ObjectSelector() for key in SERVICE_DATA_FIELDS},
    }


def _reconfigure_fields(config):
    target = vol.Optional if config.get(CONF_TRIGGER_ON_ACTIVATE) else vol.Required
    # Legacy controllers can be activated through an action without any sensors.
    sensors = vol.Required if config.get(CONF_SENSORS) else vol.Optional
    return {
        "general": {
            vol.Required(CONF_NAME): selector.TextSelector(),
            vol.Required(CONF_ENABLED): selector.BooleanSelector(),
            sensors(CONF_SENSORS): _entities(),
            target(CONF_CONTROL_ENTITIES): _entities(),
            vol.Optional(CONF_STATE_ENTITIES): _entities(),
        },
        "schedule": {
            vol.Required(CONF_SENSOR_TYPE): _sensor_type(),
            vol.Required(CONF_DELAY): selector.DurationSelector(),
            vol.Optional(CONF_SENSOR_RESETS_TIMER): selector.BooleanSelector(),
            **_time_fields(),
            vol.Optional(CONF_ON_ENTER_CONSTRAINED): _behaviour(),
            vol.Optional(CONF_SENSOR_STATES_ON): selector.TextSelector(),
            vol.Optional(CONF_SENSOR_STATES_OFF): selector.TextSelector(),
        },
        "manual": {
            vol.Optional(CONF_OVERRIDES): _entities(),
            **{vol.Optional(key): _behaviour() for key in OVERRIDE_ACTIONS},
            vol.Optional(CONF_DISABLE_BLOCK): selector.BooleanSelector(),
            vol.Optional(CONF_BLOCK_TIMEOUT): selector.DurationSelector(),
        },
        "lights": _light_fields(),
        "night": {
            **_time_fields(),
            vol.Optional(CONF_DELAY): selector.DurationSelector(),
            **_light_fields(),
        },
    }


def _light_suggestions(config):
    values = {key: config[key] for key in SERVICE_DATA_FIELDS if config.get(key) is not None}
    for field, (group, key) in LIGHT_FIELDS.items():
        params = values.get(group, {})
        value = params.get(key)
        if isinstance(value, (int, float)):
            values[field] = value
            remaining = {name: item for name, item in params.items() if name != key}
            if remaining:
                values[group] = remaining
            else:
                values.pop(group)
    return values


def _suggested_settings(controller, config):
    behaviours = config.get(CONF_BEHAVIOURS) or {}
    night = config.get(CONF_NIGHT_MODE) or {}
    schedule = {
        CONF_DELAY: _duration(config[CONF_DELAY]),
        CONF_SENSOR_TYPE: config[CONF_SENSOR_TYPE],
        CONF_SENSOR_RESETS_TIMER: config[CONF_SENSOR_RESETS_TIMER],
        CONF_ON_ENTER_CONSTRAINED: behaviours.get(
            CONF_ON_ENTER_CONSTRAINED, CONF_TRANSITION_BEHAVIOUR_IGNORE
        ),
    }
    schedule.update({
        key: ", ".join(str(state) for state in config[key])
        for key in (CONF_SENSOR_STATES_ON, CONF_SENSOR_STATES_OFF)
        if config.get(key)
    })
    schedule.update({key: config[key] for key in (CONF_START_TIME, CONF_END_TIME) if config.get(key)})

    night_settings = _light_suggestions(night)
    night_settings.update({key: night[key] for key in (CONF_START_TIME, CONF_END_TIME) if night.get(key)})
    if night.get(CONF_DELAY) is not None:
        night_settings[CONF_DELAY] = _duration(night[CONF_DELAY])

    return {
        "general": {
            CONF_NAME: controller.title,
            CONF_ENABLED: controller.data.get(CONF_ENABLED, True),
            **{key: config.get(key) or [] for key in (
                CONF_SENSORS, CONF_CONTROL_ENTITIES, CONF_STATE_ENTITIES,
            )},
        },
        "schedule": schedule,
        "manual": {
            CONF_OVERRIDES: config.get(CONF_OVERRIDES) or [],
            **{key: behaviours.get(key, CONF_TRANSITION_BEHAVIOUR_IGNORE) for key in OVERRIDE_ACTIONS},
            CONF_DISABLE_BLOCK: config.get(CONF_DISABLE_BLOCK, False),
            CONF_BLOCK_TIMEOUT: _duration(config.get(CONF_BLOCK_TIMEOUT) or 0),
        },
        "lights": _light_suggestions(config),
        "night": night_settings,
    }


def _edited_sections(initial, submitted, current):
    """Apply the user's edits to the latest data, including fields they cleared."""
    for name, values in submitted.items():
        previous = initial[name]
        edits = {
            key: values.get(key)
            for key in values.keys() | previous.keys()
            if values.get(key) != previous.get(key)
        }
        if edits:
            yield name, {**current[name], **edits}, edits.keys()


def _time_settings(values, saved):
    times = {}
    for key in (CONF_START_TIME, CONF_END_TIME):
        value = values.get(key)
        try:
            times[key] = value if value == saved.get(key) else normalize_time(value or "")
        except ValueError:
            return {}, "invalid_time"
    if bool(times[CONF_START_TIME]) != bool(times[CONF_END_TIME]):
        return {}, "time_pair_required"
    return times, None


def _light_settings(values):
    settings = {
        key: None if values.get(key) in (None, "") else values[key]
        for key in SERVICE_DATA_FIELDS
    }
    if any(value is not None and not isinstance(value, dict) for value in settings.values()):
        return {}, "invalid_service_data"

    for field, (group, key) in LIGHT_FIELDS.items():
        if values.get(field) is not None:
            settings[group] = {**(settings[group] or {}), key: values[field]}
    try:
        json.dumps(settings, allow_nan=False)
    except (TypeError, ValueError):
        return {}, "invalid_service_data"
    return settings, None


def _format_delay(seconds):
    duration = _duration(seconds)
    return " ".join(
        f"{duration[key]} {unit}"
        for key, unit in (("hours", "h"), ("minutes", "min"), ("seconds", "s"))
        if duration[key]
    ) or "0 s"


def _overview(controller, config):
    """Supply the saved settings to the translated form description."""
    controlled = config.get(CONF_CONTROL_ENTITIES) or []
    monitored = config.get(CONF_STATE_ENTITIES) or []
    start = config.get(CONF_START_TIME) or ""
    end = config.get(CONF_END_TIME) or ""
    duration_mode = config[CONF_SENSOR_TYPE] == SENSOR_TYPE_DURATION

    return {
        "controller_name": controller.title,
        "enabled": "✓" if controller.data.get(CONF_ENABLED, True) else "—",
        "sensor_count": str(len(config.get(CONF_SENSORS) or [])),
        "target_count": str(len(controlled)),
        "monitored_count": str(len(monitored or controlled)),
        "override_count": str(len(config.get(CONF_OVERRIDES) or [])),
        "duration_mode": "✓" if duration_mode else "—",
        "reset_on_clear": "✓" if duration_mode and config[CONF_SENSOR_RESETS_TIMER] else "—",
        "delay": _format_delay(config[CONF_DELAY]),
        "active_hours": f"{start} → {end}" if start and end else "24 h",
    }


class ControllerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create the shared config entry for all controllers."""

    VERSION = 2

    async def async_step_user(self, user_input=None):
        parent = self.hass.config_entries.async_entry_for_domain_unique_id(
            DOMAIN, INTEGRATION_UNIQUE_ID
        )
        if parent:
            return self.async_abort(reason="already_configured")
        if user_input is None:
            return self.async_show_form(step_id="user")
        return await self.async_step_import(user_input)

    async def async_step_import(self, user_input):
        await self.async_set_unique_id(INTEGRATION_UNIQUE_ID)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=INTEGRATION_NAME, data={})

    @classmethod
    @callback
    def async_get_supported_subentry_types(cls, entry):
        if entry.unique_id == INTEGRATION_UNIQUE_ID:
            return {SUBENTRY_CONTROLLER: ControllerSubentryFlow}
        return {}


class ControllerSubentryFlow(ConfigSubentryFlow):
    """Create or reconfigure an individual controller."""

    @property
    def _entry(self):
        return self.hass.config_entries.async_get_known_entry(self.handler[0])

    @property
    def _controller(self):
        subentry = self._entry.subentries.get(self.context["subentry_id"])
        if subentry is None:
            raise AbortFlow("controller_removed")
        return subentry

    def _duplicate_name(self, name, current=None):
        slug = slugify(name)
        return any(
            subentry is not current and slugify(subentry.title) == slug
            for subentry in self._entry.subentries.values()
        )

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            name = user_input[CONF_NAME].strip()
            unique_id = slugify(name)
            if not unique_id:
                errors[CONF_NAME] = "invalid_name"
            elif self._duplicate_name(name) or any(
                subentry.unique_id == unique_id for subentry in self._entry.subentries.values()
            ):
                errors[CONF_NAME] = "duplicate_name"
            for key in (CONF_SENSORS, CONF_CONTROL_ENTITIES):
                if not user_input[key]:
                    errors[key] = "entities_required"
            delay = _duration_seconds(user_input, errors, CONF_DELAY)
            if not errors:
                data = {key: value for key, value in user_input.items() if key != CONF_NAME}
                data[CONF_DELAY] = delay or 0
                return self.async_create_entry(title=name, data=data, unique_id=unique_id)

        fields = {
            vol.Required(CONF_NAME): selector.TextSelector(),
            vol.Required(CONF_SENSORS): _entities(),
            vol.Required(CONF_CONTROL_ENTITIES): _entities(),
            vol.Required(CONF_DELAY, default=_duration(DEFAULT_DELAY)): selector.DurationSelector(),
            vol.Required(CONF_SENSOR_TYPE, default=SENSOR_TYPE_EVENT): _sensor_type(),
        }
        return self.async_show_form(
            step_id="user", data_schema=_suggest(fields, user_input or {}), errors=errors
        )

    async def async_step_reconfigure(self, user_input=None):
        controller = self._controller
        config = controller_config(controller)
        saved_form = _suggested_settings(controller, config)
        errors = {}
        if user_input is None:
            self._initial_settings = saved_form
        else:
            changes = {}
            title = controller.title
            for name, values, edited in _edited_sections(
                self._initial_settings, user_input, saved_form
            ):
                if name == "general":
                    settings, error = self._read_general(values, controller, config)
                    title = settings.pop(CONF_NAME, title)
                elif name == "schedule":
                    settings, error = self._read_schedule(values, config)
                elif name == "manual":
                    settings, error = self._read_manual(values)
                elif name == "lights":
                    settings, error = _light_settings(values)
                else:
                    settings, error = self._read_night(
                        values, config.get(CONF_NIGHT_MODE) or {}, edited
                    )
                if error:
                    errors[name] = error
                else:
                    changes.update(settings)

            if not errors:
                behaviours = {key: changes.pop(key) for key in BEHAVIOUR_FIELDS if key in changes}
                if behaviours:
                    changes[CONF_BEHAVIOURS] = {**(config.get(CONF_BEHAVIOURS) or {}), **behaviours}
                return self.async_update_and_abort(
                    self._entry, controller, title=title, data_updates=changes
                )

        shown = saved_form if user_input is None else user_input
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({
                vol.Required(name): section(
                    _suggest(fields, shown.get(name, {})),
                    {"collapsed": name not in OPEN_SECTIONS and name not in errors},
                )
                for name, fields in _reconfigure_fields(config).items()
            }),
            errors=errors,
            description_placeholders=_overview(controller, config),
        )

    def _read_general(self, values, controller, config):
        name = values[CONF_NAME].strip()
        if not slugify(name):
            return {}, "invalid_name"
        if name != controller.title and self._duplicate_name(name, controller):
            return {}, "duplicate_name"

        targets = values.get(CONF_CONTROL_ENTITIES) or []
        sensors = values.get(CONF_SENSORS) or []
        if not targets and not config.get(CONF_TRIGGER_ON_ACTIVATE):
            return {}, "targets_required"
        if not sensors and config.get(CONF_SENSORS):
            return {}, "sensors_required"
        return {
            CONF_NAME: name,
            CONF_ENABLED: values[CONF_ENABLED],
            CONF_CONTROL_ENTITIES: targets,
            CONF_SENSORS: sensors,
            CONF_STATE_ENTITIES: values.get(CONF_STATE_ENTITIES) or [],
        }, None

    def _read_schedule(self, values, config):
        times, error = _time_settings(values, config)
        if error:
            return {}, error
        errors = {}
        delay = _duration_seconds(values, errors, CONF_DELAY)
        if errors:
            return {}, errors[CONF_DELAY]
        return {
            **times,
            CONF_DELAY: delay or 0,
            CONF_SENSOR_TYPE: values[CONF_SENSOR_TYPE],
            CONF_SENSOR_RESETS_TIMER: values.get(CONF_SENSOR_RESETS_TIMER, False),
            CONF_ON_ENTER_CONSTRAINED: values.get(
                CONF_ON_ENTER_CONSTRAINED, CONF_TRANSITION_BEHAVIOUR_IGNORE
            ),
            **{
                key: [
                    state.strip() for state in (values.get(key) or "").split(",") if state.strip()
                ] or None
                for key in (CONF_SENSOR_STATES_ON, CONF_SENSOR_STATES_OFF)
            },
        }, None

    def _read_manual(self, values):
        errors = {}
        timeout = _duration_seconds(values, errors, CONF_BLOCK_TIMEOUT)
        if errors:
            return {}, errors[CONF_BLOCK_TIMEOUT]
        return {
            CONF_OVERRIDES: values.get(CONF_OVERRIDES) or [],
            CONF_DISABLE_BLOCK: values.get(CONF_DISABLE_BLOCK, False),
            CONF_BLOCK_TIMEOUT: timeout or None,
            **{key: values.get(key, CONF_TRANSITION_BEHAVIOUR_IGNORE) for key in OVERRIDE_ACTIONS},
        }, None

    def _read_night(self, values, config, edited):
        times, error = _time_settings(values, config)
        if error:
            return {}, error
        lights, error = _light_settings(values)
        if error:
            return {}, error
        errors = {}
        delay = _duration_seconds(values, errors, CONF_DELAY)
        if errors:
            return {}, errors[CONF_DELAY]
        if not times[CONF_START_TIME]:
            if not config and (delay is not None or any(v is not None for v in lights.values())):
                return {}, "night_times_required"
            return {CONF_NIGHT_MODE: None}, None

        # Preserve inherited or explicit settings when their fields were not edited.
        night = {**config, **times}
        updated = edited | {group for field, (group, _) in LIGHT_FIELDS.items() if field in edited}
        for key, value in {**lights, CONF_DELAY: delay}.items():
            if key not in updated:
                continue
            if value is None:
                night.pop(key, None)
            else:
                night[key] = value
        return {CONF_NIGHT_MODE: night}, None
