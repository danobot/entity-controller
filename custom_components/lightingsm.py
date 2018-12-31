"""
State Machine-based Motion Lighting Implementation (Home Assistant Component)
Maintainer:       Daniel Mason
Version:          v2.2.3 - Component Rewrite
Documentation:    https://github.com/danobot/appdaemon-motion-lights

"""
import logging
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import entity, service, event
from homeassistant.util import dt
from homeassistant.helpers.entity_component import EntityComponent
import logging
from transitions import Machine
from transitions.extensions import HierarchicalMachine as Machine
from threading import Timer
from datetime import datetime,  timedelta, date, time

DEPENDENCIES = ['light','sensor','binary_sensor','cover','fan','media_player']
REQUIREMENTS = ['transitions==0.6.9']

DOMAIN = 'lightingsm'


VERSION = '2.2.3'
SENSOR_TYPE_DURATION = 1
SENSOR_TYPE_EVENT = 2
DEFAULT_DELAY = 180
DEFAULT_BRIGHTNESS = 100
DEFAULT_NAME = 'Motion Light'
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
    _LOGGER.info("The {} component is ready! {}".format(DOMAIN, config))
    _LOGGER.info("The {} component is ready! {}".format(DOMAIN, myconfig))

    _LOGGER.info("Config: "  + str(myconfig))
    
    machine = Machine(states=STATES, 
        initial='idle',
        # title=self.name+" State Diagram",
        # show_conditions=True
        # show_auto_transitions = True,
        finalize_event='finalize'
    )

    
    # for key, config in myconfig.items():
    #     _LOGGER.info("Config Item {}: {}".format(str(key), str(config)))
    #     config["name"] = key
    #     m = LightingSM(hass, config, machine)
    #     # machine.add_model(m.model)
    #     # m.model.after_model(config)
    #     devices.append(m)
    #     # hass.

    machine.add_transition(trigger='constrain',        source='*',    dest='constrained')
    machine.add_transition(trigger='override',              source='*',                 dest='overridden')

    # Idle
    machine.add_transition(trigger='sensor_off',           source='idle',              dest=None)
    machine.add_transition(trigger='sensor_on',            source='idle',              dest='active',          conditions=['is_state_entities_off'])
    machine.add_transition(trigger='sensor_on',            source='idle',              dest='blocked',          conditions=['is_state_entities_on'])
    
    # Blocked
    machine.add_transition(trigger='enable',               source='blocked',              dest='idle')

    # Overridden      
    machine.add_transition(trigger='enable',               source='overridden',          dest='idle')
    machine.add_transition(trigger='sensor_on',            source=['overridden'],          dest=None)
    

    machine.add_transition(trigger='sensor_off',           source=['overridden'],          dest=None)

    machine.add_transition(trigger='enter',                source='active',            dest='active_timer',    unless='will_stay_on')
    machine.add_transition(trigger='enter',                source='active',            dest='active_stay_on',  conditions='will_stay_on')

    # Active Timer
    machine.add_transition(trigger='sensor_on',            source='active_timer',      dest=None,              after='_reset_timer')
    machine.add_transition(trigger='sensor_off',           source='active_timer',      dest=None,              conditions=['is_event_sensor'])
    machine.add_transition(trigger='sensor_off_duration',  source='active_timer',      dest='idle',            conditions=['is_timer_expired'])
    machine.add_transition(trigger='timer_expires',        source='active_timer',      dest='idle',            conditions=['is_event_sensor'])
    machine.add_transition(trigger='timer_expires',        source='active_timer',      dest='idle',            conditions=['is_duration_sensor', 'is_sensor_off'])
    # machine.add_transition(trigger='control',              source='active_timer',      dest='idle')

    machine.add_transition(trigger='sensor_off',           source='active_stay_on',    dest=None)
    machine.add_transition(trigger='timer_expires',        source='active_stay_on',    dest=None)

    # Constrained
    machine.add_transition(trigger='enable',                source='constrained',    dest='idle')
    machine.add_transition(trigger='sensor_on',             source='constrained',    dest=None)
    machine.add_transition(trigger='sensor_off',            source='constrained',    dest=None)
    machine.add_transition(trigger='control',               source='constrained',    dest=None)


    for key, config in myconfig.items():
        _LOGGER.info("Config Item {}: {}".format(str(key), str(config)))
        config["name"] = key
        m = None
        m = LightingSM(hass, config, machine)
        # machine.add_model(m.model)
        # m.model.after_model(config)
        devices.append(m)

    await component.async_add_entities(devices)
    return True


