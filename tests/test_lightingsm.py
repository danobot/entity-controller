"""The tests for the MQTT lightingsm platform."""
import json
from unittest.mock import patch
import pytest
from datetime import timedelta, datetime
from homeassistant.core import callback
from homeassistant import setup
from homeassistant.const import STATE_UNAVAILABLE, ATTR_ASSUMED_STATE
import homeassistant.core as ha
from homeassistant.components.mqtt.discovery import async_start
from homeassistant.components import light
from tests.common import (
    get_test_home_assistant, assert_setup_component,
    async_fire_time_changed)
from freezegun import freeze_time

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
STATE_ACTIVE = 'active'


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

    def test_demo(self):
        with assert_setup_component(1, 'lightingsm'):
            assert setup.setup_component(self.hass, 'lightingsm', {
                'lightingsm': {
                    'test': {
                        'entity': CONTROL_ENTITY,
                        'sensor': SENSOR_ENTITY,
                        'delay': 2
                    }
                }
            })
        
    def test_basic_config(self):
        """Test the controlling state via topic."""
        with assert_setup_component(1, 'lightingsm'):
            assert setup.setup_component(self.hass, 'lightingsm', {
                'lightingsm': {
                    'test2': {
                        'entity': CONTROL_ENTITY,
                        'sensor': SENSOR_ENTITY,
                        'delay': 2
                    }
                }
            })
        # self.hass.start()
        # self.hass.block_till_done()

        self.hass.states.set(CONTROL_ENTITY, 'off')
        self.hass.block_till_done()
        assert self.hass.states.get('lightingsm.test').state == STATE_IDLE

        self.hass.states.set(SENSOR_ENTITY, 'on')
        self.hass.block_till_done()
        # how to trigger state change? send event?
        
        assert self.hass.states.get('SENSOR_ENTITY').state == 'on'
        assert self.hass.states.get('lightingsm.test').state == STATE_ACTIVE
        assert light.is_on(CONTROL_ENTITY)
        future = datetime.now() + timedelta(seconds=3)
        # async_fire_time_changed(self.hass, future)

        # self.hass.block_till_done()

        # assert not light.is_on(CONTROL_ENTITY)
        # assert self.hass.states.get('lightingsm.test').state == STATE_IDLE