"""The tests for the input_boolean component."""
# pylint: disable=protected-access
import asyncio
import logging
import pytest
from unittest.mock import patch
from datetime import timedelta
from homeassistant.core import CoreState, State, Context
from homeassistant import core, const, setup
from homeassistant.setup import async_setup_component
from homeassistant.components import light, binary_sensor, async_setup
from homeassistant.const import (
    STATE_ON, STATE_OFF, ATTR_ENTITY_ID, ATTR_FRIENDLY_NAME, ATTR_ICON,
    SERVICE_TOGGLE, SERVICE_TURN_OFF, SERVICE_TURN_ON)
import homeassistant.util.dt as dt
from tests.common import (
    mock_component, mock_restore_cache, async_fire_time_changed)

_LOGGER = logging.getLogger(__name__)


@pytest.fixture
def hass_et(loop, hass):
    """Set up a Home Assistant instance for these tests."""
    # We need to do this to get access to homeassistant/turn_(on,off)
    loop.run_until_complete(async_setup(hass, {core.DOMAIN: {}}))

    loop.run_until_complete(
        setup.async_setup_component(hass, light.DOMAIN, {
            'light': [{
                'platform': 'demo'
            }]
        }))
    loop.run_until_complete(
        setup.async_setup_component(hass, binary_sensor.DOMAIN, {
            'binary_sensor': [{
                'platform': 'demo'
            }]
        }))

    return hass


async def test_config(hass):
    """Test config."""
    invalid_configs = [
        None,
        1,
        {},
        {'name with space': None},
    ]

    for cfg in invalid_configs:
        assert not await async_setup_component(hass, 'input_boolean',
                                               {'input_boolean': cfg})
