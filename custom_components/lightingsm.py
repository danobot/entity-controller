"""
Entity timer component for Home Assistant Component
Maintainer:       Daniel Mason
Version:          v2.3.14
Documentation:    https://github.com/danobot/appdaemon-motion-lights

"""
import logging
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import entity, service, event
from homeassistant.const import (
    SUN_EVENT_SUNSET, SUN_EVENT_SUNRISE)
from homeassistant.util import dt
from homeassistant.helpers.entity_component import EntityComponent
import logging
from transitions import Machine
from transitions.extensions import HierarchicalMachine as Machine
from threading import Timer
from datetime import datetime,  timedelta, date, time
import re
from homeassistant.core import callback
from homeassistant.helpers.sun import get_astral_event_date

DEBUG_CONSTRAINED = False
DEBUG_NOT_CONSTRAINED = False

DEPENDENCIES = ['light','sensor','binary_sensor','cover','fan','media_player']
REQUIREMENTS = ['transitions==0.6.9']

DOMAIN = 'lightingsm'
CONSTRAIN_START = 1
CONSTRAIN_END = 2

VERSION = '2.3.14'
SENSOR_TYPE_DURATION = 'duration'
SENSOR_TYPE_EVENT = 'event'
MODE_DAY = 'day'
MODE_NIGHT = 'night'

DEFAULT_DELAY = 180
DEFAULT_BRIGHTNESS = 100
DEFAULT_NAME = 'Entity Timer'

CONF_NAME = 'name'
CONF_CONTROL = 'entities'
CONF_SENSORS = 'sensors'
CONF_STATE = 'state_entities'
CONF_DELAY= 'delay'
CONF_NIGHT_MODE = 'night_mode'

STATES = ['idle', 'overridden','constrained','blocked', {'name': 'active', 'children': ['timer','stay_on'], 'initial': False}]

_LOGGER = logging.getLogger(__name__)
devices = []
async def async_setup(hass, config):
    """Load graph configurations."""


    component = EntityComponent(
        _LOGGER, DOMAIN, hass)

    # logging.basicConfig(level=logging.DEBUG)
    # logging.getLogger('transitions').setLevel(logging.DEBUG)
    myconfig = config[DOMAIN]

    _LOGGER.info("Component Configuration: "  + str(myconfig))
    
    machine = Machine(states=STATES, 
        initial='idle',
        # title=self.name+" State Diagram",
        # show_conditions=True
        # show_auto_transitions = True,
        finalize_event='finalize'
    )

    
    machine.add_transition(trigger='constrain',             source='*',    dest='constrained')
    machine.add_transition(trigger='override',              source=['idle','active_timer','blocked'],                 dest='overridden')

    # Idle
    # machine.add_transition(trigger='sensor_off',           source='idle',              dest=None)
    machine.add_transition(trigger='sensor_on',            source='idle',              dest='active',          conditions=['is_state_entities_off'])
    machine.add_transition(trigger='sensor_on',            source='idle',              dest='blocked',          conditions=['is_state_entities_on'])
    
    # Blocked
    machine.add_transition(trigger='enable',               source='blocked',              dest='idle')
    machine.add_transition(trigger='sensor_on',               source='blocked',              dest='blocked') # re-entering self-transition (on_enter callback executed.)

    # Overridden      
    machine.add_transition(trigger='enable',               source='overridden',          dest='idle')

    # machine.add_transition(trigger='sensor_off',           source=['overridden'],          dest=None)

    machine.add_transition(trigger='enter',                source='active',            dest='active_timer',    unless='will_stay_on')
    machine.add_transition(trigger='enter',                source='active',            dest='active_stay_on',  conditions='will_stay_on')

    # Active Timer
    machine.add_transition(trigger='sensor_on',            source='active_timer',      dest=None,              after='_reset_timer')
    # machine.add_transition(trigger='sensor_off',           source='active_timer',      dest=None,              conditions=['is_event_sensor'])
    machine.add_transition(trigger='sensor_off_duration',  source='active_timer',      dest='idle',            conditions=['is_timer_expired'])
    machine.add_transition(trigger='timer_expires',        source='active_timer',      dest='idle',            conditions=['is_event_sensor'])
    machine.add_transition(trigger='timer_expires',        source='active_timer',      dest='idle',            conditions=['is_duration_sensor', 'is_sensor_off'])
    machine.add_transition(trigger='control',              source='active_timer',      dest='idle',            conditions=['is_state_entities_off'])

    # machine.add_transition(trigger='sensor_off',           source='active_stay_on',    dest=None)
    machine.add_transition(trigger='timer_expires',        source='active_stay_on',    dest=None)

    # Constrained
    machine.add_transition(trigger='enable',                source='constrained',    dest='idle')


    for key, config in myconfig.items():
        _LOGGER.info("Config Item {}: {}".format(str(key), str(config)))
        config["name"] = key
        m = None
        m = LightingSM(hass, config, machine)
        # machine.add_model(m.model)
        # m.model.after_model(config)
        devices.append(m)

    await component.async_add_entities(devices)

    _LOGGER.info("The {} component is ready!".format(DOMAIN))

    return True


