"""The tests for the MQTT switch platform."""
import json
from asynctest import patch
import pytest

from homeassistant.setup import async_setup_component
from homeassistant.const import STATE_UNAVAILABLE, ATTR_ASSUMED_STATE
import homeassistant.core as ha
from homeassistant.components import switch, mqtt
from homeassistant.components.mqtt.discovery import async_start

from tests.common import (
    mock_coro, async_mock_mqtt_component, async_fire_mqtt_message,
    MockConfigEntry)
from tests.components.switch import common


CONTROL_ENTITY = 'light.test_light';
CONTROL_ENTITY2 = 'light.test_light2';
CONTROL_ENTITIES = [CONTROL_ENTITY, CONTROL_ENTITY2]
SENSOR_ENTITY = 'binary_sensor.test_sensor';
SENSOR_ENTITY2 = 'binary_sensor.test_sensor2';
SENSOR_ENTITIES = [SENSOR_ENTITY, SENSOR_ENTITY2]
STATE_ENTITY = 'binary_sensor.test_state_entity'
STATE_ENTITY2 = 'binary_sensor.test_state_entity2'
STATE_ENTITIES = [STATE_ENTITY, STATE_ENTITY2]

# test_flux.py:75 example of mockiong time
STATE_IDLE = 'idle'
@pytest.fixture
def mock_publish(hass):
    """Initialize components."""
    yield hass.loop.run_until_complete(async_mock_mqtt_component(hass))


async def test_basic_config(hass):
    """Test the controlling state via topic."""
    assert await async_setup_component(hass, switch.DOMAIN, {

        # switch.DOMAIN: {
        #         'platform': 'mqtt',
        #         'name': 'test',
        #         'command_topic': 'command-topic',
        #         'payload_on': 'beer on',
        #         'payload_off': 'beer off',
        #         'qos': '2'
        #     }

        'switch': {
            'platform': 'lightingsm',
            'entities': {
                'test': {
                        'entity': CONTROL_ENTITY,
                        'sensor': SENSOR_ENTITY
                    }
            }
        }
        # switch.DOMAIN: {
        #     'platform': 'lightingsm',
        #     'entities': [
                
        #             'test': {
        #                 'entity': CONTROL_ENTITY,
        #                 'sensor': SENSOR_ENTITY
        #             }
                
        #     ]
        # }
        
    })

    # setup.setup_component(self.hass, 'switch', {
    #             'switch': {
    #                 'platform': 'template',
    #                 'switches': {
    #                     'test_template_switch': {
    #                         'value_template':
    #                             "{{ states.switch.test_state.state }}",
    #                         'turn_on': {
    #                             'service': 'switch.turn_on',
    #                             'entity_id': 'switch.test_state'
    #                         },
    #                         'turn_off': {
    #                             'service': 'switch.turn_off',
    #                             'entity_id': 'switch.test_state'
    #                         },
    #                     }
    #                 }
    #             }
    #         })

    state = hass.states.get('switch.test')
    assert STATE_IDLE == state.state
    assert not state.attributes.get(ATTR_ASSUMED_STATE)

