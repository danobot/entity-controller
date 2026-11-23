"""Normalize saved controller configuration for the state machine."""

from copy import deepcopy
from datetime import time
import re

import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_NAME
import voluptuous as vol

from .const import (
    CONF_BLOCK_TIMEOUT,
    CONF_CONTROL_ENTITIES,
    CONF_CONTROL_ENTITY,
    CONF_DELAY,
    CONF_ENABLED,
    CONF_IMPORTED_FROM_YAML,
    CONF_OVERRIDE,
    CONF_OVERRIDES,
    CONF_SENSOR,
    CONF_SENSORS,
    CONF_SENSOR_RESETS_TIMER,
    CONF_SENSOR_TYPE,
    CONF_SENSOR_TYPE_DURATION,
    CONF_STATE_ENTITIES,
    CONF_TRIGGER_ON_ACTIVATE,
    CONF_TRIGGER_ON_DEACTIVATE,
    DEFAULT_DELAY,
    SENSOR_TYPE_DURATION,
    SENSOR_TYPE_EVENT,
)


def normalize_yaml(config):
    """Convert legacy aliases to the keys used in the UI and preserve other options."""
    config = deepcopy(dict(config))
    for alias, plural in (
        (CONF_CONTROL_ENTITY, CONF_CONTROL_ENTITIES),
        (CONF_SENSOR, CONF_SENSORS),
        (CONF_OVERRIDE, CONF_OVERRIDES),
    ):
        if alias in config or plural in config:
            config[plural] = list(dict.fromkeys(
                cv.entity_ids(config.pop(alias, None) or [])
                + cv.entity_ids(config.get(plural) or [])
            ))
    for key in (CONF_STATE_ENTITIES, CONF_TRIGGER_ON_ACTIVATE, CONF_TRIGGER_ON_DEACTIVATE):
        if config.get(key) is not None:
            config[key] = cv.entity_ids(config[key])

    for key in (CONF_DELAY, CONF_BLOCK_TIMEOUT):
        if config.get(key) is not None:
            config[key] = cv.positive_int(config[key])

    if not config.get(CONF_CONTROL_ENTITIES) and not config.get(CONF_TRIGGER_ON_ACTIVATE):
        raise vol.Invalid("configure entities or trigger_on_activate")
    return config


def controller_config(subentry):
    """Copy saved controller settings before passing them to the state machine."""
    config = deepcopy(dict(subentry.data))
    config.pop(CONF_ENABLED, None)
    config.pop(CONF_IMPORTED_FROM_YAML, None)
    config[CONF_NAME] = subentry.unique_id
    legacy_duration = config.pop(CONF_SENSOR_TYPE_DURATION, False)
    if CONF_SENSOR_TYPE in config:
        config[CONF_SENSOR_TYPE] = config[CONF_SENSOR_TYPE].lower()
    else:
        config[CONF_SENSOR_TYPE] = SENSOR_TYPE_DURATION if legacy_duration else SENSOR_TYPE_EVENT
    config.setdefault(CONF_SENSOR_RESETS_TIMER, False)
    config.setdefault(CONF_DELAY, DEFAULT_DELAY)
    return config


def normalize_time(value):
    """Validate a clock time or a sunrise/sunset expression from the UI."""
    value = value.strip().lower()
    if not value:
        return None
    if match := re.fullmatch(
        r"(sunrise|sunset)(?:\s*([+-])\s*(\d{1,5}):([0-5]\d)(?::([0-5]\d))?)?",
        value,
    ):
        event, sign, hours, minutes, seconds = match.groups()
        if hours is None:
            return event
        return f"{event} {sign} {int(hours):02}:{minutes}:{seconds or '00'}"
    if match := re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", value):
        hours, minutes, seconds = match.groups()
        return time(int(hours), int(minutes), int(seconds or 0)).isoformat()
    raise ValueError("invalid clock time or solar expression")