class LightingSM(entity.Entity):


    def __init__(self, hass, config, machine):
        self.attributes = {}
        self.may_update = False
        self.model = None
        self.friendly_name = config.get('name', 'Motion Light')
        if 'friendly_name' in config:
            self.friendly_name = config.get('friendly_name')

        self.model = Model(hass, config, machine, self)
        event.async_call_later(hass, 1, self.do_update)

    @property
    def state(self):
        """Return the state of the entity."""
        return self.model.state 

    @property
    def name(self):
        """Return the state of the entity."""
        return self.friendly_name
    @property
    def icon(self):
        """Return the entity icon."""
        if self.model.state == 'idle':
            return 'mdi:circle-outline'
        if self.model.state == 'active':
            return 'mdi:check-circle'
        if self.model.state == 'active_timer':
            return 'mdi:timer'
        if self.model.state == 'constrained':
            return 'mdi:cancel'
        if self.model.state == 'overridden':
            return 'mdi:timer-off'
        if self.model.state == 'blocked':
            return 'mdi:close-circle'
        return 'mdi:eye'

    @property
    def state_attributes(self):
        """Return the state of the entity."""
        return self.attributes.copy()

    def reset_state(self):
        """ Reset state attributes by removing any state specific attributes when returning to idle state """
        self.model.log.debug("Resetting state")
        att = {}

        PERSISTED_STATE_ATTRIBUTES = [
            'last_triggered_by',
            'last_triggered_at',
            'state_entities',
            'control_entities',
            'sensor_entities',
            'override_entities',
            'delay',
            'sensor_type',
            'mode'
        ]
        for k,v in self.attributes.items():
            if k in PERSISTED_STATE_ATTRIBUTES:
                att[k] = v

        self.attributes = att
        self.do_update()

    def do_update(self, wait=False,**kwargs):
        """ Schedules an entity state update with HASS """
        # _LOGGER.debug("Scheduled update with HASS")
        if self.may_update:
            self.async_schedule_update_ha_state(True)

    def set_attr(self, k, v):
        # _LOGGER.debug("Setting state attribute {} to {}".format(k, v))
        if k == 'delay':
            v = str(v) + 's'
        self.attributes[k] = v
        # self.do_update()
        # _LOGGER.debug("State attributes: " + str(self.attributes))
    # HA Callbacks
    async def async_added_to_hass(self):
        """Register update dispatcher."""
        self.may_update = True