class LightingSM(entity.Entity):


    def __init__(self, hass, config, machine):
        self.attributes = {}
        self.model = None
        self.friendly_name = config.get('name', 'Motion Light')
        # StateMachine.__init__(self, config)
        self.machine = machine # backwards reference to machine
        self.model = Model(hass, config, self)
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
            return 'mdi:timer-sand'
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
        return self.attributes

    def reset_state(self):
        """ Reset state attributes by removing any state specific attributes when returning to idle state """
        att = {}

        PERSIST_STATE_ATTRIBUTES = [
            'last_overridden_by',
            'last_overridden_at',
            'last_triggered_by',
            'last_triggered_at',
            'state_entities',
            'control_entities',
            'sensor_entities',
            'override_entities',
            'delay'

        ]
        for k,v in self.attributes.items():
            if k in PERSIST_STATE_ATTRIBUTES:
                att[k] = v


        self.attributes = att
        self.do_update()

    def do_update(self, wait=False,**kwargs):
        # self._state_attributes = kwargs


        # if 'reset_count' in kwargs:
        #     attributes["reset_count"] = kwargs.get('reset_count')
            
        # attributes["reset_at"] = self.model.reset_at
        # attributes["expires_at"] = self.model.expires_at
        # attributes["delay"] = self.model.delay
        

        # attributes["overridden_by"] = None
        # attributes["overridden_at"] = None
        
        # if 'last_triggered_by' in kwargs: attributes["last_triggered_by"] = kwargs.get('last_triggered_by')
        # if 'last_triggered_at' in kwargs: attributes["last_triggered_at"] = kwargs.get('last_triggered_at')

        # attributes["last_blocked_by"] = kwargs.get('last_blocked_by')
        # attributes["last_blocked_at"] = kwargs.get('last_blocked_at')

        # attributes["last_overridden_by"] = kwargs.get('last_overridden_by')
        # attributes["last_overridden_at"] = kwargs.get('last_overridden_at')

        # if 'control_entities' in kwargs:
        #     attributes["controlEntities"] = kwargs.get('control_entities')
        # if 'sensor_entities' in kwargs:
        #     attributes["sensorEntities"] = kwargs.get('sensor_entities')
        # if 'state_entities' in kwargs:
        #     attributes["state_entities"] = kwargs.get('state_entities')
        # if 'override_entities' in kwargs:
        #     attributes["overrideEntities"] = kwargs.get('override_entities')

        # _LOGGER.debug("state: " + str(attributes))


        if wait == False:
            self.async_schedule_update_ha_state(True)

    def set_attr(self, k, v):
        self.attributes[k] = v

