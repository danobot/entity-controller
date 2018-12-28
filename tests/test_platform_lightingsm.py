"""The tests for the MQTT switch platform."""
import json
from asynctest import patch
import pytest

from homeassistant.core import callback
from homeassistant import setup
from homeassistant.const import STATE_UNAVAILABLE, ATTR_ASSUMED_STATE
import homeassistant.core as ha
from homeassistant.components import switch, mqtt
from homeassistant.components.mqtt.discovery import async_start

from tests.common import (
    get_test_home_assistant, assert_setup_component)
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
STATE_ACTIVE = 'active_timer'


class TestLightingSM:
    hass = None
    calls = None
    # pylint: disable=invalid-name

    def setup_method(self, method):
        """Set up things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.calls = []

        @callback
        def record_call(service):
            """Track function calls.."""
            self.calls.append(service)

        self.hass.services.register('test', 'automation', record_call)

    def teardown_method(self, method):
        """Stop everything that was started."""
        self.hass.stop()
    def test_basic_config(self):
        """Test the controlling state via topic."""
        with assert_setup_component(1, 'switch'):
            assert setup.setup_component(self.hass, switch.DOMAIN, {
                'switch': {
                    'platform': 'lightingsm',
                    'entities': {
                        'test': {
                            'entity': CONTROL_ENTITY,
                            'sensor': SENSOR_ENTITY,
                            'delay': 2
                        }
                    }
                }
            })
        self.hass.start()
        self.hass.block_till_done()

        state = self.hass.states.set(CONTROL_ENTITY, 'off')
        self.hass.block_till_done()
        assert self.hass.states.get('switch.test').state == STATE_IDLE

        self.hass.states.set(SENSOR_ENTITY, 'on')
        self.hass.block_till_done()
        assert self.hass.states.get('switch.test').state == STATE_ACTIVE