class Model():
    """ Represents the transitions state machine model """

       
    def __init__(self, hass, config, machine, entity):
        self.hass = hass # backwards reference to hass object
        self.entity = entity # backwards reference to entity containing this model

        
        self.stateEntities = []
        self.controlEntities = []
        self.sensorEntities = []
        self.offEntities = []
        self.timer_handle = None
        self.sensor_type = None
        self.night_mode = None
        self.backoff = False
        self.backoff_count = 0
        self.light_params_day = {}
        self.light_params_night = {}
        self.lightParams = {}
        self.name = None
        self.stay = False
        self.start = None
        self.end = None
        self.reset_count = None
        self.log = logging.getLogger(__name__ + '.' + config.get('name'))
        self.log.setLevel(logging.DEBUG)
        self.log.debug("Initialising LightingSM entity with this configuration: " + str(config))
        self.name = config.get('name', 'Unnamed Motion Light')
        self.log.debug("Entity name: " + str(self.name))

        machine.add_model(self) # add here because machine generated methods are being used in methods below.
        self.config_static_strings(config)
        self.config_control_entities(config) 
        self.config_state_entities(config) # must come after config_control_entities (uses control entities if not set)
        self.config_sensor_entities(config)
        self.config_override_entities(config)
        self.config_off_entities(config)
        self.config_normal_mode(config) 
        self.config_night_mode(config) #must come after normal_mode (uses normal mode parameters if not set)
        self.config_constrain_times(config)
        self.config_other(config)
        self.prepare_service_data()
        # def draw(self):
        #     self.update()
        #     if self.do_draw:
        #         self.log.debug("Updating graph in state: " + self.state)
        #         self.get_graph().draw(self.image_path + self.image_prefix + str(self.name)+'.png', prog='dot', format='png')

    def update(self, wait=False, **kwargs):
        """ Called from different methods to report a state attribute change """
        # self.log.debug("Update called with {}".format(str(kwargs)))
        for k,v in kwargs.items():
            if v is not None:
                self.entity.set_attr(k,v)
        
        if wait == False:
            self.entity.do_update()

    def finalize(self):
        self.entity.do_update()


   
    # =====================================================
    # S T A T E   C H A N G E   C A L L B A C K S
    # =====================================================

    def sensor_state_change(self, entity, old, new):
        """ State change callback for sensor entities """
        self.log.debug("Sensor state change: " + new.state)
        self.log.debug("state: " + self.state)

        if self.matches(new.state, self.SENSOR_ON_STATE) and (self.is_idle() or self.is_active_timer() or self.is_blocked()):
            self.update(last_triggered_by=entity)
            self.sensor_on()

        if self.matches(new.state, self.SENSOR_OFF_STATE) and self.is_duration_sensor() and self.is_active_timer():
            self.update(last_triggered_by=entity, sensor_turned_off_at=datetime.now())
            # We only care about sensor off state changes when the sensor is a duration sensor and we are in active_timer state.
            self.sensor_off_duration()
                


    def override_state_change(self, entity, old, new):
        """ State change callback for override entities """
        self.log.debug("Override state change")
        if self.matches(new.state, self.OVERRIDE_ON_STATE) and (self.is_active() or self.is_active_timer() or self.is_idle() or self.is_blocked()):
            self.update(overridden_by=entity)
            self.override()
            self.update(overridden_at=str(datetime.now()))
        if self.matches(new.state, self.OVERRIDE_OFF_STATE) and self.is_override_state_off() and self.is_overridden():
            self.enable()


    def state_entity_state_change(self, entity, old, new):
        """ State change callback for state entities """
        if self.is_active_timer():
            self.control()

        if self.is_blocked() and self.is_state_entities_off():
            self.enable()


    # def event_handler(self,event, data):
    #     self.log.debug("Event: " + str(event))
    #     self.log.debug("Data: " + str(data))
    #     self.log.debug("kwargs: " + str(el))
    #     if event == 'start_end_reached':
    #         self.enable()
        
    #     if event == 'start_time_reached':
    #         self.constrain()
        
    #     if data['entity_id'] == self.name:
    #         self.log.debug("It is me!")
    #         if event == 'lightingsm-reset':
    #             self.set_state('idle')
    #             self.log.debug("Reset was called")


    def _start_timer(self):
        self.log.info(self.lightParams)
        if self.backoff_count == 0:
            self.previous_delay = self.lightParams.get('delay', DEFAULT_DELAY)
        else:
            self.log.debug("Backoff: {},  count: {}, delay{}, factor: {}".format(self.backoff,self.backoff_count, self.lightParams.get('delay',DEFAULT_DELAY), self.backoff_factor))
            self.previous_delay = round(self.previous_delay*self.backoff_factor, 2)
            if self.previous_delay > self.backoff_max:
                self.log.debug("Max backoff reached. Will not increase further.")
                self.previous_delay = self.backoff_max
            self.update(delay=self.previous_delay)

        expiry_time = datetime.now() + timedelta(seconds=self.previous_delay)

        # not able to use async_call_later because no known way to check whether timer is active.
        #self.timer_handle = event.async_call_later(self.hass, self.previous_delay, self.timer_expire)
        #self.log.debug("Timer handle" + str(dir(self.timer_handle)))
        self.timer_handle = Timer(self.previous_delay, self.timer_expire)
        # self.log.debug("Delay: " + str(self.previous_delay))
        self.timer_handle.start()
        self.update(expires_at=expiry_time)
    
    def _cancel_timer(self):
        if self.timer_handle.is_alive():
            self.timer_handle.cancel()

    def _reset_timer(self):
        self.log.debug("Resetting timer" + str(self.backoff))
        self._cancel_timer()
        self.update(reset_at=datetime.now())
        if self.backoff:
            self.log.debug("inc backoff")
            self.backoff_count += 1
            self.update(backoff_count=self.backoff_count)
        self._start_timer()

        return True

    def timer_expire(self):
        # self.log.debug("Timer expired")
        if self.is_duration_sensor() and self.is_sensor_on(): # Ignore timer expiry because duration sensor overwrites timer
            self.update(expires_at="pending sensor")
        else:    
            self.timer_expires()

    # =====================================================
    # S T A T E   M A C H I N E   C O N D I T I O N S
    # =====================================================
    def _override_entity_state(self):
        for e in self.overrideEntities:
            s = self.hass.states.get(e)
            if self.matches(s.state, self.OVERRIDE_ON_STATE):
                self.log.debug("Override entities are ON. [{}]".format(e))
                return e
        self.log.debug("Override entities are OFF.")
        return None

    def is_override_state_off(self):
        return self._override_entity_state() is None
        
    def is_override_state_on(self):
        return self._override_entity_state() is not None

    def _sensor_entity_state(self):
        for e in self.sensorEntities:
            s = self.hass.states.get(e)
            if self.matches(s.state, self.SENSOR_ON_STATE):
                self.log.debug("Sensor entities are ON. [{}]".format(e))
                return e
        self.log.debug("Sensor entities are OFF.")
        return None

    def is_sensor_off(self):
        return self._sensor_entity_state() is None

    def is_sensor_on(self):
        return self._sensor_entity_state() is not None
        

    def _state_entity_state(self):
        for e in self.stateEntities:
            s = self.hass.states.get(e)
            self.log.info(s)
            if self.matches(s.state, self.STATE_ON_STATE):
                self.log.debug("State entities are ON. [{}]".format(e))
                return e
        self.log.debug("State entities are OFF.")
        return None
    
    def is_state_entities_off(self):
        return self._state_entity_state() is None

    def is_state_entities_on(self):
        return self._state_entity_state() is not None
    
    
    def will_stay_on(self):
        return self.stay

    def is_night(self):
        if self.night_mode is None:
            return False # if night mode is undefined, it's never night :)
        else:
            self.log.debug("NIGHT MODE ENABLED: " + str(self.night_mode))
            start=  dt.parse_time(self.night_mode['start_time'])
            end=  dt.parse_time(self.night_mode['end_time'])
            return self.now_is_between(start, end)



    def is_event_sensor(self):
        return self.sensor_type == SENSOR_TYPE_EVENT

    def is_duration_sensor(self):
        return self.sensor_type == SENSOR_TYPE_DURATION

    def is_timer_expired(self):
        expired = self.timer_handle.is_alive() == False
        self.log.debug("is_timer_expired -> " + str(expired))
        return expired
    



    # =====================================================
    # S T A T E   M A C H I N E   C A L L B A C K S
    # =====================================================
    def on_enter_idle(self):
        self.log.debug("Entering idle")
        self.entity.reset_state()

    def on_exit_idle(self):
        self.log.debug("Exiting idle")

    def on_enter_overridden(self):
        self.log.debug("Now overridden")


    def on_enter_active(self):
        self.update(last_triggered_at=str(datetime.now()))
        self.backoff_count = 0
        self.prepare_service_data()

        
        self._start_timer()

        self.log.debug("light params before turning on: " + str(self.lightParams))
        for e in self.controlEntities:
        
            # self.log.debug("brightness value" + str(self.lightParams.get('brightness')))
            if self.lightParams.get('service_data') is not None:
                self.log.debug("Turning on {} with service parameters {}".format(e, self.lightParams.get('service_data')))
                self.call_service(e, 'turn_on', **self.lightParams.get('service_data'))
            else:
                self.log.debug("Turning on {} (no parameters passed to service call)".format(e))
                self.call_service(e, 'turn_on')
        self.enter()



    def on_exit_active(self):
        self.log.debug("Turning off entities, cancelling timer")
        self._cancel_timer() # cancel previous timer
        self.update(delay=self.lightParams.get('delay')) # no need to update immediately
        if len(self.offEntities) > 0:
            self.log.info("Turning on special off_entities that were defined, instead of turning off the regular control_entities")
            for e in self.offEntities: 
                self.log.debug("Turning on {}".format(e))
                self.call_service(e, 'turn_on')
        else:
            for e in self.controlEntities:
                self.log.debug("Turning off {}".format(e))
                self.call_service(e, 'turn_off')


    def on_enter_blocked(self):
        self.update(blocked_at=datetime.now())
        self.update(blocked_by=self._state_entity_state())
    
    # =====================================================
    #    C O N F I G U R A T I O N  &  V A L I D A T I O N
    # =====================================================



    def config_control_entities(self, config):
    
        self.controlEntities = []

        if "entity" in config:
            self.controlEntities.append( config["entity"])

        if "entities" in config: 
            self.controlEntities.extend( config['entities'])

        if "entity_on" in config: 
            self.controlEntities.append( config["entity_on"] )


        self.log.debug("Control Entities: " + str(self.controlEntities))


        


    def config_state_entities(self, config):
        self.stateEntities = []
        if config.get('state_entities', False):
            self.stateEntities.extend(config.get('state_entities', []))
            self.log.info("State Entities (explicitly defined): " + str(self.stateEntities))
            event.async_track_state_change(self.hass, self.stateEntities, self.state_entity_state_change)

        # If no state entities are defined, use control entites as state
        if len(self.stateEntities) == 0:
            self.stateEntities = self.controlEntities.copy()
            self.log.debug("Added Control Entities as state entities: " + str(self.stateEntities))
            event.async_track_state_change(self.hass, self.stateEntities, self.state_entity_state_change)



    def config_off_entities(self, config):
    
        self.offEntities = []
        temp = config.get("entity_off", None)
        if temp is not None:
            self.log.debug("Setting up off_entities")
            if type(temp) == str:
                self.offEntities.append(temp)
            else:
                self.offEntities.extend(temp)
            #self.update(off_entities=self.offEntities, delay=True)
            self.log.info('Off Entities: ' + str(self.offEntities))


    def config_sensor_entities(self, config):
        self.sensorEntities = []
        temp = config.get("sensor", None)
        if temp is not None:
            self.sensorEntities.append(temp)
            
        temp = config.get("sensors", None)
        if temp is not None:
            self.sensorEntities.extend(temp)

        if len(self.sensorEntities) == 0:
            self.log.error("No sensor entities defined. You must define at least one sensor entity.")

        self.log.debug("Sensor Entities: " + str(self.sensorEntities))

        event.async_track_state_change(self.hass, self.sensorEntities, self.sensor_state_change)

    def config_static_strings(self, config):
        DEFAULT_ON = ["on","playing","home"]
        DEFAULT_OFF = ["off","idle","paused","away"]
        self.CONTROL_ON_STATE = config.get("control_states_on", DEFAULT_ON)
        self.CONTROL_OFF_STATE = config.get("control_states_off", DEFAULT_OFF)
        self.SENSOR_ON_STATE = config.get("sensor_states_on", DEFAULT_ON)
        self.SENSOR_OFF_STATE = config.get("sensor_states_off", DEFAULT_OFF)
        self.OVERRIDE_ON_STATE = config.get("override_states_on", DEFAULT_ON)
        self.OVERRIDE_OFF_STATE = config.get("override_states_off", DEFAULT_OFF)
        self.STATE_ON_STATE = config.get("state_states_on", DEFAULT_ON)
        self.STATE_OFF_STATE = config.get("state_states_off", DEFAULT_OFF)

        on = config.get('state_strings_on', False)
        if on:
            self.CONTROL_ON_STATE.extend(on)
            self.CONTROL_ON_STATE.extend(on)
            self.SENSOR_ON_STATE.extend(on)
            self.OVERRIDE_ON_STATE.extend(on)
            self.STATE_ON_STATE.extend(on)

        off = config.get('state_strings_off', False)
        if off:
            self.CONTROL_OFF_STATE.extend(off)
            self.SENSOR_OFF_STATE.extend(off)
            self.OVERRIDE_OFF_STATE.extend(off)
            self.STATE_OFF_STATE.extend(off)

    



    def config_night_mode(self, config):
        """
            Configured night mode parameters. If no night_mode service parameters are given, the day mode parameters are used instead. If those do not exist, the 
        """
        if "night_mode" in config:
            self.night_mode = config["night_mode"]
            night_mode = config["night_mode"]
            self.light_params_night['delay'] = night_mode.get('delay',config.get("delay", DEFAULT_DELAY))
            self.light_params_night['service_data'] = night_mode.get('service_data',self.light_params_day.get('service_data'))

            if not "start_time" in night_mode:
                self.log.error("Night mode requires a start_time parameter !")

            if not "end_time" in night_mode:
                self.log.error("Night mode requires a end_time parameter !")

            
            
    def config_normal_mode(self, config):
        params = {}
        params['delay'] = config.get("delay", DEFAULT_DELAY)
        params['service_data'] = config.get("service_data", None)
        self.log.info("serivce data set up: " + str(config))
        self.light_params_day = params

    def config_constrain_times(self, config):
        self._start_time = config.get('start_time')
        self._end_time = config.get('end_time')
        # Find XOR function
        # if self._start_time and self._end_time:
        #     self.log.error("Must specify both start and end time.")
        if self._start_time and self._end_time:

            self.constrain_start_hook, constrain_start_abs = self.setup_time_callback_please(self._start_time, CONSTRAIN_START)
            self.constrain_end_hook, constrain_end_abs = self.setup_time_callback_please(self._end_time, CONSTRAIN_END)
            
            self.log.debug("Constrains - Entity active from: " + str(constrain_start_abs))
            self.log.debug("Constrains - Entity active until: " + str(constrain_end_abs))
            # if end and start:
                # self.end = datetime.time(datetime.utcnow()+timedelta(seconds=5))
                # e = dt.now()+timedelta(seconds=5)#datetime.datetime(end)
                # self.log.debug("Setting time callbacks")

            # We now have to constrain the entity if we are currently within the
            # constrain period. To do this, we must convert sun-relative time 
            # to absolute time
            if not self.now_is_between(constrain_start_abs.time(), constrain_end_abs.time()):
                self.log.debug("Constrain period active. Scheduling transition to 'constrained'")
                event.async_call_later(self.hass, 1, self.constrain_fake)
            

    def setup_time_callback_please(self,time, callback_const):
        """
            Handles parsing of time input string and setting up an appropriate call back time. 

            Should be called on start up and in each call back method to set the next callback.
        """
        sun, time_or_offset = self.parse_time_sun(time)

        @callback
        def constrain_start(evt):
            """
                Called when `end_time` is reached, will change state to `constrained` and schedule `start_time` callback.
            """
            self.log.debug("Constrain Start reached. Disabling ML: ")
            self.constrain()
            #   time = datetime.combine(datetime.today(), self.end) + timedelta(hours=24)
            self.constrain_start_hook, constrain_start_abs = self.setup_time_callback_please(self._start_time, CONSTRAIN_START)
            self.update(constrain_start=constrain_start_abs)
            self.log.debug("setting new START callback in ~24h" + str(constrain_start_abs))

        @callback
        def constrain_end(evt):
            """
                Called when `start_time` is reached, will change state to `idle` and schedule `end_time` callback.
            """
            self.log.debug("Constrain End reached. Enabling ML: ")
            self.enable()
            #        time = datetime.combine(datetime.today(), self.end) + timedelta(hours=24)
            self.constrain_start_hook, constrain_end_abs = self.setup_time_callback_please(self._end_time, CONSTRAIN_END)
            self.log.debug("setting new END callback in ~24h" + str(constrain_end_abs))
            self.update(constrain_end=constrain_end_abs)

        if callback_const == CONSTRAIN_START:
            callbacks = constrain_end
        else:
            callbacks = constrain_start    

        
        # Sets up event callbacks in such a way to enable quick time 
        # related testing.
        

        if DEBUG_CONSTRAINED: # starts in constrained mode going to idle

            if callback_const == CONSTRAIN_END:
                time_or_offset = self.five_seconds_from_now(sun)
            else:
                time_or_offset = self.five_minutes_ago(sun)
        if DEBUG_NOT_CONSTRAINED: # Starts in Idle mode going to constrained
            # Sets up event callbacks in such a way to enable quick time 
            if callback_const == CONSTRAIN_START:
                time_or_offset = self.five_seconds_from_now(sun)
            else:
                time_or_offset = self.five_minutes_ago(sun)
    
        

        self.log.debug("Next sunrise: " + str(dt.as_local(get_astral_event_date(self.hass, SUN_EVENT_SUNRISE, datetime.now()))))
        self.log.debug("Next sunset: " + str(dt.as_local(get_astral_event_date(self.hass, SUN_EVENT_SUNSET, datetime.now()))))
        if sun is not None:
            self.log.debug("Sun: {}, time_or_offset: {}".format(sun, time_or_offset))
            self.log.debug("Start time contains sun reference")
   
            if time_or_offset is None:
                delta = timedelta(0)
            else:
                delta = time_or_offset
            
            if sun == 'sunrise':
                return event.async_track_sunrise(self.hass, callbacks, delta), self.delta_from(delta, sun)
            else: 
                return event.async_track_sunset(self.hass, callbacks, delta), self.delta_from(delta, sun)
        else:
            self.start = time_or_offset 
            s = self.if_time_passed_get_tomorrow(time_or_offset)
            self.log.debug("Constrain callback for : " + str(s))

            return event.async_track_point_in_time(self.hass, callbacks, s), s


    def config_override_entities(self, config):
        self.overrideEntities = []
        if 'override' in config:
            self.overrideEntities.append(config.get('override'))

        if 'overrides' in config:
            self.overrideEntities.extend(config.get('overrides'))

        if len(self.overrideEntities) > 0:
            self.log.debug("Override Entities: " + str(self.overrideEntities))
            event.async_track_state_change(self.hass, self.overrideEntities, self.override_state_change)

    def config_other(self, config):
        self.log.debug("Config other")

        self.do_draw = config.get("draw", False)
        
        if "entity_off" in config:
            self.entityOff = config.get("entity_off", None)
       
        self.image_prefix = config.get('image_prefix','/fsm_diagram_')
        self.image_path = config.get('image_path','/conf/temp')
        self.backoff = config.get('backoff', False)
        self.stay = config.get('stay', False)

        if self.backoff:
            self.log.debug("setting up backoff. Using delay as initial backoff value.")
            self.backoff_factor = config.get('backoff_factor', 1.1)
            self.backoff_max = config.get('backoff_max', 300)

        self.stay = config.get("stay", False)
   

        
        if config.get("sensor_type_duration"):
            self.sensor_type = SENSOR_TYPE_DURATION
        else:
            self.sensor_type = SENSOR_TYPE_EVENT

        self.update(sensor_type=self.sensor_type)