class Model():
    """ Represents the transitions state machine model """

       
    def __init__(self, hass, config, entity):
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
        self.name = None
        self.machine = None
        self.delay = None
        self.stay = False
        self.start = None
        self.end = None
        self.reset_count = None
        self.log = logging.getLogger(__name__ + '.' + config.get('name'))
        self.log.setLevel(logging.DEBUG)
        self.log.debug("Init LightingSM with: " + str(config))
        self.name = config.get('name', 'Unnamed Motion Light')
        self.log.debug("Name: " + str(self.name))

        entity.machine.add_model(self) # add here because machine generated methods are being used in methods below.
        self.config_static_strings(config)
        self.config_state_entities(config)
        self.config_control_entities(config) # must come after config_state_entities
        self.config_sensor_entities(config)
        self.config_off_entities(config)
        self.config_normal_mode(config) 
        self.config_night_mode(config) #must come after normal_mode
        self.config_constrain_times(config)
        self.config_other(config)
        self.update(wait=True, 
            delay=self.light_params_day['delay'], 
            state_entities=self.stateEntities, 
            sensor_entities=self.sensorEntities,
            override_entities=self.overrideEntities,
            control_entities=self.controlEntities,

        )
        # def draw(self):
        #     self.update()
        #     if self.do_draw:
        #         self.log.debug("Updating graph in state: " + self.state)
        #         self.get_graph().draw(self.image_path + self.image_prefix + str(self.name)+'.png', prog='dot', format='png')

    def update(self, wait=False, reset=False, **kwargs):
        """ Called from different methods to report a state attribute change """
        for k,v in kwargs.items():
            if v is not None:
                self.entity.set_attr(k,v)
        
        self.entity.do_update(wait, **kwargs)

        # if delay == False:
        #     self.async_schedule_update_ha_state(True)
        # self.set_state("{}.{}".format(DOMAIN,str(self.name)), state=self.state, attributes=kwargs)

    def finalize(self):
        self.log.debug("state: " + self.state)
        self.update()

    # def clear_state_attributes(self):
    #     kwargs = {}
    #     kwargs["reset_count"] = None
    #     kwargs["reset_at"] = None
    #     kwargs["expires_at"] = None
    #     kwargs["delay"] = None
    #     kwargs["overridden_by"] = None
    #     kwargs["overridden_at"] = None
    #     kwargs["service_data"] = None
    #     self.update(**kwargs)

   
    # =====================================================
    # S T A T E   C H A N G E   C A L L B A C K S
    # =====================================================

    def sensor_state_change(self, entity, old, new):
        self.log.debug("Sensor state change: " + new.state)
        self.log.debug("state: " + self.state)

        if self.matches(new.state, self.SENSOR_ON_STATE):
            self.log.debug("matches on")
            self.update(last_triggered_by=entity)
            self.sensor_on()
        if self.matches(new.state, self.SENSOR_OFF_STATE) and self.sensor_type == SENSOR_TYPE_DURATION:
            self.log.debug("matches off")
            self.update(last_triggered_by=entity)
            # We only care about sensor off state changes when the sensor is a duration sensor.
            self.sensor_off_duration()
                


    def override_state_change(self, entity, old, new):
        self.log.debug("Override state change")
        if self.matches(new.state, self.OVERRIDE_ON_STATE):
            self.update(overridden_by=entity)
            self.override()
            self.update(overridden_at=str(datetime.now()))
        if self.matches(new.state, self.OVERRIDE_OFF_STATE) and not self._override_entity_state():
            self.enable()


    def control_state_change(self, entity, old, new):
        self.log.debug(self.is_active())
        if self.is_active():
            self.control()

        if self.is_blocked() and self.is_state_entities_off:
            self.enable()

    def time_event_handler(self, event):
        self.log.debug("Time event: " + str(event))


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
            self.update(backoff_delay=self.previous_delay)

        self.timer_handle = Timer(self.previous_delay, self.timer_expire)
        self.log.debug("Delay: " + str(self.previous_delay))
        self.timer_handle.start()
        expiry_time = str(datetime.now() + timedelta(seconds=self.previous_delay))
        self.update(expires_at=expiry_time)
    
    def _cancel_timer(self):
        if self.timer_handle.is_alive():
            self.timer_handle.cancel()

    def _reset_timer(self):
        self.log.debug("Resetting timer" + str(self.backoff))
        self._cancel_timer()
        self.update(reset_at=str(datetime.now()))
        if self.backoff:
            self.log.debug("inc backoff")
            self.backoff_count += 1
            self.update(backoff_count=self.backoff_count)
        self._start_timer()
        # self.log.debug(str(self.timer_handle))
        return True

       

    # =====================================================
    # S T A T E   M A C H I N E   C O N D I T I O N S
    # =====================================================
    def _override_entity_state(self):
        for e in self.overrideEntities:
            s = self.hass.states.get(e)
            self.log.debug(" * State of {} is {}".format(e, s.state))
            if self.matches(s.state, self.OVERRIDE_ON_STATE):
                self.log.debug("Override entities are ON. [{}]".format(e))
                return True
        self.log.debug("Override entities are OFF.")
        return False

    def _sensor_entity_state(self):
        for e in self.sensorEntities:
            s = self.hass.states.get(e)
            self.log.debug(" * State of {} is {}".format(e, s.state))
            if self.matches(s.state, self.SENSOR_ON_STATE):
                self.log.debug("Sensor entities are ON. [{}]".format(e))
                return True
        self.log.debug("Sensor entities are OFF.")
        return False

    def is_sensor_off(self):
        return self._sensor_entity_state() == False

    def is_sensor_on(self):
        return self._sensor_entity_state()
        
    def _state_entity_state(self):
        for e in self.stateEntities:
            s = self.hass.states.get(e)
            self.log.info(s)
            self.log.debug(" * State of {} is {}".format(e, s.state))
            if self.matches(s.state, self.STATE_ON_STATE):
                self.log.debug("State entities are ON. [{}]".format(e))
                return True
        self.log.debug("State entities are OFF.")
        return False
    
    def is_state_entities_off(self):
        return self._state_entity_state() == False

    def is_state_entities_on(self):
        return self._state_entity_state()
    
    def will_stay_on(self):
        return self.stay

    def is_night(self):
        if self.night_mode is None:
            self.log.debug("(night mode disabled): " + str(self.night_mode))
            self.update(night_mode='on')
            return False
        else:
            self.update(night_mode='off')
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
    
    def timer_expire(self):
        # self.log.debug("Timer expired")
        if self.is_duration_sensor():
            self.log.debug("It's a DURATION sensor")
            if self.is_sensor_off():
                self.log.debug("Sensor entities are OFF.")
                self.timer_expires()
        else:    
            self.timer_expires()


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
        if self.is_night():
            self.log.debug("Using NIGHT MODE parameters: " + str(self.light_params_night))
            self.lightParams = self.light_params_night
        else:
            self.log.debug("Using DAY MODE parameters: " + str(self.light_params_day))
            self.lightParams = self.light_params_day

        
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

        if len(self.offEntities) > 0:
            self.log.info("Turning on special off_entities that were defined, instead of turning off the regular control_entities")
            for e in self.offEntities: 
                self.log.debug("Turning on {}".format(e))
                self.call_service(e, 'turn_on')
        else:
            for e in self.controlEntities:
                self.log.debug("Turning off {}".format(e))
                self.call_service(e, 'turn_off')


    
    # =====================================================
    #    C O N F I G U R A T I O N  &  V A L I D A T I O N
    # =====================================================



    def config_control_entities(self, config):
    
        self.log.debug("Setting up control entities")
        self.controlEntities = []

        if "entity" in config:
            self.controlEntities.append( config["entity"])

        if "entities" in config: 
            self.controlEntities.extend( config['entities'])

        if "entity_on" in config: 
            self.controlEntities.append( config["entity_on"] )


        for control in self.controlEntities:
          self.log.debug("Registering control: " + str(control))
          event.async_track_state_change(self.hass, control, self.control_state_change)

        # If no state entities are defined, use control entites as state
        if len(self.stateEntities) == 0:
            self.stateEntities.extend(self.controlEntities)
            self.log.debug("Added Control Entities as state entities: " + str(self.stateEntities))
        else:
            self.log.debug("Using existing state entities: " + str(self.stateEntities))
        self.log.debug("Control Entities: " + str(self.controlEntities))


    def config_state_entities(self, config):
        self.stateEntities = []
        self.log.info("Setting up state entities")
        if config.get('state_entities',False):
            self.log.debug("State entitity config defined")
            self.stateEntities.extend(config.get('state_entities',[]))
            #self.update(state_entities=self.stateEntities, delay=True)
            self.log.info("State Entities: " + str(self.stateEntities))

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
            self.log.debug("No sensor specified, doing nothing")

        self.log.debug("Sensor Entities: " + str(self.sensorEntities))
        #self.update(sensor_entities=self.sensorEntities)

        for sensor in self.sensorEntities:
            self.log.debug("Registering sensor: " + str(sensor))
            event.async_track_state_change(self.hass, sensor, self.sensor_state_change)

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

    

    def matches(self, value, list):
        """
            Checks whether a string is contained in a list (used for matching state strings)
        """
        try:
            index = list.index(value)
            return True
        except ValueError:
            return False

    def config_night_mode(self, config):
        """
            Configured night mode parameters. If no night_mode service parameters are given, the day mode parameters are used instead. If those do not exist, the 
        """
        if "night_mode" in config:
            self.night_mode = config["night_mode"]
            night_mode = config["night_mode"]
            self.log.info(night_mode)
            self.light_params_night['delay'] = night_mode.get('delay',config.get("delay", DEFAULT_DELAY))
            self.light_params_night['service_data'] = night_mode.get('service_data',self.light_params_day.get('service_data'))
            self.log.info(self.light_params_night)
            if not "start_time" in night_mode:
                self.log.debug("Night mode requires a start_time parameter !")

            if not "end_time" in night_mode:
                self.log.debug("Night mode requires a end_time parameter !")
            
    def config_normal_mode(self, config):
        params = {}
        params['delay'] = config.get("delay", DEFAULT_DELAY)
        params['service_data'] = config.get("service_data", None)
        self.log.info("serivce data set up: " + str(config))
        self.light_params_day = params

    def config_constrain_times(self, config):
        start = dt.parse_time(config.get('start_time'))
        end = dt.parse_time(config.get('end_time'))
        self.log.debug("SEtting time callbacks  " + str(start) + "   " + str(end))
        if end and start:
            self.start = start # Time object
            self.end = end # Time object
            # self.end = datetime.time(datetime.utcnow()+timedelta(seconds=5))
            s = self.if_time_passed_get_tomorrow(start)
            e = self.if_time_passed_get_tomorrow(end)
            # e = dt.now()+timedelta(seconds=5)#datetime.datetime(end)
            self.log.debug(type(self.end))
            self.log.debug("Setting time callbacks")
            self.log.debug("Constrain end callback for : " + str(s))
            self.log.debug("Constrain start callback for : " + str(e))
            self.constrain_end_hook = event.async_track_point_in_time(self.hass, self.constrain_end, s) # dt.now()+timedelta(seconds=3)) # s
            self.constrain_start_hook = event.async_track_point_in_time(self.hass, self.constrain_start, e) # dt.now()+timedelta(seconds=1)) # e
            if not self.now_is_between(start, end):
                self.log.debug("Constrain period active. Scheduling transition to 'constrained'")
                event.async_call_later(self.hass, 1, self.constrain_fake)

    
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
   

        self.overrideEntities = []
        if 'override' in config:
            self.overrideEntities.append(config.get('override'))

        if 'overrides' in config:
            self.overrideEntities.extend(config.get('overrides'))

        self.log.debug("Override Entities: " + str(self.overrideEntities))
        if len(self.overrideEntities) > 0:
            for e in self.overrideEntities:
                self.log.info("Setting override callback/s: " + str(e))
                event.async_track_state_change(self.hass, e, self.override_state_change)
                # self.listen_state(self.override_state_change, e)
        if config.get("sensor_type_duration"):
            self.sensor_type = SENSOR_TYPE_DURATION
        else:
            self.sensor_type = SENSOR_TYPE_EVENT
        
