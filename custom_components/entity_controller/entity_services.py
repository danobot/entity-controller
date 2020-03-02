""" Entity Service Definitions """

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.config_validation import (  # noqa: F401
    make_entity_service_schema,
)

from homeassistant.helpers.entity_component import EntityComponent

from homeassistant.const import (
    STATE_OFF,
    STATE_ON,
)

import homeassistant.util.dt as dt_util

from .const import (
    SERVICE_CLEAR_BLOCK,
    SERVICE_SET_STAY_ON,
    SERVICE_SET_STAY_OFF,
    SERVICE_SET_NIGHT_MODE,
    CONF_START_TIME,
    CONF_END_TIME,
)

TIME_STR_FORMAT = "%H:%M:%S"

def async_setup_entity_services(component: EntityComponent):
    """ Setup Entity services."""

    component.logger.debug("Setting up entity services")
    component.async_register_entity_service(SERVICE_CLEAR_BLOCK, {}, "async_clear_block")
    component.async_register_entity_service(SERVICE_SET_STAY_ON, {}, "async_set_stay_on")
    component.async_register_entity_service(SERVICE_SET_STAY_OFF, {}, "async_set_stay_off")
    component.async_register_entity_service(
        SERVICE_SET_NIGHT_MODE, 
        { vol.Optional(CONF_START_TIME): cv.string, vol.Optional(CONF_END_TIME): cv.string },
        "async_set_night_mode")

    return True

def async_entity_service_clear_block(self):
    """ Clear the block property, if set"""

    if(self.model is None or self.model.state != 'blocked'):
        return

    self.model.log.debug("Clearing Blocked state")
    self.model.block_timer_expires()

def async_entitiy_service_set_stay_on(self):
    """ Changes the stay attribute with a custom value """

    self.model.log.debug("Changing stay to on")
    self.model.stay = True

def async_entitiy_service_set_stay_off(self):
    """ Changes the stay attribute with a custom value """

    self.model.log.debug("Changing stay to off")
    self.model.stay = False

def async_entity_service_set_night_mode(self, start_time=None, end_time=None):
    """ Changes the night mode start and/or end times """

    if(self.model is None or self.model.night_mode is None):
        return

    now = None
    if(start_time == 'now'):
        if now is None:
            now = dt_util.utcnow()        
        start_time = dt_util.as_local(now).strftime(TIME_STR_FORMAT)
    elif(start_time == 'constraint'):
        start_time = self.model._start_time_private

    if(end_time == 'now'):
        if now is None:
            now = dt_util.utcnow()        
        end_time = dt_util.as_local(now).strftime(TIME_STR_FORMAT)
    elif(end_time == 'constraint'):
        end_time = self.model._end_time_private

    if(start_time is None and end_time is None):
        start_time = end_time = '00:00:00'

    if(not start_time is None):
        self.model.log.debug("Setting Night Mode Start to: %s", start_time)
        self.model.night_mode[CONF_START_TIME] = start_time

    if(not end_time is None):
        self.model.log.debug("Setting Night Mode End to: %s", end_time)
        self.model.night_mode[CONF_END_TIME] = end_time

    self.model.prepare_service_data()