# =====================================================
#    E V E N T   C A L L B A C K S
# =====================================================

    def constrain_fake(self, evt):
        """ 
            Event callback used on component setup if current time requires entity to start in constrained state.
        """
        self.constrain()
        
    
# =====================================================
#    H E L P E R   F U N C T I O N S
# =====================================================
# use homeassistant.util.dt.find_next_time_expression_time where appropriate


    def parse_time_sun(self, time):
        try:
            if 'soon-after' in time:
                t =  datetime.now() + timedelta(seconds=10)

                self.log.debug("DEBUG: Making time happen in 10 seconds!")
                return None, t.time()
            elif 'soon' in time:
                t = datetime.now() + timedelta(seconds=5)

                self.log.debug("DEBUG: Making time happen in 5 seconds!")
                return None, t.time()
            if 'sun' in time:
                self.log.debug("Time contains sunset/sunrise relative time.")

                regex = r"(sunset|sunrise) ?(\+|\-)? ?'?(\d\d\:\d\d\:\d\d)?'?"

                matches = re.finditer(regex, time, re.MULTILINE)

                for matchNum, match in enumerate(matches, start=1):
                    
                    self.log.debug("Match {matchNum} was found at {start}-{end}: {match}".format(matchNum = matchNum, start = match.start(), end = match.end(), match = match.group()))
                    
                    for groupNum in range(0, len(match.groups())):
                        groupNum = groupNum + 1
                        
                        self.log.debug("Group {groupNum} found at {start}-{end}: {group}".format(groupNum = groupNum, start = match.start(groupNum), end = match.end(groupNum), group = match.group(groupNum)))
                    break
                
                if match.group(2) is not None and match.group(3) is not None:
                    self.log.debug(match.group(2)+match.group(3))
                    t = datetime.strptime(match.group(3),"%H:%M:%S")
                    d = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
                    if match.group(2) == '-':

                        t = timedelta(0) - d
                    else:
                        t = d
                    self.log.debug("Using custom sun offset: " + str(t))
                else:
                    t = timedelta(0)
                    self.log.debug("No sun offset given.")
                return match.group(1), t 
            else:
                return None, dt.parse_time(time)
        except TypeError as e:
            self.log.error("PARSE ERROR: Please put quotes around time fields starting with a number.")
            return None, None
            
    def if_time_passed_get_tomorrow(self, time):
        """ Returns tomorrows time if time is in the past """
        today = date.today()
        t = datetime.combine(today, time)
        x = datetime.combine(today, datetime.time(datetime.now()))
        # self.log.debug("if_time_passed --- input time: " + str(t))
        # self.log.debug("if_time_passed --- current time: " + str(x))
        if t <= x:
            t += timedelta(1) # tomorrow!
            # self.log.debug("if_time_passed --- Time already happened. Returning tomorrow instead. " + str(t))
        # else:
            # self.log.debug("if_time_passed --- Time still happening today. " + str(t))

        return t

    def now_is_between(self, start, end, x=None):
        if x is None:
            x = datetime.time(datetime.now())

        today = date.today()
        start = datetime.combine(today, start)
        end = datetime.combine(today, end)
        x = datetime.combine(today, x)
        if end <= start:
            end += timedelta(1) # tomorrow!
        if x <= start:
            x += timedelta(1) # tomorrow!
        return start <= x <= end

    def prepare_service_data(self):
        """ Called when entering active state and on initial set up to set correct service parameters."""
        if self.is_night():
            self.log.debug("Using NIGHT MODE parameters: " + str(self.light_params_night))
            self.lightParams = self.light_params_night
            self.update(mode=MODE_NIGHT)
        else:
            self.log.debug("Using DAY MODE parameters: " + str(self.light_params_day))
            self.lightParams = self.light_params_day
            if self.night_mode is not None:
                self.update(mode=MODE_DAY) # only show when night mode set up
        self.update(delay=self.lightParams.get('delay'))

    def call_service(self, entity, service, **kwargs):
        """ Helper for calling HA services with the correct parameters """
        domain, e = entity.split('.')
        params = {}
        if kwargs is not None:
            params = kwargs

        params['entity_id'] = entity

        self.hass.services.call(domain, service, kwargs)
        self.update(service_data=kwargs)
    
    def matches(self, value, list):
        """
            Checks whether a string is contained in a list (used for matching state strings)
        """
        try:
            index = list.index(value)
            return True
        except ValueError:
            return False

    
       
  
    def five_seconds_from_now(self, sun):
        """ Returns a timedelta that will result in a sunrise trigger in 5 seconds time"""

        
        return dt.now()+timedelta(seconds=5)-get_astral_event_date(self.hass, sun, datetime.now())
    def five_minutes_ago(self, sun):
        """ Returns a timedelta that will result in a sunrise trigger in 5 seconds time"""
        return dt.now() -timedelta(minutes=5)-get_astral_event_date(self.hass, sun, datetime.now())

    def delta_from(self, delta, sun):
        """ Returns absolute time sun + delta """
        sun_time = get_astral_event_date(self.hass, sun, dt.now())
        t = dt.as_local(sun_time + delta ).time()
        return self.if_time_passed_get_tomorrow(t)