# =====================================================
#    E V E N T   C A L L B A C K S
# =====================================================

    def constrain_fake(self, evt):
        self.constrain()
        
    def constrain_start(self, evt):
        self.log.debug("Constrain Start reached. Disabling ML: " + str(evt))
        self.constrain()
        time = datetime.combine(datetime.today(), self.end) + timedelta(hours=24)
        # time = datetime.now() + timedelta(seconds=5)
        self.log.debug("setting new callback in 24h" + str(time))
        event.async_track_point_in_time(self.hass, self.constrain_start, time)

    def constrain_end(self, evt):
        self.log.debug("Constrain End reached. Enabling ML: " + str(evt))
        self.enable()
        time = datetime.combine(datetime.today(), self.end) + timedelta(hours=24)
        # time = datetime.now() + timedelta(seconds=5)
        self.log.debug("setting new callback in 24h" + str(time))
        event.async_track_point_in_time(self.hass, self.constrain_end, time)
        
    # def block_poll(self, evt):
    #     """ When in blocked state, we will poll `is_state_entities_off` periodically. If i"""
    #     self.log.debug("Constrain End reached. Enabling ML: " + str(evt))
    #     self.enable()
    #     # time = datetime.combine(datetime.today(),self.end) + timedelta(seconds=5)
    #     time = datetime.now() + timedelta(seconds=5)
    #     self.log.debug("setting new callback in 24h" + str(time))
    #     event.async_track_point_in_time(self.hass, self.constrain_end, time)
        
