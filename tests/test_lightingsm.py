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
    mock_component, mock_restore_cache ,async_fire_time_changed)

_LOGGER = logging.getLogger(__name__)
ENTITY = 'lightingsm.test'
CONTROL_ENTITY = 'light.kitchen_lights';
CONTROL_ENTITY2 = 'light.bed_light';
CONTROL_ENTITIES = [CONTROL_ENTITY, CONTROL_ENTITY2]
SENSOR_ENTITY = 'binary_sensor.movement_backyard';
SENSOR_ENTITY2 = 'binary_sensor.basement_floor_wet';
SENSOR_ENTITIES = [SENSOR_ENTITY, SENSOR_ENTITY2]
STATE_ENTITY = 'binary_sensor.movement_backyard'
STATE_ENTITY2 = 'binary_sensor.basement_floor_wet'
STATE_ENTITIES = [STATE_ENTITY, STATE_ENTITY2]
STATE_IDLE = 'idle'
STATE_ACTIVE = 'active_timer'
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
        assert not await async_setup_component(hass, 'input_boolean', {'input_boolean': cfg})


async def test_config_options(hass_et):
    """Test configuration options."""
    hass = hass_et
    hass.state = CoreState.starting
    _LOGGER.debug('ENTITIES @ start: %s', hass.states.async_entity_ids())

    assert await async_setup_component(hass, 'lightingsm', {'lightingsm': {
        'test': {'entity': CONTROL_ENTITY,
            'sensor': SENSOR_ENTITY
        },
        }})

    _LOGGER.debug('ENTITIES: %s', hass.states.async_entity_ids())
    hass.states.async_set(CONTROL_ENTITY, 'off')
    hass.states.async_set(SENSOR_ENTITY, 'off')

    await hass.async_block_till_done()
    
    assert state(hass) == STATE_IDLE

    hass.states.async_set(SENSOR_ENTITY, 'on')
    await hass.async_block_till_done()

    assert hass.states.get(ENTITY).state == STATE_ACTIVE
    
    # with patch(('threading.timer.dt_util.utcnow'), return_value=future):
    #     async_fire_time_changed(hass, future)
    #     await hass.async_block_till_done()
    # future = dt.utcnow() + timedelta(seconds=300)
    # async_fire_time_changed(hass, future)
    # assert state(hass) == STATE_IDLE


def state(hass):
    return hass.states.get(ENTITY).state
async def methods(hass):
    """Test is_on, turn_on, turn_off methods."""
    assert await async_setup_component(hass, DOMAIN, {DOMAIN: {
        'test_1': None,
    }})
    entity_id = 'input_boolean.test_1'

    assert not is_on(hass, entity_id)

    await hass.services.async_call(
        DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: entity_id})

    await hass.async_block_till_done()

    assert is_on(hass, entity_id)

    await hass.services.async_call(
        DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: entity_id})

    await hass.async_block_till_done()

    assert not is_on(hass, entity_id)

    await hass.services.async_call(
        DOMAIN, SERVICE_TOGGLE, {ATTR_ENTITY_ID: entity_id})

    await hass.async_block_till_done()

    assert is_on(hass, entity_id)