# =====================================================
#    H E L P E R   F U N C T I O N S
# =====================================================
    def if_time_passed_get_tomorrow(self, time):
        """ Returns tomorrows time if time is in the past """
        today = date.today()
        t = datetime.combine(today, time)
        x = datetime.combine(today, datetime.time(datetime.now()))
        self.log.debug("if_time_passed --- input time: " + str(t))
        self.log.debug("if_time_passed --- current time: " + str(x))
        if t <= x:
            t += timedelta(1) # tomorrow!
            self.log.debug("if_time_passed --- Time already happened. Returning tomorrow instead. " + str(t))
        else:
            self.log.debug("if_time_passed --- Time still happening today. " + str(t))

        return t

    def now_is_between(self, start, end, x=datetime.time(datetime.now())):
        today = date.today()
        start = datetime.combine(today, start)
        end = datetime.combine(today, end)
        x = datetime.combine(today, x)
        if end <= start:
            end += timedelta(1) # tomorrow!
        if x <= start:
            x += timedelta(1) # tomorrow!
        return start <= x <= end

    def call_service(self, entity, service, **kwargs):
        """ Helper for calling HA services with the correct parameters """
        domain, e = entity.split('.')
        params = {}
        if kwargs is not None:
            params = kwargs

        params['entity_id'] = entity

        self.hass.services.call(domain, service, kwargs)
        self.update(service_data=kwargs)